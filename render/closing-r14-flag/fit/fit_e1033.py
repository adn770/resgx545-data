# SPDX-License-Identifier: MIT
"""fit_e1033.py: the builder's post hoc search (before the freeze) of address forms for E1033's two
fault pages (f1-tw32 scratch + 0x21000, f1-small + 0x40000; 16 scratch pages and 3 coordinate
pages mapped). For each layout (E561's tile law at a tile-row pitch, or plain Morton), column form
and row form it prints the forms that put both kept pages among the unmapped pages they read,
with the first unmapped page in raster order and the lowest; f1-zero (u = 0) for comparison.
gen/f1.py freezes three of them (pitch 4096 or 4128, column s + floor(4096 fr) or floor(4096
fr)); fit_e1033.out is its output. Standard library only: `python3 fit/fit_e1033.py`."""
from fractions import Fraction as F
import itertools
def morton(x, y, w, h):
    bw, bh = max(w, 1).bit_length() - 1, max(h, 1).bit_length() - 1
    common = min(bw, bh); i = 0
    for b in range(common):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    rest = (x if bw > bh else y) >> common
    return i | rest << (2 * common)
def tl(s, t, w):
    return morton(s % 16, t % 16, 16, 16) + 256 * (s // 16 + (w // 16) * (t // 16))
MAPPED = 19456  # dwords mapped from the scratch start (16 pages + 3 coordinate pages)
def rows(job):
    for y in range(32):
        for x in range(64):
            if job == "tw32":
                q = x & 31; u = 1 + F(2*q+1, 64); v = 1 + F(2*y+1, 64)
            elif job == "small":
                u = F(x, 4096); v = F(2*y+1, 64)
            else:
                u = F(0); v = F(2*y+1, 64)
            yield x, y, u, v
fl = lambda f: int(f.__floor__())
S_OPTS = {
 "s": lambda u: fl(u*32) % 32,
 "s+m": lambda u: fl(u*32) % 32 + fl(4096*min(max(u,0),1)),
 "su+m": lambda u: fl(u*32) + fl(4096*min(max(u,0),1)),
 "s+4096u": lambda u: fl(u*32) % 32 + fl(4096*u),
 "s+4096fr": lambda u: fl(u*32) % 32 + fl(4096*(u - fl(u))),
 "u*4128": lambda u: fl(u*4128),
 "fr*4128": lambda u: fl((u-fl(u))*4128),
 "fr*4096": lambda u: fl((u-fl(u))*4096),
 "u*4096c": lambda u: fl(min(max(u,0),1)*4096),
 "s+fr*4096+32": lambda u: fl(u*32) % 32 + fl(4096*(u - fl(u))) + 32,
}
T_OPTS = {"t": lambda v: fl(v*32) % 32, "tu": lambda v: fl(v*32)}
LAYOUTS = {f"TL{w}": (lambda w: lambda s, t: tl(s, t, w))(w) for w in (32, 64, 128, 256, 512, 1024, 2048, 2112, 4096, 4112, 4128, 4160, 8192, 8224)}
LAYOUTS["MORT"] = lambda s, t: morton(s, t, 1 << 16, 1 << 16)
LAYOUTS["MORTyx"] = lambda s, t: morton(t, s, 1 << 16, 1 << 16)
OBS = {"tw32": 0x21000 // 4096, "small": 0x40000 // 4096}
for (ln, L), (sn, Sf), (tn, Tf) in itertools.product(LAYOUTS.items(), S_OPTS.items(), T_OPTS.items()):
    res = {}
    for job in ("tw32", "small", "zero"):
        first = None; pages = set(); mx = 0
        for x, y, u, v in rows(job):
            a = L(Sf(u), Tf(v)); mx = max(mx, a)
            if a >= MAPPED:
                p = a // 1024; pages.add(p)
                if first is None: first = p
        res[job] = (first, min(pages) if pages else None, p in pages if False else pages, mx)
    ok = all(OBS[j] in res[j][2] for j in OBS)
    okf = all(res[j][0] == OBS[j] for j in OBS)
    okm = all(res[j][1] == OBS[j] for j in OBS)
    if ok:
        print(f"{ln:8} {sn:9} {tn:3} first={okf} min={okm} tw32 first {res['tw32'][0]} min {res['tw32'][1]} max {res['tw32'][3]}; small first {res['small'][0]} min {res['small'][1]} max {res['small'][3]}; zero first {res['zero'][0]} max {res['zero'][3]}")
