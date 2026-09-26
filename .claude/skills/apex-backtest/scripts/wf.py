"""Evaluation progressive a origine glissante (walk-forward), par discipline."""
import sys, os, json, pickle, datetime
import numpy as np
sys.path.insert(0, '/tmp/bt')
import btmetrics as M

DISC = sys.argv[1]                      # trot | obst
SUB = sys.argv[2] if len(sys.argv) > 2 else 'all'   # all | ATTELE | MONTE | HAIE | STEEPLECHASE
if DISC == 'trot':
    sys.path.insert(0, '/tmp/turf'); import dataset as DS, model
    PATH, BURN, CACHE = '/tmp/turf/hist.jsonl', 200, '/tmp/bt/races_trot.pkl'
else:
    sys.path.insert(0, '/tmp/obst'); import dataset_obst as DS, model
    PATH, BURN, CACHE = '/tmp/obst/hist.jsonl', 240, '/tmp/bt/races_obst.pkl'

if os.path.exists(CACHE):
    races, feats = pickle.load(open(CACHE, 'rb'))
else:
    races, feats = DS.build(PATH, burn_days=BURN)
    pickle.dump((races, feats), open(CACHE, 'wb'))
races.sort(key=lambda r: r['date'])
if SUB != 'all':
    races = [r for r in races if r['discipline'] == SUB]
print(f"discipline={DISC} sous-ensemble={SUB} : {len(races)} courses, "
      f"{sum(r['n'] for r in races)} partants, {races[0]['date']} -> {races[-1]['date']}")

PEN = [i for i, f in enumerate(feats) if f in ('pen', 'has_pen')] if DISC == 'obst' else []
if PEN:
    for r in races:
        r['X_all'] = [list(row) for row in r['X']]
        r['X'] = [[0.0 if j in PEN else v for j, v in enumerate(row)] for row in r['X']]

def quarters(rs):
    d0 = datetime.date.fromisoformat(rs[0]['date'])
    d1 = datetime.date.fromisoformat(rs[-1]['date'])
    out = []
    y, q = d0.year, (d0.month - 1) // 3 + 1
    while True:
        m = 3 * (q - 1) + 1
        start = datetime.date(y, m, 1)
        ny, nq = (y + 1, 1) if q == 4 else (y, q + 1)
        end = datetime.date(ny, 3 * (nq - 1) + 1, 1)
        if start > d1: break
        out.append((start.isoformat(), end.isoformat()))
        y, q = ny, nq
    return out

MIN_TRAIN = 600
L2S = (40., 150., 600., 2500.)
blocks = []
for start, end in quarters(races):
    tr = [r for r in races if r['date'] < start]
    fc = [r for r in races if start <= r['date'] < end]
    if len(tr) < MIN_TRAIN or len(fc) < 40: continue
    # L2 choisie DANS la fenetre d'apprentissage, sur son dernier cinquieme
    cut = int(len(tr) * 0.80)
    itr, iva = tr[:cut], tr[cut:]
    best = None
    for lam in L2S:
        b, sd = model.fit_win(itr, feats, lam=lam, use_market=True, gamma=1.0)
        ll = M.logloss_win(model.predict_win(iva, b, sd, True, 1.0), iva)
        if best is None or ll < best[0]: best = (ll, lam)
    lam = best[1]
    b, sd = model.fit_win(tr, feats, lam=lam, use_market=True, gamma=1.0)
    p_mod = model.predict_win(fc, b, sd, True, 1.0)
    p_mkt = M.market_p(fc); p_uni = M.uniform_p(fc)
    if PEN:
        for r in fc: r['X'] = r['X_all']
        for r in tr: r['X'] = r['X_all']
    bf, mu, sdf = model.fit_fault(tr, feats, lam=5.0)
    p_f = model.predict_fault(fc, bf, mu, sdf)
    if PEN:
        for r in fc: r['X'] = [[0.0 if j in PEN else v for j, v in enumerate(row)] for row in r['X_all']]
        for r in tr: r['X'] = [[0.0 if j in PEN else v for j, v in enumerate(row)] for row in r['X_all']]
    blocks.append(dict(start=start, end=end, n=len(fc), nr=sum(r['n'] for r in fc), l2=lam,
                       ll_mod=M.logloss_win(p_mod, fc), ll_mkt=M.logloss_win(p_mkt, fc),
                       ll_uni=M.logloss_win(p_uni, fc),
                       br_mod=M.brier_win(p_mod, fc), br_mkt=M.brier_win(p_mkt, fc),
                       fc=fc, p_mod=p_mod, p_mkt=p_mkt, p_uni=p_uni, p_f=p_f))
    print(f"  {start} n={len(fc):>4} L2={lam:<7} modele {blocks[-1]['ll_mod']:.4f} | "
          f"marche {blocks[-1]['ll_mkt']:.4f} | uniforme {blocks[-1]['ll_uni']:.4f} | "
          f"gain {blocks[-1]['ll_mkt']-blocks[-1]['ll_mod']:+.4f}", flush=True)

ALL = [r for b in blocks for r in b['fc']]
PM = [p for b in blocks for p in b['p_mod']]
PK = [p for b in blocks for p in b['p_mkt']]
PU = [p for b in blocks for p in b['p_uni']]
PF = [p for b in blocks for p in b['p_f']]
pickle.dump(dict(blocks=[{k: v for k, v in b.items() if k not in ('fc','p_mod','p_mkt','p_uni','p_f')} for b in blocks],
                 races=ALL, p_mod=PM, p_mkt=PK, p_uni=PU, p_f=PF, feats=feats),
            open(f'/tmp/bt/wf_{DISC}_{SUB}.pkl', 'wb'))
print(f"\n=== AGREGAT walk-forward : {len(ALL)} courses, {sum(r['n'] for r in ALL)} partants ===")
print(f"  log-loss  modele {M.logloss_win(PM,ALL):.4f} | marche {M.logloss_win(PK,ALL):.4f} | uniforme {M.logloss_win(PU,ALL):.4f}")
print(f"  Brier     modele {M.brier_win(PM,ALL):.5f} | marche {M.brier_win(PK,ALL):.5f}")
print(f"  ECE       modele {M.ece(PM,ALL)*100:.3f} pt | marche {M.ece(PK,ALL)*100:.3f} pt")
d, lo, hi = M.paired_cluster_bootstrap(M.logloss_win, ALL, PK, PM, B=2000)
print(f"  gain de log-loss sur le marche : {d:+.4f}  IC95 par course [{lo:+.4f} ; {hi:+.4f}]")
pos = sum(1 for b in blocks if b['ll_mkt'] > b['ll_mod'])
print(f"  V3 stabilite : gain positif sur {pos}/{len(blocks)} blocs = {pos/len(blocks)*100:.0f}%")
fm = M.fault_metrics(PF, ALL)
print(f"\n  PORTE DE RISQUE : base {fm['base']*100:.1f}% | log-loss {fm['ll_base']:.4f} -> {fm['ll_model']:.4f} (gain {fm['gain']:+.4f})")
for i,(pp,yy,k) in enumerate(fm['quintiles'],1): print(f"    Q{i} predit {pp*100:5.1f}%  observe {yy*100:5.1f}%  n={k}")
print(f"    monotone={fm['monotone']}  amplitude Q5/Q1={fm['amplitude']:.2f}")
