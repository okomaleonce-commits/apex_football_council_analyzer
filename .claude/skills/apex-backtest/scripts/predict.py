"""Prevision scellee avant le depart : simulation complete + incertitude + tracabilite."""
import sys, os, json, hashlib, datetime, pickle
import numpy as np
sys.path.insert(0, '/tmp/bt'); import racesim as RS

DMY, RN, CN, DISC = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
SEED = int(sys.argv[5]) if len(sys.argv) > 5 else 20260926
if DISC == 'trot':
    sys.path.insert(0, '/tmp/turf'); import features as F, dataset as DS, model
    HIST, FIT = '/tmp/turf/hist.jsonl', '/tmp/turf/apex_trot_fit.json'
else:
    sys.path.insert(0, '/tmp/obst'); import features_obst as F, dataset_obst as DS, model
    HIST, FIT = '/tmp/obst/hist.jsonl', '/tmp/obst/apex_obst_fit.json'
import urllib.request
BASE = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme"
def g(u):
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())

prog = g(f"{BASE}/{DMY}")
reu = [x for x in prog['programme']['reunions'] if x['numOfficiel'] == RN][0]
crs = [x for x in reu['courses'] if x['numOrdre'] == CN][0]
if crs.get('ordreArrivee'):
    print("REFUS : la course est deja courue, aucune prevision scellee possible."); sys.exit(2)
parts = g(f"{BASE}/{DMY}/R{RN}/C{CN}/participants")['participants']
course = dict(hippo=reu['hippodrome']['libelleCourt'], distance=crs.get('distance'),
              montantPrix=crs.get('montantPrix'), discipline=crs.get('discipline'),
              particularite=crs.get('categorieParticularite'), libelle=crs.get('libelle'),
              penetrometre=crs.get('penetrometre'))
field = []
for p in parts:
    if p.get('statut') != 'PARTANT': continue
    q = dict(p); q['coteFinale'] = (p.get('dernierRapportDirect') or {}).get('rapport')
    q['gains'] = p.get('gainsParticipant', {}); field.append(q)
odds_ts = max((p.get('dernierRapportDirect') or {}).get('dateRapport', 0) for p in parts)
fit = json.load(open(FIT)); feats = fit['feats']
d = datetime.date(int(DMY[4:]), int(DMY[2:4]), int(DMY[:2]))
st = DS.live_state(HIST, upto=d.isoformat())
rows = [dict(F.runner_features(p, course, field), **st.feats(p, course, d)) for p in field]
X = np.array([[r[k] for k in feats] for r in rows], float)
odds = np.array([p['coteFinale'] for p in field], float)
q = 1 / odds; q = q / q.sum(); ml = np.log(q) - np.log(q).mean()
Xw = X.copy()
for j in fit.get('pen_idx', []): Xw[:, j] = 0.0
eta = (Xw - Xw.mean(0)) / np.asarray(fit['sd']) @ np.asarray(fit['beta']) + ml
eta -= eta.max(); pw = np.exp(eta); pw /= pw.sum()
Z = np.hstack([(X - np.asarray(fit['fault_mu'])) / np.asarray(fit['fault_sd']), np.ones((len(X), 1))])
pf = 1 / (1 + np.exp(-np.clip(Z @ np.asarray(fit['fault_b']), -30, 30)))
sh = json.load(open(f'/tmp/bt/shared_{DISC}.json')) if os.path.exists(f'/tmp/bt/shared_{DISC}.json') else dict(tau=0.4, cf=0.4)
U = RS.exposures(X.tolist(), feats, DISC)
sim = RS.run(pw, np.clip(pf, 1e-6, 1 - 1e-6), U, sh['tau'], sh['cf'], seed=SEED, target_se=0.002)
nums = [p['numPmu'] for p in field]
exo = RS.exotics(sim['ranks'], nums)

# --- incertitude de MODELE : reechantillonnage des coefficients ---
cov_scale = 0.0
try:
    bs = pickle.load(open(f'/tmp/bt/beta_boot_{DISC}.pkl', 'rb'))
    PS = []
    for b in bs:
        e = (Xw - Xw.mean(0)) / np.asarray(fit['sd']) @ np.asarray(b) + ml
        e -= e.max(); v = np.exp(e); PS.append(v / v.sum())
    PS = np.asarray(PS)
    lo_m, hi_m = np.percentile(PS, 2.5, axis=0), np.percentile(PS, 97.5, axis=0)
