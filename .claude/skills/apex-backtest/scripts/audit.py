import json, math, numpy as np, urllib.request, os
from scipy.stats import norm
BASE="https://online.turfinfo.api.pmu.fr/rest/client/1/programme"
def g(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=30).read())
GH_x,GH_w=np.polynomial.hermite_e.hermegauss(31); GH_w=GH_w/GH_w.sum()

# previsions : scellees quand elles existent, sinon celles publiees en chat
PRED={
 ('26092026',1,2): dict(src='scelle', f='/tmp/bt/predictions/26092026_R1C2.json'),
 ('26092026',1,3): dict(src='scelle', f='/tmp/bt/predictions/26092026_R1C3.json'),
 ('22092026',1,4): dict(src='chat', p={12:.160,3:.120,10:.104,1:.075,6:.069,2:.066,5:.059,4:.059,16:.058,8:.057,7:.041,13:.036,14:.031,9:.031,11:.022,15:.016},
                        pf={12:.143,3:.115,10:.132,1:.098,6:.109,2:.067,5:.145,4:.101,16:.135,8:.095,7:.203,13:.088,14:.160,9:.148,11:.149,15:.262}),
}
rows=[]
for (dmy,rn,cn),spec in PRED.items():
    parts=g(f"{BASE}/{dmy}/R{rn}/C{cn}/participants")['participants']
    ps=[p for p in parts if p.get('statut')=='PARTANT']
    arr={p['numPmu']:p.get('ordreArrivee') for p in ps}
    inc={p['numPmu']:(p.get('incident') or '') for p in ps}
    nom={p['numPmu']:p['nom'] for p in ps}
    cote={p['numPmu']:(p.get('dernierRapportDirect') or {}).get('rapport') for p in ps}
    if spec['src']=='scelle':
        rec=json.load(open(spec['f']))
        P={r['num']:r['p_win'] for r in rec['partants']}
        PF={r['num']:r['p_fault'] for r in rec['partants']}
        P3={r['num']:r['p_top3'] for r in rec['partants']}
        P5={r['num']:r['p_top5'] for r in rec['partants']}
        lib=rec['libelle']
    else:
        P,PF=spec['p'],spec['pf']; P3=P5={}; lib='PRIX CALABRAIS'
    nums=[n for n in P if n in arr]
    win=[n for n in nums if arr.get(n)==1]
    nf=[n for n in nums if not arr.get(n)]
    # marche
    q={n:1/cote[n] for n in nums if cote.get(n)}; s=sum(q.values()); qm={n:v/s for n,v in q.items()}
    w=win[0] if win else None
    rank=sorted(nums,key=lambda n:-P[n]).index(w)+1 if w else None
    rows.append(dict(course=f"{dmy} R{rn}C{cn}", lib=lib, n=len(nums), src=spec['src'],
        w=w, wnom=nom.get(w), wcote=cote.get(w), rank=rank,
        ll=-math.log(max(P[w],1e-9)) if w else None, llm=-math.log(max(qm[w],1e-9)) if w else None,
        p3ok=[n for n in nums if arr.get(n) and arr[n]<=3], nf=nf, P=P, PF=PF, P3=P3, P5=P5,
        nom=nom, arr=arr, inc=inc))
print("=== AUDIT VICTOIRE ===")
print(f"{'course':<18} {'vainqueur':<22} {'cote':>6} {'rang APEX':>10} {'p_APEX':>7} {'LL_APEX':>8} {'LL_marche':>10}")
for r in rows:
    print(f"{r['course']:<18} {str(r['wnom'])[:22]:<22} {str(r['wcote']):>6} {str(r['rank'])+'/'+str(r['n']):>10} "
          f"{r['P'][r['w']]*100:>6.1f}% {r['ll']:>8.3f} {r['llm']:>10.3f}")
la=np.mean([r['ll'] for r in rows]); lm=np.mean([r['llm'] for r in rows])
print(f"{'MOYENNE (n=3)':<18} {'':<22} {'':>6} {'':>10} {'':>7} {la:>8.3f} {lm:>10.3f}   ecart {la-lm:+.3f}")
print("\n=== AUDIT PORTE DE NON-TERMINAISON ===")
for r in rows:
    byrisk=sorted(r['P'].keys(),key=lambda n:-r['PF'][n])
    exp=sum(r['PF'][n] for n in r['P'])
    print(f"\n{r['course']} {r['lib']} — {len(r['nf'])} non-finissants sur {r['n']} "
          f"({len(r['nf'])/r['n']*100:.0f}%), attendu {exp:.1f} ({exp/r['n']*100:.0f}%)")
    print("   3 plus a risque estimes : " + " · ".join(
        f"{r['nom'][n][:16]} {r['PF'][n]*100:.1f}% -> {'NON TERMINE' if n in r['nf'] else ('gagne' if r['arr'].get(n)==1 else str(r['arr'].get(n))+'e')}"
        for n in byrisk[:3]))
    for n in r['nf']:
        print(f"     non-finissant {r['nom'][n][:20]:<20} P(chute) {r['PF'][n]*100:4.1f}% -> rang {byrisk.index(n)+1}/{r['n']} du risque  [{r['inc'][n]}]")
    # test de la surdispersion cf=0.4 : ou tombe le nombre observe ?
    p=np.array([r['PF'][n] for n in r['P']])
    def pk(cf):
        lo=np.log(p/(1-p))[:,None]+cf*GH_x[None,:]
        s=1/(1+np.exp(-lo))
        dist=np.zeros((len(GH_x),len(p)+1)); dist[:,0]=1.0
        for j in range(len(p)):
            nd=np.zeros_like(dist)
            nd[:,1:]+=dist[:,:-1]*s[j][:,None]; nd+=dist*(1-s[j])[:,None]
            dist=nd
        return dist.T@GH_w
    k=len(r['nf'])
    for cf,lab in ((0.0,'independant'),(0.4,'cf=0.4 calibre')):
        d=pk(cf); print(f"     P(k={k}) {lab:<16} {d[k]*100:5.2f}%   P(k>={k}) {d[k:].sum()*100:5.2f}%")
print("\n=== AUDIT TOP 3 / TOP 5 (previsions scellees) ===")
for r in rows:
    if not r['P3']: continue
    y3=[1 if (r['arr'].get(n) and r['arr'][n]<=3) else 0 for n in r['P']]
    y5=[1 if (r['arr'].get(n) and r['arr'][n]<=5) else 0 for n in r['P']]
    p3=np.array([r['P3'][n] for n in r['P']]); p5=np.array([r['P5'][n] for n in r['P']])
    b3=np.mean((p3-np.array(y3))**2); b5=np.mean((p5-np.array(y5))**2)
    print(f"  {r['course']} Brier top3 {b3:.4f} | top5 {b5:.4f} | somme p3 {p3.sum():.2f} (attendu 3) | somme p5 {p5.sum():.2f} (attendu 5)")
