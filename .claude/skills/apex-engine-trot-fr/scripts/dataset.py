"""Assemble le jeu de donnees APEX-TROT : variables statiques + longitudinales,
en ordre chronologique, avec periode de chauffe pour laisser l'historique se remplir."""
import json, datetime
import features as F
import longitudinal as L

ALL_FEATS = None

def build(path, burn_days=180, min_runners=6):
    global ALL_FEATS
    raw = []
    for line in open(path):
        line = line.strip()
        if not line: continue
        try: c = json.loads(line)
        except json.JSONDecodeError: continue
        if c.get('arrivee'): raw.append(c)
    raw.sort(key=lambda c: (c['date'], c['reunion'], c['course']))
    if not raw: return [], []
    d0 = L.dkey(raw[0]['date'])
    st = L.State()
    races = []
    for c in raw:
        d = L.dkey(c['date'])
        field = [p for p in c['partants']
                 if p.get('statut') == 'PARTANT' and p.get('incident') != 'NON_PARTANT']
        usable = (len(field) >= min_runners and (d - d0).days >= burn_days
                  and all(p.get('coteFinale') for p in field)
                  and sum(1 for p in field if p.get('ordreArrivee') == 1) == 1)
        if usable:
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
                y_fault=[1 if ((p.get('incident') or '').startswith('DISQUALIFIE')
                               or (p.get('incident') or '') in ('TOMBE','ARRETE','DISTANCE'))
                         else 0 for p in field],
                odds=[p['coteFinale'] for p in field],
                nums=[p['numPmu'] for p in field],
                noms=[p['nom'] for p in field]))
        st.update(c, d)
    return races, ALL_FEATS

def live_state(path, upto=None):
    """Rejoue tout l'historique pour obtenir l'etat courant (pour une course a venir)."""
    raw = []
    for line in open(path):
        line = line.strip()
        if not line: continue
        try: c = json.loads(line)
        except json.JSONDecodeError: continue
        if c.get('arrivee'): raw.append(c)
    raw.sort(key=lambda c: (c['date'], c['reunion'], c['course']))
    st = L.State()
    for c in raw:
        if upto and c['date'] >= upto: break
        st.update(c, L.dkey(c['date']))
    return st
