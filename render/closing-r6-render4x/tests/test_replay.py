#!/usr/bin/env python3
"""tests/test_replay.py: every frozen scorer replayed before the freeze on KEPT files it must hold on and on kept files it must fail on
(round 6's addition to the brief; the plan names them: E869's dump, r5's m, l, x, d outcomes, r5's t rows, E829's kpoke rows).
Published sessions only (resgx545-data render/closing-r5-render4x, render/closing-r4-q285):
  - s0: r5's kept s0 scores PASS on all three controls; r5's t6 (E827's row) as t8 PASS; must fail: E829's pb-p2-own11 (the same
    poke in a two-render job) scored as t8 FAILS (r5's t1, the poke on a 4x context, is no such file: it equals t6 in every frozen
    quantity, E847's H-SAME);
  - a, outcomes: r5's 14 decided rows of m, l, x, d read by argv through rule_obs agree with H-TPM's prediction 14 of 14 (the fit's
    own data: it must hold), and K-OR, the dead rule a1 tests, is contradicted;
  - a, held sets: E869's held dump (r5's d) through held_row with H-TPM's set for 1280 x 1024 frozen as a prediction: set equal (1023);
    must fail: the same dump against h2's frozen set (another size), against the x-even set (both 426), m1's COMPLETED dump presented
    as a held one with d's set moved to m1's td.rgn (0 lost: predicted only 1023), and r4's error-text held dump (cannot tell, never a pass);
  - t: r5's t3c and t4c (0x80) and t3, t4 (0x40) as t5 and t6 against the frozen 11.31 heads: H-PAD held at 9 and 11, image empty;
    must fail: r5's t3b baseline (no insertion), r5's t4c (a point) scored as t5 (a line), r5's t3b's drawn pixels against "empty";
  - t7: E829's pb-p4a-ffff scored with its own value frozen (0xffffffff): H-OLD held; must fail: E829's pb-p3a-twin (render 2 draws
    the twin's picture) with its value frozen; with this session's value (0x00000001) frozen, p4a reads "the poke did not land".
Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "gen"), os.path.join(KP, "score"), HERE]
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import score_r as S  # noqa: E402

S.preds()
bad = 0
A = L.R5X_A


def check(cond, msg):
    global bad
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        bad = 1


def jobs(d):
    c = L.read_cases(d)
    return c, (lambda n: S.job(d, c, n))


# ---- s0 and t8 --------------------------------------------------------------------------------------------------------------------
r = S.s0_stage(A + "/s0")[1]
check(all(v == "PASS" for v in r["verdicts"].values()), "replay s0 on r5's kept s0: %s" % r["verdicts"])
_, tj = jobs(A + "/t")
P = S.PRED["t"]
v, t = S.ctl(tj("t6-ctl-te40-1array"), P, "t8-ctl-te40-1array")
check(v == "PASS", "replay t8 on r5's t6 (the same row): PASS (%s)" % t[:60])
qc0, qj0 = jobs(L.Q285)
v, t = S.ctl(qj0("pb-p2-own11"), P, "t8-ctl-te40-1array")
check(v == "FAILED", "must fail: E829's pb-p2-own11 (the same poke, two renders) scored as t8 FAILS: %s" % t[:80])

# ---- a: outcomes of r5's decided rows ----------------------------------------------------------------------------------------------
obs = []
for st in ("m", "l", "x", "d"):
    c, j = jobs(A + "/" + st)
    for n in c:
        ob, _ = S.rule_obs(j(n))
        if ob:
            obs.append(S.dims(c[n]["args"]) + (ob, n))
agree = [o for o in obs if R.fault(R.HTPM, *o[:4]) == (o[4] == "fault")]
check(len(obs) == 14 and len(agree) == 14, "replay: r5's %d decided rows of m, l, x, d by argv: H-TPM agrees with %d (the fit's data: it must hold)" % (len(obs), len(agree)))
kor = [o[5] for o in obs if R.fault("K-OR", *o[:4]) != (o[4] == "fault")]
check(kor, "must fail: K-OR (the dead rule a1, a8, a9, a12, a13 test) is contradicted by r5's rows: %s" % kor)
check(R.survivors([o[:5] for o in obs], R.ALL) == ["TPM-y-rgn"], "replay: of every variant and dead rule only H-TPM survives r5's rows: %s" % R.survivors([o[:5] for o in obs], R.ALL))

# ---- a: the held sets on E869's dump --------------------------------------------------------------------------------------------------
c, j = jobs(A + "/d")
dj = j("d1-1280x1024-held")
n = "d1-1280x1024-held"


def ph(lost):
    """h's predictions as the generator writes them, for row d's size (the frozen form, built from rules.lost())."""
    return {(n, "lost"): [(",".join("0x%x" % o for o in lost), "", "heldout")], (n, "header0_lost"): [("yes" if lost and lost[0] == R.lay(1280, 1024)["rgn"] else "no", "", "heldout")]}


ob, st, t = S.held_row(n, dj, S.PRED["a"], ph(R.lost(1280, 1024)))
check(ob == "fault" and st is True and "set equal (1023)" in t, "replay h on E869's dump with H-TPM's set: %s" % t[-90:])
h2 = [int(x, 16) for x in L.pred(S.PRED["h"], "h2-1280x768-held", "lost").split(",")]
ob, st, t = S.held_row(n, dj, S.PRED["a"], ph(h2))
check(st is False and "lost only" in t, "must fail: E869's dump against h2's frozen set (another size): %s" % t.split("; ", 1)[1][:90])
ob, st, t = S.held_row(n, dj, S.PRED["a"], ph(R.lost(1280, 1024, yeven=False)))
check(st is False and "both 426" in t, "must fail: E869's dump against the x-even set: %s" % t.split("; ", 1)[1][:90])
mc, mj = jobs(A + "/m")
m1 = mj("m1-1280x1024-max1280x1040")
fake = dict(dj)
fake["heldtadata"] = L.read_bytes(A + "/m/m1-1280x1024-max1280x1040.tri.tadata.bin.gz")
fake["row"] = dict(dj["row"], args=dj["row"]["args"].replace("--max-height 1024", "--max-height 1040"))
ob, st, t = S.held_row(n, fake, S.PRED["a"], ph([o + 0xc000 for o in R.lost(1280, 1024)]))
check(st is False and "predicted only 1023" in t, "must fail: m1's completed dump presented as a held one (nothing lost): %s" % t.split("; ", 1)[1][:90])
o5 = dict(dj)
o5["heldtadata"] = L.read_bytes(L.R4G_A2 + "/o/o5-4x-288x144-p23-held.heldtadata.bin.gz")
ob, st, t = S.held_row(n, o5, S.PRED["a"], ph(R.lost(1280, 1024)))
check(st is None and "cannot tell" in t, "must fail (cannot tell, never a pass): r4's error-text held dump: %s" % t.split("; ", 1)[1][:80])
ex = S.held_explore(n, dj)
check("'bit27': 914" in ex and "held scene pages 321" in ex, "explore on E869's dump: bit 27 on 914 headers, 321 held scene pages (E869, E870): %s" % ex[:120])

# ---- t: 0xc0's insertion against the frozen 11.31 heads -----------------------------------------------------------------------------
for src, case, pos in (("t3c-line-te80", "t5-line-tec0", 9), ("t3-line-te40", "t5-line-tec0", 9), ("t4c-point-te80", "t6-point-tec0", 11), ("t4-point-te40", "t6-point-tec0", 11)):
    st, t = S.t_ins_row(case, tj(src), P)
    check(st is True and ("inserted at %d" % pos) in t and "image empty" in t, "replay %s (r5's %s): %s" % (case, src, t))
st, t = S.t_ins_row("t5-line-tec0", tj("t3b-line-base"), P)
check(st is False and "matched no hypothesis" in t and "drawn 48" in t, "must fail: r5's t3b baseline scored as t5 (no insertion, a drawn line): %s" % t[:90])
st, t = S.t_ins_row("t5-line-tec0", tj("t4c-point-te80"), P)
check(st is False, "must fail: r5's t4c (a point) scored as t5 (a line): %s" % t[:90])

# ---- t7: E829's kpoke rows ----------------------------------------------------------------------------------------------------------
qc, qj = jobs(L.Q285)
q = "t7-tri-te40-poke11"


def pt7(val):
    p = dict(P)
    p[(q, "kpoke")] = [("par:11=0x%08x" % val, "", "heldout")]
    p[(q, "dword11")] = [("0x%08x" % val, "", "heldout")]
    return p


st, t = S.t_poke_row(q, qj("pb-p4a-ffff"), pt7(0xffffffff))
check(st is True and "render 2: 0 triangle, 4096 background, 0 other" in t, "replay t7 on E829's pb-p4a-ffff with its value frozen: %s" % t)
st, t = S.t_poke_row(q, qj("pb-p3a-twin"), pt7(0x00040101))
check(st is False, "must fail: E829's pb-p3a-twin (the twin's picture drawn) with its value frozen: %s" % t[:100])
st, t = S.t_poke_row(q, qj("pb-p4a-ffff"), P)
check(st is None and "did not land" in t, "with this session's 0x00000001 frozen, E829's 0xffffffff row reads 'the poke did not land': %s" % t[:90])
sys.exit(bad)
