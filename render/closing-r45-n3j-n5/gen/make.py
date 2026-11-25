#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of the r45-n3j-* sessions (the n3j design §3: which client event lands in
attribute 1, second reads, and what land's page follows; §9: the rebuild rows). One session per
step, STEP below says which: N5 (stages wj zn wk zt wl zft wm zf wn zff wo ztf wp ztt: a plant (row
W, mark) then crumbz after no draw, tri, fill,tri, fill, fill,fill, tri,fill, tri,tri), N6 (stages wq q:
a plant, then landq with no draws, ends in the planned stop); N1 (stages wa ff2 wb t2 wc tf2 wd tt we f3 f2b: a plant (row W, mark) then a second read with
crumb3 after fill,fill / tri / tri,fill, the new tri,tri, a third read of one fill, then F2b, a read
with no plant), N2 (wg, row W; lf2, row LF2: land after one fill again), N3 (wh; lt: land after a
triangle alone), N4 (wi; lff: land after fill,fill); the user's decisions A=a, B=a, C=a, D=b, F=a.
Built on the r44-n3i-* generator. Writes tables/STAGE.txt, predictions/STAGE.tsv for each stage and
gen/constants.txt; every input is read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Every stage (flagged, on_stop "end", #limit 0) arms emitsb_sbc43s once (slot 0, entry 0, form sbc43,
pdsat=fw14) and runs one row: job 1 is command 1 (`"ticks": true`, 200 ms, no kick; the fill
0xdeadc0de in slots 2-5 and dwords 128-223 first, as B11); the land rows' job 2 is command 6 on the
next tick pass. The outcomes are frozen per stage (design §3.1-§3.6); the scorer derives the
quantities they name (score/score.py) from the kept files, each job-scoped control and reading from
that job's own record, never from the row-end page.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

STEP = "N5"
BLOB, BASE_BLOB, FORM, SIDEBAND = "emitsb_sbc43s", "emitsb_sbc43", "sbc43", 0xC43
# the stages of each step (design §3, run order §6): stage, model, image, the stage's keys
# (session.toml), the row's jobs ("j1": command 1; "tick": command 6 on the next tick pass).
# K8 (round 44): a read stage's begin_draws is the draw sequence it reads after; own_gate none
W_KEYS = (("own_gate", "none"), ("end_draws", "none"))


def rkeys(draws):
    return (("begin_draws", draws), ("own_gate", "none"))


STAGES = {
    "N5": [("wj", "W", "mark", W_KEYS, ("j1",)),
           ("zn", "ZN", "crumbz", rkeys("none"), ("j1",)),
           ("wk", "W", "mark", W_KEYS, ("j1",)),
           ("zt", "ZT", "crumbz", rkeys("tri"), ("j1",)),
           ("wl", "W", "mark", W_KEYS, ("j1",)),
           ("zft", "ZFT", "crumbz", rkeys("fill,tri"), ("j1",)),
           ("wm", "W", "mark", W_KEYS, ("j1",)),
           ("zf", "ZF", "crumbz", rkeys("fill"), ("j1",)),
           ("wn", "W", "mark", W_KEYS, ("j1",)),
           ("zff", "ZFF", "crumbz", rkeys("fill,fill"), ("j1",)),
           ("wo", "W", "mark", W_KEYS, ("j1",)),
           ("ztf", "ZTF", "crumbz", rkeys("tri,fill"), ("j1",)),
           ("wp", "W", "mark", W_KEYS, ("j1",)),
           ("ztt", "ZTT", "crumbz", rkeys("tri,tri"), ("j1",))],
    # K7: a session's first stage keeps the default begin draws, so q (begin_draws none, as LM after
    # WL in round 44) follows the plant stage wq (builder's deviation from design §9.5's one stage)
    "N6": [("wq", "W", "mark", W_KEYS, ("j1",)),
           ("q", "Q", "landq", (("begin_draws", "none"),), ("j1", "tick"))],
}
STEPS = tuple(STAGES)
READS = ("ZN", "ZT", "ZFT", "ZF", "ZFF", "ZTF", "ZTT")   # crumbz: one quiet job after draws
LANDS = ("Q",)                                    # landq: two jobs, the early stop
# the plant stage right before a Z stage in the same attempt (design §9.1: WJ-ZN, WK-ZT, WL-ZFT,
# WM-ZF, WN-ZFF, WO-ZTF, WP-ZTT); Q has none (design §9.5)
PLANT = {"zn": "wj", "zt": "wk", "zft": "wl", "zf": "wm", "zff": "wn", "ztf": "wo", "ztt": "wp"}
# the begin draws each read stage declares (DR reads that the health mark names them at try 1)
DRAWS = {st: dict(keys)["begin_draws"] for st, m, image, keys, jobs in sum(STAGES.values(), [])
         if "begin_draws" in dict(keys)}
