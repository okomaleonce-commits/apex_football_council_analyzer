"""Metriques de backtesting hippique. Le regroupement est TOUJOURS la course."""
import numpy as np

def logloss_win(pl, races):
    return float(np.mean([-np.log(max(p[int(np.argmax(r['y_win']))], 1e-12))
                          for p, r in zip(pl, races)]))

def brier_win(pl, races):
    return float(np.mean([np.mean((np.asarray(p) - np.asarray(r['y_win'], float)) ** 2)
                          for p, r in zip(pl, races)]))

def uniform_p(races):
    return [np.full(r['n'], 1.0 / r['n']) for r in races]

def market_p(races):
    out = []
    for r in races:
        q = 1.0 / np.asarray(r['odds'], float)
        out.append(q / q.sum())
    return out

def ece(pl, races, key='y_win', bins=20):
    p = np.concatenate([np.asarray(x) for x in pl])
    y = np.concatenate([np.asarray(r[key], float) for r in races])
    o = np.argsort(p); e = 0.0
    for d in range(bins):
        s = o[d * len(o) // bins:(d + 1) * len(o) // bins]
        if len(s) == 0: continue
        e += len(s) / len(o) * abs(p[s].mean() - y[s].mean())
    return float(e)

def reliability(pl, races, key='y_win', bins=10):
    p = np.concatenate([np.asarray(x) for x in pl])
    y = np.concatenate([np.asarray(r[key], float) for r in races])
    o = np.argsort(p); rows = []
    for d in range(bins):
        s = o[d * len(o) // bins:(d + 1) * len(o) // bins]
        rows.append((d + 1, float(p[s].mean()), float(y[s].mean()), int(len(s))))
    return rows

def topk_observed(races, k):
    """1 si le partant termine dans les k premiers, 0 sinon (non-classe = 0)."""
    out = []
    for r in races:
        y = r.get('y_rank')
        if y is None:
            out.append(np.asarray(r['y_place'], float) if k == 3 else None)
        else:
            out.append(np.asarray([1.0 if (a and a <= k) else 0.0 for a in y]))
    return out

def cluster_bootstrap(fn, races, pl, B=2000, seed=0):
    """IC 95 % par reechantillonnage AU NIVEAU COURSE (les partants restent groupes)."""
    rng = np.random.default_rng(seed)
    n = len(races); vals = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        vals.append(fn([pl[i] for i in idx], [races[i] for i in idx]))
    v = np.asarray(vals)
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))

def paired_cluster_bootstrap(fn, races, pa, pb, B=2000, seed=0):
    """IC 95 % de la DIFFERENCE fn(a)-fn(b), meme reechantillonnage pour les deux."""
    rng = np.random.default_rng(seed)
    n = len(races); d = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        rs = [races[i] for i in idx]
        d.append(fn([pa[i] for i in idx], rs) - fn([pb[i] for i in idx], rs))
    d = np.asarray(d)
    return float(d.mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))

def fault_metrics(pf, races):
    y = np.concatenate([np.asarray(r['y_fault'], float) for r in races])
    p = np.concatenate([np.asarray(x) for x in pf])
    base = y.mean()
    llb = float(-np.mean(y * np.log(base) + (1 - y) * np.log(1 - base)))
    llm = float(-np.mean(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12)))
    o = np.argsort(p); qs = []
    for d in range(5):
        s = o[d * len(o) // 5:(d + 1) * len(o) // 5]
        qs.append((float(p[s].mean()), float(y[s].mean()), int(len(s))))
    mono = all(qs[i][1] < qs[i + 1][1] for i in range(4))
    amp = qs[4][1] / qs[0][1] if qs[0][1] > 0 else float('inf')
    return dict(base=float(base), ll_base=llb, ll_model=llm, gain=llb - llm,
                quintiles=qs, monotone=bool(mono), amplitude=float(amp))
