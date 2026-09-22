"""Historique cheval / jockey / entraineur en obstacle, accumule en ordre
chronologique strict : une course ne lit que l'information anterieure."""
import math, datetime
from collections import defaultdict

FALL_INC = None   # renseigne par dataset_obst apres enumeration des codes reels

def dkey(s): return datetime.date.fromisoformat(s)
def shrink(w, n, prior, k): return (w + k * prior) / (n + k)

def is_fall(inc):
    if not inc: return False
    return inc in FALL_INC

class State:
    def __init__(self):
        self.h = defaultdict(lambda: dict(n=0, w=0, t3=0, f=0, last=None, pos=[],
                                          hip=defaultdict(lambda: [0, 0]),
                                          dist=[], disc=defaultdict(int), nobst=0))
        self.j = defaultdict(lambda: [0, 0, 0])   # montes, victoires, chutes
        self.t = defaultdict(lambda: [0, 0, 0])
        self.p = defaultdict(lambda: [0, 0])
        self.g = [0, 0, 0]                        # global n, victoires, chutes

    def hkey(self, p, d):
        return (p['nom'], d.year - (p.get('age') or 0))

    def feats(self, p, course, d):
        hk = self.hkey(p, d)
        gw = self.g[1] / max(self.g[0], 1) or 0.10
        gf = self.g[2] / max(self.g[0], 1) or 0.15
        H = self.h.get(hk)
        f = {}
        if not H or H['n'] == 0:
            f.update(h_n=0.0, h_win=gw, h_t3=0.28, h_fall=gf, h_days=math.log(45),
                     h_nodate=1.0, h_last=0.25, h_last3=0.25, h_hip_n=0.0,
                     h_hip_win=gw, h_distfit=0.0, h_obst_n=0.0, h_disc_fit=0.0)
        else:
            n = H['n']
            f['h_n'] = math.log1p(n)
            f['h_win'] = shrink(H['w'], n, gw, 6)
            f['h_t3'] = shrink(H['t3'], n, 0.28, 6)
            f['h_fall'] = shrink(H['f'], n, gf, 6)
            days = (d - H['last']).days if H['last'] else 45
            f['h_days'] = math.log(max(days, 1)); f['h_nodate'] = 0.0
            pts = {1: 1.0, 2: .72, 3: .55, 4: .40, 5: .30, 6: .20, 7: .14, 8: .10, 9: .07}
            f['h_last'] = pts.get(H['pos'][-1], 0.03) if H['pos'] else 0.25
            l3 = H['pos'][-3:]
            f['h_last3'] = sum(pts.get(x, 0.03) for x in l3) / len(l3) if l3 else 0.25
            hp = H['hip'].get(course['hippo'], [0, 0])
            f['h_hip_n'] = math.log1p(hp[0])
            f['h_hip_win'] = shrink(hp[1], hp[0], gw, 5)
            if H['dist']:
                avg = sum(H['dist']) / len(H['dist'])
                f['h_distfit'] = -abs(math.log((course.get('distance') or avg) / avg))
            else:
                f['h_distfit'] = 0.0
            f['h_obst_n'] = math.log1p(H['nobst'])
            f['h_disc_fit'] = math.log1p(H['disc'].get(course['discipline'], 0))
        jn, jw, jf = self.j[p.get('driver') or '?']
        f['j_n'] = math.log1p(jn)
        f['j_win'] = shrink(jw, jn, gw, 30)
        f['j_fall'] = shrink(jf, jn, gf, 30)
        tn, tw, tf = self.t[p.get('entraineur') or '?']
        f['t_n'] = math.log1p(tn)
        f['t_win'] = shrink(tw, tn, gw, 30)
        f['t_fall'] = shrink(tf, tn, gf, 30)
        pn, pw = self.p[(hk, p.get('driver'))]
        f['pair_n'] = math.log1p(pn)
        f['pair_win'] = shrink(pw, pn, f['j_win'], 8)
        return f

    def update(self, course, d):
        field = [p for p in course['partants']
                 if p.get('statut') == 'PARTANT' and p.get('incident') != 'NON_PARTANT']
        for p in field:
            hk = self.hkey(p, d); H = self.h[hk]
            arr = p.get('ordreArrivee'); fall = is_fall(p.get('incident'))
            H['n'] += 1; H['nobst'] += 1; self.g[0] += 1
            if arr == 1: H['w'] += 1; self.g[1] += 1
            if arr and arr <= 3: H['t3'] += 1
            if fall: H['f'] += 1; self.g[2] += 1
            H['last'] = d
            H['pos'].append(arr if arr else 0)
            hp = H['hip'][course['hippo']]; hp[0] += 1
            if arr == 1: hp[1] += 1
            if course.get('distance'): H['dist'].append(course['distance'])
            H['disc'][course['discipline']] += 1
            j = self.j[p.get('driver') or '?']
            j[0] += 1; j[1] += (arr == 1); j[2] += fall
            t = self.t[p.get('entraineur') or '?']
            t[0] += 1; t[1] += (arr == 1); t[2] += fall
            pa = self.p[(hk, p.get('driver'))]
            pa[0] += 1; pa[1] += (arr == 1)
