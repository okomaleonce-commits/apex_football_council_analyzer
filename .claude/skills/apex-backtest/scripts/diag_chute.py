"""La porte de chute est-elle biaisee selon le contexte ? Test stratifie sur
toutes les previsions walk-forward, pas sur trois courses."""
import sys, pickle, numpy as np
sys.path.insert(0,'/tmp/bt'); sys.path.insert(0,'/tmp/obst')
import dataset_obst as DS, model, btmetrics as M
races,feats=DS.build('/tmp/obst/hist.jsonl',burn_days=240)
races.sort(key=lambda r:r['date'])
import json,datetime
# rejoue le walk-forward uniquement pour la porte de chute
def quarters(rs):
    d0=datetime.date.fromisoformat(rs[0]['date']); d1=datetime.date.fromisoformat(rs[-1]['date'])
    out=[]; y,q=d0.year,(d0.month-1)//3+1
    while True:
        m=3*(q-1)+1; start=datetime.date(y,m,1)
        ny,nq=(y+1,1) if q==4 else (y,q+1); end=datetime.date(ny,3*(nq-1)+1,1)
        if start>d1: break
        out.append((start.isoformat(),end.isoformat())); y,q=ny,nq
    return out
ALL=[];PF=[]
for start,end in quarters(races):
    tr=[r for r in races if r['date']<start]; fc=[r for r in races if start<=r['date']<end]
    if len(tr)<600 or len(fc)<40: continue
    bf,mu,sd=model.fit_fault(tr,feats,lam=5.0)
    ALL+=fc; PF+=model.predict_fault(fc,bf,mu,sd)
print(f"porte de chute evaluee sur {len(ALL)} courses, {sum(r['n'] for r in ALL)} partants")
y=np.concatenate([np.asarray(r['y_fault'],float) for r in ALL])
p=np.concatenate([np.asarray(x) for x in PF])
print(f"global : predit {p.mean()*100:.2f}%  observe {y.mean()*100:.2f}%  ecart {(y.mean()-p.mean())*100:+.2f} pt")
def strat(key,label,bins):
    print(f"\n-- par {label} --")
    v=np.concatenate([np.full(r['n'],key(r)) for r in ALL])
    for lo,hi in bins:
        m=(v>=lo)&(v<hi)
        if m.sum()<300: continue
        print(f"   {lo:>6}-{hi:<6} n={m.sum():>6}  predit {p[m].mean()*100:5.2f}%  observe {y[m].mean()*100:5.2f}%  "
              f"ecart {(y[m].mean()-p[m].mean())*100:+5.2f} pt")
strat(lambda r:r['n'],"taille du champ",[(5,9),(9,12),(12,15),(15,18),(18,30)])
def pen(r):
    for c in [l for l in open('/tmp/obst/hist.jsonl')][:0]: pass
    return 0
# penetrometre : relu depuis le brut
import json as J
PEN={}
for line in open('/tmp/obst/hist.jsonl'):
    line=line.strip()
    if not line: continue
    try: c=J.loads(line)
    except: continue
    pe=(c.get('penetrometre') or {}).get('valeurMesure')
    if pe: PEN[(c['date'],c['reunion'],c['course'])]=float(str(pe).replace(',','.'))
# on ne dispose pas de la cle reunion/course dans races -> approximation par date+hippo+distance
KEY={}
for line in open('/tmp/obst/hist.jsonl'):
    line=line.strip()
    if not line: continue
    try: c=J.loads(line)
    except: continue
    pe=(c.get('penetrometre') or {}).get('valeurMesure')
    if pe: KEY[(c['date'],c['hippo'],c['distance'])]=float(str(pe).replace(',','.'))
pv=np.concatenate([np.full(r['n'],KEY.get((r['date'],r['hippo'],r['distance']),np.nan)) for r in ALL])
print("\n-- par penetrometre --")
for lo,hi in [(0,3.0),(3.0,3.8),(3.8,4.3),(4.3,5.0),(5.0,9.0)]:
    m=(pv>=lo)&(pv<hi)
    if m.sum()<300: continue
    print(f"   {lo:>4}-{hi:<4} n={m.sum():>6}  predit {p[m].mean()*100:5.2f}%  observe {y[m].mean()*100:5.2f}%  ecart {(y[m].mean()-p[m].mean())*100:+5.2f} pt")
hp=np.concatenate([np.full(r['n'],1.0 if r['hippo']=='AUTEUIL' else 0.0) for r in ALL])
print("\n-- Auteuil contre les autres --")
for v,lab in ((1.0,'AUTEUIL'),(0.0,'autres')):
    m=hp==v
    print(f"   {lab:<10} n={m.sum():>6}  predit {p[m].mean()*100:5.2f}%  observe {y[m].mean()*100:5.2f}%  ecart {(y[m].mean()-p[m].mean())*100:+5.2f} pt")
dc=np.concatenate([np.full(r['n'],r['discipline']) for r in ALL])
print("\n-- par discipline --")
for d in ('HAIE','STEEPLECHASE','CROSS'):
    m=dc==d
    if m.sum()<300: continue
    print(f"   {d:<14} n={m.sum():>6}  predit {p[m].mean()*100:5.2f}%  observe {y[m].mean()*100:5.2f}%  ecart {(y[m].mean()-p[m].mean())*100:+5.2f} pt")
