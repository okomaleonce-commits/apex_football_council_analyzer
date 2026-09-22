"""Variables longitudinales cheval / driver / entraineur, calculees en ordre
chronologique strict : chaque course n'utilise que l'information anterieure."""
import json, math, datetime
from collections import defaultdict

def dkey(s): return datetime.date.fromisoformat(s)

def shrink(w, n, prior, k): return (w + k * prior) / (n + k)

class State:
    def __init__(self):
        self.h = defaultdict(lambda: dict(n=0, w=0, t3=0, f=0, last=None, pos=[],
                                          rk=[], hip=defaultdict(lambda: [0, 0]),
                                          dist=[], gain=0.0))
        self.d = defaultdict(lambda: [0, 0, 0])      # n, wins, fautes
        self.t = defaultdict(lambda: [0, 0])         # n, wins
        self.p = defaultdict(lambda: [0, 0])         # paire cheval-driver
        self.gw = [0, 0]                             # global n, wins
        self.gf = [0, 0]                             # global n, fautes

    def hkey(self, p, d):
        return (p['nom'], d.year - (p.get('age') or 0))

    def feats(self, p, course, d):
        hk = self.hkey(p, d)
        H = self.h[hk] if hk in self.h else None
        gwr = self.gw[1] / max(self.gw[0], 1) or 0.09
        gfr = self.gf[1] / max(self.gf[0], 1) or 0.20
        f = {}
        if H is None or H['n'] == 0:
            f.update(h_n=0.0, h_win=gwr, h_t3=0.28, h_fault=gfr, h_days=math.log(30),
                     h_nodate=1.0, h_last=0.25, h_last3=0.25, h_rk=0.0, h_rkn=0.0,
                     h_hip_n=0.0, h_hip_win=gwr, h_distfit=0.0, h_gpc=0.0)
        else:
            n = H['n']
            f['h_n'] = math.log1p(n)
            f['h_win'] = shrink(H['w'], n, gwr, 8)
            f['h_t3'] = shrink(H['t3'], n, 0.28, 8)
            f['h_fault'] = shrink(H['f'], n, gfr, 8)
            days = (d - H['last']).days if H['last'] else 30
            f['h_days'] = math.log(max(days, 1)); f['h_nodate'] = 0.0
            pts = {1: 1.0, 2: .72, 3: .55, 4: .40, 5: .30, 6: .20, 7: .14, 8: .10, 9: .07}
            f['h_last'] = pts.get(H['pos'][-1], 0.03) if H['pos'] else 0.25
            l3 = H['pos'][-3:]
            f['h_last3'] = sum(pts.get(x, 0.03) for x in l3) / len(l3) if l3 else 0.25
            rk = H['rk'][-5:]
            f['h_rk'] = -sum(rk) / len(rk) if rk else 0.0
            f['h_rkn'] = float(len(rk))
            hp = H['hip'].get(course['hippo'], [0, 0])
            f['h_hip_n'] = math.log1p(hp[0])
            f['h_hip_win'] = shrink(hp[1], hp[0], gwr, 6)
            if H['dist']:
                avg = sum(H['dist']) / len(H['dist'])
                f['h_distfit'] = -abs(math.log((course['distance'] or avg) / avg))
            else:
                f['h_distfit'] = 0.0
            f['h_gpc'] = math.log1p(H['gain'] / n)
        dn, dw, df_ = self.d[p.get('driver') or '?']
        f['d_n'] = math.log1p(dn)
        f['d_win'] = shrink(dw, dn, gwr, 25)
        f['d_fault'] = shrink(df_, dn, gfr, 25)
        tn, tw = self.t[p.get('entraineur') or '?']
        f['t_n'] = math.log1p(tn)
        f['t_win'] = shrink(tw, tn, gwr, 25)
        pn, pw = self.p[(hk, p.get('driver'))]
        f['pair_n'] = math.log1p(pn)
        f['pair_win'] = shrink(pw, pn, f['d_win'], 10)
        return f

    def update(self, course, d):
        field = [p for p in course['partants']
                 if p.get('statut') == 'PARTANT' and p.get('incident') != 'NON_PARTANT']
        win_rk = None
        for p in field:
            if p.get('ordreArrivee') == 1: win_rk = p.get('reductionKilometrique')
        for p in field:
            hk = self.hkey(p, d)
            H = self.h[hk]
            arr = p.get('ordreArrivee')
            inc = p.get('incident') or ''
            fault = inc.startswith('DISQUALIFIE') or inc in ('TOMBE', 'ARRETE', 'DISTANCE')
            H['n'] += 1; self.gw[0] += 1; self.gf[0] += 1
            if arr == 1: H['w'] += 1; self.gw[1] += 1
            if arr and arr <= 3: H['t3'] += 1
            if fault: H['f'] += 1; self.gf[1] += 1
            H['last'] = d
            H['pos'].append(arr if arr else 0)
            if p.get('reductionKilometrique') and win_rk:
                H['rk'].append((p['reductionKilometrique'] - win_rk) / 1000.0)
            hp = H['hip'][course['hippo']]
            hp[0] += 1
            if arr == 1: hp[1] += 1
            if course.get('distance'): H['dist'].append(course['distance'])
            H['gain'] += (course.get('montantPrix') or 0) if arr == 1 else 0
            dr = self.d[p.get('driver') or '?']
            dr[0] += 1; dr[1] += (arr == 1); dr[2] += fault
            tr = self.t[p.get('entraineur') or '?']
            tr[0] += 1; tr[1] += (arr == 1)
            pa = self.p[(hk, p.get('driver'))]
            pa[0] += 1; pa[1] += (arr == 1)

LONG_FEATS = ['h_n','h_win','h_t3','h_fault','h_days','h_nodate','h_last','h_last3',
              'h_rk','h_rkn','h_hip_n','h_hip_win','h_distfit','h_gpc',
              'd_n','d_win','d_fault','t_n','t_win','pair_n','pair_win']
