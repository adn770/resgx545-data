#!/usr/bin/env python3
"""The timeline reader and the two frozen rules (score/r4tl.py) on the REAL kept records of round 3 (published copy of closing-r3-pixel):
the TA rule (bit 7 set iff L >= 129.5 us, clear below 122, edge to 136, the latch 118..138 us after the run) on E807's 74 vertex-loop jobs
(0 on the wrong side), the fill rule (tile time (B - 60.2) / 4 against 118 / 132 us) on the 106 load-free fills of E804 / E805 (0 on the
wrong side), the reader on synthetic timelines, and the agreement of the fill rule with sgx-pipe's `events::status2_bit6` (constants and
shape read from the landed source: score/r4tl.py must not drift from it).  Prints ok / FAIL; exit 1 on any FAIL."""
import collections
import gzip
import os
import pathlib
import re
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R4 / "score"), str(R4 / "tests")]
import r4lib as L  # noqa: E402
import r4tl as T  # noqa: E402
import worlds as W  # noqa: E402

MAIN = pathlib.Path(os.environ.get("RESGX545_MAIN", str(pathlib.Path.home() / "src/resgx545")))
DATA = pathlib.Path(os.environ.get("RESGX545_DATA", str(pathlib.Path.home() / "src/resgx545-data")))
OUT = DATA / "render/closing-r3-pixel/out/20261110-160415"
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def real(st):
    for f in sorted(os.listdir(OUT / st)):
        if f.endswith(".txt.gz") and not any(x in f for x in (".regs", ".dmesg", "health")):
            yield f[:-7], gzip.open(OUT / st / f, "rt", errors="replace").read()


# ---- the TA rule on E807's jobs
res, bad, lat = collections.Counter(), [], []
for name, txt in real("q-v"):
    r = T.ta_run(txt)
    if r is None:
        continue
    v = T.verdict(T.bit7_rule(r["L"]), r["bit7"])
    res[v] += 1
    if v is False:
        bad.append((name, r["L"], r["bit7"]))
    if r["bit7"]:
        lat.append(T.LATCH7[0] <= r["d7"] <= T.LATCH7[1])
check("TA rule on E807's 74 kept vertex-loop jobs: 0 on the wrong side", sum(res.values()) == 74 and not bad and res[True] + res[None] == 74, f"{dict(res)} {bad}")
check("... 69 on the predicted side, 5 in the edge band 122..136 us", res[True] == 69 and res[None] == 5, str(dict(res)))
check("the latch window: bit 7 shows 118..138 us after the run began in all 39 set jobs", len(lat) == 39 and all(lat), f"{len(lat)} {sum(lat)}")
# ---- the fill rule on E804 / E805's fills
res, bad, n = collections.Counter(), [], 0
for st in ("q-f0", "q-f1a", "q-f1b"):
    for name, txt in real(st):
        if "ld8" in name:
            continue
        b = L.burst(txt)
        if not b:
            continue
        n += 1
        v = T.verdict(T.bit6_rule(T.tile_time(b["B"])), b["t6"] is not None)
        res[v] += 1
        if v is False:
            bad.append((st, name))
check("fill rule on the 106 load-free fills of R3-pixel: 0 on the wrong side (92 on the predicted side, 14 in the edge)", n == 106 and not bad and res[True] == 92 and res[None] == 14, f"{n} {dict(res)} {bad}")
# ---- synthetic timelines through the reader
for Lus, d7, rule in ((60.0, None, "clear"), (129.0, None, "edge"), (140.0, 125.0, "set"), (0.0, None, "clear")):
    r = T.ta_run(W.timeline_ta(Lus, d7))
    check(f"reader: synthetic TA run L = {Lus}, d7 = {d7}: L within one sample, rule {rule}",
          r is not None and abs(r["L"] - Lus) <= 5.0 and T.bit7_rule(r["L"]) == rule and ((r["d7"] is None) == (d7 is None)), str(r))
r = T.ta_run(W.timeline_ta(140.0, 125.0))
check("reader: d7 of a synthetic job is within one sample of the placed 125 us", abs(r["d7"] - 125.0) <= 5.0, str(r["d7"]))
check("reader: a text without a timeline reads None", T.ta_run("probe x: o0 0x1 (1 of 1)\n") is None and T.parse("") == (None, []))
check("verdict: an edge is not scored, a match is held, a mismatch is false", T.verdict("edge", True) is None and T.verdict("set", True) is True and T.verdict("clear", True) is False)
# ---- agreement with sgx-pipe
src = (MAIN / "crates/sgx-pipe/src/events.rs").read_text()
m = re.search(r"BIT6_EDGE_US: \(f64, f64\) = \(([\d.]+), ([\d.]+)\)", src)
check("sgx-pipe's BIT6_EDGE_US is the edge of r4tl.BIT6_EDGE (118, 132)", m and (float(m[1]), float(m[2])) == T.BIT6_EDGE, str(m and m.groups()))
m = re.search(r"fn tile_time_us\(burst_us: f64\) -> f64 \{\s*\(burst_us - ([\d.]+)\) / ([\d.]+)\s*\}", src)
check("sgx-pipe's tile time is (B - 60.2) / 4 as r4tl.tile_time", m and (float(m[1]), float(m[2])) == (T.B0, T.TILES), str(m and m.groups()))
check("sgx-pipe's status2_bit6 speaks for a 64 x 32 fill without a load only (the rule's scope)", "Work::Fill { w: 64, h: 32, load: false } => {}" in src and "Work::Fill { load: true, .. }" in src)
for tau in (36.0, 117.9, 132.1, 307.0):
    pipe = "false" if tau < 118.0 else "true"
    check(f"tile time {tau}: r4tl and sgx-pipe's thresholds give the same side", (T.bit6_rule(tau) == T.SET) == (pipe == "true"))
sys.exit(0 if ok else 1)
