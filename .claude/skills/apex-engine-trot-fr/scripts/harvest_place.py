"""Rapports definitifs du Simple Place, pour tester l'efficience du marche placé."""
import json, sys, threading, queue, time, urllib.request, urllib.error
BASE="https://online.turfinfo.api.pmu.fr/rest/client/1/programme"
HDR={"User-Agent":"Mozilla/5.0"}; LOCK=threading.Lock()
def get(u,tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=HDR),timeout=25) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (404,204): return None
            time.sleep(1.2*(i+1))
        except Exception: time.sleep(1.2*(i+1))
    return None
since=sys.argv[2]
keys=[]
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    try: c=json.loads(line)
    except: continue
    if c['date']>=since: keys.append((c['date'],c['dmy'],c['reunion'],c['course']))
print(len(keys),"courses a interroger",flush=True)
out=open(sys.argv[3],"w"); q=queue.Queue(); [q.put(k) for k in keys]; n=[0]
def wk():
    while True:
        try: k=q.get_nowait()
        except queue.Empty: return
        d=get(f"{BASE}/{k[1]}/R{k[2]}/C{k[3]}/rapports-definitifs")
        rec=None
        if isinstance(d,list):
            for b in d:
                if b.get('typePari')=='SIMPLE_PLACE':
                    rec={'date':k[0],'reunion':k[2],'course':k[3],
                         'place':{r['combinaison']: r['dividendePourUnEuro']/100.0
                                  for r in b.get('rapports',[])}}
        with LOCK:
            n[0]+=1
            if rec: out.write(json.dumps(rec)+"\n")
            if n[0]%500==0: print(f"  {n[0]}/{len(keys)}",flush=True)
ts=[threading.Thread(target=wk) for _ in range(8)]
[t.start() for t in ts]; [t.join() for t in ts]; out.close(); print("termine",flush=True)
