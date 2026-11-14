"""POST HOC (r14-tex build, before the run; fitted on r13-tex's kept srgb3-tri only): a declared
family of third-stage forms (operand grid 2^(e - n), the difference floored to m bits or not,
ties up / even / toward zero, the exponent of the larger operand or of the result), halves exact
of 4096. Its best, n = 15 ties up, is frozen as TRI-G15 (README.md "Deviations" 1)."""
import collections, gzip, math, os, sys, subprocess
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import srgb as S, tex, pins
F = tex.F
R = S.rule()
raw = subprocess.run(["git","-C","/Users/jtorra/src/resgx545-data","show","3309b5fd9:render/closing-r13-tex/out/20261113-214825/srgb3/srgb3-tri.txt.gz"],capture_output=True).stdout
px = pins.pixels(gzip.decompress(raw).decode())
sp = S.tri_spec()
data=[]
for p, v in enumerate(px):
    x, y = p % 64, p // 64
    u, vv = tex.coord(sp["u"], x, y), tex.coord(sp["v"], x, y)
    a = S.level_bilinear(R, u, vv, 1, "out"); b = S.level_bilinear(R, u, vv, 2, "out")
    for c in (0,1):
        data.append((F(R.h2f(a[c])), F(R.h2f(b[c])), v >> 16*c & 0xFFFF))
def fl(x,g): return math.floor(x/g)*g
def rnd(r, mode):
    if mode=="rhu": return R.half_rhu(r)
    if mode=="rne": return R.half_rne(float(r))
    if mode=="rz":
        h=R.half_rne(float(r)); return h-1 if F(R.h2f(h))>r else h
def form(A,B,k,opbits,mode,diffbits,which):
    # which: exponent reference 'max','res'
    if which=='max': e=max(R.expo(float(A)),R.expo(float(B)))
    else: e=R.expo(float(A+F(k,64)*(B-A)))
    g=F(2)**(e-opbits)
    qa,qb=fl(A,g),fl(B,g)
    d=qb-qa
    if diffbits:
        gd=F(2)**(R.expo(float(d)) - diffbits) if d else 1
        d=fl(d,gd) if d>=0 else -fl(-d,gd)
    return rnd(qa+F(k,64)*d, mode)
res=[]
for opbits in (11,12,13,14,15,16,18,20,24,40):
  for mode in ("rhu","rne","rz"):
    for diffbits in (0,11,12,13,14,16):
      for which in ("max","res"):
        n=sum(form(A,B,16,opbits,mode,diffbits,which)==g for A,B,g in data)
        res.append((n,opbits,mode,diffbits,which))
res.sort(reverse=True)
for r in res[:15]: print(r)
