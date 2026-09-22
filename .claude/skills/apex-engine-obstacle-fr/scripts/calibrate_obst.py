"""APEX-ENGINE OBSTACLE-FR v1.0 - calibration et validation hors echantillon."""
import sys, json, numpy as np, dataset_obst as dataset, model, evaluate
import longitudinal_obst as L

path = sys.argv[1]
raw = dataset.load(path)
cnt, codes = dataset.set_fall_codes(raw)
print("=== codes de non-terminaison releves dans les donnees ===")
for k, v in cnt.most_common(12):
    if k != 'NON_PARTANT': print(f"  {k:<42} {v}")
print()
races, feats = dataset.build(path, burn_days=240, min_runners=5)
races.sort(key=lambda r: r['date'])
print(f"courses exploitables : {len(races)}   variables : {len(feats)}")
print(f"periode : {races[0]['date']} -> {races[-1]['date']}")
from collections import Counter
print("disciplines :", Counter(r['discipline'] for r in races).most_common())
print("taille moyenne du champ : %.1f" % (sum(r['n'] for r in races)/len(races)))
print("taux de non-terminaison : %.1f%%" % (100*sum(sum(r['y_fault']) for r in races)/sum(r['n'] for r in races)))
n = len(races)
tr, va, te = races[:int(n*.60)], races[int(n*.60):int(n*.78)], races[int(n*.78):]
print(f"\napprentissage {len(tr)} | validation {len(va)} | test {len(te)} (test depuis {te[0]['date']})")

def market_p(rs):
    return [(lambda q: q/q.sum())(1.0/np.asarray(r['odds'], float)) for r in rs]
pm_va, pm_te = market_p(va), market_p(te)
ll_m_va, ll_m_te = model.logloss_win(pm_va, va), model.logloss_win(pm_te, te)
print("\n=== REFERENCE : marche PMU ===")
print(f"  validation {ll_m_va:.4f} | test {ll_m_te:.4f} | Brier test {model.brier_win(pm_te, te):.5f}")

print("\n=== A. fondamental seul (sans cotes) ===")
bestA = None
for lam in (2., 10., 40., 150.):
    b, sd = model.fit_win(tr, feats, lam=lam)
    ll = model.logloss_win(model.predict_win(va, b, sd), va)
    print(f"  L2={lam:<6} validation {ll:.4f}")
    if bestA is None or ll < bestA[0]: bestA = (ll, lam, b, sd)
pA = model.predict_win(te, bestA[2], bestA[3])
ll_A = model.logloss_win(pA, te)
print(f"  -> L2={bestA[1]}  TEST {ll_A:.4f}")

print("\n=== B. residuel : marche en offset ===")
bestB = None
for lam in (10., 40., 150., 600., 2500.):
    b, sd = model.fit_win(tr, feats, lam=lam, use_market=True, gamma=1.0)
    ll = model.logloss_win(model.predict_win(va, b, sd, True, 1.0), va)
    print(f"  L2={lam:<7} validation {ll:.4f}   gain vs marche {ll_m_va-ll:+.4f}")
    if bestB is None or ll < bestB[0]: bestB = (ll, lam, b, sd)
pB = model.predict_win(te, bestB[2], bestB[3], True, 1.0)
ll_B = model.logloss_win(pB, te)
print(f"  -> L2={bestB[1]}  TEST {ll_B:.4f}  (marche {ll_m_te:.4f}, gain {ll_m_te-ll_B:+.4f})")

print("\n=== coefficients du residu (standardises) ===")
bb = bestB[2]
for i in np.argsort(-np.abs(bb[:len(feats)]))[:16]:
    print(f"  {feats[i]:<22} {bb[i]:+.4f}")

print("\n=== biais favori-outsider (test) ===")
print("  cote        n     implicite   observe      ROI")
for lo, hi, k, imp, obs, roi in evaluate.fav_longshot(te):
    hs = '+inf' if hi > 1e8 else f'{hi:g}'
    print(f"  {lo:g}-{hs:<7} {k:>6}   {imp*100:6.2f}%   {obs*100:6.2f}%   {roi*100:+7.2f}%")

print("\n=== calibration gagnant (deciles, test) ===")
for d, pp, yy, k in evaluate.calib_table(pB, te):
    print(f"  D{d:<3} predit {pp*100:6.2f}%   observe {yy*100:6.2f}%   n={k}")

