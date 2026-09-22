"""Collecte l'historique des courses d'obstacle francaises (haies, steeple, cross)."""
import json, sys, time, datetime, threading, queue
import urllib.request, urllib.error

BASE = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme"
HDR = {"User-Agent": "Mozilla/5.0"}
LOCK = threading.Lock()

def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (404, 204): return None
            time.sleep(1.5 * (i + 1))
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None

def day_courses(d):
    prog = get(f"{BASE}/{d.strftime('%d%m%Y')}")
    if not prog: return []
    out = []
    for r in prog.get("programme", {}).get("reunions", []):
        if r.get("pays", {}).get("code") != "FRA": continue
        for c in r.get("courses", []):
            if c.get("specialite") != "OBSTACLE": continue
            if not c.get("ordreArrivee"): continue
            out.append(dict(
                date=d.strftime("%Y-%m-%d"), dmy=d.strftime("%d%m%Y"),
                reunion=r["numOfficiel"], course=c["numOrdre"],
                hippo=r["hippodrome"]["libelleCourt"],
                discipline=c["discipline"], distance=c.get("distance"),
                montantPrix=c.get("montantPrix"), corde=c.get("corde"),
                particularite=c.get("categorieParticularite"),
                conditions=(c.get("conditions") or "")[:400],
                nbDeclares=c.get("nombreDeclaresPartants"),
                arrivee=c.get("ordreArrivee"),
                penetrometre=c.get("penetrometre"),
            ))
    return out

KEEP = ("nom numPmu age sexe race statut oeilleres driver driverChange entraineur "
        "proprietaire musique nombreCourses nombreVictoires nombrePlaces nombrePlacesSecond "
        "nombrePlacesTroisieme handicapPoids handicapValeur poidsConditionMonte "
        "tauxReclamation ordreArrivee incident indicateurInedit supplement engagement "
        "paysEntrainement distanceChevalPrecedent").split()

def fetch_course(meta):
    d = get(f"{BASE}/{meta['dmy']}/R{meta['reunion']}/C{meta['course']}/participants")
    if not d or "participants" not in d: return None
    ps = []
    for p in d["participants"]:
        row = {k: p.get(k) for k in KEEP}
        row["gains"] = p.get("gainsParticipant", {})
        rd = p.get("dernierRapportDirect") or {}
        row["coteFinale"] = rd.get("rapport")
        row["coteRef"] = (p.get("dernierRapportReference") or {}).get("rapport")
        ps.append(row)
    meta = dict(meta); meta["partants"] = ps
    return meta

def main():
    start = datetime.date.fromisoformat(sys.argv[1])
    end = datetime.date.fromisoformat(sys.argv[2])
    out = open(sys.argv[3], "w")
    days = [start + datetime.timedelta(days=i) for i in range((end - start).days + 1)]
    metas = []; dq = queue.Queue()
    for d in days: dq.put(d)
    def dworker():
        while True:
            try: d = dq.get_nowait()
            except queue.Empty: return
            cs = day_courses(d)
            with LOCK: metas.extend(cs)
    ts = [threading.Thread(target=dworker) for _ in range(10)]
    [t.start() for t in ts]; [t.join() for t in ts]
    print(f"{len(days)} jours -> {len(metas)} courses d'obstacle FR courues", flush=True)
    cq = queue.Queue()
    for m in metas: cq.put(m)
    n = [0]
    def cworker():
        while True:
            try: m = cq.get_nowait()
            except queue.Empty: return
            r = fetch_course(m)
            with LOCK:
                n[0] += 1
                if r: out.write(json.dumps(r, ensure_ascii=False) + "\n")
                if n[0] % 250 == 0: print(f"  {n[0]}/{len(metas)}", flush=True)
    ts = [threading.Thread(target=cworker) for _ in range(12)]
    [t.start() for t in ts]; [t.join() for t in ts]
    out.close(); print("termine:", sys.argv[3], flush=True)

main()
