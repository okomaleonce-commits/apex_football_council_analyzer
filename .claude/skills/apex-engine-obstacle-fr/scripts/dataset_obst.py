"""Assemblage du jeu de donnees obstacle."""
import json
import features_obst as F
import longitudinal_obst as L

ALL_FEATS = None

def load(path):
    raw = []
    for line in open(path):
        line = line.strip()
        if not line: continue
        try: c = json.loads(line)
        except json.JSONDecodeError: continue
        if c.get('arrivee'): raw.append(c)
    raw.sort(key=lambda c: (c['date'], c['reunion'], c['course']))
    return raw

def set_fall_codes(raw):
    """Un partant qui n'a pas de rang d'arrivee et porte un incident n'a pas
    termine. On en deduit l'ensemble des codes de non-terminaison."""
    from collections import Counter
    cnt = Counter()
    for c in raw:
        for p in c['partants']:
            if p.get('statut') != 'PARTANT': continue
            if p.get('ordreArrivee'): continue
            if p.get('incident'): cnt[p['incident']] += 1
    codes = {k for k in cnt if k != 'NON_PARTANT'}
    L.FALL_INC = codes
    return cnt, codes

def build(path, burn_days=270, min_runners=5):
    global ALL_FEATS
    raw = load(path)
    if not raw: return [], []
    set_fall_codes(raw)
    d0 = L.dkey(raw[0]['date']); st = L.State(); races = []
    for c in raw:
        d = L.dkey(c['date'])
        field = [p for p in c['partants']
                 if p.get('statut') == 'PARTANT' and p.get('incident') != 'NON_PARTANT']
        ok = (len(field) >= min_runners and (d - d0).days >= burn_days
              and all(p.get('coteFinale') for p in field)
              and sum(1 for p in field if p.get('ordreArrivee') == 1) == 1)
        if ok:
            rows = []
            for p in field:
                r = F.runner_features(p, c, field)
                r.update(st.feats(p, c, d))
                rows.append(r)
            if ALL_FEATS is None: ALL_FEATS = sorted(rows[0].keys())
            races.append(dict(
                date=c['date'], hippo=c['hippo'], discipline=c['discipline'],
                distance=c['distance'], prix=c['montantPrix'], part=c['particularite'],
                n=len(field),
                X=[[r[k] for k in ALL_FEATS] for r in rows],
                y_win=[1 if p.get('ordreArrivee') == 1 else 0 for p in field],
                y_place=[1 if (p.get('ordreArrivee') and p['ordreArrivee'] <= 3) else 0
                         for p in field],
                y_fault=[1 if L.is_fall(p.get('incident')) else 0 for p in field],
                odds=[p['coteFinale'] for p in field],
                nums=[p['numPmu'] for p in field],
                noms=[p['nom'] for p in field]))
        st.update(c, d)
    return races, ALL_FEATS

def live_state(path, upto=None):
    raw = load(path)
    set_fall_codes(raw)
    st = L.State()
    for c in raw:
        if upto and c['date'] >= upto: break
        st.update(c, L.dkey(c['date']))
    return st
