"""Tests d'efficience du marche et backtest de rentabilite."""
import numpy as np

def fav_longshot(races):
    """Biais favori-outsider : cote finale vs frequence de victoire observee."""
    o, y = [], []
    for r in races:
        o += list(r['odds']); y += list(r['y_win'])
    o = np.asarray(o, float); y = np.asarray(y, float)
    buckets = [(1, 2), (2, 3), (3, 5), (5, 8), (8, 13), (13, 21), (21, 34), (34, 60), (60, 1e9)]
    rows = []
    for lo, hi in buckets:
        m = (o >= lo) & (o < hi)
        if m.sum() < 30: continue
        imp = (1 / o[m]).mean()
        obs = y[m].mean()
        roi = (y[m] * o[m]).mean() - 1
        rows.append((lo, hi, int(m.sum()), imp, obs, roi))
    return rows

def roi_backtest(pl, races, thresholds, max_odds=None, place=False, pplace=None):
    """Mise plate sur chaque partant dont EV = p*cote depasse le seuil."""
    out = []
    for th in thresholds:
        stake = ret = 0; nb = 0; hits = 0
        for i, r in enumerate(races):
            p = pplace[i] if place else pl[i]
            for j in range(r['n']):
                c = r['odds'][j]
                if max_odds and c > max_odds: continue
                if p[j] * c < th: continue
                stake += 1; nb += 1
                if r['y_win'][j]: ret += c; hits += 1
        if stake == 0: out.append((th, 0, 0, 0.0, 0.0)); continue
        roi = (ret - stake) / stake
        se = np.sqrt(max(ret / stake, 1e-9) ** 2) / np.sqrt(stake)
        out.append((th, nb, hits, roi, se))
    return out

def calib_table(pl, races, key='y_win', bins=10):
    p, y = [], []
    for pr, r in zip(pl, races):
        p += list(np.asarray(pr)); y += list(r[key])
    p = np.asarray(p); y = np.asarray(y, float)
    o = np.argsort(p); rows = []
    for d in range(bins):
        s = o[d * len(o) // bins:(d + 1) * len(o) // bins]
        rows.append((d + 1, p[s].mean(), y[s].mean(), len(s)))
    return rows
