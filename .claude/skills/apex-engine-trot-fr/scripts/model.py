"""APEX-TROT : logit conditionnel (Plackett-Luce premier rang) estime par maximum
de vraisemblance, porte de faute logistique, et correction Stern pour le place."""
import numpy as np
from scipy.optimize import minimize

def center_scale(races, feats, stats=None):
    """Centre chaque variable a l'interieur de sa course, puis reduit globalement."""
    Xs = [np.asarray(r['X'], float) for r in races]
    Xc = [x - x.mean(axis=0, keepdims=True) for x in Xs]
    if stats is None:
        allc = np.vstack(Xc)
        sd = allc.std(axis=0)
        sd[sd < 1e-9] = 1.0
        stats = sd
    return [x / stats for x in Xc], stats

def market_logit(races):
    """log de la probabilite implicite du marche, centre par course."""
    out = []
    for r in races:
        q = 1.0 / np.asarray(r['odds'], float)
        q = q / q.sum()
        l = np.log(q)
        out.append(l - l.mean())
    return out

def nll_condlogit(beta, Xl, ywl, lam, extra=None, g=None):
    """Log-vraisemblance negative du logit conditionnel + penalite L2."""
    tot = 0.0
    grad = np.zeros_like(beta)
    for i, X in enumerate(Xl):
        eta = X @ beta
        if extra is not None:
            eta = eta + g * extra[i]
        eta -= eta.max()
        e = np.exp(eta); s = e.sum(); p = e / s
        k = ywl[i]
        tot -= (eta[k] - np.log(s))
        grad += X.T @ p - X[k]
    tot += lam * beta @ beta
    grad += 2 * lam * beta
    return tot, grad

def fit_win(races, feats, lam=1.0, use_market=False, gamma=None):
    Xl, sd = center_scale(races, feats)
    ywl = [int(np.argmax(r['y_win'])) for r in races]
    extra = market_logit(races) if use_market else None
    if use_market and gamma is None:
        # estime gamma conjointement en l'ajoutant comme colonne supplementaire
        Xl = [np.hstack([X, m.reshape(-1, 1)]) for X, m in zip(Xl, extra)]
        extra = None
    p0 = np.zeros(Xl[0].shape[1])
    res = minimize(nll_condlogit, p0, args=(Xl, ywl, lam, extra, gamma),
                   jac=True, method='L-BFGS-B',
                   options=dict(maxiter=500, ftol=1e-10))
    return res.x, sd

def predict_win(races, beta, sd, use_market=False, gamma=None):
    """gamma=None + use_market : le marche est une colonne estimee.
       gamma=1.0 : le marche est un offset, beta modelise le residu."""
    Xl, _ = center_scale(races, None, sd)
    extra = market_logit(races) if use_market else None
    if use_market and gamma is None:
        Xl = [np.hstack([X, m.reshape(-1, 1)]) for X, m in zip(Xl, extra)]
        extra = None
    out = []
    for i, X in enumerate(Xl):
        eta = X @ beta
        if extra is not None:
            eta = eta + gamma * extra[i]
        eta -= eta.max()
        e = np.exp(eta); out.append(e / e.sum())
    return out

def fit_fault(races, feats, lam=1.0):
    """Regression logistique P(disqualification), sans centrage par course."""
    X = np.vstack([np.asarray(r['X'], float) for r in races])
    y = np.concatenate([np.asarray(r['y_fault'], float) for r in races])
    mu, sd = X.mean(0), X.std(0); sd[sd < 1e-9] = 1.0
    Z = np.hstack([(X - mu) / sd, np.ones((len(X), 1))])
    def obj(b):
        z = Z @ b
        z = np.clip(z, -30, 30)
        p = 1 / (1 + np.exp(-z))
        ll = -(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12)).sum()
        gr = Z.T @ (p - y)
        pen = np.r_[b[:-1], 0.0]
        return ll + lam * pen @ pen, gr + 2 * lam * pen
    res = minimize(obj, np.zeros(Z.shape[1]), jac=True, method='L-BFGS-B',
                   options=dict(maxiter=500))
    return res.x, mu, sd

def predict_fault(races, b, mu, sd):
    out = []
    for r in races:
        X = np.asarray(r['X'], float)
        Z = np.hstack([(X - mu) / sd, np.ones((len(X), 1))])
        out.append(1 / (1 + np.exp(-np.clip(Z @ b, -30, 30))))
    return out

def place_probs(pw, lam_stern, n_place=3):
    """Probabilite d'etre dans les n premiers, modele de Stern : force^lambda."""
    s = np.power(np.asarray(pw, float), lam_stern)
    s = s / s.sum()
    n = len(s)
    k = min(n_place, n - 1) if n > 1 else 1
    # Harville exact pour k<=3
    P = np.zeros(n)
    idx = range(n)
    if k >= 1: P += s
    if k >= 2:
        for i in idx:
            for j in idx:
                if j == i: continue
                P[i] += s[j] * s[i] / (1 - s[j])
    if k >= 3:
        for i in idx:
            for j in idx:
                if j == i: continue
                d1 = 1 - s[j]
                for m in idx:
                    if m in (i, j): continue
                    P[i] += s[j] * (s[m] / d1) * (s[i] / (d1 - s[m]))
    return np.clip(P, 1e-6, 1 - 1e-6)

def logloss_win(pl, races):
    return -np.mean([np.log(max(p[int(np.argmax(r['y_win']))], 1e-12))
                     for p, r in zip(pl, races)])

def brier_win(pl, races):
    v = []
    for p, r in zip(pl, races):
        y = np.asarray(r['y_win'], float)
        v.append(np.mean((p - y) ** 2))
    return float(np.mean(v))
