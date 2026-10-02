"""Preuves des trois garanties du registre WORM. Aucune n'est declarative."""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worm import Worm, WormError

ok = fail = 0
def check(label, cond, detail=''):
    global ok, fail
    if cond: ok += 1;   print(f"  OK   {label}")
    else:    fail += 1; print(f"  ECHEC {label} {detail}")

def tmp():
    return os.path.join(tempfile.mkdtemp(), 'ledger.jsonl')

PREV = dict(course='26092026-R4C6', kind='prevision', moteur='trot',
            empreinte='6c13785d', partants=[dict(num=8, p_win=0.151)])
RES  = dict(course='26092026-R4C6', kind='resultat', arrivee=[8, 4, 5])

print("\n1. CHAINAGE — une modification apres coup est detectee")
p = tmp(); w = Worm(p)
w.append(dict(PREV)); w.append(dict(RES))
check("chaine intacte apres 2 ecritures", w.verify()[0])
rows = [json.loads(l) for l in open(p) if l.strip()]
rows[0]['payload']['partants'][0]['p_win'] = 0.99        # on truque la prevision
open(p, 'w').write('\n'.join(json.dumps(r, sort_keys=True, separators=(',', ':')) for r in rows) + '\n')
good, info = w.verify()
check("falsification du contenu detectee", not good, info)
check("le message nomme l'enregistrement 0", not good and 'enregistrement 0' in info, info)

print("\n2. CHAINAGE — une suppression de ligne est detectee")
p = tmp(); w = Worm(p)
for i in range(4): w.append(dict(PREV, course=f'c{i}'))
rows = [l for l in open(p) if l.strip()]
open(p, 'w').writelines(rows[:1] + rows[2:])             # on retire la ligne 1
good, info = w.verify()
check("suppression detectee", not good, info)

print("\n3. ANTERIORITE — on ne peut pas predire apres l'arrivee")
p = tmp(); w = Worm(p)
w.append(dict(RES))
try:
    w.append(dict(PREV)); check("prevision post-resultat refusee", False, "elle a ete acceptee")
except WormError as e:
    check("prevision post-resultat refusee", True)
    check("le refus dit pourquoi", 'resultat est deja scelle' in str(e), str(e))

print("\n4. ANTERIORITE — une autre course n'est pas bloquee")
try:
    w.append(dict(PREV, course='autre-course'))
    check("course differente acceptee", True)
except WormError as e:
    check("course differente acceptee", False, str(e))

print("\n5. NON-EFFACEMENT — la correction s'ajoute et cite sa cible")
p = tmp(); w = Worm(p)
r0 = w.append(dict(PREV))
try:
    w.append(dict(course=PREV['course'], kind='correction'))
    check("correction sans motif refusee", False, "acceptee")
except WormError:
    check("correction sans motif refusee", True)
try:
    w.append(dict(course=PREV['course'], kind='correction', corrige_seq=99, motif='x'))
    check("correction d'une cible inexistante refusee", False, "acceptee")
except WormError:
    check("correction d'une cible inexistante refusee", True)
r1 = w.append(dict(course=PREV['course'], kind='correction', corrige_seq=r0['seq'],
                   motif='regle top 3 dependante de la discipline'))
check("correction acceptee avec motif et cible", r1['seq'] == 1)
hist = w.course(PREV['course'])
check("les deux versions restent lisibles", len(hist) == 2 and hist[0]['hash'] == r0['hash'])
check("l'original n'a pas bouge", hist[0]['payload']['partants'][0]['p_win'] == 0.151)

print("\n6. REFUS D'EMPILER SUR UN REGISTRE CORROMPU")
p = tmp(); w = Worm(p)
w.append(dict(PREV))
rows = [json.loads(l) for l in open(p) if l.strip()]
rows[0]['payload']['empreinte'] = 'truque'
open(p, 'w').write(json.dumps(rows[0], sort_keys=True, separators=(',', ':')) + '\n')
try:
    w.append(dict(RES)); check("ecriture sur chaine rompue refusee", False, "acceptee")
except WormError as e:
    check("ecriture sur chaine rompue refusee", True)
    check("la corruption ne peut pas etre enterree", 'corrompu' in str(e), str(e))

print("\n7. GARDE-FOUS DE FORME")
p = tmp(); w = Worm(p)
for bad, lab in [(dict(course='x'), "payload sans kind"),
                 (dict(course='x', kind='inconnu'), "kind hors liste")]:
    try:
        w.append(bad); check(f"{lab} refuse", False, "accepte")
    except WormError:
        check(f"{lab} refuse", True)

print("\n8. ORDRE ET NUMEROTATION STRICTS")
p = tmp(); w = Worm(p)
seqs = [w.append(dict(PREV, course=f'c{i}'))['seq'] for i in range(5)]
check("seq strictement croissant depuis 0", seqs == [0, 1, 2, 3, 4], seqs)
good, n = w.verify()
check("verify compte les 5", good and n == 5, n)

print(f"\n{'='*52}\n{ok} reussis, {fail} echoues\n{'='*52}")
sys.exit(1 if fail else 0)
