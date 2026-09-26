"""Backtest de la regle de pari PRE-ENREGISTREE (section 6 du pre-enregistrement).
Reglement au rapport PMU reellement paye, qui est deja net de prelevement.
IC par bootstrap AU NIVEAU COURSE."""
import sys, pickle, numpy as np
DISC = sys.argv[1]
d = pickle.load(open(f'/tmp/bt/wf_{DISC}_all.pkl', 'rb'))
races, PM, PK, PF = d['races'], d['p_mod'], d['p_mkt'], d['p_f']

def apply_rule(ps, ev_min=1.15, cote_max=13.0, fault_max=0.20, nmin=8):
    """Renvoie, par course, la liste des (rendement) des paris declenches."""
    per_race = []
    for r, p, pf in zip(races, ps, PF):
        bets = []
        if r['n'] >= nmin:
            for j in range(r['n']):
                c = r['odds'][j]
                if p[j] * c >= ev_min and c <= cote_max and pf[j] <= fault_max:
                    bets.append(c if r['y_win'][j] else 0.0)
        per_race.append(bets)
    return per_race

def roi_ci(per_race, B=4000, seed=0):
    flat = [x for b in per_race for x in b]
    if not flat: return 0, 0, (0, 0), 0
    rng = np.random.default_rng(seed); n = len(per_race)
    idx_nonempty = [i for i, b in enumerate(per_race) if b]
    vals = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        s = [x for i in idx for x in per_race[i]]
        vals.append(np.mean(s) - 1 if s else 0.0)
    a = np.asarray(flat, float)
    return len(flat), float(a.mean() - 1), (float(np.percentile(vals, 2.5)),
                                            float(np.percentile(vals, 97.5))), sum(1 for x in flat if x > 0)

print(f"=== {DISC} : regle pre-enregistree EV>=1.15, cote<=13, chute<=0.20, n>=8 ===")
for nom, ps in (('MODELE', PM), ('MARCHE', PK)):
    pr = apply_rule(ps)
    nb, roi, ci, hits = roi_ci(pr)
    print(f"  {nom:<7} paris {nb:>5} gagnants {hits:>4}  ROI {roi*100:+7.2f}%  IC95 par course [{ci[0]*100:+7.2f}% ; {ci[1]*100:+7.2f}%]")
print("\n  sensibilite du seuil d'EV (modele) :")
for ev in (1.00, 1.05, 1.10, 1.15, 1.25):
    pr = apply_rule(PM, ev_min=ev)
    nb, roi, ci, hits = roi_ci(pr)
    print(f"    EV>={ev:.2f}  paris {nb:>5} gagnants {hits:>4}  ROI {roi*100:+7.2f}%  IC95 [{ci[0]*100:+7.2f}% ; {ci[1]*100:+7.2f}%]")