print("\n=== PORTE DE CHUTE ===")
bf, mu, sdf = model.fit_fault(tr, feats, lam=5.0)
pf = model.predict_fault(te, bf, mu, sdf)
yf = np.concatenate([r['y_fault'] for r in te]); pfa = np.concatenate(pf)
base = np.concatenate([r['y_fault'] for r in tr]).mean()
llb = -np.mean(yf*np.log(base)+(1-yf)*np.log(1-base))
llm = -np.mean(yf*np.log(pfa+1e-12)+(1-yf)*np.log(1-pfa+1e-12))
print(f"  taux de base {base*100:.1f}%  log-loss {llb:.4f} -> {llm:.4f}  (gain {llb-llm:+.4f})")
o = np.argsort(pfa)
for d in range(5):
    s = o[d*len(o)//5:(d+1)*len(o)//5]
    print(f"  Q{d+1}  predit {pfa[s].mean()*100:5.1f}%  observe {yf[s].mean()*100:5.1f}%")
print("  coefficients :")
for i in np.argsort(-np.abs(bf[:-1]))[:10]:
    print(f"    {feats[i]:<22} {bf[i]:+.4f}")

print("\n=== PLACE : exposant de Stern ===")
pB_va = model.predict_win(va, bestB[2], bestB[3], True, 1.0)
bl = None
for ls in (0.55, 0.62, 0.70, 0.76, 0.82, 0.90, 1.0):
    v = []
    for p, r in zip(pB_va, va):
        if r['n'] < 8: continue
        P = model.place_probs(p, ls); y = np.asarray(r['y_place'], float)
        v.append(-np.mean(y*np.log(P)+(1-y)*np.log(1-P)))
    if not v: continue
    v = float(np.mean(v))
    if bl is None or v < bl[0]: bl = (v, ls)
    print(f"  lambda={ls:.2f}  validation {v:.4f}")
stern = bl[1]
pp_te = [model.place_probs(p, stern) for p in pB]
q_te = [model.place_probs(q, stern) for q in pm_te]
def llp(ps):
    v = []
    for P, r in zip(ps, te):
        if r['n'] < 8: continue
        y = np.asarray(r['y_place'], float)
        v.append(-np.mean(y*np.log(P)+(1-y)*np.log(1-P)))
    return float(np.mean(v))
print(f"  -> lambda={stern}  TEST modele {llp(pp_te):.4f}  |  marche+Stern {llp(q_te):.4f}")

print("\n=== BACKTEST GAGNANT (mise plate, bootstrap 4000) ===")
def boot(sel, R=4000):
    if not sel: return 0, (0, 0)
    a = np.asarray(sel, float); rng = np.random.default_rng(1)
    bs = a[rng.integers(0, len(a), (R, len(a)))].mean(axis=1) - 1
    return a.mean()-1, (np.percentile(bs, 2.5), np.percentile(bs, 97.5))
print("  seuil    paris   gagnants     ROI        IC 95%")
for th in (1.00, 1.05, 1.10, 1.20, 1.35):
    sel = []; hits = 0
    for p, r in zip(pB, te):
        for j in range(r['n']):
            if p[j]*r['odds'][j] >= th:
                sel.append(r['odds'][j] if r['y_win'][j] else 0.0); hits += r['y_win'][j]
    roi, ci = boot(sel)
    print(f"  {th:.2f}   {len(sel):>6}   {hits:>6}    {roi*100:+7.2f}%   [{ci[0]*100:+6.2f}% , {ci[1]*100:+6.2f}%]")

def ece(ps, key='y_win', bins=20):
    p = np.concatenate([np.asarray(x) for x in ps])
    y = np.concatenate([np.asarray(r[key], float) for r in te])
    o = np.argsort(p); e = 0.0
    for d in range(bins):
        s = o[d*len(o)//bins:(d+1)*len(o)//bins]
        e += len(s)/len(o)*abs(p[s].mean()-y[s].mean())
    return e
print(f"\nECE gagnant : modele {ece(pB)*100:.3f} pt | marche {ece(pm_te)*100:.3f} pt")
print(f"ECE chute   : {ece(pf,'y_fault')*100:.3f} pt")
hn = [r['X'][j][feats.index('h_n')] for r in te for j in range(r['n'])]
cov = float(np.mean(np.asarray(hn) > 0))
print(f"couverture historique : {cov*100:.1f}%")

json.dump(dict(feats=feats, beta=bestB[2].tolist(), sd=bestB[3].tolist(), l2=bestB[1],
               fault_b=bf.tolist(), fault_mu=mu.tolist(), fault_sd=sdf.tolist(),
               stern=stern, fall_codes=sorted(codes),
               ll_market_test=ll_m_te, ll_model_test=ll_B, ll_fonda_test=ll_A,
               ll_fault_base=llb, ll_fault_model=llm, fault_base_rate=float(base),
               ece_win=ece(pB), ece_market=ece(pm_te), ece_fault=ece(pf,'y_fault'),
               coverage=cov, n_train=len(tr), n_val=len(va), n_test=len(te),
               periode=[races[0]['date'], races[-1]['date']]),
          open('/tmp/obst/apex_obst_fit.json','w'), indent=1)
print("\nparametres -> apex_obst_fit.json")
