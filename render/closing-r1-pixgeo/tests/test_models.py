#!/usr/bin/env python3
"""The offline models of gen/r1models.py against the data they were read from (FIT checks, not evidence): HU1 on the 16
measured page needs, HU2's frozen values, the SH + zigzag + prim + depth model on the S1/S1b clipped objects, and the
clamp ladder's separating cells.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import json  # noqa: E402
import pathlib  # noqa: E402

R1 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R1 / "gen"), str(R1 / "score")]
import r1models as M  # noqa: E402
from r1lib import Kept  # noqa: E402
import score_geo2 as G  # noqa: E402
from rcommon import f32  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


D = M.default_tri
# measured U (E626/E705/E625/E735/E627): the default triangle at five grids, the four positions, E735's K scenes
meas = [((64, 64), 2), ((128, 128), 3), ((192, 128), 5), ((256, 256), 5), ((512, 384), 8), ((1024, 768), 19),
        ((4096, 4096), 287)]
bad = [(w, h, M.hu1(w, h, [D(w, h)])[0], u) for (w, h), u in meas if M.hu1(w, h, [D(w, h)])[0] != u]
check("HU1: the default triangle at 7 grids (2, 3, 5, 5, 8, 19, 287)", not bad, str(bad))
pos = [((192, 0), 20), ((384, 0), 17), ((576, 0), 12)]
bad = [(dx, M.hu1(1024, 768, [D(1024, 768, dx, 0)])[0], u) for (dx, _), u in pos if M.hu1(1024, 768, [D(1024, 768, dx, 0)])[0] != u]
check("HU1: 1024x768 moved (192,0) (384,0) (576,0) = 20 17 12", not bad, str(bad))
apart = [(0, 288), (-64, -240), (-768, -96)]
stacked = [(16, 0), (32, 0), (48, 0)]
U = json.load(open(pathlib.Path.home() / "src/resgx545-data/render/closing-s1/U.json"))
bad = []
for k in (2, 3, 4):
    for lay, mv in (("a", apart), ("s", stacked)):
        got = M.hu1(1024, 768, M.scene(1024, 768, mv[:k - 1]))[0]
        if got != U[f"u-{k}{lay}-0x422"]:
            bad.append((k, lay, got, U[f"u-{k}{lay}-0x422"]))
check("HU1: E735's six K-scenes as S1 measured them (U.json: 29 35 37, 19 22 22)", not bad, str(bad))
u2 = M.hu1(1024, 768, M.scene(1024, 768, [(-96, 0)]))[0]
check("HU1: E627's two-triangle scene is 24, inside the measured 23..26", 23 <= u2 <= 26, str(u2))
hu2 = {n: M.hu2(1024, 768, t) for n, t in (("ctl-1", [D(1024, 768)]), ("2a", M.scene(1024, 768, [(0, 288)])),
                                            ("m32", [D(1024, 768, 32, 0)]), ("4c", [D(1024, 768, a, b) for a, b in ((0, 0), (512, 0), (0, 384), (512, 384))]))}
check("HU2: coverage + 8 reproduces the proposal's bracket values (19, 23, 19, 24)",
      [hu2[k] for k in ("ctl-1", "2a", "m32", "4c")] == [19, 23, 19, 24], str(hu2))
# E625's boundary rule with HU1's U: the proposal's pair for the two-triangle scene (0x45/0x46) is U = 35's, not 24's
check("boundary pairs: U = 24 gives P = 0x39 / 0x3a, U = 21 gives 0x36 / 0x37; the proposal's 0x45 / 0x46 would be U = 36",
      (24 + 0x22 - 1, 24 + 0x22) == (0x39, 0x3a) and (21 + 0x22 - 1, 21 + 0x22) == (0x36, 0x37) and 36 + 0x22 - 1 == 0x45)
# ---- SH model on the measured clipped objects (S1b g-e3: e3z-cut-p, e3z-cut-m, e3z-flat099)
S1B = pathlib.Path.home() / "src/scratch/resgx545/closing/s1b-v2/out/g-e3"
k = Kept(S1B)
for nm, A, B in (("e3z-cut-p", 2.0, 1.0), ("e3z-cut-m", 2.0, -1.0), ("e3z-flat099", 0.0, 0.99)):
    d = G.decode_object(k.dump(nm, "param.bin"), k.dump(nm, "tadata.bin"))
    p = M.predict_zclip(A, B, "x")
    got_xy = G._xy(d)
    check(f"SH: {nm} vertices in stored order, prim list and depth words equal the measured object",
          G._near(got_xy, p["xy"], 1 / 256) and d["prims"] == p["prims"]
          and [z for _, _, z in d["packed"]] == [f32(x) for x in p["depth"]] and d["nvert"] == p["nv"],
          f"{[(round(a, 2), round(b, 2)) for a, b in got_xy]} {d['prims']}")
bad = [(A, B) for A, B in ((2.0, 0.5), (4.0, 0.0), (2.0, 1.0), (4.0, -1.0)) if not M.predict_zclip(A, B, "x")["xy"]]
check("SH: the new rows give a polygon", not bad)
p = M.predict_zclip(4.0, -1.0, "x")
check("SH: z = 4x - 1 clips B too (z = 2 > w): 4 vertices, not the proposal's 3 with B kept", p["nv"] == 4 and (56.0, 20.0) not in p["xy"],
      str(p["xy"]))
# ---- clamp ladder
for c, w, sep in ((6e-5, 1e-5, True), (1.5e-4, 1e-5, True), (2e-4, 1e-5, False), (6e-4, 1e-4, True), (7e-4, 1e-4, True),
                  (1.2e-3, 1e-4, True)):
    rz, rn = M.recip_words(M.bits(float(__import__("numpy").float32(c))))
    check(f"clamp {c:g}: RZ and RN of 1/clamp {'differ' if sep else 'agree'}", (rz != rn) == sep, f"{rz:#x} {rn:#x}")
rz, rn = M.recip_words(0x37fba882)
check("clamp control: RZ of 1/3e-5 is the measured 0x47023555 (E754 e3k-i-c3e5)", rz == 0x47023555 and rn == 0x47023556)
sys.exit(0 if ok else 1)
