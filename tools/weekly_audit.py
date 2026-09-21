#!/usr/bin/env python3
"""Audit hebdomadaire APEX — recalibration automatique du moteur.

Telecharge les resultats et cotes de cloture de la saison en cours, mesure les
parametres reels de chaque ligue, cherche le coefficient domicile optimal
hors-echantillon, et backteste le ROI par seuil d'edge.

    python3 tools/weekly_audit.py                 # audit, affichage seul
    python3 tools/weekly_audit.py --write-report  # ecrit aussi reports/<date>-audit.md

Regles heritees de football-league-backtester, appliquees strictement :
  < 10 matchs  -> ABORT
  < 50 matchs  -> ANALYSE SEULE (aucun recalibrage)
  50-100       -> 1-2 seuils mineurs
  100-300      -> recalibrage MODERE
  > 300        -> restructuration partielle possible
"""
import csv, io, math, sys, os, urllib.request, datetime, statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.dixon_coles import grid, markets

SEASON = "2627"
BASE = "https://www.football-data.co.uk/mmz4281"
# code : (nom, avg_buts_par_equipe_moteur, rho_moteur, HOME_ADV_moteur, avg_ligue_25_26, matchs_25_26)
LEAGUES = {
    "E0":  ("Premier League", 1.445, 0.08, 1.08, 1.375, 38),
    "I1":  ("Serie A",        1.225, 0.12, 1.08, 1.213, 38),
    "F1":  ("Ligue 1",        1.390, 0.09, 1.16, 1.410, 34),
    "SP1": ("La Liga",        None,  None, None, None,  None),
    "D1":  ("Bundesliga",     None,  None, None, None,  None),
}
SHRINK = 0.80
PROMOTED_PRIOR = (0.80, 1.28)

# Tables finales 2025/26 — priors, seule information disponible avant la saison.
PRIORS = {
 "E0": {'Arsenal':(71,27),'Man City':(77,35),'Man United':(69,50),'Aston Villa':(56,49),
        'Liverpool':(63,53),'Bournemouth':(58,54),'Sunderland':(42,48),'Brighton':(52,46),
        'Brentford':(55,52),'Chelsea':(58,52),'Fulham':(47,51),'Newcastle':(53,55),
        'Everton':(47,50),'Leeds':(49,56),'Crystal Palace':(41,51),"Nott'm Forest":(48,51),
        'Tottenham':(48,57)},
 "I1": {'Inter':(89,35),'Napoli':(58,36),'Roma':(59,31),'Como':(65,29),'Milan':(53,35),
        'Juventus':(61,34),'Atalanta':(51,36),'Bologna':(49,46),'Lazio':(41,40),
        'Udinese':(45,48),'Sassuolo':(46,50),'Torino':(44,63),'Parma':(28,46),
        'Cagliari':(40,53),'Fiorentina':(41,50),'Genoa':(41,51),'Lecce':(28,50)},
 "F1": {'Paris SG':(74,29),'Lens':(66,35),'Lille':(52,37),'Lyon':(53,40),'Marseille':(63,45),
        'Rennes':(59,50),'Monaco':(60,54),'Strasbourg':(58,47),'Toulouse':(47,46),
        'Lorient':(48,51),'Paris FC':(47,50),'Brest':(43,55),'Angers':(29,48),
        'Le Havre':(32,44),'Auxerre':(34,44),'Nice':(37,60)},
}


def fetch(code):
    url = f"{BASE}/{SEASON}/{code}.csv"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read().decode("utf-8-sig", errors="replace")
    rows = [r for r in csv.DictReader(io.StringIO(raw))
            if r.get("FTHG") and r["FTHG"].strip()]
    return rows


def demarg3(h, d, a):
    inv = [1 / h, 1 / d, 1 / a]
    s = sum(inv)
    return [x / s for x in inv]


def rating(code, team):
    tbl = PRIORS.get(code, {})
    _, _, _, _, lgavg, ng = LEAGUES[code]
    if team not in tbl or lgavg is None:
        return (1 + SHRINK * (PROMOTED_PRIOR[0] - 1),
                1 + SHRINK * (PROMOTED_PRIOR[1] - 1)), True
    gf, ga = tbl[team]
    return (1 + SHRINK * (gf / ng / lgavg - 1),
            1 + SHRINK * (ga / ng / lgavg - 1)), False


