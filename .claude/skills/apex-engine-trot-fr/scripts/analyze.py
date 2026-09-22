"""APEX-TROT v1.0 - notation d'une course a venir avec le moteur calibre."""
import sys, json, math, datetime, urllib.request
import numpy as np
import features as F, longitudinal as L, dataset, model

BASE = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme"

def fetch(dmy, r, c):
    def g(u):
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as h:
            return json.loads(h.read().decode())
    prog = g(f"{BASE}/{dmy}")
    reu = [x for x in prog['programme']['reunions'] if x['numOfficiel'] == r][0]
    crs = [x for x in reu['courses'] if x['numOrdre'] == c][0]
    parts = g(f"{BASE}/{dmy}/R{r}/C{c}/participants")['participants']
    course = dict(hippo=reu['hippodrome']['libelleCourt'], distance=crs.get('distance'),
                  montantPrix=crs.get('montantPrix'), discipline=crs.get('discipline'),
                  particularite=crs.get('categorieParticularite'),
                  libelle=crs.get('libelle'), conditions=crs.get('conditions'))
    field = []
    for p in parts:
        if p.get('statut') != 'PARTANT': continue
        q = dict(p)
        q['coteFinale'] = (p.get('dernierRapportDirect') or {}).get('rapport')
        q['gains'] = p.get('gainsParticipant', {})
        field.append(q)
    return course, field

def main():
    dmy, rn, cn, hist, fitf = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    fit = json.load(open(fitf))
    feats = fit['feats']
    course, field = fetch(dmy, rn, cn)
    d = datetime.date(int(dmy[4:]), int(dmy[2:4]), int(dmy[:2]))
    st = dataset.live_state(hist, upto=d.isoformat())
    rows = []
    for p in field:
        r = F.runner_features(p, course, field)
        r.update(st.feats(p, course, d))
        rows.append(r)
    X = np.array([[r[k] for k in feats] for r in rows], float)
    odds = np.array([p['coteFinale'] for p in field], float)
    q = 1 / odds; q = q / q.sum()
    ml = np.log(q); ml -= ml.mean()
    Xc = (X - X.mean(0)) / np.asarray(fit['sd'])
    eta = Xc @ np.asarray(fit['beta']) + ml
    eta -= eta.max(); e = np.exp(eta); pw = e / e.sum()
    Z = np.hstack([(X - np.asarray(fit['fault_mu'])) / np.asarray(fit['fault_sd']),
                   np.ones((len(X), 1))])
    pf = 1 / (1 + np.exp(-np.clip(Z @ np.asarray(fit['fault_b']), -30, 30)))
    pp = model.place_probs(pw, fit['stern'])
    print(f"\n{course['libelle']}  |  {course['hippo']}  {course['distance']}m  "
          f"{course['discipline']}  {course['particularite']}  |  {len(field)} partants")
    print(f"moteur APEX-TROT v1.0 (test {fit['n_test']} courses, "
          f"log-loss modele {fit['ll_model_test']:.4f} vs marche {fit['ll_market_test']:.4f})\n")
    print(f"{'N':>3} {'Cheval':<22} {'cote':>6} {'p_mar':>7} {'p_APEX':>7} {'EV_G':>6} "
          f"{'P_faute':>8} {'P_top3':>7}")
    order = np.argsort(-pw)
    res = []
    for i in order:
        p = field[i]
        res.append(dict(num=p['numPmu'], nom=p['nom'], cote=float(odds[i]),
                        p_mar=float(q[i]), p=float(pw[i]), ev=float(pw[i]*odds[i]),
                        pf=float(pf[i]), p3=float(pp[i])))
        print(f"{p['numPmu']:>3} {p['nom'][:22]:<22} {odds[i]:>6} {q[i]*100:>6.1f}% "
              f"{pw[i]*100:>6.1f}% {pw[i]*odds[i]:>6.2f} {pf[i]*100:>7.1f}% {pp[i]*100:>6.1f}%")
    json.dump(res, open('/tmp/turf/live_out.json', 'w'), indent=1)

main()
