"""Construction des variables APEX-TROT a partir de l'historique PMU brut."""
import json, re, math

MUS_TOKEN = re.compile(r'\((\d{2})\)|([0-9DATRAO])([a-z])')
FAULT_CODES = {'D', 'A', 'T', 'R'}

def parse_musique(m):
    """Renvoie la liste des dernieres performances, la plus recente en premier.
    Chaque element: (valeur, discipline). valeur = 0..9 ou code de faute."""
    out = []
    if not m: return out
    for yr, val, disc in MUS_TOKEN.findall(m):
        if yr: continue
        out.append((val, disc))
    return out

def musique_features(m):
    perf = parse_musique(m)
    f = {}
    n = len(perf)
    if n == 0:
        return dict(mus_n=0, mus_win=0.0, mus_top3=0.0, mus_fault=0.0,
                    mus_score=0.0, mus_recent=0.0, mus_trot=1.0)
    vals = [v for v, d in perf]
    f['mus_n'] = n
    f['mus_win'] = sum(v == '1' for v in vals) / n
    f['mus_top3'] = sum(v in '123' for v in vals) / n
    f['mus_fault'] = sum(v in FAULT_CODES for v in vals) / n
    # score pondere par recence : poids geometrique 0.85
    pts = {'1': 1.0, '2': 0.72, '3': 0.55, '4': 0.40, '5': 0.30,
           '6': 0.20, '7': 0.14, '8': 0.10, '9': 0.07, '0': 0.03}
    num = den = 0.0
    for i, v in enumerate(vals):
        w = 0.85 ** i
        num += w * pts.get(v, 0.0); den += w
    f['mus_score'] = num / den
    # 3 dernieres sorties seulement
    r = vals[:3]
    f['mus_recent'] = sum(pts.get(v, 0.0) for v in r) / len(r)
    f['mus_trot'] = sum(d == 'a' for v, d in perf) / n
    return f

DEF_MAP = {
    'DEFERRE_ANTERIEURS_POSTERIEURS': 'def4',
    'DEFERRE_POSTERIEURS': 'defpost',
    'DEFERRE_ANTERIEURS': 'defant',
    'PROTEGE_ANTERIEURS_DEFERRRE_POSTERIEURS': 'defpost',
    'DEFERRE_ANTERIEURS_PROTEGE_POSTERIEURS': 'defant',
}

def runner_features(p, course, field):
    g = p.get('gains') or {}
    car = (g.get('gainsCarriere') or 0) / 100.0
    ann = (g.get('gainsAnneeEnCours') or 0) / 100.0
    nc = p.get('nombreCourses') or 0
    nv = p.get('nombreVictoires') or 0
    npl = p.get('nombrePlaces') or 0
    f = {}
    f.update(musique_features(p.get('musique')))
    f['log_gains_par_course'] = math.log1p(car / max(nc, 1))
    f['log_gains_annee'] = math.log1p(ann)
    f['log_gains_car'] = math.log1p(car)
    f['win_rate'] = nv / nc if nc else 0.0
    f['place_rate'] = npl / nc if nc else 0.0
    f['log_experience'] = math.log1p(nc)
    f['age'] = p.get('age') or 6
    f['femelle'] = 1.0 if p.get('sexe') == 'JUMENTS' else 0.0
    f['male_entier'] = 1.0 if p.get('sexe') == 'MALES' else 0.0
    hd = p.get('handicapDistance') or course.get('distance') or 0
    base = min(x.get('handicapDistance') or 0 for x in field) or hd
    f['recul_m'] = (hd - base) if hd and base else 0.0
    f['recul_pct'] = f['recul_m'] / max(hd, 1) * 100.0
    d = DEF_MAP.get(p.get('deferre') or '', 'ferre')
    for k in ('def4', 'defpost', 'defant'):
        f[k] = 1.0 if d == k else 0.0
    f['avis_pos'] = 1.0 if p.get('avisEntraineur') == 'POSITIF' else 0.0
    f['avis_neg'] = 1.0 if p.get('avisEntraineur') == 'NEGATIF' else 0.0
    f['driver_change'] = 1.0 if p.get('driverChange') else 0.0
    f['inedit'] = 1.0 if p.get('indicateurInedit') else 0.0
    f['supplement'] = 1.0 if (p.get('supplement') or 0) > 0 else 0.0
    corde = p.get('placeCorde')
    f['corde'] = float(corde) if corde else 0.0
    f['has_corde'] = 1.0 if corde else 0.0
    f['monte'] = 1.0 if course.get('discipline') == 'MONTE' else 0.0
    return f

FEATS = None

def build(path, min_runners=6):
    """Charge le JSONL et renvoie (races, noms des variables)."""
    global FEATS
    races = []
    for line in open(path):
        line = line.strip()
        if not line: continue
        try: c = json.loads(line)
        except json.JSONDecodeError: continue
        field = [p for p in c['partants']
                 if p.get('statut') == 'PARTANT' and p.get('incident') != 'NON_PARTANT']
        if len(field) < min_runners: continue
        if not c.get('arrivee'): continue
        rows, y_win, y_fault, y_place, odds = [], [], [], [], []
        ok = True
        for p in field:
            if not p.get('coteFinale'): ok = False; break
            rows.append(runner_features(p, c, field))
            arr = p.get('ordreArrivee')
            y_win.append(1 if arr == 1 else 0)
            y_place.append(1 if (arr and arr <= 3) else 0)
            y_fault.append(1 if (p.get('incident') or '') in
                           ('DISQUALIFIE_POUR_ALLURE_IRREGULIERE', 'DISQUALIFIE_POTEAU_GALOP',
                            'TOMBE', 'ARRETE', 'DISTANCE') else 0)
            odds.append(p['coteFinale'])
        if not ok or sum(y_win) != 1: continue
        if FEATS is None: FEATS = sorted(rows[0].keys())
        races.append(dict(date=c['date'], hippo=c['hippo'], discipline=c['discipline'],
                          distance=c['distance'], prix=c['montantPrix'],
                          part=c['particularite'], n=len(field),
                          X=[[r[k] for k in FEATS] for r in rows],
                          y_win=y_win, y_place=y_place, y_fault=y_fault, odds=odds,
                          nums=[p['numPmu'] for p in field],
                          noms=[p['nom'] for p in field]))
    return races, FEATS
