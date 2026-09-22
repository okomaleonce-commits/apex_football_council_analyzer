"""APEX-TROT v1.0 - calibration complete et validation hors echantillon."""
import sys, json, numpy as np, dataset, model, evaluate

path = sys.argv[1]
races, feats = dataset.build(path, burn_days=200)
races.sort(key=lambda r: r['date'])
print(f"courses exploitables : {len(races)}   variables : {len(feats)}")
print(f"periode : {races[0]['date']} -> {races[-1]['date']}")
n = len(races)
tr, va, te = races[:int(n*.60)], races[int(n*.60):int(n*.78)], races[int(n*.78):]
print(f"apprentissage {len(tr)} | validation {len(va)} | test {len(te)} "
      f"(test a partir du {te[0]['date']})\n")

def market_p(rs):
    return [ (lambda q: q/q.sum())(1.0/np.asarray(r['odds'], float)) for r in rs ]

pm_va, pm_te = market_p(va), market_p(te)
ll_m_va = model.logloss_win(pm_va, va); ll_m_te = model.logloss_win(pm_te, te)
print("=== REFERENCE : marche PMU (cotes finales) ===")
print(f"  validation log-loss {ll_m_va:.4f} | test log-loss {ll_m_te:.4f} "
      f"| test Brier {model.brier_win(pm_te, te):.5f}")

print("\n=== A. modele fondamental seul (sans cotes) ===")
bestA = None
for lam in (2., 10., 40., 150.):
    b, sd = model.fit_win(tr, feats, lam=lam)
    ll = model.logloss_win(model.predict_win(va, b, sd), va)
    print(f"  L2={lam:<6} validation {ll:.4f}")
    if bestA is None or ll < bestA[0]: bestA = (ll, lam, b, sd)
pA = model.predict_win(te, bestA[2], bestA[3])
print(f"  -> L2={bestA[1]}  TEST {model.logloss_win(pA, te):.4f}")

print("\n=== B. residuel : marche en offset, variables sur le residu ===")
bestB = None
for lam in (10., 40., 150., 600., 2500.):
    b, sd = model.fit_win(tr, feats, lam=lam, use_market=True, gamma=1.0)
    ll = model.logloss_win(model.predict_win(va, b, sd, True, 1.0), va)
    gain = ll_m_va - ll
    print(f"  L2={lam:<7} validation {ll:.4f}   gain vs marche {gain:+.4f}")
    if bestB is None or ll < bestB[0]: bestB = (ll, lam, b, sd)
pB = model.predict_win(te, bestB[2], bestB[3], True, 1.0)
ll_B = model.logloss_win(pB, te)
print(f"  -> L2={bestB[1]}  TEST {ll_B:.4f}  (marche {ll_m_te:.4f}, gain {ll_m_te-ll_B:+.4f})")

print("\n=== C. marche recalibre (exposant unique) ===")
bestC = None
for tau in (0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15):
    p = [ (lambda s: s/s.sum())(np.power(q, tau)) for q in pm_va ]
    ll = model.logloss_win(p, va)
    if bestC is None or ll < bestC[0]: bestC = (ll, tau)
    print(f"  tau={tau:.2f}  validation {ll:.4f}")
tau = bestC[1]
pC = [ (lambda s: s/s.sum())(np.power(q, tau)) for q in pm_te ]
print(f"  -> tau={tau}  TEST {model.logloss_win(pC, te):.4f}")

print("\n=== biais favori-outsider (jeu de test) ===")
print("  cote        n     implicite   observe     ROI mise plate")
for lo, hi, k, imp, obs, roi in evaluate.fav_longshot(te):
    hs = '+inf' if hi > 1e8 else f'{hi:g}'
    print(f"  {lo:g}-{hs:<7} {k:>6}   {imp*100:6.2f}%   {obs*100:6.2f}%   {roi*100:+7.2f}%")

print("\n=== calibration du modele retenu (deciles, jeu de test) ===")
for d, pp, yy, k in evaluate.calib_table(pB, te):
    print(f"  D{d:<3} predit {pp*100:6.2f}%   observe {yy*100:6.2f}%   n={k}")

print("\n=== porte de faute ===")
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

print("\n=== PLACE : exposant de Stern ===")
pB_va = model.predict_win(va, bestB[2], bestB[3], True, 1.0)
bl = None
for ls in (0.55,0.62,0.70,0.76,0.82,0.90,1.0):
    v = []
    for p, r in zip(pB_va, va):
        if r['n'] < 8: continue
        P = model.place_probs(p, ls); y = np.asarray(r['y_place'], float)
        v.append(-np.mean(y*np.log(P)+(1-y)*np.log(1-P)))
    v = float(np.mean(v))
    if bl is None or v < bl[0]: bl = (v, ls)
    print(f"  lambda={ls:.2f}  validation {v:.4f}")
stern = bl[1]
pp_te = [model.place_probs(p, stern) for p in pB]
vv = []
for P, r in zip(pp_te, te):
    if r['n'] < 8: continue
    y = np.asarray(r['y_place'], float)
    vv.append(-np.mean(y*np.log(P)+(1-y)*np.log(1-P)))
print(f"  -> lambda={stern}  TEST {np.mean(vv):.4f}")
print("  calibration place (deciles, test) :")
for d, pp, yy, k in evaluate.calib_table(pp_te, te, key='y_place'):
    print(f"    D{d:<3} predit {pp*100:6.2f}%  observe {yy*100:6.2f}%  n={k}")

print("\n=== BACKTEST rentabilite GAGNANT (mise plate, jeu de test) ===")
print("  seuil EV    paris   gagnants      ROI")
for th, nb, hits, roi, se in evaluate.roi_backtest(pB, te, [1.00,1.05,1.10,1.15,1.25,1.40]):
    print(f"  {th:.2f}      {nb:>6}   {hits:>6}    {roi*100:+7.2f}%")
print("  (rappel : la cote PMU est deja nette de prelevement ; ROI 0% = equilibre)")

json.dump(dict(feats=feats, beta=bestB[2].tolist(), sd=bestB[3].tolist(), l2=bestB[1],
               beta_fonda=bestA[2].tolist(), sd_fonda=bestA[3].tolist(),
               fault_b=bf.tolist(), fault_mu=mu.tolist(), fault_sd=sdf.tolist(),
               stern=stern, tau=tau,
               ll_market_test=ll_m_te, ll_model_test=ll_B,
               ll_fonda_test=model.logloss_win(pA, te),
               n_train=len(tr), n_val=len(va), n_test=len(te),
               periode=[races[0]['date'], races[-1]['date']]),
          open('/tmp/turf/apex_trot_fit.json','w'), indent=1)
print("\nparametres -> apex_trot_fit.json")
