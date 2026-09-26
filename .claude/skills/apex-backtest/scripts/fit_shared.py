"""Estimation des DEUX parametres de structure jointe, sur donnees :
  cf  = regroupement des non-terminaisons dans une meme course (surdispersion)
  tau = force des scenarios partages, qui remplace l'exposant de Stern
Aucun des deux ne touche les marginales : ils ne decrivent que la dependance."""
import sys, pickle, numpy as np
sys.path.insert(0, '/tmp/bt')
import btmetrics as M, racesim as RS

DISC = sys.argv[1]
d = pickle.load(open(f'/tmp/bt/wf_{DISC}_all.pkl', 'rb'))
races, PM, PF, feats = d['races'], d['p_mod'], d['p_f'], d['feats']
# moitie validation / moitie test, dans l'ordre chronologique
cut = len(races) // 2
va, te = slice(0, cut), slice(cut, len(races))
print(f"{DISC} : {len(races)} courses walk-forward, validation {cut}, test {len(races)-cut}")

# ---------- 1. regroupement des chutes ----------
GH_x, GH_w = np.polynomial.hermite_e.hermegauss(21)
GH_w = GH_w / GH_w.sum()

def recentre(p, cf):
    """Decalage d_i tel que E_z[sigmoid(logit(p)+cf z+d)] = p : marginales preservees."""
    lo = np.log(p / (1 - p)); d = np.zeros_like(p)
    for _ in range(40):
        s = 1 / (1 + np.exp(-(lo[:, None] + cf * GH_x[None, :] + d[:, None])))
        m = s @ GH_w
        g = (s * (1 - s)) @ GH_w
        step = (p - m) / np.maximum(g, 1e-9)
        d += np.clip(step, -1.0, 1.0)
        if np.max(np.abs(p - m)) < 1e-8: break
    return d

def ll_faults(rs, pf, cf):
    tot = 0.0
    for r, p in zip(rs, pf):
        p = np.clip(np.asarray(p), 1e-6, 1 - 1e-6)
        y = np.asarray(r['y_fault'], float)
        dd = recentre(p, cf) if cf > 0 else np.zeros_like(p)
        lo = np.log(p / (1 - p))[:, None] + cf * GH_x[None, :] + dd[:, None]
        s = 1 / (1 + np.exp(-lo))
        lp = (y[:, None] * np.log(s) + (1 - y[:, None]) * np.log(1 - s)).sum(axis=0)
        tot += np.log(np.maximum((np.exp(lp - lp.max()) * GH_w).sum(), 1e-300)) + lp.max()
    return tot / len(rs)

print("\n=== regroupement des non-terminaisons (validation) ===")
best_cf = None
for cf in (0.0, 0.2, 0.4, 0.6, 0.9, 1.2):
    v = ll_faults(races[va], PF[va], cf)
    print(f"  cf={cf:.1f}  log-vraisemblance/course {v:+.4f}")
    if best_cf is None or v > best_cf[0]: best_cf = (v, cf)
cf = best_cf[1]
print(f"  -> cf retenu {cf}  |  TEST {ll_faults(races[te], PF[te], cf):+.4f} "
      f"contre {ll_faults(races[te], PF[te], 0.0):+.4f} sans regroupement")

# ---------- 2. force des scenarios partages ----------
def top3_ll(rs, ps, pfs, tau, cfv, seed=0, N=4000):
    v = []
    for i, (r, p, pf) in enumerate(zip(rs, ps, pfs)):
        if r['n'] < 8: continue
        U = RS.exposures(r['X'], feats, DISC)
        a = np.log(np.maximum(np.asarray(p), 1e-9))
        rng = np.random.default_rng(seed + i)
        ranks = RS._simulate(a, U, tau, np.clip(np.asarray(pf), 1e-6, 1 - 1e-6), cfv, N, rng)
        P = np.clip(((ranks >= 1) & (ranks <= 3)).mean(axis=0), 1e-4, 1 - 1e-4)
        y = np.asarray(r['y_place'], float)
        v.append(-np.mean(y * np.log(P) + (1 - y) * np.log(1 - P)))
    return float(np.mean(v))

sub = slice(0, min(cut, 400))
print("\n=== force des scenarios partages tau (log-loss top 3, validation) ===")
best_tau = None
for tau in (0.0, 0.2, 0.4, 0.7, 1.0, 1.5):
    v = top3_ll(races[sub], PM[sub], PF[sub], tau, cf)
    print(f"  tau={tau:.1f}  log-loss top3 {v:.4f}")
    if best_tau is None or v < best_tau[0]: best_tau = (v, tau)
tau = best_tau[1]
# reference : Harville/Stern sur les memes courses
sys.path.insert(0, '/tmp/turf' if DISC == 'trot' else '/tmp/obst')
import model as MDL
for lam_s in (0.70, 0.82, 1.0):
    v = []
    for r, p in zip(races[sub], PM[sub]):
        if r['n'] < 8: continue
        P = np.clip(MDL.place_probs(p, lam_s), 1e-4, 1 - 1e-4)
        y = np.asarray(r['y_place'], float)
        v.append(-np.mean(y * np.log(P) + (1 - y) * np.log(1 - P)))
    print(f"  reference Harville/Stern lambda={lam_s:.2f} : {np.mean(v):.4f}")
tsub = slice(cut, min(len(races), cut + 400))
print(f"\n  -> tau retenu {tau} | TEST simulateur {top3_ll(races[tsub], PM[tsub], PF[tsub], tau, cf, seed=999):.4f}")
v = []
for r, p in zip(races[tsub], PM[tsub]):
    if r['n'] < 8: continue
    P = np.clip(MDL.place_probs(p, 0.82 if DISC == 'obst' else 0.70), 1e-4, 1 - 1e-4)
    y = np.asarray(r['y_place'], float)
    v.append(-np.mean(y * np.log(P) + (1 - y) * np.log(1 - P)))
print(f"     TEST Harville/Stern : {np.mean(v):.4f}")
import json
json.dump(dict(disc=DISC, cf=cf, tau=tau), open(f'/tmp/bt/shared_{DISC}.json', 'w'))
