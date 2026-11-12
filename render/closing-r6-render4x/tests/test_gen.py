#!/usr/bin/env python3
"""tests/test_gen.py: the generated tables and predictions of r6-render4x stage A against the plan and the kept records they came from.
  - the generator reproduces every file on disk (rgen.py --check), the bins equal r5's published programs (rgen.py checks it);
  - the job count by stage (s0 3, a 13, t 4: 20 in all, 19 if a1 faults), the limits (s0 1, a 8, t 1), the knobs every row carries;
  - every frozen H-TPM prediction, entries end and td.rgn is the plan's table cell (typed here from exp-render4x-r6.md section 2,
    independent of rules.py), and so is K-OR's column; h1's and h2's frozen sets have the plan's counts and ends;
  - H-TPM on the 26 recorded cells: 0 misses, and its variants miss as E870 says (y even: 8, 4, 3; x even: 8, 8, 5, 3);
  - the frozen lost set of a 1280 x 1024 held fault is E869's 1023 lost offsets as the reader reads them on the kept dump;
  - every maximum's TA data fits the 4 MiB slot; the doubled-grid header rule holds on the kept four-array dumps; the census of dump
    names; every control's page need is its twins'; the sources exist and none is excluded.
Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
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
check(stages == ["s0", "a", "t"], "stages in the order s0, a, t (the main rows before Q293's rider)")
counts = {st: len(WD.table(st)) for st in stages}
check(counts == {"s0": 3, "a": 13, "t": 4} and sum(counts.values()) == 20, "20 jobs (16 of the plan's stage A with a1's replicate, 4 of Q293): %s" % counts)
lim = {st: int([ln for ln in open(os.path.join(KP, "tables", st + ".txt")) if ln.startswith("#limit")][0].split()[1]) for st in stages}
check(lim == {"s0": 1, "a": 8, "t": 1}, "fault limits s0 1, a 8 (the plan's 'limit 8 for a + h'), t 1: %s" % lim)
for st in stages:
    for row in WD.table(st):
        k = row["knobs"].split()
        if row["args"].startswith("tri "):
            check("expectdiff" in k and "--keep-going" in row["args"], "%s/%s: a tri row with expectdiff and --keep-going" % (st, row["name"]))
        if st == "a":
            want = None if row["name"].startswith("a4") else ("hypo:a1:1" if row["name"].split("-")[0] in ("a1", "a1r") else "hypo:q292:8")
            got = next((x for x in k if x.startswith("hypo:")), None)
            check("strict" in k and got == want, "%s/%s: strict health, hypothesis knob %s (a4 has none: a fault there stops the stage)" % (st, row["name"], got))
        check(("held" in k) == row["name"].startswith("h"), "%s/%s: held only in h1, h2" % (st, row["name"]))
        check(not any(x.startswith("pb:") for x in k), "%s/%s: no PB knob in stage A" % (st, row["name"]))

# the plan's table (section 2), typed: entries end, td.rgn, H-TPM, K-OR
PLAN = {"a1-1024x1280": (0x13000, 0x13000, "complete", "fault"), "a1r-1024x1280": (0x13000, 0x13000, "complete", "fault"),
        "a2-1024x1296": (0x13ab0, 0x13000, "fault", "fault"), "a3-1040x1280": (0x18560, 0x13000, "fault", "fault"),
        "a4-1024x768-max2048x1024": (0x7000, 0x7000, "complete", "complete"), "a5-1024x800-max2048x1024": (0x7ac0, 0x7000, "fault", "fault"),
        "a8-1024x1024-max1024x1280": (0x8000, 0x13000, "complete", "fault"), "a9-1024x800-max1024x1280": (0x7ac0, 0x13000, "complete", "fault"),
        "a12-992x1280": (0x12fe0, 0x13000, "complete", "fault"), "a13-512x1536": (0x12000, 0x13000, "complete", "fault"),
        "a14-1024x1536": (0x14000, 0x13000, "fault", "fault"), "h1-1024x800-held": (0x7ac0, 0x7000, "fault", "fault"),
        "h2-1280x768-held": (0xc800, 0x7000, "fault", "fault")}
P = L.load_predictions("a.tsv", KP)
for n, (e, rg, ht, kor) in PLAN.items():
    got = (int(L.pred(P, n, "entries_end"), 16), int(L.pred(P, n, "td_rgn"), 16), L.pred(P, n, "htpm"), L.pred(P, n, "rule:K-OR"))
    check(got == (e, rg, ht, kor), "%s: entries end 0x%x, td.rgn 0x%x, H-TPM %s, K-OR %s as the plan's table" % (n, e, rg, ht, kor))
check(set(PLAN) == {r_["name"] for r_ in WD.table("a")}, "every plan row of stage A is a table row and back")
nf = sum(1 for n in PLAN if L.pred(P, n, "htpm") == "fault")
check(nf == 6, "6 predicted faults (a2, a3, a5, a14, h1, h2): %d" % nf)
PH = L.load_predictions("h.tsv", KP)
for n, cnt, first, last, h0 in (("h1-1024x800-held", 43, 0x7000, 0x7ab0, "yes"), ("h2-1280x768-held", 511, 0x7ffc, 0xc7f0, "no")):
    lo = [int(x, 16) for x in L.pred(PH, n, "lost").split(",")]
    check((len(lo), lo[0], lo[-1], L.pred(PH, n, "header0_lost")) == (cnt, first, last, h0) and lo == sorted(set(lo)),
          "%s: the frozen set is the plan's %d headers 0x%x to 0x%x, header 0 lost %s" % (n, cnt, first, last, h0))

# H-TPM and its variants on the 26 recorded cells (E870)
miss = {v: len(R.recorded_misses(v)) for v in R.TPM}
check(len(R.RECORDED) == 26 and miss == {"TPM-y-tail": 8, "TPM-y-otpm": 4, "TPM-y-state": 3, "TPM-y-rgn": 0, "TPM-x-tail": 8, "TPM-x-otpm": 8,
                                         "TPM-x-state": 5, "TPM-x-rgn": 3}, "the 26 recorded cells: H-TPM 0 misses, the variants as E870: %s" % miss)
d = L.read_bytes(L.R5X_A + "/d/d1-1280x1024-held.heldtadata.bin.gz")
lo = L.lost_offsets(d, 1280, 1024)
check(lo is not None and set(lo) == set(R.lost(1280, 1024)) and len(lo) == 1023,
      "the fit, by this session's reader: E869's held dump lost exactly R.lost(1280 x 1024), 1023 offsets")
check(len(set(lo) & set(R.lost(1280, 1024, yeven=False))) == 426 and len(R.lost(1280, 1024, yeven=False)) == 1708,
      "the other interleave on E869's dump: 426 of 1708 (E870)")

# every maximum's TA data in the 4 MiB slot
mx = []
for st in ("s0", "a"):
    for row in WD.table(st):
        a = WD.parse(row["args"].replace('"$W/dump"', "D").split())
        if a["aa4"]:
            mx.append((M.tadata_4x(a["mw"], a["mh"]), row["name"]))
check(max(mx)[0] <= 4 << 20, "every 4x maximum's TA data fits the 4 MiB slot; the largest 0x%x (%s)" % max(mx))
u4s = [R.u4(WD.parse(r_["args"].split())["w"], WD.parse(r_["args"].split())["h"]) for r_ in WD.table("a")]
check(max(u4s) <= M.usable(M.PB_PAGES), "every a row's scene pages (U4, at most %d) fit the PB at 0x422" % max(u4s))

# the header rule on the kept four-array dumps (r5's completed rows included)
kept = [(L.K2 + "/%s.tri.tadata.bin.gz" % n, w, h, w, h) for n, w, h in [("c2-64x64-k4", 64, 64), ("h1-288x144-k4", 288, 144), ("h8-1024x768-k4", 1024, 768)]]
kept += [(L.R5X_A + "/m/m1-1280x1024-max1280x1040.tri.tadata.bin.gz", 1280, 1024, 1280, 1040), (L.R5X_A + "/m/m0-1024x768-max2048x2048.tri.tadata.bin.gz", 1024, 768, 2048, 2048),
         (L.R5X_A + "/l/l2-256x1536.tri.tadata.bin.gz", 256, 1536, 256, 1536), (L.R5X_A + "/x/x1-1024x512.tri.tadata.bin.gz", 1024, 512, 1024, 512)]
offs = [len(L.headers(L.read_bytes(p), w, h, mw, mh)["off"]) for p, w, h, mw, mh in kept]
lost0 = [len(L.lost_offsets(L.read_bytes(p), w, h, mw, mh)) for p, w, h, mw, mh in kept]
nz = [L.nonzero_below(L.read_bytes(p), R.lay(mw, mh)["rgn"]) for p, w, h, mw, mh in kept]
check(offs == [0] * len(kept) and lost0 == [0] * len(kept) and nz == [0] * len(kept),
      "the doubled-grid rule: 0 headers off, 0 lost offsets and nothing non-zero below td.rgn on %d kept completed dumps (incl. maxima larger than the target)" % len(kept))
syn = WD.tadata_4x(1024, 800, 1024, 800, lost=R.lost(1024, 800), noise=True)
check(set(L.lost_offsets(syn, 1024, 800)) == set(R.lost(1024, 800)) and len(L.headers(WD.tadata_4x(1024, 800, 1024, 1280), 1024, 800, 1024, 1280)["off"]) == 0,
      "the mock's synthesized held dump reads back its own lost set through word-0 noise; its completed dump is on the rule")

# the name census
for st in stages:
    Pp = L.load_predictions(st + ".tsv", KP)
    for row in WD.table(st):
        dn = L.dump_names(row["name"], row["args"])
        got = L.pred_or(Pp, row["name"], "dump_param")
        check(got == (dn[0] if dn else None), "census: %s/%s resolves to one dump name: %s" % (st, row["name"], got))
for dd in (L.R5X_A + "/t", L.R5X_A + "/s0"):
    cases = L.read_cases(dd)
    for n, row in cases.items():
        dn = L.dump_names(n, row["args"])
        files = sorted(f for f in os.listdir(dd) if f.startswith(n + ".") and f.endswith(".param.bin.gz"))
        check(files == ([dn[0]] if dn and row["class"] == "ok" else []), "census, r5's real files: %s/%s has exactly the param dump the verb names (%s)" % (dd.split("/out/")[1], n, files))

# the needs: every control's need is its twins'
tb = TW.table()
P0 = L.load_predictions("s0.tsv", KP)
rows = [(row["name"], row["args"], row["knobs"], L.pred_or(P0, row["name"], "pb_used"), row["set"], False) for row in WD.table("s0")]
probs = TW.check(rows, tb)
check(not probs, "twins: every s0 control's page need is its kept twins'%s" % ("" if not probs else ": " + "; ".join(probs)))
check([L.pred(P0, n, "pb_used") for n in ("s0-1x-1024x768", "s0-4x-288x144", "s0-4x-1024x768")] == ["19", "12", "193"], "s0's scene pages from the kept dumps: 19, 12, 193")
PT = L.load_predictions("t.tsv", KP)
check(L.pred(PT, "t5-line-tec0", "insert_pos") == "9" and L.pred(PT, "t6-point-tec0", "insert_pos") == "11" and L.pred(PT, "t7-tri-te40-poke11", "tri2") == "0 triangle, 4096 background, 0 other",
      "t: the frozen positions 9 (line) and 11 (point) and t7's render 2 (E829 p4: nothing drawn)")
src = open(os.path.join(KP, "gen", "data", "sources.lst")).read().split()
check(all(os.path.exists(p) and re.search(r"/src/resgx545(-data)?/", p) for p in src),
      "sources.lst: %d files, all exist, all from resgx545 or resgx545-data" % len(src))
sys.exit(bad)
