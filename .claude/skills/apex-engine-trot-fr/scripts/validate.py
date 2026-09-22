"""Significativite du ROI et efficience du marche place."""
import json, sys, numpy as np, dataset, model, evaluate

fit = json.load(open('/tmp/turf/apex_trot_fit.json'))
races, feats = dataset.build(sys.argv[1], burn_days=200)
races.sort(key=lambda r: r['date'])
n = len(races); te = races[int(n*.78):]
beta, sd = np.asarray(fit['beta']), np.asarray(fit['sd'])
pB = model.predict_win(te, beta, sd, True, 1.0)
pP = [model.place_probs(p, fit['stern']) for p in pB]

def boot_roi(sel, R=4000, seed=0):
    """sel = liste de (rendement) par pari ; IC par bootstrap."""
    if not sel: return 0, 0, (0, 0)
    a = np.asarray(sel, float); rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), (R, len(a)))
    bs = a[idx].mean(axis=1) - 1
    return a.mean() - 1, a.std() / np.sqrt(len(a)), (np.percentile(bs, 2.5), np.percentile(bs, 97.5))

print("=== ROI GAGNANT : significativite (bootstrap 4000 tirages) ===")
print("  seuil    paris   ROI       ecart-type   IC 95%")
for th in (1.00, 1.03, 1.06, 1.10, 1.20):
    sel = []
    for p, r in zip(pB, te):
        for j in range(r['n']):
            if p[j] * r['odds'][j] >= th:
                sel.append(r['odds'][j] if r['y_win'][j] else 0.0)
    roi, se, ci = boot_roi(sel)
    print(f"  {th:.2f}   {len(sel):>6}  {roi*100:+7.2f}%   +/-{se*100:5.2f}%   "
          f"[{ci[0]*100:+6.2f}% , {ci[1]*100:+6.2f}%]")

# ---- marche place ----
pl = {}
for line in open('/tmp/turf/place.jsonl'):
    d = json.loads(line)
    pl[(d['date'], d['reunion'], d['course'])] = d['place']
print(f"\n=== MARCHE PLACE : {len(pl)} courses avec rapports definitifs ===")
import features as Fm
raw = {}
for line in open(sys.argv[1]):
    line = line.strip()
    if not line: continue
    try: c = json.loads(line)
    except: continue
    raw[(c['date'], c['reunion'], c['course'])] = c

# on reconstitue l'appariement course -> rapports place via date/reunion/course
key_by_race = []
import dataset as DS
raws = sorted([c for c in raw.values() if c.get('arrivee')],
              key=lambda c: (c['date'], c['reunion'], c['course']))
# reconstruit l'ordre identique a dataset.build
seq = []
import longitudinal as L
d0 = L.dkey(raws[0]['date']); st = L.State()
for c in raws:
    d = L.dkey(c['date'])
    field = [p for p in c['partants'] if p.get('statut') == 'PARTANT'
             and p.get('incident') != 'NON_PARTANT']
    usable = (len(field) >= 6 and (d - d0).days >= 200
              and all(p.get('coteFinale') for p in field)
              and sum(1 for p in field if p.get('ordreArrivee') == 1) == 1)
    if usable: seq.append((c['date'], c['reunion'], c['course']))
    st.update(c, d)
assert len(seq) == len(races), (len(seq), len(races))
keys_te = seq[int(n*.78):]

print("  seuil    paris   ROI place   IC 95%")
for th in (1.00, 1.05, 1.10, 1.20, 1.35):
    sel = []
    for k, P, r in zip(keys_te, pP, te):
        rap = pl.get(k)
        if not rap: continue
        if r['n'] < 8: continue
        for j in range(r['n']):
            num = str(r['nums'][j])
            div = rap.get(num)
            ev = P[j] * (div if div else 0)
            # on parie sur l'estimation ex ante : il faut une cote place ex ante.
            # faute de cote place ex ante historisee, on teste l'edge structurel :
            # parier les chevaux dont P_top3 depasse le seuil implicite du marche gagnant
            pass
    # approche correcte : cote place implicite = rapport observe (biais de selection)
    print(f"  (non evaluable sans cote place ex ante - voir note)")
    break

# test alternatif : le modele place bat-il la reference de Harville sur le marche ?
q = [ (lambda x: x/x.sum())(1.0/np.asarray(r['odds'], float)) for r in te ]
pP_mkt = [model.place_probs(qq, fit['stern']) for qq in q]
def ll_place(ps):
    v = []
    for P, r in zip(ps, te):
        if r['n'] < 8: continue
        y = np.asarray(r['y_place'], float)
        v.append(-np.mean(y*np.log(P)+(1-y)*np.log(1-P)))
    return float(np.mean(v))
print(f"\n  log-loss place : marche+Stern {ll_place(pP_mkt):.4f}  |  "
      f"APEX+Stern {ll_place(pP):.4f}")

# rentabilite reelle des rapports place observes, par tranche de proba modele
print("\n=== rapports place observes par tranche de P_top3 du modele ===")
rows = []
for k, P, r in zip(keys_te, pP, te):
    rap = pl.get(k)
    if not rap or r['n'] < 8: continue
    for j in range(r['n']):
        div = rap.get(str(r['nums'][j]))
        rows.append((P[j], r['y_place'][j], div if (div and r['y_place'][j]) else 0.0))
rows.sort()
if rows:
    a = np.asarray([x[0] for x in rows]); b = np.asarray([x[1] for x in rows], float)
    c = np.asarray([x[2] for x in rows], float)
    print("  tranche P_top3     n     observe   rapport moyen   ROI mise plate")
    for d in range(8):
        s = slice(d*len(rows)//8, (d+1)*len(rows)//8)
        roi = c[s].mean() - 1
        print(f"  {a[s].min()*100:5.1f}-{a[s].max()*100:5.1f}%  {len(a[s]):>6}   "
              f"{b[s].mean()*100:6.2f}%   {c[s][c[s]>0].mean() if (c[s]>0).any() else 0:7.2f}      {roi*100:+7.2f}%")
