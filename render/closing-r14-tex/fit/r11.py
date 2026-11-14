"""POST HOC (r14-tex build, before the run): E723's kept r11 point jobs (tx_map_r11.s, the
sample's second dword) against decodes of texel bytes 2 and 3, texel per pixel by texmodel.py
(point sampling returns the texel's dword); the r10 jobs as the check. The premise of srgb4's
alpha forms (README.md "Deviations" 3)."""
import collections, gzip, json, math, os, sys, subprocess, struct
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import srgb as S, tex, pins
R = S.rule()
TM = pins.module("data:texture/p1141/support/texmodel.py")
def g(p): return subprocess.run(["git","-C","/Users/jtorra/src/resgx545-data","show","3309b5fd9:"+p],capture_output=True).stdout
cases={c['name']:c for c in json.loads(g("texture/p1141/gen/cases.json"))}
def h_lin(b): return R.half_rne(b/255.0)
def h_srgb(b): return R.half_rne(R.s2l(b))
for n in ("g-st8x4-r11","g-tw8x8-r11","g-st8x4","g-tw8x8"):
    px = pins.pixels(gzip.decompress(g("texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/%s.txt.gz"%n)).decode())
    sp=cases[n]['spec']
    tx = TM.render(sp)
    hits=collections.Counter(); lo=collections.Counter(); hi=collections.Counter()
    for p,v in enumerate(px):
        b=[tx[p]>>8*i&255 for i in range(4)]
        for nm,f in (("srgb b2 | lin b3",lambda: h_srgb(b[2])|h_lin(b[3])<<16),("both srgb",lambda: h_srgb(b[2])|h_srgb(b[3])<<16),("both lin",lambda: h_lin(b[2])|h_lin(b[3])<<16),("r10 form",lambda: h_srgb(b[0])|h_srgb(b[1])<<16)):
            hits[nm]+= f()==v
        lo[(v&0xffff)==h_srgb(b[2])]+=1; hi[(v>>16)==h_lin(b[3])]+=1
    print(n, len(set(px)), dict(hits), "lo=srgb(b2)",dict(lo),"hi=lin(b3)",dict(hi))