# the end draws of a stage (K9's end KC): a plant none, a Z stage the default, the land stage stops
ENDS = {st: ("none" if m == "W" else "fill,tri" if m in READS else None)
        for st, m, image, keys, jobs in sum(STAGES.values(), [])}
WHEN = {"N5": "after the user's OK and the one-shot boot onto the r45-kernel module (decision F "
              "(a)): the W build control wj, then crumbz after no draw, tri, fill-tri, fill, "
              "fill-fill, tri-fill and tri-tri, each right after its plant wk-wp; quiet, no "
              "planned stop",
        "N6": "after N5 (decision F (a)): wq plants M1 (the kit's K7 keeps a session's first stage "
              "on the default begin draws), q runs landq with no draws and ends in the runner's "
              "planned stop (row Q)"}
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
MAGIC = 0x4E574F53        # page dword 0, the kernel's header (PG)
M1, X0, M4, S1, M6 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306
FILL = 0xDEADC0DE
FILL_AT, FILL_N = 0x48, 16                # slots 2-5 (dwords 72-87)
SURVEY_FILL_AT, SURVEY_FILL_N = 128, 96   # dwords 128-223 (B11's)
PRE_AT, POST_SA_AT, POST_PA_AT, AFTER_AT = 128, 160, 192, 224
AFTER_SLOTS = list(range(40, 48))         # dwords 224-255 as result slots (0x40 + 4 s)
TIMEOUT_MS = 200
T3 = 0x005A3305
MK13, MK1 = 0x005D3000, 0x005D1000        # mark's markers: M13 to attribute 13, M1 to attribute 1
V1 = 0x32005000                           # the boot's #11 attribute 1 (H-BOOT, E002)
SNAP_PIN = "data:render/closing-r44-n3i-n1/out/20261124-005624/wa/wa1-a.snap0.regs.gz"


def row_name(stage):
    return f"{stage}1-a"


def arm(image):
    return f"slots=0x1 entry=0 pds={image} pdsat=fw14 form={FORM}"


def job(kind):
    fill = ", ".join([str(FILL)] * FILL_N)
    if kind == "j1":
        survey = ", ".join([str(FILL)] * SURVEY_FILL_N)
        return ('{"cmd": 1, "params": {"%d": [%s], "%d": [%s]}, "timeout_ms": %d, "ticks": true}'
                % (FILL_AT, fill, SURVEY_FILL_AT, survey, TIMEOUT_MS))
    after = ", ".join([str(FILL)] * 32)
    return ('{"cmd": 6, "params": {"%d": [%s]}, "timeout_ms": %d, "ticks": true, "slots": [%s]}'
            % (AFTER_AT, after, TIMEOUT_MS, ", ".join(map(str, AFTER_SLOTS))))


def args(jobs):
    return job(jobs[0]) if len(jobs) == 1 else "[" + ", ".join(job(k) for k in jobs) + "]"


def page(w):
    return f"cid15 page 0x{w & ~0xFFF:08x}"


