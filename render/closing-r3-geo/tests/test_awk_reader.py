#!/usr/bin/env python3
"""The laptop-side awk twins of the scorer's readers (run/dpm_read.awk, run/bis.awk) against score/dpm3.py: the runner derives its gates
and bisect cells from the kept output in awk, the scorer reads the same output in Python; both must agree.
  1. every kept DPM job of R1 and R2 (73 jobs with a timeline) and the synthetic worlds: nparts, thr0, reach, valid, knob, page need and
     the first and last abort's 0x072c count read by awk equal dpm3's;
  2. bis.awk against dpm3.pick / bracket on 3000 random observation sets (a raise set, a silent set, void cells): the midpoint, the L and
     F references and every refusal (no raise, non-monotone, no silent cell above, closed, void inside) agree;
  3. the raise word: dword 38 read with od from a buf09 file equals dpm3's.
Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import pathlib  # noqa: E402
import random  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "score"), str(R3 / "gen"), str(R3 / "tests")]
import dpm3  # noqa: E402
import world_r3 as W  # noqa: E402
from r1lib import Kept  # noqa: E402

(R3 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R3 / "debug/tmp")
C2 = pathlib.Path.home() / "src/scratch/resgx545/closing2"
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def awk_read(txt):
    r = subprocess.run(["awk", "-f", str(R3 / "run/dpm_read.awk")], input=txt, capture_output=True, text=True)
    return dict(kv.split("=") for kv in r.stdout.split())


def same(a, j):
    c = j["cnt"] or dict(before=[])
    return (int(a["nparts"]) == j["nparts"] and int(a["thr0"], 16) == (j["thr0"] or 0) and int(a["reach"]) == int(j["reach"])
            and int(a["valid"]) == int(j["valid"]) and int(a["knob"], 16) == j["knob"] and int(a["need"]) == j["need"]
            and int(a["c1"]) == (c["before"][0] if c["before"] else 0) and int(a["cN"]) == (c["before"][-1] if c["before"] else 0))


n = bad = 0
for sess, st in [("r1-pixgeo", s) for s in ("g-u1", "g-c1", "g-c1f", "g-u2")] + [("r2-geo", s) for s in ("g-c3", "g-c2")]:
    k = Kept(C2 / sess / "out" / st)
    for name in k.names():
        j = dpm3.read_job(k, name, knob_proof=False)
        if j.get("void") or j["cnt"] is None:
            continue
        n += 1
        a = awk_read(k.out(name))
        if not same(a, j):
            bad += 1
            print("   mismatch", st, name, a, {x: j[x] for x in ("nparts", "thr0", "reach", "valid", "knob", "need")}, j["cnt"] and j["cnt"]["before"])
check(f"dpm_read.awk equals dpm3 on {n} kept jobs of R1 and R2 (nparts, thr0, reach, valid, knob, need, first and last count)", n >= 70 and bad == 0, f"{bad} of {n} differ")
world = W.World(lambda j: 0xd4)
bad = 0
for thr0, need in ((0xc0, 531), (0x100, 531), (0x140, 531), (0x80, 531), (0x400, 531), (0x60, 531), (0x300, 2124), (0x2c0, 2124), (0x1c6, 1062)):
    text, buf = W.job_reading(world, "probe --tri pixel --width 2048 --height 2048 --vertices 1500", thr0)
    d = pathlib.Path(tempfile.mkdtemp())
    W.write_job(d, [], "x", "t", "heldout", hex(thr0 + 0x22), "-", "-", 3, "ok", text, buf)
    j = dpm3.read_job(Kept(d), "x")
    if not same(awk_read(k.out("x") if False else Kept(d).out("x")), j):
        bad += 1
        print("   world mismatch", thr0, need, awk_read(Kept(d).out("x")), j["nparts"], j["thr0"])
check("dpm_read.awk equals dpm3 on synthetic jobs (no abort, one, several; thr0 0x60 .. 0x400)", bad == 0, f"{bad} differ")
# the raise word
d = pathlib.Path(tempfile.mkdtemp())
text, buf = W.job_reading(W.World(lambda j: 0xd4), "probe --tri pixel --width 2048 --height 2048 --vertices 1500", 0xc0)
import struct  # noqa: E402
(d / "b.bin").write_bytes(struct.pack("<59I", *buf))
od = subprocess.run(["od", "-An", "-tu4", "-j152", "-N4", "-v", str(d / "b.bin")], capture_output=True, text=True).stdout.strip()
check("od -j152 -N4 reads dword 38 of buf09 (0x20 = 32 on a raise)", od == "32" and buf[38] == 0x20, od)
# bis.awk on random observation sets
rnd = random.Random(20261110)
mism = 0
runs = 3000


def bis(obs, mode, off=0):
    f = pathlib.Path(tempfile.mkdtemp()) / "obs"
    f.write_text("".join(f"{t} {c} j{t}\n" for t, c in obs.items()))
    r = subprocess.run(["awk", "-v", f"mode={mode}", "-v", f"off={off}", "-f", str(R3 / "run/bis.awk"), str(f)], capture_output=True, text=True)
    return r.stdout.strip()


def twin(obs, mode, off=0):
    if mode == "B":
        t, why = dpm3.pick(obs)
        return str(t) if t is not None else "SKIP"
    lo, hi, why = dpm3.bracket(obs)
    if why == "not monotone":
        return "SKIP"
    if mode == "L":
        return str(lo + off) if lo is not None else "SKIP"
    return str(hi + off) if hi is not None else "SKIP"


for _ in range(runs):
    cells = rnd.sample(range(0x60, 0x140), rnd.randint(1, 9))
    cut = rnd.choice(cells)
    obs = {}
    for t in cells:
        c = ("R" if t <= cut else "N") if rnd.random() > 0.15 else rnd.choice("RNV")
        if rnd.random() < 0.1:
            c = "V"
        obs[t] = c
    for mode, off in (("B", 0), ("L", 0), ("F", 0), ("L", -16), ("F", 4)):
        a, b = bis(obs, mode, off), twin(obs, mode, off)
        a1 = a.split()[0] if a else ""
        if a1 != b:
            mism += 1
            print("   bis mismatch", obs, mode, off, a, b)
            break
    if mism > 3:
        break
check(f"bis.awk equals dpm3.pick / bracket on {runs} random observation sets (B, L, F, offsets, every refusal)", mism == 0, f"{mism} differ")
sys.exit(0 if ok else 1)
