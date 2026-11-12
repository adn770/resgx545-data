#!/usr/bin/env python3
"""tests/test_replay.py: the fixed scorers replayed on ROUND 4'S KEPT FILES (published: resgx545-data render/closing-r4-render4x), the
plan's mandatory dry runs (exp-render4x-r5.md 2.1 dry runs 3 and 4, 2.2 dry run 1, 3.6 reader census):
  - t: the fixed scorer on r4's kept t directory: t3b and t4b PASS, t3 held at 9, t4 held at 11 (E847's post hoc reading, now the
    scorer's own), t1, t2 held, t6 PASS, a decided headline (4 of 6 rows: t3c, t4c never ran in round 4); r4's own kept score-t.txt had
    NODATA there (the slip, on the record);
  - o: r4's kept o rows matched to r5's rows by ARGV and P (never by name): exactly o3, o4, o5 match, and they score PASS, held, held;
    the rows that ran with other P (o1, o2) or are new do not match;
  - the gate across attempts on r4's two real attempt directories: the gate names the first attempt's s0, and o and t scored through a
    gate file there read s0's controls as PASS (r4's kept score-o.txt and score-t.txt read NODATA);
  - reader census: r4's p-1280x1024 (a fault, no dump) scores as a fault with E845's word; s0's 4x 1024 x 768 as a completion with 193
    pages, TA data 0x1e000 and 0 headers off the rule; r4's held o5 dump (62 and 63 bytes of error text) reads "held dump not read".
Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "gen"), os.path.join(KP, "score"), HERE]
import rlib as L  # noqa: E402
import score_r as S  # noqa: E402
import twins as TW  # noqa: E402
import worlds as WD  # noqa: E402

S.preds()
bad = 0
A1, A2 = L.R4G_A1, L.R4G_A2
os.makedirs(os.path.join(KP, "debug"), exist_ok=True)
TMP = tempfile.mkdtemp(prefix="replay-", dir=os.path.join(KP, "debug"))


def check(cond, msg):
    global bad
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        bad = 1


# ---- t ------------------------------------------------------------------------------------------------------------------------------
lines, r = S.t_stage(A2 + "/t", A1 + "/s0")
txt = "\n".join(lines)
check(r["controls"]["t3b-line-base"] == "PASS" and r["controls"]["t4b-point-base"] == "PASS" and r["controls"]["t6-ctl-te40-1array"] == "PASS",
      "replay t on r4's kept files: t3b, t4b, t6 PASS")
check("t3-line-te40 (replicate of E847): H-PAD held: one dword inserted at 9" in txt and "t4-point-te40 (replicate of E847): H-PAD held: one dword inserted at 11" in txt,
      "replay t: t3 held at 9, t4 held at 11 (E847's reading is the scorer's own output)")
check(r["verdicts"]["t1-aa4-te40"] is True and r["verdicts"]["t2-aa4-te80"] is True, "replay t: t1, t2 H-SAME held")
check(r["q293"].endswith("(4 of 6 rows decided)") and not r["misses"], "replay t: a decided headline, no READER-MISS: %s" % r["q293"][-40:])
old = open(A2 + "/score-t.txt").read()
check("t3b-line-base: NODATA" in old and "t4b-point-base: NODATA" in old, "on the record: r4's kept score-t.txt read t3b and t4b as NODATA (the slip the replay fixes)")

# ---- o: match by argv and P -------------------------------------------------------------------------------------------------------
P = S.PRED["o"]
r5 = {}
for row in WD.table("o"):
    k = row["knobs"].split()
    pb = next(x for x in k if x.startswith("pb:"))
    r5[(TW.key(row["args"]), " ".join(TW.tokens(row["args"])), pb)] = row["name"]
cases = L.read_cases(A2 + "/o")
matched = {}
for n4, row in cases.items():
    pb = next((x for x in row["knobs"].split() if x.startswith("pb:")), "pb:0x422")
    kk = (TW.key(row["args"]), " ".join(TW.tokens(row["args"])), pb)
    if kk in r5:
        matched[n4] = r5[kk]
check(matched == {"o3-4x-1024x768-pe3": "o3-4x-1024x768-pe3", "o4-4x-1024x768-pe2": "o4-4x-1024x768-pe2", "o5-4x-288x144-p23-held": "o5-4x-288x144-p23"},
      "replay o: r4's rows that match an r5 row by argv and P are exactly o3, o4, o5: %s" % sorted(matched))
res = {r5n: S.o_row(r5n, S.job(A2 + "/o", cases, n4), P) for n4, r5n in matched.items()}
check(res.get("o3-4x-1024x768-pe3", (0, None))[1] is True and res["o3-4x-1024x768-pe3"][0] == "complete", "replay o3: PASS (complete, 193 pages): %s" % (res.get("o3-4x-1024x768-pe3"),))
check(res.get("o4-4x-1024x768-pe2", (0, None))[:2] == ("overflow", True), "replay o4: held (-ENOSPC, no fault)")
check(res.get("o5-4x-288x144-p23", (0, None))[:2] == ("overflow", True), "replay o5: held (-ENOSPC, no fault)")

# ---- the files the scorers must FAIL on (the replay can fail) -------------------------------------------------------------------
oc4 = S.o_row("o3-4x-1024x768-pe3", S.job(A2 + "/o", cases, "o4-4x-1024x768-pe2"), P)
check(oc4[:2] == ("overflow", False), "must fail: r4's o4 (an overflow at 0xe2) scored as r5's o3 control (frozen complete) FAILS: %s" % oc4[2])
tc = L.read_cases(A2 + "/t")
st_, tx = S.t_row("t4-point-te40", S.job(A2 + "/t", tc, "t4-point-te40"), S.job(A2 + "/t", tc, "t3b-line-base"), S.PRED["t"])
check(st_ is False, "must fail: r4's t4 (a point) against the line baseline matches no hypothesis: %s" % tx[:70])
st_, tx = S.t_row("t3c-line-te80", S.job(A2 + "/t", tc, "t3-line-te40"), S.job(A2 + "/t", tc, "t3b-line-base"), S.PRED["t"])
check(st_ is True, "  and r4's t3 read as t3c (same position frozen) holds: the row reader is not name-bound")
pj = S.job(A1 + "/p", L.read_cases(A1 + "/p"), "p-1280x1024")
surv = __import__("rules").survivors([S.dims(pj["row"]["args"]) + ("fault",), (1280, 1024, 1280, 1040, "fault")])
check(not any(r.startswith("TPC") for r in surv), "must fail: r4's p-1280x1024 fault, were m1 to fault too, leaves no H-TPC variant: %s" % surv)

# ---- the gate across r4's two real attempts ---------------------------------------------------------------------------------------
code, msg = S.gate("o", [A2, A1])
check(code == 0 and ("s0 at %s/s0" % A1) in msg, "gate across r4's two attempts: open, s0 named in the first attempt")
att = os.path.join(TMP, "att2")
os.makedirs(att)
for st in ("o", "t"):
    os.symlink(A2 + "/" + st, os.path.join(att, st))
    open(os.path.join(att, "gate-%s.txt" % st), "w").write(S.gate(st, [att, A1])[1] + "\n")
ro = S.o_stage(os.path.join(att, "o"))[1]
rt = S.t_stage(os.path.join(att, "t"))[1]
check(all(v == "PASS" for k, v in ro["controls"].items() if k.startswith("s0:")) and all(v == "PASS" for k, v in rt["controls"].items() if k.startswith("s0:")),
      "o and t scored through the gate file read s0's controls PASS (r4's kept score-o.txt: %s)" % ("NODATA" if "s0:s0-1x-1024x768: NODATA" in open(A2 + "/score-o.txt").read() else "?"))

# ---- reader census on real files ----------------------------------------------------------------------------------------------------
pc = L.read_cases(A1 + "/p")
j = S.job(A1 + "/p", pc, "p-1280x1024")
ob, t = S.rule_obs(j)
check(ob == "fault" and "0x10000011" in t and j["miss"] is None, "census: r4's p-1280x1024 (a fault, no dump) reads as a fault with E845's word, no READER-MISS: %s" % t[:70])
sc = L.read_cases(A1 + "/s0")
j = S.job(A1 + "/s0", sc, "s0-4x-1024x768")
ob, t = S.rule_obs(j)
P0 = dict(S.PRED["s0"])
P0[("s0-4x-1024x768", "hdr_off")] = [("0", "", "model")]
aux = S.aux(j, P0, "s0-4x-1024x768")
check(ob == "complete" and "pb_used 193" in aux and "tadata_size 122880" in aux and "hdr_off 0" in aux and "DIFFERS" not in aux,
      "census: s0's 4x 1024 x 768 reads as a completion: %s" % aux)
oc = L.read_cases(A2 + "/o")
j = S.job(A2 + "/o", oc, "o5-4x-288x144-p23-held")
check(j["heldparam"] is not None and len(j["heldparam"]) < 4096 and len(j["heldtadata"]) < 4096,
      "census: r4's held o5 dumps are %d and %d bytes of error text (the fixture of 'held dump not read')" % (len(j["heldparam"]), len(j["heldtadata"])))
dd = os.path.join(TMP, "d-fixture", "d")
os.makedirs(dd)
WD.kept(dd, "d", "model")
import shutil  # noqa: E402
shutil.copy(A2 + "/o/o5-4x-288x144-p23-held.heldparam.bin.gz", dd + "/d1-1280x1024-held.heldparam.bin.gz")
shutil.copy(A2 + "/o/o5-4x-288x144-p23-held.heldtadata.bin.gz", dd + "/d1-1280x1024-held.heldtadata.bin.gz")
rd = S.d_stage(dd)[1]
check(rd["dumps"].startswith("held dump not read") and rd["replicated"] is True, "census: row d with o5's kept held files reads 'held dump not read': %s" % rd["dumps"][:60])
print("work dir (kept for inspection): %s" % TMP)
sys.exit(bad)
