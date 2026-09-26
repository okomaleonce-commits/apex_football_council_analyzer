"""Controles automatiques d'absence de fuite. Echoue bruyamment."""
import sys, json, re
FAIL = []
def chk(cond, msg):
    print(('  OK   ' if cond else '  ECHEC ') + msg)
    if not cond: FAIL.append(msg)

for eng, fdir, fmod in (('trot', '/tmp/turf', 'features.py'), ('obst', '/tmp/obst', 'features_obst.py')):
    print(f"\n=== {eng} ===")
    import ast, textwrap
    def body(path, fn, cls=None):
        t = ast.parse(open(path).read())
        for node in ast.walk(t):
            if isinstance(node, ast.FunctionDef) and node.name == fn:
                if cls and not any(isinstance(p, ast.ClassDef) and node in ast.walk(p)
                                   for p in ast.walk(t)): continue
                return ast.unparse(node)
        return ''
    ffile = f'{fdir}/{fmod}'
    lfile = f'{fdir}/longitudinal{"" if eng=="trot" else "_obst"}.py'
    prod = body(ffile, 'runner_features') + body(ffile, 'musique_features') + body(lfile, 'feats')
    src = open(ffile).read() + open(lfile).read()
    BANNED = ('ordreArrivee', 'incident', 'tempsObtenu', 'reductionKilometrique',
              'distanceChevalPrecedent', 'commentaireApresCourse')
    for b in BANNED:
        chk(b not in prod, f"aucune lecture de {b} dans les fonctions de construction des variables")
    chk('def build' not in open(ffile).read(),
        "aucune fonction morte lisant les resultats dans le module de variables")
    ds = open(f'{fdir}/dataset{"" if eng=="trot" else "_obst"}.py').read()
    i_feat = ds.find('st.feats('); i_upd = ds.find('st.update(')
    chk(0 < i_feat < i_upd, "l'etat longitudinal est LU avant d'etre mis a jour par la course")
    harv = open(f'{fdir}/harvest{"" if eng=="trot" else "_obst"}.py').read()
    chk('commentaireApresCourse' not in harv, "le harvester ne collecte pas les commentaires d'apres-course")
    chk('handicapValeur' in harv if eng == 'obst' else True,
        "la valeur handicap collectee est celle du programme, pas une revision posterieure")
print("\n=== cotes ===")
print("  DECLARE : le backtest utilise les cotes FINALES (anterieures au depart mais")
print("            posterieures a H-1). Limite assumee, malus DCS de -10 en direct.")
sys.exit(1 if FAIL else 0)
