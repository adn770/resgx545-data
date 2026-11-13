#!/usr/bin/env python3
"""Q030 offline (round 10): which sample-slot sets the kept seam1/seam4 images of r9-geo (E953, E954)
can tell apart in the tiles past the first, under the landed region model. Rivals frozen in
q030_slots_rule.json. Standard library only; loads the published msaa_model.py (sha checked)."""
import gzip, hashlib, importlib.util, os, re, sys
DATA = "/Users/jtorra/src/resgx545-data"
S = DATA + "/render/closing-r9-geo"
HERE = os.path.dirname(os.path.abspath(__file__))
assert hashlib.sha256(open(HERE + "/q030_slots_rule.json", "rb").read()).hexdigest() == \
    open(HERE + "/q030_slots_rule.sha256").read().split()[0]
mp = DATA + "/texture/p1141/recompute/msaa_model.py"
assert hashlib.sha256(open(mp, "rb").read()).hexdigest().startswith("1c0e8205")
spec = importlib.util.spec_from_file_location("msaa_model", mp); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
sys.path.insert(0, S + "/gen")
import seam as G
E = M.SAMP
RIV = {"S-E281": E, "S-CENTRE": [(8, 8)] * 4, "S-MIRX": [(16 - x, y) for x, y in E],
       "S-MIRY": [(x, 16 - y) for x, y in E], "S-TRANS": [(y, x) for x, y in E],
       "S-SWAP": [E[1], E[0], E[3], E[2]]}
OUT = S + "/out/20261113-081038/"
def pixels(text, w, h):
    out = {}
    for m in re.finditer(r"row (\d+): ([0-9a-fx ]+)$", text, re.M):
        y = int(m.group(1))
        for x, t in enumerate(m.group(2).split()):
            out[(x, y)] = int(t, 16)
    return out if len(out) == w * h else None
tot = {r: [0, 0, 0] for r in RIV}   # rows exact past tile 0, rows told apart from E281, pixels differing from kept
for stage in ("seam1", "seam4"):
    for name, st, w, h, mode, te, verts in G.jobs():
        f = OUT + stage + "/" + ("f4-" if stage == "seam4" else "") + name + ".txt.gz"
        if not os.path.exists(f): continue
        px = pixels(gzip.open(f, "rt").read(), w, h)
        if px is None: continue
        got = {p for p, v in px.items() if v == G.TRI}
        prims = G.prims(w, h, verts, M)
        line = []
        base = None
        for r, sl in RIV.items():
            pred = set(M.predict(prims, w, h, mode, te, slots=sl))
            past = lambda s: {p for p in s if p[0] >= 32 or p[1] >= 16}
            first = lambda s: {p for p in s if p[0] < 32 and p[1] < 16}
            dpast = len(past(pred) ^ past(got)); dfirst = len(first(pred) ^ first(got))
            if r == "S-E281": base = pred
            told = len(past(pred) ^ past(base))
            tot[r][0] += dpast == 0; tot[r][1] += told > 0; tot[r][2] += dpast
            line.append(f"{r} past {dpast} first {dfirst} vsE281 {told}")
        print(f"{stage} {name} m{mode} te {te:#x} {w}x{h} stored {len(got)}: " + "; ".join(line))
print("TOTAL (rows exact past tile 0, rows where the rival differs from E281 past tile 0, pixels off the kept image past tile 0):")
for r, v in tot.items(): print(" ", r, v)
