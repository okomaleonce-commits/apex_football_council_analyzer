"""Simulation de course complete a scenarios partages.

Modele de performance latente, un tirage = une course entiere :

    perf_i = a_i + tau * u_ik * z_k  +  eps_i        eps_i ~ Gumbel(0,1)

z_k sont les facteurs de scenario TIRES UNE FOIS PAR COURSE (rythme, terrain,
trafic) : le meme scenario touche tous les partants, mais differemment selon
leurs expositions u_ik. Sans heterogeneite des u, un facteur commun est un
decalage uniforme et n'a aucun effet sur le classement : tau n'est donc
identifiable que par cette heterogeneite.

Les a_i sont recales par ajustement proportionnel iteratif pour que les
probabilites de victoire simulees reproduisent EXACTEMENT les marginales du
moteur valide. Les scenarios ne peuvent donc pas deformer une marginale
calibree : ils n'agissent que sur la structure jointe (top 3, top 5, couples,
trios), la ou Plackett-Luce seul est connu pour se tromper.
"""
import numpy as np

def exposures(X, feats, disc):
    """Expositions aux scenarios, derivees des variables disponibles.
    Ce sont des HYPOTHESES DE STRUCTURE, pas des coefficients estimes — elles
    ne touchent pas les marginales (voir le recalage IPF)."""
    def col(name, default=0.0):
        return np.asarray([row[feats.index(name)] for row in X]) if name in feats \
               else np.full(len(X), default)
    n = len(X)
    U = np.zeros((n, 2))
    if disc == 'obst':
        U[:, 0] = col('poids_rel')            # terrain : le poids pese plus quand ca colle
        U[:, 1] = -col('log_experience')      # trafic/incident : l'inexperience expose
    else:
        U[:, 0] = col('recul_m') / 25.0       # rythme : le recule subit le train
        U[:, 1] = -col('h_n')                 # trafic : peu de references = plus expose
    for k in range(U.shape[1]):               # centrer-reduire DANS la course
        c = U[:, k] - U[:, k].mean()
        s = c.std()
        U[:, k] = c / s if s > 1e-9 else 0.0
    return U

def _simulate(a, U, tau, qf, cf, N, rng):
    """Retourne la matrice des rangs (N x n), 0 = non classe."""
    n = len(a)
    K = U.shape[1]
    z = rng.standard_normal((N, K))
    common = tau * (z @ U.T)                                  # N x n
    g = rng.gumbel(size=(N, n))
    perf = a[None, :] + common + g
    # chutes : correlees au facteur de trafic, marginales preservees par calage
    zt = z[:, min(1, K - 1)]
    lo = np.log(qf / (1 - qf))[None, :] + cf * zt[:, None]
    pf = 1.0 / (1.0 + np.exp(-lo))
    fell = rng.random((N, n)) < pf
    perf = np.where(fell, -np.inf, perf)
    order = np.argsort(-perf, axis=1)
    ranks = np.zeros((N, n), dtype=np.int16)
    valid = ~fell
    for j in range(n):
        idx = order[:, j]
        ok = valid[np.arange(N), idx]
        prev = ranks.max(axis=1)
        ranks[np.arange(N), idx] = np.where(ok, prev + 1, 0)
    return ranks

def calibrate_a(p_target, U, tau, qf, cf, seed=0, N=20000, iters=25, tol=3e-4):
    """Ajustement proportionnel iteratif : les marginales simulees rejoignent
    exactement les probabilites de victoire du moteur."""
    rng = np.random.default_rng(seed)
    a = np.log(np.maximum(p_target, 1e-9))
    for _ in range(iters):
        ranks = _simulate(a, U, tau, qf, cf, N, rng)
        pw = (ranks == 1).mean(axis=0)
        pw = np.maximum(pw, 1e-6)
        if np.max(np.abs(pw - p_target)) < tol: break
        a = a + np.log(p_target / pw)
        a -= a.mean()
    return a

def run(p_target, qf, U, tau, cf, seed=0, target_se=0.002, n0=10000, nmax=1_000_000):
    """Simule jusqu'a la precision numerique visee. Retourne probabilites,
    erreur Monte-Carlo, arrivees simulees et nombre de tirages execute."""
    a = calibrate_a(p_target, U, tau, qf, cf, seed=seed)
    rng = np.random.default_rng(seed + 1)
    n = len(p_target)
    tot = np.zeros((0, n), dtype=np.int16)
    N = n0
    while True:
        tot = np.vstack([tot, _simulate(a, U, tau, qf, cf, N, rng)])
        M = len(tot)
        pw = (tot == 1).mean(axis=0)
        se = np.sqrt(np.maximum(pw * (1 - pw), 0) / M)
        if se.max() <= target_se or M >= nmax: break
        N = min(M, nmax - M)
    M = len(tot)
    out = dict(N=M,
               p_win=(tot == 1).mean(axis=0),
               p_top3=((tot >= 1) & (tot <= 3)).mean(axis=0),
               p_top5=((tot >= 1) & (tot <= 5)).mean(axis=0),
               p_unplaced=(tot == 0).mean(axis=0),
               ranks=tot)
    for k in ('p_win', 'p_top3', 'p_top5', 'p_unplaced'):
        out['se_' + k] = np.sqrt(np.maximum(out[k] * (1 - out[k]), 0) / M)
    return out

def exotics(ranks, nums, kmax=3, top=10):
    """Probabilites de combinaisons calculees SUR LES ARRIVEES SIMULEES.
    Aucun produit de marginales : les classements ne sont pas independants."""
    from collections import Counter
    N = len(ranks)
    n = ranks.shape[1]
    pos = {}
    for k in range(1, kmax + 1):
        pos[k] = np.argmax(ranks == k, axis=1)
        pos[k] = np.where((ranks == k).any(axis=1), pos[k], -1)
    ok = np.ones(N, bool)
    for k in range(1, kmax + 1): ok &= pos[k] >= 0
    trio = Counter(); tierce = Counter(); couple = Counter()
    for i in np.nonzero(ok)[0]:
        t = tuple(nums[pos[k][i]] for k in range(1, kmax + 1))
        tierce[t] += 1
        trio[tuple(sorted(t))] += 1
        couple[tuple(sorted(t[:2]))] += 1
    def fmt(c):
        return [(k, v / N, np.sqrt(max(v / N * (1 - v / N), 0) / N)) for k, v in c.most_common(top)]
    return dict(trio=fmt(trio), tierce=fmt(tierce), couple_gagnant=fmt(couple), N=N,
                min_resolvable=1.0 / N)
