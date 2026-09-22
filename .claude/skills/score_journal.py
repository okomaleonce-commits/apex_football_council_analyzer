import math
# (course, [(num, nom, p_apex, p_marche_au_moment_analyse, cote_analyse, p_chute)], gagnant, non_finissants)
R = {
 "R2C1 Borely (trot)": dict(
   rows=[(5,"JOLIE COSTARDIERE",.557,.463,1.8,.184),(3,"JURDIG LESMELCHEN",.098,.117,7.1,.133),
         (10,"INDESKAYA BIRD",.080,.094,8.9,.118),(11,"GAETAN",.068,.083,10.0,.079),
         (9,"HARMONICA",.059,.083,10.0,.082),(1,"JASMIN DE LARRE",.044,.040,21.0,.254),
         (8,"JOYAU BLUE",.029,.038,22.0,.103),(6,"HATOUT DE CONNEE",.029,.038,22.0,.103),
         (2,"JALAPA",.013,.014,59.0,.240),(7,"GABARRET DAIRPET",.012,.017,48.0,.105),
         (4,"JERELDA",.010,.013,66.0,.138)],
   arrivee=[6,5,3], nonfin=[]),
 "R2C2 Borely (trot)": dict(
   rows=[(11,"NADER",.388,.325,2.6,.299),(5,"NORREY",.149,.143,5.9,.135),
         (1,"NOLAN D'OR",.131,.141,6.0,.233),(2,"NINAMYS",.084,.085,10.0,.300),
         (4,"NICE PARIS",.061,.077,11.0,.211),(8,"NEW HOT SUMMER",.061,.070,12.0,.192),
         (13,"NAOS DELTO",.024,.037,23.0,.147),(3,"NANDY COOL",.023,.023,36.0,.233),
         (7,"NAOS DE CHOC",.016,.022,39.0,.106),(10,"NOVA",.015,.017,50.0,.239),
         (15,"NIGHT DES FORGES",.012,.017,51.0,.174),(14,"NAOMIE FAMILY",.012,.015,57.0,.202),
         (12,"NORTHFIELDS",.011,.011,74.0,.361),(9,"NIZONNE",.008,.009,90.0,.166),
         (16,"NOVA DE VISAIS",.005,.008,110.0,.090)],
   arrivee=[4,11,5], nonfin=[9,13]),
 "R1C1 Auteuil (obstacle)": dict(
   rows=[(2,"DOCTORINO",.374,.415,2.0,.145),(1,"WANTOKNOWHATLOVEIS",.239,.224,3.7,.150),
         (9,"NECTAR DES DIEUX",.095,.083,10.0,.232),(5,"RATOUNET",.088,.083,10.0,.170),
         (7,"TACTICIEN",.081,.069,12.0,.178),(4,"NORTH SEA",.042,.044,19.0,.181),
         (6,"DEAL DAILY",.037,.038,22.0,.211),(3,"SEVERAN",.023,.021,40.0,.261),
         (8,"NATIVE RULER",.022,.023,36.0,.177)],
   arrivee=[4,2,5], nonfin=[3,8,9]),
}
print(f"{'course':<26} {'vainqueur':<20} {'rang APEX':>9} {'p_APEX':>7} {'p_marche':>9} {'LL_APEX':>8} {'LL_marche':>10}")
la=[];lm=[]
for k,v in R.items():
    rows=sorted(v['rows'],key=lambda r:-r[2]); w=v['arrivee'][0]
    r=[x for x in v['rows'] if x[0]==w][0]
    rank=[i for i,x in enumerate(rows,1) if x[0]==w][0]
    a=-math.log(r[2]); m=-math.log(r[3]); la.append(a); lm.append(m)
    print(f"{k:<26} {r[1][:20]:<20} {rank:>4}/{len(rows):<4} {r[2]*100:>6.1f}% {r[3]*100:>8.1f}% {a:>8.3f} {m:>10.3f}")
print(f"\n{'MOYENNE':<26} {'':<20} {'':>9} {'':>7} {'':>9} {sum(la)/3:>8.3f} {sum(lm)/3:>10.3f}")
print(f"-> sur ces 3 courses le moteur est {'MOINS BON' if sum(la)>sum(lm) else 'meilleur'} que le marche de {abs(sum(la)-sum(lm))/3:+.3f}\n")

print("=== positions occupees par le top 3 du classement APEX ===")
for k,v in R.items():
    rows=sorted(v['rows'],key=lambda r:-r[2])
    pos={n:i for i,n in enumerate(v['arrivee'],1)}
    out=[]
    for i,x in enumerate(rows[:3],1):
        p=pos.get(x[0]); s=f"{p}e" if p else ("NF" if x[0] in v['nonfin'] else "non place")
        out.append(f"APEX#{i} {x[1][:16]} -> {s}")
    print(f"  {k:<26} " + " | ".join(out))

print("\n=== porte de risque : les non-finissants etaient-ils signales ? ===")
for k,v in R.items():
    if not v['nonfin']:
        print(f"  {k:<26} aucun non-finissant"); continue
    byrisk=sorted(v['rows'],key=lambda r:-r[5])
    n=len(byrisk)
    print(f"  {k}  ({len(v['nonfin'])} non-finissants sur {n} = {len(v['nonfin'])/n*100:.0f}%)")
    for num in v['nonfin']:
        x=[y for y in v['rows'] if y[0]==num][0]
        rk=[i for i,y in enumerate(byrisk,1) if y[0]==num][0]
        print(f"     {x[1][:20]:<20} P(risque)={x[5]*100:4.1f}%  -> rang {rk}/{n} du risque estime")
    print(f"     les 3 plus a risque estimes : " + ", ".join(f"{y[1][:14]} {y[5]*100:.0f}%" for y in byrisk[:3]))