# the outcomes of each model (design §3.1-§3.5): {name: ({quantity: value}, prediction, meaning)};
# the quantities are the scorer's derived readings (score.py readings_of). A prediction "printed"
# is an outcome the design prints and never scores (X-OTHER, F2-OTHER, LM-OTHER, LF-AOTHER)
def hexw(w):
    return f"0x{w:08x}"


def sa1(*ws):
    """postsa1 equal to one word, or any of several (the design's `or`)."""
    return {"postsa1": hexw(ws[0]) if len(ws) == 1 else "@any:" + ",".join(map(hexw, ws))}


M1W = MK1                                   # the planted word, kept
Q0 = 0x005D2000                             # landq's Q0, attribute 0 (above M1's page)
W_TRI3, W_TRI2 = 0x02400000, 0x02000010     # a lone triangle's 3:22 and 3:4 at K 2 (H-KC)
W_FILL4 = 0x04000010                        # a fill's 3:4 at K 4 (the fill,tri read's X variant)
W_FT4 = 0x04400000                          # fill,tri's 3:22 at K 4 (E1189)
W_TRI8, W_TRI8B = 0x08400000, 0x08000010    # the second triangle's 3:22 and 3:4 at K 8
W_TICK1 = 0x01000000                        # F's read (E1187): a tick before the first kick


def sa1(*ws):
    """postsa1 equal to one word, or any of several (the design's `or`)."""
    return {"postsa1": hexw(ws[0]) if len(ws) == 1 else "@any:" + ",".join(map(hexw, ws))}


def hexw(w):
    return f"0x{w:08x}"


def read_common(m):
    return {"Z-QUIET": ({"snap9:0x0c08": "0x0"}, "held", "snap9 BIF_FAULT 0 (control B as a "
                                                          "scored outcome)"),
            "Z-FAULT": ({"fault1": "yes"}, "failed", "a BIF fault after job 1 (snap9 or the "
                                                     "disarm's dump)")}


def kind(*ks):
    """sa0, sa2 of job 1's post as one of the scorer's kinds (LF: 2 and a timer; TRIPLE: 0 and a
    timer; ONE: V0 and V2); the AOTHER outcomes are the kinds not named."""
    return {"sa02kind": "@in:" + ",".join(ks)}


def aother(*ks):
    return {"sa02kind": "@notin:" + ",".join(ks)}


