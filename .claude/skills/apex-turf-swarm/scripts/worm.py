"""
APEX-TURF WORM — registre scelle en ecriture unique (Write Once, Read Many).

Ce fichier est la couche de tracabilite du swarm turf. Il n'analyse rien.
Son unique role est de rendre une prevision INFALSIFIABLE APRES COUP.

Trois garanties, chacune testable :

  1. CHAINAGE   chaque enregistrement porte le hash du precedent. Modifier
                une ligne ancienne casse la chaine a partir de ce point, et
                verify() dit exactement ou.
  2. ANTERIORITE  une prevision ne peut pas etre scellee pour une course dont
                un resultat est deja au registre. C'est le garde-fou contre
                la prevision ecrite apres l'arrivee.
  3. NON-EFFACEMENT  rien n'est jamais reecrit. Une correction s'ajoute et
                cite l'enregistrement qu'elle corrige ; les deux restent
                lisibles cote a cote.

Le format est du JSONL : une ligne = un enregistrement, append-only.
"""
import json, hashlib, os, datetime, fcntl

GENESIS = '0' * 64


def _canon(obj):
    """Serialisation canonique : le hash ne doit pas dependre de l'ordre des cles."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _digest(seq, ts, prev, payload):
    return hashlib.sha256(
        f"{seq}|{ts}|{prev}|{_canon(payload)}".encode('utf-8')
    ).hexdigest()


class WormError(Exception):
    """Toute violation d'une des trois garanties. Jamais rattrapee silencieusement."""


class Worm:
    def __init__(self, path):
        self.path = path
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)

    # ------------------------------------------------------------ lecture

    def records(self):
        """Tous les enregistrements, dans l'ordre d'ecriture. Lignes vides ignorees."""
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, encoding='utf-8') as f:
            for ln, raw in enumerate(f, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    out.append(json.loads(raw))
                except json.JSONDecodeError as e:
                    raise WormError(f"ligne {ln} illisible : {e}") from None
        return out

    def verify(self):
        """
        Rejoue la chaine. Retourne (True, n) si intacte, sinon (False, message)
        nommant le premier enregistrement en defaut.
        """
        prev = GENESIS
        last_ts = ''
        for i, r in enumerate(self.records()):
            for k in ('seq', 'ts', 'prev_hash', 'hash', 'payload'):
                if k not in r:
                    return False, f"enregistrement {i} : champ '{k}' absent"
            if r['seq'] != i:
                return False, f"enregistrement {i} : seq={r['seq']}, rupture de numerotation"
            if r['prev_hash'] != prev:
                return False, (f"enregistrement {i} : prev_hash ne correspond pas au "
                               f"hash de {i - 1} — insertion ou suppression")
            exp = _digest(r['seq'], r['ts'], r['prev_hash'], r['payload'])
            if r['hash'] != exp:
                return False, (f"enregistrement {i} : contenu modifie apres coup "
                               f"(hash attendu {exp[:16]}…, trouve {r['hash'][:16]}…)")
            if r['ts'] < last_ts:
                return False, (f"enregistrement {i} : horodatage {r['ts']} anterieur "
                               f"a {last_ts} — antidatage")
            last_ts = r['ts']
            prev = r['hash']
        return True, len(self.records())

    def course(self, course_id):
        """Tout ce que le registre sait d'une course, dans l'ordre."""
        return [r for r in self.records() if r['payload'].get('course') == course_id]

    # ------------------------------------------------------------ ecriture

    def append(self, payload, kind=None):
        """
        Ajoute un enregistrement. Verifie la chaine AVANT d'ecrire : on n'empile
        jamais sur un registre deja corrompu, sinon la corruption devient
        indetectable sous une couche de hashes valides.
        """
        if kind:
            payload = dict(payload, kind=kind)
        if 'kind' not in payload:
            raise WormError("payload sans champ 'kind'")
        k = payload['kind']
        if k not in ('prevision', 'resultat', 'correction', 'audit', 'note'):
            raise WormError(f"kind inconnu : {k}")

        with open(self.path, 'a+', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)          # deux agents du swarm peuvent sceller
            try:
                ok, info = self.verify()
                if not ok:
                    raise WormError(f"registre corrompu, ecriture refusee : {info}")
                recs = self.records()

                cid = payload.get('course')
                if k == 'prevision' and cid:
                    # garde-fou d'anteriorite : la raison d'etre de ce fichier
                    for r in recs:
                        if (r['payload'].get('course') == cid
                                and r['payload']['kind'] == 'resultat'):
                            raise WormError(
                                f"REFUS : un resultat est deja scelle pour {cid} "
                                f"(enregistrement {r['seq']}). Une prevision posterieure "
                                f"a l'arrivee n'est pas une prevision.")
                if k == 'correction':
                    tgt = payload.get('corrige_seq')
                    if tgt is None:
                        raise WormError("une correction doit citer 'corrige_seq'")
                    if not any(r['seq'] == tgt for r in recs):
                        raise WormError(f"correction d'un enregistrement inexistant : {tgt}")
                    if not payload.get('motif'):
                        raise WormError("une correction doit porter un 'motif'")

                seq = len(recs)
                prev = recs[-1]['hash'] if recs else GENESIS
                ts = datetime.datetime.now(datetime.timezone.utc).isoformat(
                    timespec='seconds').replace('+00:00', 'Z')
                if recs and ts < recs[-1]['ts']:
                    ts = recs[-1]['ts']            # horloge qui recule : on ne recule pas
                rec = dict(seq=seq, ts=ts, prev_hash=prev, payload=payload,
                           hash=_digest(seq, ts, prev, payload))
                f.write(_canon(rec) + '\n')
                f.flush()
                os.fsync(f.fileno())
                return rec
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)


# ------------------------------------------------------------------ CLI

def _main(argv):
    import sys
    if len(argv) < 2:
        print(__doc__)
        print("usage: worm.py verify <registre>")
        print("       worm.py course <registre> <course_id>")
        print("       worm.py seal   <registre> <fichier.json> <kind>")
        return 2
    cmd, path = argv[0], argv[1]
    w = Worm(path)
    if cmd == 'verify':
        ok, info = w.verify()
        print(f"chaine {'INTACTE' if ok else 'ROMPUE'} — {info}"
              + (f" enregistrement(s)" if ok else ""))
        return 0 if ok else 1
    if cmd == 'course':
        for r in w.course(argv[2]):
            p = r['payload']
            print(f"  [{r['seq']:>3}] {r['ts']} {p['kind']:<10} {r['hash'][:12]}…"
                  + (f" corrige {p['corrige_seq']}" if p.get('corrige_seq') is not None else ""))
        return 0
    if cmd == 'seal':
        payload = json.load(open(argv[2], encoding='utf-8'))
        rec = w.append(payload, kind=argv[3])
        print(f"scelle seq={rec['seq']} hash={rec['hash'][:16]}… ts={rec['ts']}")
        return 0
    print(f"commande inconnue : {cmd}")
    return 2


if __name__ == '__main__':
    import sys
    sys.exit(_main(sys.argv[1:]))
