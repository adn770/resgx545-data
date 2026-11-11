#!/usr/bin/env python3
"""Scorer tests of R3K-pixel: round 2's kept fault data (held a5 / a6, S3's e1 held faults, E728's split-flow images) and
synthetic worlds in which each hypothesis wins and loses (tests/worlds.py).  Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import gzip
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "score"))
import worlds as W  # noqa: E402
import klib as L  # noqa: E402
import score_k as S  # noqa: E402

fails = 0


def check(name, cond, detail=""):
    global fails
    if cond:
        print("ok   %s" % name)
    else:
        fails += 1
        print("FAIL %s %s" % (name, detail))


def tmp():
    return tempfile.mkdtemp(prefix="k-score-")


S.preds()
FX = os.path.join(KP, "tests", "fixtures")

# ---- readers on landed data ----------------------------------------------------------------------------------------------
j = S.job(os.path.join(FX, "r2-a-fault"), L.read_cases(os.path.join(FX, "r2-a-fault")), "a6-320x400-max320")
h = S.held_fault(j)
check("held reading of R2's a6 (E789): 0x90004, page 0x20008", h and h["word"] == 0x90004 and h["page"] == 0x20008, h)
j = S.job(os.path.join(FX, "s3-e1-ctl"), L.read_cases(os.path.join(FX, "s3-e1-ctl")), "e1-ta-read")
h = S.held_fault(j)
check("held reading of S3's e1-ta-read (E444): 0x90008, page 0x3e000", h and h["word"] == 0x90008 and h["page"] == 0x3e000, h)
j = S.job(os.path.join(FX, "r2-a-fault"), L.read_cases(os.path.join(FX, "r2-a-fault")), "a5-320x400-max544")
r = S.read_complete(j, 320, 400, 544, 400, 1)
check("a complete 4x job of R2 (a5): diff 0, TA data 0xa000, 4 arrays, nothing below rgn", r["diff"] == "0 of 128000" and r["size"] == 0xa000 and r["slots"] == 4 and r["below"] == 0, r)
t = gzip.open(os.path.join(FX, "pb", "own-40.txt.gz")).read().decode()
check("E728's empty image: diff 3969 of 4096, target hash 0xfc5ff15e0434a325, 0 triangle", L.diff_line(t)[:2] == (3969, 4096) and L.target_hash(t) == "0xfc5ff15e0434a325" and L.tri_lines(t)["tri"] == 0)
t = gzip.open(os.path.join(FX, "pb", "twin-60.txt.gz")).read().decode()
check("the twin's image: diff 0, hash 0xd0530839d87ea325, 4096 triangle", L.diff_line(t)[:2] == (0, 4096) and L.target_hash(t) == "0xd0530839d87ea325" and L.tri_lines(t)["tri"] == 4096)
own = L.dwords(gzip.open(os.path.join(FX, "pb", "own-40.param.bin.gz")).read()); twin = L.dwords(gzip.open(os.path.join(FX, "pb", "twin-60.param.bin.gz")).read())
check("E728's shift in the landed dumps: own[i+1] = twin[i] on 12..25, the stream words at dwords 0-2 of both",
      all(own[i + 1] == twin[i] for i in range(11, 26)) and [hex(x) for x in own[:3]] == ["0x4000004", "0x30001", "0x4000000"] and list(own[:3]) == list(twin[:3]))
d = ("[1.0] gma500 0000:00:02.0: [drm] sgxfive: kregnow 0x0c04: 0x00090008 -> 0x00000001, reads 0x00090008, BIF_INT_STAT 0x00090008 BIF_FAULT 0x3e000001\n"
     "[1.1] gma500 0000:00:02.0: [drm] sgxfive: kregnow 0x0c00: 0x00000000 -> 0x00000010, reads 0x00000000, BIF_INT_STAT 0x00080000 BIF_FAULT 0x00000000\n"
     "[1.2] gma500 0000:00:02.0: [drm] sgxfive: kregnow 0x0114 = 0x00000040 (write-only), EVENT_STATUS 0x20000000/0x00000480\n"
     "[1.3] gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/0x480\n"
     "[1.4] gma500 0000:00:02.0: [drm] SGX reset: after the fault clear BIF_FAULT 0x3e000001 BIF_INT_STAT 0x80000\n"
     "[1.5] gma500 0000:00:02.0: [drm] sgxfive: kpoke par:11=0xffffffff applied\n")
k = L.kregnow_lines(d)
check("the kregnow log line parses (two BIF lines; the write-only line is not one)", len(k) == 2 and k[0]["int_stat"] == 0x90008 and k[1]["off"] == 0xc00 and k[1]["new"] == 0x10, k)
rl = L.reset_lines(d)
check("the reset's two new BIF lines parse (halt, then the fault clear); %#x prints 0 as 0", [x["kind"] for x in rl] == ["halt", "clear"] and rl[0]["fault"] == 0 and rl[1]["fault"] == 0x3e000001, rl)
check("kpoke applied lines parse", L.kpoke_applied(d) == [("par", 11, 0xffffffff)])
check("the whole output is searched for an overflow message (not a tail)", L.overflowed("x" * 12000 + "scene overflowed the parameter buffer" + "y" * 12000))

# ---- k-f4 ----------------------------------------------------------------------------------------------------------------
d = W.f4_world(tmp(), "f4")
lines, res = S.f4_stage(d)
v = res["verdicts"]
check("f4 world: c1, c2, c3 PASS and h1-h8 all AGREE", v["c1-288x144-k1"] == "PASS" and v["c2-64x64-k4"] == "PASS" and v["c3-64x64-k1"] == "PASS"
      and all(v[n] == "AGREES" for n in v if n.startswith("h")), v)
check("f4 world: the stage summary says four arrays suffice at 8 of 8 held-out rows", "8 of 8 held-out rows complete" in res["summary"], res["summary"])
d = W.f4_world(tmp(), "hfault:h3-384x384-k4")
lines, res = S.f4_stage(d); v = res["verdicts"]
check("an h row that faults is REFUTED with its fault page (and the others still agree)", v["h3-384x384-k4"] == "REFUTED" and v["h1-288x144-k4"] == "AGREES"
      and any("0x20008" in x for x in lines if x.startswith("h3-384x384-k4")), (v, lines))
d = W.f4_world(tmp(), "leak")
lines, res = S.f4_stage(d); v = res["verdicts"]
check("the knob did not take (TA data of the knob-1 layout): the h rows cannot tell, they are not refutations",
      all(v[n].startswith("cannot tell") for n in v if n.startswith(("h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8"))) and v["c2-64x64-k4"] in ("PASS", "FAIL"), v)
check("... and the verdict line says the knob did not apply", "knob" in res["summary"].lower(), res["summary"])
d = W.f4_world(tmp(), "c1ok")
lines, res = S.f4_stage(d); v = res["verdicts"]
check("c1 completing (the knob leaks) fails the control and the h rows cannot tell", v["c1-288x144-k1"] == "FAIL" and "cannot tell" in res["summary"]
      and all(v[n].startswith("cannot tell") for n in v if n.startswith("h")), (v, res["summary"]))
d = W.f4_world(tmp(), "slots3")
lines, res = S.f4_stage(d); v = res["verdicts"]
check("h rows writing 3 arrays are REFUTED (slots), not AGREES", all(v[n] == "REFUTED" for n in v if n.startswith("h")), v)
d = W.f4_world(tmp(), "overflow")
lines, res = S.f4_stage(d); v = res["verdicts"]
check("a parameter-buffer overflow (h8) is cannot tell, never a refutation of the layout", v["h8-1024x768-k4"].startswith("cannot tell"), v)
d = W.f4_world(tmp(), "c2sha")
lines, res = S.f4_stage(d); v = res["verdicts"]
check("c2's TA data differing from c3's fails c2", v["c2-64x64-k4"] == "FAIL", v)
d = W.f4_world(tmp(), "nodata")
lines, res = S.f4_stage(d); v = res["verdicts"]
check("a row that did not run is NODATA, the others are read", v["h3-384x384-k4"] == "NODATA" and v["h1-288x144-k4"] == "AGREES", v)
d = W.f4_world(tmp(), "f4")
cs = open(os.path.join(d, "cases.tsv")).read().replace("h1-288x144-k4\tk-f4\theldout\tsafe", "h1-288x144-k4\tk-f4\theldout\tsafe", 1)
rows = cs.splitlines(); rows[3] = rows[3].replace("\t0\tok\t", "\t124\tok\t"); open(os.path.join(d, "cases.tsv"), "w").write("\n".join(rows) + "\n")
lines, res = S.f4_stage(d)
check("rc 124 (a freeze) is not a result: NODATA", res["verdicts"][rows[3].split("\t")[0]] == "NODATA", res["verdicts"])

# ---- k-pb0, gate, k-pb ----------------------------------------------------------------------------------------------------
d = W.pb0_world(tmp(), "ok")
lines, res = S.pb0_stage(d); v = res["verdicts"]
check("pb0: the dump run, p0 (the twin) and p1 PASS", all(v[n] == "PASS" for n in ("pb-d0-te40", "pb-p0-te60", "pb-p1-te40")), (v, lines))
root0 = tmp(); os.symlink(d, os.path.join(root0, "k-pb0"))
check("gate k-pb opens on passing controls", S.gate("k-pb", [root0])[0] == 0)
d = W.pb0_world(tmp(), "p0empty"); lines, res = S.pb0_stage(d)
r0 = tmp(); os.symlink(d, os.path.join(r0, "k-pb0")); g = S.gate("k-pb", [r0])
check("p0 drawing nothing closes the gate and names the stage to rerun", res["verdicts"]["pb-p0-te60"] == "FAIL" and g[0] == 1 and "run/k.sh --only k-pb0" in g[1], (res["verdicts"], g))
d = W.pb0_world(tmp(), "p1full"); lines, res = S.pb0_stage(d)
check("p1 drawing the full image (TE 0x40 not empty) fails p1", res["verdicts"]["pb-p1-te40"] == "FAIL", res["verdicts"])
d = W.pb0_world(tmp(), "d0stream"); lines, res = S.pb0_stage(d)
check("the stream words not at dwords 0-2 of the dump fail the dump run (the index of par is not the dword index)", res["verdicts"]["pb-d0-te40"] == "FAIL", res["verdicts"])
check("gate k-pb with no k-pb0 kept is closed (nothing proven)", S.gate("k-pb", [tmp()])[0] == 1)

def pbv(world):
    d = W.pb_world(tmp(), world)
    lines, res = S.pb_stage(d)
    return lines, res

lines, res = pbv("old"); v = res["verdicts"]
check("H-OLD world: p3 gives the twin's image, p4 stays empty: p3 twin, p4 empty, verdict H-OLD", v["pb-p3a-twin"] == "twin" and v["pb-p3b-twin"] == "twin" and v["pb-p4a-ffff"] == "empty"
      and v["pb-p2-own11"] == "PASS" and res["q285"].startswith("H-OLD"), (v, res["q285"]))
lines, res = pbv("field"); v = res["verdicts"]
check("H-FIELD world: p3 not the twin's, p4 draws pixels: verdict H-FIELD", v["pb-p3a-twin"] == "not twin" and v["pb-p4a-ffff"] == "drawn" and res["q285"].startswith("H-FIELD"), (v, res["q285"]))
lines, res = pbv("bothempty")
check("p3 and p4 both empty: cannot tell, parked under Q030", res["q285"].startswith("cannot tell") and "Q030" in res["q285"], res["q285"])
lines, res = pbv("mixed")
check("p3 the twin's AND p4 draws: neither hypothesis alone (cannot tell, both reported)", res["q285"].startswith("cannot tell") and "both" in res["q285"], res["q285"])
lines, res = pbv("unapplied"); v = res["verdicts"]
check("the pokes missing from the kernel log: p3 NODATA (not read as a refutation)", v["pb-p3a-twin"] == "NODATA" and res["q285"].startswith("cannot tell"), (v, res["q285"]))
lines, res = pbv("hang"); v = res["verdicts"]
check("a hang in p4 is OTHER/NODATA for p4a, the replicate still read", v["pb-p4a-ffff"] in ("NODATA", "OTHER") and v["pb-p4b-ffff"] == "empty", v)
lines, res = pbv("p2changed"); v = res["verdicts"]
check("p2 (its own value) changing the dump fails the control and the held-out rows cannot tell", v["pb-p2-own11"] == "FAIL" and res["q285"].startswith("cannot tell"), (v, res["q285"]))

# ---- k-bif ----------------------------------------------------------------------------------------------------------------
def bifv(world, rows=None):
    d = W.bif_world(tmp(), world, rows)
    return S.bif_stage(d)

for wname, hyp in (("w1c", "H-W1C"), ("clr", "H-CLR"), ("rst", "H-RST")):
    lines, res = bifv(wname); v = res["verdicts"]
    check("%s world: n0 PASS, the four held rows read %s, replicate agrees, verdict %s" % (hyp, hyp, hyp),
          v["n0-idle"] == "PASS" and all(v[n] == hyp for n in ("f1-ta-read", "f1r-ta-read", "f2-ta-write", "f3-tex")) and res["q003"].startswith(hyp), (v, res["q003"], lines))
lines, res = bifv("clr", {"f3-tex": "w1c"}); v = res["verdicts"]
check("rows disagreeing: the verdict is MIXED with the rows named (never one hypothesis)", res["q003"].startswith("MIXED") and "f3-tex" in res["q003"], (v, res["q003"]))
lines, res = bifv("other"); v = res["verdicts"]
check("a partial change after a write is OTHER", all(v[n] == "OTHER" for n in ("f1-ta-read", "f2-ta-write", "f3-tex")), v)
lines, res = bifv("s1changed"); v = res["verdicts"]
check("the unset-bit write changing the state fails the control: cannot tell for the row", v["f2-ta-write"].startswith("cannot tell"), v)
lines, res = bifv("ebusy"); v = res["verdicts"]
check("writes refused (status != 0): NODATA, not read as 'nothing clears'", v["f1-ta-read"] == "NODATA", v)
lines, res = bifv("nolines"); v = res["verdicts"]
check("no kregnow line in the log: NODATA", v["f1-ta-read"] == "NODATA", v)
lines, res = bifv("wrongfault"); v = res["verdicts"]
check("another fault word than the frozen one fails the row's control: cannot tell", v["f1-ta-read"].startswith("cannot tell"), v)
lines, res = bifv("nofault"); v = res["verdicts"]
check("the job completing (no fault latched): NOFAULT", v["f1-ta-read"] == "NOFAULT", v)
lines, res = bifv("ctrlstuck"); v = res["verdicts"]
check("BIF_CTRL not back at its first value after the second flip is recorded (control fails: cannot tell)", v["f1-ta-read"].startswith("cannot tell") or v["f1-ta-read"] == "OTHER", v)
lines, res = bifv("clr", {"n0-idle": "n0changed"}); v = res["verdicts"]
check("n0 changing something fails the n0 control and the verdict cannot tell", v["n0-idle"] == "FAIL" and res["q003"].startswith("cannot tell"), (v, res["q003"]))
lines, res = bifv("rst")
check("the reset's new log lines are reported as data", any("reset" in x and "0x80000" in x for x in lines), lines)

# ---- post-run fixes (POSTRUN-FIX.md, 2026-11-11) -------------------------------------------------------------------------
import glob  # noqa: E402
d = W.f4_world(tmp(), "f4")
for f in glob.glob(os.path.join(d, "c3-64x64-k1*")):
    os.remove(f)                      # the audit's repro: control c3 loses its output, its cases row stays
lines, res = S.f4_stage(d); v = res["verdicts"]
check("C2: a NODATA control gates the held-out rows (cannot tell, not AGREES)", v["c3-64x64-k1"] == "NODATA"
      and all(v[n].startswith("cannot tell (control c3-64x64-k1 NODATA") for n in v if n.startswith("h")), v)
check("C2: ... and the summary says so (no '8 of 8 held-out rows complete')", "cannot tell for the held-out rows: control c3-64x64-k1 NODATA" in res["summary"]
      and "8 of 8" not in res["summary"], res["summary"])
lines, res = bifv("other", {"n0-idle": "ok"})
check("C10: held rows read OTHER are read, not 'no held row could be read'", res["q003"].startswith("none of H-W1C, H-CLR, H-RST")
      and "4 of 4 held rows were read" in res["q003"], res["q003"])
lines, res = bifv("other", {"f3-tex": "ebusy"})
check("C10: OTHER rows and a NODATA row: the read rows and the unread row both named", res["q003"].startswith("none of H-W1C, H-CLR, H-RST")
      and "3 of 4 held rows were read" in res["q003"] and "f3-tex" in res["q003"], res["q003"])
lines, res = bifv("ebusy")
check("C10: no held row read at all stays 'no held row could be read'", res["q003"].startswith("cannot tell: no held row could be read"), res["q003"])
d = W.pb_world(tmp(), "old")
for f in glob.glob(os.path.join(d, "pb-p4b-ffff*")):
    os.remove(f)
lines, res = S.pb_stage(d)
check("C10: k-pb with one p4 job not read says 1 of 2 jobs, not 2 of 2", res["verdicts"]["pb-p4b-ffff"] == "NODATA" and "draws nothing in 1 of 2 jobs" in res["q285"]
      and "twin's image in 2 of 2 jobs" in res["q285"], res["q285"])

# ---- the whole verdict and the freeze --------------------------------------------------------------------------------------
root = tmp()
for st, mk in (("k-f4", lambda d: W.f4_world(d, "f4")), ("k-pb0", lambda d: W.pb0_world(d, "ok")), ("k-pb", lambda d: W.pb_world(d, "old")), ("k-bif", lambda d: W.bif_world(d, "clr"))):
    mk(os.path.join(root, st))
vv = S.verdict([root])
check("verdict: Q140, Q285 and Q003 lines from the kept stages", "Q140:" in vv and "Q285: H-OLD" in vv and "Q003: H-CLR" in vv, vv)
ok, msg = L.verify_freeze()
check("the freeze verifies (run/freeze_k.sh freeze after gen/kgen.py)", ok, msg)
sys.exit(1 if fails else 0)