def outcomes(m):
    if m == "W":
        return {
            "W-SA1": ({"postsa1": f"0x{MK1:08x}"}, "held", "job 1's post sa1 = M1 0x005d1000"),
            "W-SA13": ({"postsa13": f"0x{MK13:08x}", "postpa1": f"0x{MK13:08x}"}, "held",
                       "job 1's post sa13 = M13 and pa1 = M13"),
            "W-QUIET": ({"snap9:0x0c08": "0x0"}, "held",
                        "snap9 BIF_FAULT 0 (control B as a scored outcome)"),
            "W-FAULT": ({"fault1": "yes"}, "failed",
                        "a BIF fault after job 1 (snap9 or the disarm's dump)"),
        }
    if m == "ZN":
        out = {"ZN-SAME": ({"zn": "SAME"}, "held", "post sa0 = V0, sa1 = M1, sa2 = V2 [HW for "
                            "land, landv: E1198, E1185]"),
               "ZN-OTHER": ({"zn": "OTHER"}, "failed", "any other: control ZN fails (§9.2)")}
    elif m == "ZT":
        out = {"ZT-SA1": (sa1(W_TRI3), "held", "sa1 = 0x02400000 [HW T E1193; H-TRI, H-FIRST]"),
               "ZT-TRIPLE": (kind("TRIPLE"), "held", "sa0 = 0, sa2 timer [infer, H-KC's triple, "
                             "LC's]"),
               "ZT-ONE": (kind("ONE"), "failed", "sa0 = V0, sa2 = V2 (a triangle writes "
                          "attribute 1 alone) [infer]"),
               "ZT-AOTHER": (aother("TRIPLE", "ONE"), "printed", "any other sa0, sa2")}
    elif m == "ZFT":
        out = {"ZFT-SA1": (sa1(W_FT4, W_FILL4), "held", "sa1 = 0x04400000 (or X's 0x04000010) "
                           "[HW, eight reads, E1189 and n3i §0.1]"),
               "ZFT-TRIPLE": (kind("TRIPLE"), "held", "sa0 = 0, sa2 timer [HW under land twice: "
                              "LC, LC2, E1176, E1178]"),
               "ZFT-ONE": (kind("ONE"), "failed", "sa0 = V0, sa2 = V2 [infer]"),
               "ZFT-AOTHER": (aother("TRIPLE", "ONE"), "printed", "any other sa0, sa2")}
    elif m == "ZF":
        out = {"ZF-SA1": (sa1(M1W), "held", "sa1 = M1 [HW LF E1200; H-TRI]"),
               "ZF-TICK1": ({"postsa1": hexw(W_TICK1)}, "failed", "sa1 = 0x01000000 (F, E1187) "
                            "[infer; H-RACE allows it]"),
               "ZF-DRAW": (kind("LF"), "held", "sa0 = 0x00000002, sa2 timer (LF's shape) "
                           "[infer, R-DRAW]"),
               "ZF-PLANT": (kind("ONE"), "failed", "sa0 = V0, sa2 = V2 [infer; held under "
                            "R-TICK]"),
               "ZF-AOTHER": (aother("LF", "ONE"), "printed", "any other sa0, sa2")}
    elif m == "ZFF":
        out = {"ZFF-SA1": (sa1(M1W), "held", "sa1 = M1 [HW FF E1191; H-TRI]"),
               "ZFF-DRAW": (kind("LF"), "held", "sa0 = 0x00000002, sa2 timer [infer, R-DRAW; "
                            "§3.6's LFF-SA0]"),
               "ZFF-PLANT": (kind("ONE"), "failed", "sa0 = V0, sa2 = V2 [infer; held under "
                             "R-TICK; LFF-V0's shape]"),
               "ZFF-AOTHER": (aother("LF", "ONE"), "printed", "any other sa0, sa2")}
    elif m == "ZTF":
        out = {"ZTF-SA1": (sa1(W_TRI3), "held", "sa1 = 0x02400000 [HW TF E1195; H-TRI, "
                           "H-FIRST]"),
               "ZTF-DRAW": (kind("LF"), "held", "sa0 = 2, sa2 timer (the fill rewrites sa0 and "
                            "sa2 only) [infer, R-DRAW]"),
               "ZTF-TRIPLE": (kind("TRIPLE"), "failed", "sa0 = 0, sa2 timer (the triangle's "
                              "triple kept) [infer; held under R-TICK]"),
               "ZTF-AOTHER": (aother("LF", "TRIPLE"), "printed", "any other sa0, sa2")}
    elif m == "ZTT":
        out = {"ZTT-LAST": (sa1(W_TRI8, W_TRI8B), "held", "sa1 = 0x08400000 (or 0x08000010) "
                            "[infer, H-TRI]"),
               "ZTT-FIRST": (sa1(W_TRI3, W_TRI2), "failed", "sa1 = 0x02400000 (or 0x02000010) "
                             "[infer; held under H-FIRST]"),
               "ZTT-TRIPLE": (kind("TRIPLE"), "held", "sa0 = 0, sa2 timer [infer, H-KC's "
                              "triple]"),
               "ZTT-ONE": (kind("ONE"), "failed", "sa0 = V0, sa2 = V2 [infer]"),
               "ZTT-AOTHER": (aother("TRIPLE", "ONE"), "printed", "any other sa0, sa2")}
    elif m == "Q":
        pg = lambda w: f"cid15 page 0x{w:08x}"      # noqa: E731
        return {
            "Q-WRITE": ({"j1": "DONE", "postsa0": hexw(Q0), "postsa1": hexw(MK1)}, "held",
                        "job 1 done; post sa0 = 0x005d2000, sa1 = 0x005d1000 [infer; LV E1183]"),
            "Q-SA0": ({"j2": "notdone", "j2fault": pg(Q0)}, "held", "job 2 not done; K5 "
                       "BIF_FAULT CID 15 at 0x005d2000 (0x005d200f) [infer, H-SA0]"),
            "Q-LOW": ({"j2": "notdone", "j2fault": pg(MK1)}, "failed", "the same at page "
                      "0x005d1000 (0x005d100f) [infer; held under \"lowest page\"]"),
            "Q-OTHER": ({"j2fault": "@faultnotin:" + pg(Q0) + "," + pg(MK1)}, "printed",
                        "a fault at any other page (sa2's, sa13's, page 0)"),
            "Q-SERVE": ({"j2": "done"}, "failed", "job 2 done, no fault [HW against: "
                         "E1176-E1200's land stops]"),
        }
    else:
        raise KeyError(m)
    if m in READS:
        out.update(read_common(m))
    return out


