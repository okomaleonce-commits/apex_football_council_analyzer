import math
from itertools import product

def dc_tau(x, y, lh, la, rho):
    if x==0 and y==0: return 1 - lh*la*rho
    if x==0 and y==1: return 1 + lh*rho
    if x==1 and y==0: return 1 + la*rho
    if x==1 and y==1: return 1 - rho
    return 1.0

def pois(k, lam):
    return math.exp(-lam)*lam**k/math.factorial(k)

def grid(lh, la, rho, nmax=12):
    g = {}
    tot = 0.0
    for x, y in product(range(nmax+1), repeat=2):
        p = pois(x, lh)*pois(y, la)*dc_tau(x, y, lh, la, rho)
        p = max(p, 0.0); g[(x, y)] = p; tot += p
    for k in g: g[k] /= tot
    return g

def markets(g):
    h = sum(p for (x,y),p in g.items() if x>y)
    d = sum(p for (x,y),p in g.items() if x==y)
    a = sum(p for (x,y),p in g.items() if x<y)
    o25 = sum(p for (x,y),p in g.items() if x+y>=3)
    o15 = sum(p for (x,y),p in g.items() if x+y>=2)
    o35 = sum(p for (x,y),p in g.items() if x+y>=4)
    btts = sum(p for (x,y),p in g.items() if x>=1 and y>=1)
    top = sorted(g.items(), key=lambda kv:-kv[1])[:5]
    return dict(home=h, draw=d, away=a, over25=o25, under25=1-o25, over15=o15,
                over35=o35, btts_yes=btts, btts_no=1-btts,
                dnb_home=h/(h+a), dnb_away=a/(h+a),
                dc_home=h+d, dc_away=a+d, dc_ha=h+a,
                top=[(f"{x}-{y}", round(p,4)) for (x,y),p in top])

def am2dec(a):
    a = float(a)
    return 1+a/100 if a>0 else 1+100/(-a)

def demarg(odds):
    """odds: dict name->decimal. Returns demarginalised probs (proportional) + margin."""
    inv = {k: 1/v for k,v in odds.items()}
    s = sum(inv.values())
    return {k: v/s for k,v in inv.items()}, s-1

def report(name, comp, lh, la, rho, book, notes=""):
    g = grid(lh, la, rho); m = markets(g)
    print("="*74)
    print(f"{name}   [{comp}]")
    if notes: print(f"  notes: {notes}")
    print(f"  lambda: home={lh:.3f}  away={la:.3f}  total={lh+la:.3f}  rho={rho}")
    print(f"  1X2 model : H {m['home']*100:5.1f}%  D {m['draw']*100:5.1f}%  A {m['away']*100:5.1f}%")
    print(f"  fair odds : H {1/m['home']:5.2f}   D {1/m['draw']:5.2f}   A {1/m['away']:5.2f}")
    print(f"  O2.5 {m['over25']*100:5.1f}% (fair {1/m['over25']:.2f}) | U2.5 {m['under25']*100:5.1f}% (fair {1/m['under25']:.2f})")
    print(f"  BTTS Y {m['btts_yes']*100:5.1f}% (fair {1/m['btts_yes']:.2f}) | N {m['btts_no']*100:5.1f}% (fair {1/m['btts_no']:.2f})")
    print(f"  DC 1X {m['dc_home']*100:5.1f}% (fair {1/m['dc_home']:.2f}) | X2 {m['dc_away']*100:5.1f}% (fair {1/m['dc_away']:.2f})")
    print(f"  DNB  H {m['dnb_home']*100:5.1f}% (fair {1/m['dnb_home']:.2f}) | A {m['dnb_away']*100:5.1f}% (fair {1/m['dnb_away']:.2f})")
    print(f"  top scores: {m['top']}")
    # edges
    if '1x2' in book:
        o = book['1x2']; p_imp, mg = demarg(o)
        print(f"  -- 1X2 book: H {o['home']:.2f} D {o['draw']:.2f} A {o['away']:.2f} | marge {mg*100:.2f}%")
        for k, lab in (('home','H'),('draw','D'),('away','A')):
            edge = m[{'home':'home','draw':'draw','away':'away'}[k]]/p_imp[k]-1
            ev = m[k]*o[k]-1
            print(f"     {lab}: p_model {m[k]*100:5.1f}%  p_market {p_imp[k]*100:5.1f}%  edge {edge*100:+6.2f}%  EV {ev*100:+6.2f}%")
    for mk, keys in (('ou25',('over25','under25')), ('btts',('btts_yes','btts_no'))):
        if mk in book:
            o = book[mk]; names = list(o.keys()); p_imp, mg = demarg(o)
            print(f"  -- {mk} book: " + " ".join(f"{n} {o[n]:.2f}" for n in names) + f" | marge {mg*100:.2f}%")
            for n, mkey in zip(names, keys):
                edge = m[mkey]/p_imp[n]-1
                ev = m[mkey]*o[n]-1
                print(f"     {n}: p_model {m[mkey]*100:5.1f}%  p_market {p_imp[n]*100:5.1f}%  edge {edge*100:+6.2f}%  EV {ev*100:+6.2f}%")
    return m


# ---------------------------------------------------------------------------
# Diagnostics de calibration — indispensables avant toute lecture d'edge.
#
# Retour d'experience 2026-08-30 : sur 5 matchs analyses le modele brut sortait
# des edges de +27% a +92%, TOUS du cote exterieur. Ce n'etait pas cinq value
# bets mais un biais systematique de -8.6 pts sur la proba domicile, ne de
# ratings calcules sur des buts toutes-competitions non splittes dom/ext.
# ---------------------------------------------------------------------------

def home_bias(matches):
    """matches: [(nom, p_home_model, p_home_marche_demarginalisee), ...]

    Retourne l'ecart moyen modele-marche sur la proba domicile. Un |ecart| > 3
    points sur >= 4 matchs independants signale un defaut de calibration, pas
    une serie d'opportunites : recalibrer avant d'interpreter le moindre edge.
    """
    d = [pm - pk for _, pm, pk in matches]
    return sum(d) / len(d)


def fit_home_k(matches, lo=0.90, hi=1.45, step=0.005):
    """Cherche le coefficient k (lambda_home x k, lambda_away / k) qui annule le
    biais domicile moyen. matches: [(nom, fn_probs(k) -> p_home, p_home_marche)].
    Ancrer le modele sur le consensus marche puis lire les residus : seuls les
    residus sont interpretables comme edge.
    """
    best = None
    k = lo
    while k <= hi:
        d = [fn(k) - pk for _, fn, pk in matches]
        mb = sum(d) / len(d)
        if best is None or abs(mb) < abs(best[1]):
            best = (k, mb)
        k += step
    return best


def sensitivity(p_with, p_without, p_market):
    """Ecart d'edge selon que l'on applique ou non ses hypotheses subjectives
    (AIS-F, ACL, forme). Un signal dont l'edge bouge de plus de ~10 points entre
    les deux n'est pas un signal : c'est l'hypothese de l'analyste qui parle.
    """
    return (p_with / p_market - 1) - (p_without / p_market - 1)


def breakeven_odds(prob, edge_min=0.03):
    """Cote minimale pour respecter le filtre 1 de S7 (edge >= 3%)."""
    return (1 + edge_min) / prob
