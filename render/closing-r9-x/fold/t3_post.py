# SPDX-License-Identifier: MIT
"""fold/t3_post.py: r9-x t3 post hoc (not frozen): on the six bit-14 rows, the read offset
d = kept dword - reference dword (both kept), against S, W, H and the pixel's u and v; candidate
offsets formed after the run are printed with their counts (post hoc, stated as such)."""
import collections, gzip, math, os, re, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import t3 as T3, tex
D = os.path.join(KP, "out/20261113-081821/t3")
ROW = re.compile(r"row (\d+): ([0-9a-f ]+)$", re.M)
def px(n):
    t = gzip.open(os.path.join(D, n + ".txt.gz"), "rt").read()
    r = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()] for m in ROW.finditer(t)}
    return [v for y in sorted(r) for v in r[y]]
for name, w, h, s, u in T3.B14ROWS:
    k, ref = px(name), px(name + "-ref")
    d = collections.Counter()
    cands = collections.Counter()
    for p, (a, b) in enumerate(zip(k, ref)):
        x, y = p % 64, p // 64
        uu = tex.coord(u, x, y); vv = tex.coord(T3.V32, x, y)
        dd = (a & 0xFFFFFFF) - (b & 0xFFFFFFF)
        d[dd] += 1
        uc = min(max(uu, 0), 1)
        for nm, val in (("S*S*u01", math.floor(s * s * uc)), ("S*min(S,64)*u01", math.floor(s * min(s, 64) * uc)),
                        ("64*S*u01", math.floor(64 * s * uc)), ("S*W*u01... ", math.floor(s * w * uc)),
                        ("S*S*u01 mod S*H", math.floor(s * s * uc) % (s * h)), ("4096*u01 (R-4096)", math.floor(4096 * uc))):
            cands[nm] += dd == val
    print(f"{name} W{w} H{h} S{s}: {len(d)} distinct offsets, e.g. {sorted(d.items())[:4]} ... {sorted(d.items())[-2:]}")
    print("   ", dict(cands))