# the controls of every stage (all can fail, design §3): row-scoped PG (page dword 0), T0 (snap0's
# timer running), B (BIF_FAULT 0 in snap9; a fault is read by the outcomes that name it), DR (read
# rows: the declared begin draws ran at try 1, each exact, no other draw between the begin reset
# and the arm); job-scoped, read in that job's record and never on the row-end page (the H3 slip,
# E1176): E0 from job 1's record (slot 1 = M1 and run id 1, cmd_after 0), J1 job 1 DONE (X0, S1, M4
# with its run id, its record done; else CANNOT TELL and stop the session); land rows: J2 job 2's
# record (done, slot 6 = M6 and run id 2). Only PG, E0, T0 and J1 decide the RULE (and DR in the
# read rows, LF and F2)
COMMON = [("res:0x0", f"0x{MAGIC:08x}", "PG: the page is ours and was read"),
          ("j1rec:slot0", f"0x{M1:08x}", "E0: entry 0 ran job 1 (slot 1 marker, job 1's record)"),
          ("j1rec:slot1", "@runid1", "E0: entry 0 ran job 1 (slot 1 run id, job 1's record)"),
          ("j1rec:cmd", "0x0", "E0: cmd 0 (entry 0 cleared it; job 1's record's cmd_after)"),
          ("snap0:0x0acc", "running", "T0: the tick's timer running before the command"),
          ("snap9:0x0c08", "0x0", "B: no BIF fault after the row (a fault is read by the "
                                  "outcomes that name it)"),
          ("j1", "DONE", "J1: job 1 DONE (X0, S1, M4 with its run id, done)")]
DR = ("dr", "ok", "DR: the declared begin draws ran at try 1, each exact, no other draw between "
                  "the begin reset and the arm")
DK = ("dk", "ok", "DK: the begin command count (ccb_sent, arm minus begin load) is 2 + 2 x fills "
                  "+ 6 x tris, no retry (K9)")
ZNCTL = ("znctl", "SAME", "ZN: control ZN (session-scoped, §9.2): the stage zn of the same attempt "
                          "read ZN-SAME (post sa0 V0, sa1 M1, sa2 V2); when not, this stage's "
                          "sa0/sa2 outcomes read cannot tell")
JOBCTL = {
    "W": [],
    "Q": [("j2rec:done", "done", "J2: job 2 done (its record)"),
          ("j2rec:slot0", f"0x{M6:08x}", "J2: job 2's slot 6 marker M6 (its record)"),
          ("j2rec:slot1", "@runid2", "J2: job 2's slot 6 run id (its record)")],
}
for _m in READS:
    JOBCTL[_m] = []


def controls(m):
    """Q: DR and DK are not scored (no draws, §9.5), the scorer prints them. A Z stage after zn
    carries ZN."""
    return COMMON + ([] if m in ("W", "Q") else [DR, DK]) + \
        ([ZNCTL] if m in READS and m != "ZN" else []) + JOBCTL[m]


