"""Variables statiques APEX-OBSTACLE : poids, valeur handicap, reclamation, musique
d'obstacle. Rien de commun avec le trot hormis la structure du code."""
import re, math

MUS = re.compile(r'\((\d{2})\)|([0-9A-Z])([a-z])')
# codes de non-terminaison en obstacle
FALL_CODES = {'T', 'A', 'D', 'R', 'J'}   # J = jockey desarconne : non-terminaison
OBST_DISC = {'h', 's', 'c'}          # haies, steeple, cross
PTS = {'1': 1.0, '2': .72, '3': .55, '4': .40, '5': .30,
       '6': .20, '7': .14, '8': .10, '9': .07, '0': .03}

def parse_musique(m):
    if not m: return []
    return [(v, d) for yr, v, d in MUS.findall(m) if not yr]

def musique_features(m):
    perf = parse_musique(m)
    n = len(perf)
    if n == 0:
        return dict(mus_n=0.0, mus_win=0.09, mus_top3=0.28, mus_fall=0.15,
                    mus_score=0.25, mus_recent=0.25, mus_obst=1.0, mus_plat=0.0)
    vals = [v for v, d in perf]
    num = den = 0.0
    for i, v in enumerate(vals):
        w = 0.85 ** i
        num += w * PTS.get(v, 0.0); den += w
    r = vals[:3]
    return dict(
        mus_n=float(n),
        mus_win=sum(v == '1' for v in vals) / n,
        mus_top3=sum(v in '123' for v in vals) / n,
        mus_fall=sum(v in FALL_CODES for v in vals) / n,
        mus_score=num / den,
        mus_recent=sum(PTS.get(v, 0.0) for v in r) / len(r),
        mus_obst=sum(d in OBST_DISC for v, d in perf) / n,
        mus_plat=sum(d == 'p' for v, d in perf) / n,
    )

def runner_features(p, course, field):
    g = p.get('gains') or {}
    car = (g.get('gainsCarriere') or 0) / 100.0
    ann = (g.get('gainsAnneeEnCours') or 0) / 100.0
    nc = p.get('nombreCourses') or 0
    nv = p.get('nombreVictoires') or 0
    npl = p.get('nombrePlaces') or 0
    f = {}
    f.update(musique_features(p.get('musique')))

    # --- poids porte : la variable structurante de l'obstacle ---
    def w(x):
        v = x.get('handicapPoids') or x.get('poidsConditionMonte')
        return (v / 10.0) if v else None
    me = w(p)
    ws = [w(x) for x in field if w(x)]
    lo = min(ws) if ws else None
    mean = (sum(ws) / len(ws)) if ws else None
    f['poids'] = me if me else (mean or 68.0)
    f['poids_rel'] = (me - lo) if (me and lo) else 0.0            # kg au-dessus du plus leger
    f['poids_ecart_moy'] = (me - mean) if (me and mean) else 0.0

    # --- valeur handicap officielle (absente hors handicaps) ---
    def hv(x):
        v = x.get('handicapValeur')
        return v / 10.0 if v else None
    vm = hv(p)
    vs = [hv(x) for x in field if hv(x)]
    f['has_valeur'] = 1.0 if vm else 0.0
    f['valeur_rel'] = (vm - sum(vs) / len(vs)) if (vm and vs) else 0.0

    # --- prix de reclamation (courses a reclamer) ---
    def tr(x):
        v = x.get('tauxReclamation')
        return math.log(v / 100.0) if v else None
    rm = tr(p); rs = [tr(x) for x in field if tr(x)]
    f['has_reclam'] = 1.0 if rm else 0.0
    f['reclam_rel'] = (rm - sum(rs) / len(rs)) if (rm and rs) else 0.0

    f['log_gains_par_course'] = math.log1p(car / max(nc, 1))
    f['log_gains_annee'] = math.log1p(ann)
    f['log_gains_car'] = math.log1p(car)
    f['win_rate'] = nv / nc if nc else 0.0
    f['place_rate'] = npl / nc if nc else 0.0
    f['log_experience'] = math.log1p(nc)
    f['age'] = float(p.get('age') or 6)
    f['femelle'] = 1.0 if p.get('sexe') == 'JUMENTS' else 0.0
    f['hongre'] = 1.0 if p.get('sexe') == 'HONGRES' else 0.0
    o = p.get('oeilleres') or ''
    f['oeilleres'] = 0.0 if o == 'SANS_OEILLERES' else 1.0
    f['inedit'] = 1.0 if p.get('indicateurInedit') else 0.0
    f['etranger'] = 0.0 if (p.get('paysEntrainement') or 'FRA') == 'FRA' else 1.0
    f['supplement'] = 1.0 if (p.get('supplement') or 0) > 0 else 0.0
    f['jockey_change'] = 1.0 if p.get('driverChange') else 0.0
    d = course.get('discipline') or 'HAIE'
    f['steeple'] = 1.0 if d == 'STEEPLECHASE' else 0.0
    f['cross'] = 1.0 if d == 'CROSS' else 0.0
    f['log_distance'] = math.log((course.get('distance') or 3500) / 3500.0)
    return f