except FileNotFoundError:
    lo_m = hi_m = None

pe = course.get('penetrometre') or {}
print(f"\n{course['libelle']} | {course['hippo']} {course['distance']}m {course['discipline']} "
      f"| {len(field)} partants | terrain {pe.get('valeurMesure','?')} {pe.get('intitule','')}")
print(f"tirages executes : {sim['N']:,} | erreur Monte-Carlo max sur P(victoire) : "
      f"{sim['se_p_win'].max()*100:.3f} pt | tau={sh['tau']} cf={sh['cf']} | graine {SEED}")
# regle de production issue du backtest : Harville/Stern pour le top 3
STERN = 0.82 if DISC == 'obst' else 0.70
p3_stern = model.place_probs(sim['p_win'], STERN)
print(f"\n{'N':>3} {'Cheval':<20} {'cote':>6} {'P_gag':>7} {'±MC':>6} {'±modele':>14} "
      f"{'P_top3*':>8} {'P_top5':>7} {'P_nonclasse':>11}")
recs = []
for i in np.argsort(-sim['p_win']):
    p = field[i]
    mu = f"[{lo_m[i]*100:4.1f};{hi_m[i]*100:4.1f}]" if lo_m is not None else "n/d"
    print(f"{p['numPmu']:>3} {p['nom'][:20]:<20} {odds[i]:>6} {sim['p_win'][i]*100:>6.1f}% "
          f"{sim['se_p_win'][i]*100:>5.2f} {mu:>14} {sim['p_top3'][i]*100:>6.1f}% "
          f"{sim['p_top5'][i]*100:>6.1f}% {sim['p_unplaced'][i]*100:>10.1f}%")
    recs.append(dict(num=int(p['numPmu']), nom=p['nom'], cote=float(odds[i]),
                     p_win=float(sim['p_win'][i]), se_win=float(sim['se_p_win'][i]),
                     p_top3=float(p3_stern[i]), p_top3_sim=float(sim['p_top3'][i]), p_top5=float(sim['p_top5'][i]),
                     p_unplaced=float(sim['p_unplaced'][i]), p_fault=float(pf[i]),
                     model_lo=float(lo_m[i]) if lo_m is not None else None,
                     model_hi=float(hi_m[i]) if hi_m is not None else None))
print("  * P_top3 par Harville/Stern (valide superieur au simulateur : 0,5055 vs 0,5077)")
print(f"\n-- TRIO issu des arrivees simulees (jamais un produit de marginales) --")
for k, v, se in exo['trio'][:5]:
    print(f"  {'-'.join(map(str,k)):>10}  {v*100:5.2f}% ±{se*100:.3f}  rapport min rentable {1/v:6.1f}")
print(f"  combinaison jamais tiree : < {exo['min_resolvable']*100:.4f} %, pas impossible")

rec = dict(produit_le=datetime.datetime.utcnow().isoformat()+'Z', course=f"{DMY}-R{RN}C{CN}",
           libelle=course['libelle'], discipline=course['discipline'], moteur=DISC,
           version='v1.0.2+backtest1.0',
           empreinte_parametres=hashlib.sha256(open(FIT,'rb').read()).hexdigest(),
           graine=SEED, tirages=int(sim['N']), tau=sh['tau'], cf=sh['cf'],
           cotes_horodatage=datetime.datetime.utcfromtimestamp(odds_ts/1000).isoformat()+'Z' if odds_ts else None,
           terrain=pe, partants=recs,
           trio=[dict(combi=list(k), p=v, se=se) for k, v, se in exo['trio'][:20]])
os.makedirs('/tmp/bt/predictions', exist_ok=True)
fn = f"/tmp/bt/predictions/{DMY}_R{RN}C{CN}.json"
if os.path.exists(fn):
    print(f"\nREFUS de reecrire {fn} : un enregistrement scelle existe deja.")
else:
    json.dump(rec, open(fn, 'w'), indent=1, ensure_ascii=False)
    print(f"\nenregistrement scelle -> {fn}")
    print(f"  empreinte parametres {rec['empreinte_parametres'][:16]}…  cotes datees de {rec['cotes_horodatage']}")
