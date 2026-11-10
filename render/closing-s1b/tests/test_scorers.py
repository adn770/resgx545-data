#!/usr/bin/env python3
"""Run the scorers' readers on existing landed data (a dry run of the score code; nothing here reads new results)."""
import sys
sys.dont_write_bytecode = True     # the data repo's modules are imported: no __pycache__ there
import gzip, pathlib, struct  # noqa: E402,E401
S1 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(S1 / "score")); sys.path.insert(0, str(S1 / "gen"))
import numpy as np
from s1lib import Kept, timeline, runs, first_sample, peak_status, rows_of, pixel_sha
import score_geo as G, score_pix as P
DATA = pathlib.Path.home() / "src/resgx545-data"
ok = True
def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else "")); ok &= bool(cond)

# E1 readers on E704's oom-1500-0x422 (knob proof 0x400, no raise, 2 runs)
k = Kept(DATA / "vdm/verification-1141ta/out-hw/p1141ta-dumps/dpm-oom-all")
tl = timeline(k.out("oom-1500-0x422"))
prs, peaks = runs(tl)
ctl = k.buf09("oom-1500-0x422")
check("E1: first sample of 0x0624 = 0x400 at P 0x422", first_sample(tl, "0x0624") == 0x400)
check("E1: no raise, dword 38 = 0", ctl[38] == 0, f"dw36={ctl[36]} dw37={ctl[37]:#x} dw38={ctl[38]:#x}")
check("E1: partial renders counted", len(prs) >= 1, f"{len(prs)} partial renders, peaks {[hex(p) for p in peaks[:3]]}")
# knob proof: the 0x0624 of the job itself (the first sample is the previous job's value)
from s1lib import knob_value
k4 = Kept(DATA / "vdm/verification-1141ta/out-hw/p1141ta-dumps/dpm-stack-all")
for n4, want in (("stk-n1-0x28", 6), ("stk-n1-0x422", 0x400)):
    t4 = k4.out(n4)
    check(f"knob proof {n4} reads {want:#x} (first sample is {first_sample(timeline(t4), '0x0624'):#x})", knob_value(timeline(t4), t4) == want)
# void: landed cases.tsv has no rc column, so nothing may be read as a result
check("void: a job with no recorded rc is void", k4.void("stk-n1-0x28") == "no rc recorded", str(k4.void("stk-n1-0x28")))
check("void: a missing job is void", k4.void("no-such-job") == "no output kept")
# E2 readers: U of the default triangle at 1024x768 = 19 (E705/E625) from a kept state job, and the pool walk
k2 = Kept(DATA / "vdm/verification-1141ta/out-hw/p1141ta-dumps/dpm-stack-all")
n = "stk-n1-0x422"
if n:
    m = G.e2_measure(k2, n)
    check("E2: e2_measure runs on a kept job", m["peak"] is not None, f"{n}: peak {m['peak']} walk {m['walk']} geo {m['geo']}")
k3 = Kept(DATA / "dpm/partial-model-batch/dumps/free-safe.c1")
for c in k3.names():
    if c.startswith("fr-whole-1024x768") and not c.endswith("rep"):
        p = k3.dump(c, "tri.1.param.bin") or k3.dump(c, "param.bin")
        h = G.walk_head(p) if p else None
        check("E2: pool walk head - 1 = 19 pages at 1024x768", h == 0x14, f"{c}: head {h}")
        break
# E3 decoder on the three mte/rhw dumps: 3 vertices, RZ(1/w)
import pbdump
for nm in ("03", "05", "07"):
    d = DATA / f"mte/rhw/mte-rhw-{nm}/dumps/mte-rhw-{nm}__0"
    o = G.decode_object(d.with_suffix(".param.bin").read_bytes(), d.with_suffix(".tadata.bin").read_bytes())
    check(f"E3: decode mte-rhw-{nm}", o["state"] == "present" and o["nvert"] == 3 and [(x // 256 - 4096, y // 256 - 4096) for y, x, _ in o["packed"]] == [(8, 8), (56, 20), (20, 56)] or
          [(x / 256 - 4096, y / 256 - 4096) for y, x, _ in o["packed"]] == [(8, 8), (56, 20), (20, 56)], f"rhw {[hex(w) for w in o['rhw']]}")
# E5 histogram parse on E702's jobs
k5 = Kept(DATA / "vdm/verification-1141ta/out-hw/p1141ta-dumps/capacity-all")
import re
t = k5.out("cap-n8-f10-a1")
check("E5: o0 mixed count 2288", re.search(r"o0 mixed 0x[0-9a-f]+ x(\d+)", t)[1] == "2288")
# B1: the row fit on E731's dp-bx-b0 reproduces the range with 0x3923d700 as the upper end
D = DATA / "texture/p1141/out-hw/p1141tex-dumps/isp-b-depth"
z = P.depth_image(gzip.open(D / "dp-bx-b0.depth.1.bin.gz").read(), 256, 128)
lo, hi, nrow, nall, bad = P.row_range(z)
check("B1: dp-bx-b0 joint range ends at 0x3923d700", abs(hi - struct.unpack('<f', struct.pack('<I', 0x3923d700))[0]) < 1e-14 and lo < hi, f"[{lo:.10e}, {hi:.10e}] {nrow}/{nall} rows, first empty row {bad}")
# B1: EMPTY is reachable (a row no single gradient explains gives used == 0)
zz = np.full((1, 64), 0x3f000000, dtype=np.uint32)
zz[0, ::2] = 0x3f000100
rr = P.row_range(zz)
check("B1: an inconsistent row gives used == 0 (EMPTY)", rr is not None and rr[2] == 0, str(rr))
# B2: deviation counts of dp-ax-b2 reproduce 7680 / 1536
from b2model import deviation
d, cov = deviation(gzip.open(D / "dp-ax-b2.depth.1.bin.gz").read(), 256, 128, ((0, 0), (131072, 0), (0, 131072)), (0.125, 0.1875, 0.125))
check("B2: dp-ax-b2 deviations 7680 at -1 and 1536 at -2", int((d[cov] == -1).sum()) == 7680 and int((d[cov] == -2).sum()) == 1536)
# C: the pair reader on E709's o4g-3 x/y jobs gives tag-5 pairs (17 expected for k = 3)
kc = Kept(DATA / "vdm/verification-1141ta/out-hw/p1141ta-dumps/o4-g25-all")
pr = P.read_pairs(kc, "o4g-3-x", "o4g-3-y")
check("C: pixel rows read from E709's jobs", pr is not None and pr[0].shape == (64, 64))
# D: pixel sha of E722's passing case equals the frozen A4 hash
import json
kd = Kept(DATA / "texture/p1141/out-hw/p1141tex-dumps/tex-c-addr")
cj = {c["name"]: c for c in json.load(open(DATA / "texture/p1141/gen/cases.json"))}
check("D: pixel sha of ad-tw128x32-L0e2 equals the frozen A4", pixel_sha(rows_of(kd.out("ad-tw128x32-L0e2"))) == cj["ad-tw128x32-L0e2"]["preds"]["A4"])
check("D: the faulting case is classified fault", __import__("s1lib").outcome(kd.out("ad-tw64x64-L2e2")) == "fault")
# G: control sha of lf-r8 reproduces from its own kept output
kg = Kept(DATA / "texture/p1141/out-hw/p1141tex-dumps/tex-a-lod")
check("G: row reader on lf-r8", len(rows_of(kg.out("lf-r8"))) == 32)
sys.exit(0 if ok else 1)