def design(m, st):
    sec = {"W": "§9.3", "ZN": "§9.4", "ZT": "§9.4", "ZFT": "§9.4", "ZF": "§9.4", "ZFF": "§9.4",
           "ZTF": "§9.4", "ZTT": "§9.4", "Q": "§9.5"}[m]
    return f"n3j design {sec} ({st.upper()})"


def keys_text(keys):
    return ", ".join(f'{k} = "{v}"' for k, v in keys)


def tables():
    out = {}
    for st, m, image, keys, jobs in STAGES[STEP]:
        t = [f"#stage {st}", "#limit 0",
             f"# {st}: N3j row {m} (closing29/n3j/design.md), the task {BLOB} armed once",
             f"# ({arm(image)}; {keys_text(keys)}); one row of {len(jobs)} "
             f"job{'s' * (len(jobs) > 1)}: "
             + ", ".join({"j1": "command 1 with ticks on the timer pass",
                          "tick": "command 6 on the next tick pass"}[k] for k in jobs) + ";",
             "# any stop ends the session",
             f"{row_name(st)}|fit|flagged|-|owntask|{args(jobs)}"]
        out[f"tables/{st}.txt"] = "\n".join(t) + "\n"
    return out


def predictions():
    out = {}
    for st, m, image, keys, jobs in STAGES[STEP]:
        n = row_name(st)
        p = [HEAD]
        for model, (qs, pred, meaning) in outcomes(m).items():
            for q, v in qs.items():
                p.append(f"{n}\t{q}\t{v}\t{model}\tfit\t{design(m, st)}: {meaning} "
                         f"[predicted: {pred}]\n")
        for q, v, why in controls(m):
            p.append(f"{n}\t{q}\t{v}\tCTL\tfit\t{design(m, st)} {why}\n")
        out[f"predictions/{st}.tsv"] = "".join(p)
    return out


def snap_v():
    """TA3DCtl dwords 0-3 of the pinned snap0 (`ta3dctl 0xOO 0xVVVVVVVV` lines)."""
    t = pins.blob(SNAP_PIN).decode()
    v = {int(mm.group(1), 16) // 4: int(mm.group(2), 16)
         for mm in re.finditer(r"^ta3dctl (0x[0-9a-f]{2}) (0x[0-9a-f]{8})$", t, re.M)}
    return [v[i] for i in range(4)]


def constants():
    out = [f"STEP {STEP}"]
    for st, m, image, keys, jobs in STAGES[STEP]:
        out.append(f"STAGE {st} {m} BLOB {BLOB} BASE {BASE_BLOB} SIDEBAND 0x{SIDEBAND:03x} "
                   f"ARM {arm(image)} KEYS {keys_text(keys) or '-'} JOBS {','.join(jobs)}")
    out += [f"M1 0x{M1:08x}", f"X0 0x{X0:08x}", f"M4 0x{M4:08x}", f"S1 0x{S1:08x}",
            f"M6 0x{M6:08x}", f"T3 0x{T3:08x}", f"M13 0x{MK13:08x}", f"MK1 0x{MK1:08x}",
            f"Q0 0x{Q0:08x}",
            f"V1 0x{V1:08x}", f"PRE {PRE_AT}", f"POST_SA {POST_SA_AT}", f"POST_PA {POST_PA_AT}",
            f"AFTER {AFTER_AT}"]
    return "\n".join(out + [f"V{i} 0x{x:08x}" for i, x in enumerate(snap_v())]) + "\n"


def build():
    out = dict(tables())
    out.update(predictions())
    out["gen/constants.txt"] = constants()
    return out


def main(argv):
    out = build()
    check = "--check" in argv
    bad = []
    for rel, body in out.items():
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p).read() != body:
                bad.append(rel)
        else:
            open(p, "w").write(body)
    if bad:
        print("not current: " + ", ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