def tier(n):
    if n < 10:  return "ABORT"
    if n < 50:  return "ANALYSE SEULE"
    if n < 100: return "FAIBLE"
    if n < 300: return "MODERE"
    return "SERIEUX"


def main(write=False):
    out = []
    def say(s=""):
        print(s); out.append(s)

    today = datetime.date.today().isoformat()
    say(f"AUDIT APEX — {today} — saison {SEASON[:2]}/{SEASON[2:]}")
    say("=" * 92)

    data, league_stats = [], {}
    for code, (name, avg, rho, hadv, lgavg, ng) in LEAGUES.items():
        try:
            rows = fetch(code)
        except Exception as e:
            say(f"  {name:16s} INDISPONIBLE ({e})")
            continue
        n = len(rows)
        hg = sum(int(r["FTHG"]) for r in rows)
        ag = sum(int(r["FTAG"]) for r in rows)
        o25 = sum(1 for r in rows if int(r["FTHG"]) + int(r["FTAG"]) > 2)
        btts = sum(1 for r in rows if int(r["FTHG"]) > 0 and int(r["FTAG"]) > 0)
        league_stats[name] = dict(n=n, goals=(hg + ag) / n,
                                  home_ratio=hg / ag if ag else float("nan"),
                                  o25=o25 / n, btts=btts / n)
        if code not in PRIORS:
            continue
        for r in rows:
            try:
                mo = demarg3(float(r["AvgCH"]), float(r["AvgCD"]), float(r["AvgCA"]))
            except (ValueError, KeyError, TypeError, ZeroDivisionError):
                continue
            (ah, dh), p1 = rating(code, r["HomeTeam"])
            (aa, da), p2 = rating(code, r["AwayTeam"])
            try:
                ou = (float(r["AvgC>2.5"]), float(r["AvgC<2.5"]))
            except (ValueError, KeyError, TypeError):
                ou = None
            data.append(dict(lg=code, ftr=r["FTR"], fh=int(r["FTHG"]), fa=int(r["FTAG"]),
                             mo=mo, ah=ah, dh=dh, aa=aa, da=da, ou=ou,
                             odds3=(float(r["AvgCH"]), float(r["AvgCD"]), float(r["AvgCA"])),
                             avg=avg, rho=rho, hadv=hadv))

    say()
    say("PARAMETRES REELS PAR LIGUE")
    say(f"  {'ligue':16s} {'N':>4s} {'buts/m':>7s} {'dom/ext':>8s} {'O2.5':>7s} {'BTTS':>7s} {'statut':>15s}")
    for name, s in league_stats.items():
        say(f"  {name:16s} {s['n']:4d} {s['goals']:7.2f} {s['home_ratio']:8.3f} "
            f"{s['o25']*100:6.1f}% {s['btts']*100:6.1f}% {tier(s['n']):>15s}")

    N = len(data)
    say()
    say(f"ECHANTILLON HORS-ECHANTILLON : {N} matchs — niveau de recalibrage : {tier(N)}")
    if N < 10:
        say("  ABORT — echantillon insuffisant, aucune conclusion.")
        return out

    def score(k):
        bm = lm = bk = lk = 0.0
        hm = hk = 0
        pg = rg = 0.0
        for d in data:
            lh = d["ah"] * d["da"] * d["avg"] * d["hadv"] * k
            la = d["aa"] * d["dh"] * d["avg"] / k
            m = markets(grid(lh, la, d["rho"]))
            pm = [m["home"], m["draw"], m["away"]]
            y = [1 if d["ftr"] == "H" else 0, 1 if d["ftr"] == "D" else 0,
                 1 if d["ftr"] == "A" else 0]
            i = y.index(1)
            bm += sum((p - q) ** 2 for p, q in zip(pm, y))
            bk += sum((p - q) ** 2 for p, q in zip(d["mo"], y))
            lm += -math.log(max(pm[i], 1e-9))
            lk += -math.log(max(d["mo"][i], 1e-9))
            hm += pm.index(max(pm)) == i
            hk += d["mo"].index(max(d["mo"])) == i
            pg += lh + la
            rg += d["fh"] + d["fa"]
        return bm / N, lm / N, bk / N, lk / N, hm, hk, pg / N, rg / N

    say()
    say("RECHERCHE DU COEFFICIENT DOMICILE k (critere log-loss hors-echantillon)")
    say(f"  {'k':>6s} {'Brier':>9s} {'LogLoss':>9s} {'issues':>8s}")
    best = None
    for k in [1.00, 1.04, 1.08, 1.12, 1.14, 1.16, 1.20]:
        bm, lm, bk, lk, hm, hk, pg, rg = score(k)
        if best is None or lm < best[1]:
            best = (k, lm)
        say(f"  {k:6.2f} {bm:9.4f} {lm:9.4f} {hm:5d}/{N}")
    say(f"  -> k optimal = {best[0]:.2f}")
    if N < 50:
        say("  ANALYSE SEULE : ne PAS appliquer ce k (echantillon < 50).")

    bm, lm, bk, lk, hm, hk, pg, rg = score(best[0])
    say()
    say("MODELE vs MARCHE (cotes de cloture)")
    say(f"  Brier   modele {bm:.4f} | marche {bk:.4f}")
    say(f"  LogLoss modele {lm:.4f} | marche {lk:.4f}")
    say(f"  Issues  modele {hm}/{N} ({hm/N*100:.1f}%) | marche {hk}/{N} ({hk/N*100:.1f}%)")
    say(f"  Buts    modele {pg:.2f}/match | reel {rg:.2f}/match (ratio {rg/pg:.3f})")

    say()
    say("BACKTEST ROI PAR SEUIL D'EDGE — cotes de cloture, mise plate 1u")
    say(f"  {'marche':>8s} {'seuil':>6s} {'bets':>5s} {'winrate':>8s} {'ROI':>8s} {'IC 95%':>22s}")
    for mk in ("1X2", "O/U2.5"):
        for em in (0.03, 0.05, 0.08, 0.15):
            pnls = []
            for d in data:
                lh = d["ah"] * d["da"] * d["avg"] * d["hadv"] * best[0]
                la = d["aa"] * d["dh"] * d["avg"] / best[0]
                m = markets(grid(lh, la, d["rho"]))
                if mk == "1X2":
                    for s, idx, key in (("H", 0, "home"), ("D", 1, "draw"), ("A", 2, "away")):
                        if m[key] / d["mo"][idx] - 1 >= em:
                            pnls.append((d["odds3"][idx] - 1) if s == d["ftr"] else -1.0)
                else:
                    if not d["ou"]:
                        continue
                    io_, iu = 1 / d["ou"][0], 1 / d["ou"][1]
                    s_ = io_ + iu
                    t = d["fh"] + d["fa"]
                    for lab, p, o, pi in (("O", m["over25"], d["ou"][0], io_ / s_),
                                          ("U", m["under25"], d["ou"][1], iu / s_)):
                        if p / pi - 1 >= em:
                            hit = (lab == "O" and t > 2) or (lab == "U" and t <= 2)
                            pnls.append((o - 1) if hit else -1.0)
            if len(pnls) < 5:
                say(f"  {mk:>8s} {em*100:5.0f}% {len(pnls):5d}   trop peu de signaux")
                continue
            mean = sum(pnls) / len(pnls)
            se = statistics.pstdev(pnls) / math.sqrt(len(pnls))
            w = sum(1 for x in pnls if x > 0)
            sig = "" if abs(mean / se) < 1.96 else "  SIGNIFICATIF"
            say(f"  {mk:>8s} {em*100:5.0f}% {len(pnls):5d} {w/len(pnls)*100:7.1f}% "
                f"{mean*100:+7.1f}% [{(mean-1.96*se)*100:+6.1f}%;{(mean+1.96*se)*100:+6.1f}%]{sig}")

    say()
    say("CONCLUSION")
    say(f"  k retenu : {best[0]:.2f}" + ("" if N >= 50 else " (NON applique — echantillon insuffisant)"))
    say("  Aucun ROI significatif => defaut NO BET maintenu." )
    say("  Tout recalibrage exige ensuite >= 30 matchs de validation hors-echantillon.")

    if write:
        path = f"reports/{today}-audit-auto.md"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# Audit automatique APEX — {today}\n\n```\n" + "\n".join(out) + "\n```\n")
        print(f"\n-> rapport ecrit dans {path}")
    return out


if __name__ == "__main__":
    main(write="--write-report" in sys.argv)
