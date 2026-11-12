#!/usr/bin/env python3
"""tests/test_gen.py: the generated tables and predictions of r5-render4x against the plan and the kept records they came from.
  - the generator reproduces every file on disk (rgen.py --check), the bins equal R4-G's published programs (rgen.py checks it);
  - the job count by stage (37), the limits (m 4, l 5, x 3, d 1, o 1, t 1), the knobs every row must carry;
  - every frozen rule prediction is the plan's table cell (typed here from exp-render4x-r5.md 3.2 to 3.5, independent of rules.py);
  - the rule fit is 13 of 13 for all eleven rules; every maximum's TA data fits the 4 MiB slot (the largest m4, 0x223000);
  - the doubled-grid header rule holds on the 12 kept four-array dumps (0 off: rgn_check.out) and the reader finds the dumps the tool
    writes, by verb, in R4-G's real o and t directories (the name census);
  - every page need of a control is its twins' (gen/twins.py) and s0's pages are the kept ones.
Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import gzip
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "gen"), os.path.join(KP, "score"), HERE]
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import twins as TW  # noqa: E402
import worlds as WD  # noqa: E402

PY = os.environ.get("PY", sys.executable)
bad = 0


def check(cond, msg):
    global bad
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        bad = 1


r = subprocess.run([PY, os.path.join(KP, "gen", "rgen.py"), "--check"], capture_output=True, text=True)
check(r.returncode == 0 and "DIFFERS" not in r.stdout, "rgen.py --check: every generated file is as on disk (%s)" % r.stdout.strip().splitlines()[-1:])

stages = open(os.path.join(KP, "stages.txt")).read().split()
check(stages == ["s0", "t", "o", "m", "l", "x", "d"], "stages in the plan's order: s0, t, o, m, l, x, d")
counts = {st: len(WD.table(st)) for st in stages}
check(counts == {"s0": 3, "t": 9, "o": 11, "m": 5, "l": 5, "x": 3, "d": 1} and sum(counts.values()) == 37, "37 jobs: %s" % counts)
lim = {st: int([ln for ln in open(os.path.join(KP, "tables", st + ".txt")) if ln.startswith("#limit")][0].split()[1]) for st in stages}
check(lim == {"s0": 1, "t": 1, "o": 1, "m": 4, "l": 5, "x": 3, "d": 1}, "fault limits m 4, l 5, x 3, d 1, o 1, t 1 (R5-4 a): %s" % lim)
for st in stages:
    for row in WD.table(st):
        k = row["knobs"].split()
        if row["args"].startswith("tri "):
            check("expectdiff" in k and "--keep-going" in row["args"], "%s/%s: a tri row with expectdiff and --keep-going" % (st, row["name"]))
        if st in ("o", "m", "l", "x", "d"):
            check("strict" in k, "%s/%s: strict health after a fault" % (st, row["name"]))
        if st in ("m", "l", "x", "d"):
            want = None if row["name"].startswith("m0") else "hypo:q292:%d" % lim[st]
            got = next((x for x in k if x.startswith("hypo:")), None)
            check(got == want, "%s/%s: hypothesis knob %s (m0 has none: a fault there stops the stage)" % (st, row["name"], got))
        check(("held" in k) == (st == "d"), "%s/%s: held only in d" % (st, row["name"]))

# the plan's tables, typed: F fault, c complete, ? no threshold (exp 3.2 m, 3.3 l, 3.4 x; d every rule F)
HT = ("TPC-d-rgn", "TPC-d-state", "TPC-rs-rgn", "TPC-rb-rgn")
PLAN = {
    "m0-1024x768-max2048x2048": dict({r: "c" for r in R.RULES}),
    "m1-1280x1024-max1280x1040": dict({r: "F" for r in R.RULES}, **{r: "c" for r in HT}),
    "m2-1280x1024-max2048x2048": dict({r: "F" for r in R.RULES}, **{r: "c" for r in HT}),
    "m3-1280x1024-max2048x1024": dict({r: "F" for r in R.RULES}),
    "m4-2048x1536-max4096x4096": dict({r: "F" for r in R.RULES}, **{r: "c" for r in HT}),
    "l1-2048x240": dict({r: "c" for r in HT}, **{"K-W": "F", "K-H": "c", "K-OR": "F", "K-AND": "c", "K-TPM": "c", "K-P": "c", "K-AREA": "c"}),
    "l2-256x1536": dict({r: "c" for r in HT}, **{"K-W": "c", "K-H": "F", "K-OR": "F", "K-AND": "c", "K-TPM": "c", "K-P": "c", "K-AREA": "c"}),
    "l3-768x2048": dict({r: "c" for r in HT}, **{"K-W": "c", "K-H": "F", "K-OR": "F", "K-AND": "c", "K-TPM": "F", "K-P": "F", "K-AREA": "F"}),
    "l4-1280x768": dict({r: "F" for r in HT}, **{"K-W": "F", "K-H": "c", "K-OR": "F", "K-AND": "c", "K-TPM": "?", "K-P": "?", "K-AREA": "?"}),
    "l5-1024x1024": dict({r: "F" for r in HT}, **{"K-W": "c", "K-H": "F", "K-OR": "F", "K-AND": "c", "K-TPM": "c", "K-P": "?", "K-AREA": "?"}),
    "x1-1024x512": {"TPC-d-rgn": "c", "TPC-d-state": "F", "TPC-rs-rgn": "c", "TPC-rb-rgn": "c"},
    "x2-1184x768": {"TPC-d-rgn": "c", "TPC-d-state": "F", "TPC-rs-rgn": "F", "TPC-rb-rgn": "F"},
    "x3-1024x800": {"TPC-d-rgn": "c", "TPC-d-state": "F", "TPC-rs-rgn": "c", "TPC-rb-rgn": "F"},
    "d1-1280x1024-held": dict({r: "F" for r in R.RULES}),
}
word = {"F": "fault", "c": "complete"}
for st in ("m", "l", "x", "d"):
    P = L.load_predictions(st + ".tsv", KP)
    for case, cells in PLAN.items():
        if not any(c == case for c, _ in P):
            continue
        diff = [r for r, c in cells.items() if ((not L.pred(P, case, "rule:" + r).startswith("either")) if c == "?" else L.pred(P, case, "rule:" + r) != word[c])]
        check(not diff, "%s: the frozen rule predictions are the plan's cells%s" % (case, "" if not diff else " (differ: %s)" % diff))
check(all(all(d.values()) for *_, d in R.fit_table()), "the fit: all eleven rules agree with the 13 kept four-array cells (E824, E828, E845, E846)")
check(R.interval("K-TPM") == (128, 192) and R.interval("K-P") == (193, 321) and R.interval("K-AREA") == (786432, 1310720),
      "the threshold families' intervals from the fit: K-TPM (128, 192), K-P (193, 321), K-AREA (786432, 1310720)")

# every maximum's TA data in the 4 MiB slot
mx = []
for st in ("s0", "o", "m", "l", "x", "d"):
    for row in WD.table(st):
        a = WD.parse(row["args"].replace('"$W/dump"', "D").split())
        if a["aa4"]:
            mx.append((M.tadata_4x(a["mw"], a["mh"]), row["name"]))
check(max(mx)[0] <= 4 << 20 and max(mx) == (0x223000, "m4-2048x1536-max4096x4096"),
      "every 4x maximum's TA data fits the 4 MiB slot; the largest is m4's 0x%x" % max(mx)[0])

# the header rule on the 12 kept four-array dumps
kept12 = [(L.K2 + "/%s.tri.tadata.bin.gz" % n, w, h) for n, w, h in [("c2-64x64-k4", 64, 64), ("h1-288x144-k4", 288, 144), ("h2-256x288-k4", 256, 288),
          ("h3-384x384-k4", 384, 384), ("h4-320x160-k4", 320, 160), ("h5-512x384-k4", 512, 384), ("h6-640x480-k4", 640, 480),
          ("h7-320x400-k4", 320, 400), ("h8-1024x768-k4", 1024, 768)]]
kept12 += [(L.R4G_A1 + "/s0/s0-4x-288x144.tri.tadata.bin.gz", 288, 144), (L.R4G_A2 + "/o/o3-4x-1024x768-pe3.tri.tadata.bin.gz", 1024, 768),
           (L.R4G_A2 + "/o/o4-4x-1024x768-pe2.tri.tadata.bin.gz", 1024, 768)]
offs = [len(L.headers(L.read_bytes(p), w, h)["off"]) for p, w, h in kept12]
check(offs == [0] * 12, "the doubled-grid header rule: 0 headers off on the 12 kept four-array dumps (%d headers)" % sum(L.headers(L.read_bytes(p), w, h)["n"] for p, w, h in kept12))
syn = WD.tadata_4x(1280, 1024, 2048, 2048)
check(len(L.headers(syn, 1280, 1024, 2048, 2048)["off"]) == 0 and len(L.headers(WD.tadata_4x(1280, 1024, 1280, 1024, 0xa000), 1280, 1024)["off"]) == 1024,
      "the mock's synthesized headers are on the rule (0 off), and zeroed below 0xa000 at 1280 x 1024 they are 1024 off")

# the name census: the reader finds by verb the dumps the real tool wrote in R4-G's kept o and t directories
for d in (L.R4G_A2 + "/t", L.R4G_A2 + "/o", L.R4G_A1 + "/s0"):
    cases = L.read_cases(d)
    for n, row in cases.items():
        dn = L.dump_names(n, row["args"])
        if dn and row["class"] == "ok":
            check(all(os.path.exists(os.path.join(d, x)) for x in dn), "census, real files: %s/%s's dumps are %s" % (d.split("/out/")[1], n, dn[0]))
        files = sorted(f for f in os.listdir(d) if f.startswith(n + ".") and f.endswith(".param.bin.gz"))
        check(files == ([dn[0]] if dn and row["class"] == "ok" else []), "census, real files: %s/%s has exactly the param dump the verb names (%s)" % (d.split("/out/")[1], n, files))
for st in stages:
    P = L.load_predictions(st + ".tsv", KP)
    for row in WD.table(st):
        dn = L.dump_names(row["name"], row["args"])
        got = L.pred_or(P, row["name"], "dump_param")
        check(got == (dn[0] if dn else None), "census: %s/%s resolves to one dump name: %s" % (st, row["name"], got))

# the needs: every control's need is its twins'; s0's pages the kept ones
tb = TW.table()
rows = []
for st in ("s0", "o"):
    P = L.load_predictions(st + ".tsv", KP)
    for row in WD.table(st):
        need = L.pred_or(P, row["name"], "need") or L.pred_or(P, row["name"], "pb_used")
        rows.append((row["name"], row["args"], row["knobs"], need, row["set"], row["set"] == "explore"))
probs = TW.check(rows, tb)
check(not probs, "twins: every frozen need of s0 and o is its kept twins' (controls, replicates, held out); only o10, o11 carry a [model] need%s" % ("" if not probs else ": " + "; ".join(probs)))
P = L.load_predictions("s0.tsv", KP)
check([L.pred(P, n, "pb_used") for n in ("s0-1x-1024x768", "s0-4x-288x144", "s0-4x-1024x768")] == ["19", "12", "193"],
      "s0's scene pages from the kept dumps: 19, 12, 193 (R4-G's s0 froze 97 for the 1x row: the model, not the scene)")
check(M.u1_full(320, 400) == 10 and M.u1_full(1024, 768) == 49, "the 1x full-triangle model: 10 at 320 x 400 (the one kept dump), 49 at 1024 x 768 [model]")
src = open(os.path.join(KP, "gen", "data", "sources.lst")).read().split()
check(all(os.path.exists(p) and re.search(r"/src/resgx545(-data)?/", p) for p in src),
      "sources.lst: %d files, all exist, all from resgx545 or resgx545-data" % len(src))
sys.exit(bad)
