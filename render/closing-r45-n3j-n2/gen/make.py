#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of the r45-n3j-* sessions (the n3j design §3: which client event lands in
attribute 1, second reads, and what land's page follows). One session per step, STEP below says
which: N1 (stages wa ff2 wb t2 wc tf2 wd tt we f3 f2b: a plant (row W, mark) then a second read with
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

STEP = "N2"
BLOB, BASE_BLOB, FORM, SIDEBAND = "emitsb_sbc43s", "emitsb_sbc43", "sbc43", 0xC43
# the stages of each step (design §3, run order §6): stage, model, image, the stage's keys
# (session.toml), the row's jobs ("j1": command 1; "tick": command 6 on the next tick pass).
# K8 (round 44): a read stage's begin_draws is the draw sequence it reads after; own_gate none
W_KEYS = (("own_gate", "none"), ("end_draws", "none"))


def rkeys(draws):
    return (("begin_draws", draws), ("own_gate", "none"))


STAGES = {
    "N1": [("wa", "W", "mark", W_KEYS, ("j1",)),
           ("ff2", "FF2", "crumb3", rkeys("fill,fill"), ("j1",)),
           ("wb", "W", "mark", W_KEYS, ("j1",)),
           ("t2", "T2", "crumb3", rkeys("tri"), ("j1",)),
           ("wc", "W", "mark", W_KEYS, ("j1",)),
           ("tf2", "TF2", "crumb3", rkeys("tri,fill"), ("j1",)),
           ("wd", "W", "mark", W_KEYS, ("j1",)),
           ("tt", "TT", "crumb3", rkeys("tri,tri"), ("j1",)),
           ("we", "W", "mark", W_KEYS, ("j1",)),
           ("f3", "F3", "crumb3", rkeys("fill"), ("j1",)),
           ("f2b", "F2B", "crumb3", rkeys("fill"), ("j1",))],
    "N2": [("wg", "W", "mark", W_KEYS, ("j1",)),
           ("lf2", "LF2", "land", (("begin_draws", "fill"),), ("j1", "tick"))],
    "N3": [("wh", "W", "mark", W_KEYS, ("j1",)),
           ("lt", "LT", "land", (("begin_draws", "tri"),), ("j1", "tick"))],
    "N4": [("wi", "W", "mark", W_KEYS, ("j1",)),
           ("lff", "LFF", "land", (("begin_draws", "fill,fill"),), ("j1", "tick"))],
}
STEPS = tuple(STAGES)
READS = ("FF2", "T2", "TF2", "TT", "F3", "F2B")   # one quiet job after a draw sequence
LANDS = ("LF2", "LT", "LFF")                      # land: two jobs, the early stop
# the plant stage right before a read stage in the same attempt (design §1: the pairing WA-FF2,
# WB-T2, WC-TF2, WD-TT, WE-F3; WG-LF2, WH-LT, WI-LFF); F2B has none (design §3.3)
PLANT = {"ff2": "wa", "t2": "wb", "tf2": "wc", "tt": "wd", "f3": "we", "lf2": "wg", "lt": "wh",
         "lff": "wi"}
# the begin draws each read stage declares (DR reads that the health mark names them at try 1)
DRAWS = {st: dict(keys)["begin_draws"] for st, m, image, keys, jobs in sum(STAGES.values(), [])
         if "begin_draws" in dict(keys)}
# the end draws of a stage (K9's end KC): a plant none, a read the default, a land stage stops
ENDS = {st: ("none" if m == "W" else "fill,tri" if m in READS else None)
        for st, m, image, keys, jobs in sum(STAGES.values(), [])}
WHEN = {"N1": "first of round 45 (decisions A (a), F (a)): five plants and the second reads after "
              "fill-fill, tri and tri-fill, the new tri-tri, a third read of one fill, then F2b "
              "with no plant; all quiet, no planned stop; no build, no boot",
        "N2": "after N1 (decision F (a)): wg plants M1, lf2 runs land after one fill again and "
              "ends in the runner's planned stop (row LF2); no build, no boot",
        "N3": "after N2 (decision F (a)): wh plants M1, lt runs land after a triangle alone and "
              "ends in the runner's planned stop (row LT); no build, no boot",
        "N4": "last, after N3 (decision D (b), F (a)): wi plants M1, lff runs land after "
              "fill-fill and ends in the runner's planned stop (row LFF); no build, no boot"}
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
TICK = "tick"                               # a tick's word: bits 23:0 0, top byte 1-4 (E746)
W_TRI3, W_TRI2 = 0x02400000, 0x02000010     # a lone triangle's 3:22 and 3:4 at K 2 (H-KC)
W_FILL2, W_FILL4, W_FILL8 = 0x02000010, 0x04000010, 0x08000010   # a fill's 3:4 at K 2, 4, 8
W_TRI8, W_TRI8B = 0x08400000, 0x08000010    # the second triangle's 3:22 and 3:4 at K 8
W_END5 = 0x05400000                         # F2's read (E1196): a fill,tri end's 3:22 at K 5
W_TICK1 = 0x01000000                        # F's read (E1187): a tick before the first kick


def read_common(m):
    return {"X-QUIET": ({"snap9:0x0c08": "0x0"}, "held", "snap9 BIF_FAULT 0 (control B as a "
                                                          "scored outcome)")}


def other(*ws):
    """The printed outcome: any word the stage's outcomes do not name."""
    return {"postsa1": "@notany:" + ",".join(w if w == TICK else hexw(w) for w in ws)}


def tick_or(*ws):
    return {"postsa1": "@any:" + ",".join(w if w == TICK else hexw(w) for w in ws)}


# the page rule of design §0.4 (H-SA0): page 0 when post sa0 < 0x1000, sa1's page when post sa0 =
# V0; the scorer's `@hsa0` (unread, cannot tell, for any other sa0)
def page_rule(held_name, pred, page_meaning):
    return {"j2": "notdone", "j2fault": "@hsa0"}


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
    if m == "FF2":
        out = {"FF2-KEEP": (sa1(M1W), "held", "M1 (FF's read, E1191) [HW once; H-TRI, H-FIRST]"),
               "FF2-FILL": (sa1(W_FILL4, W_FILL2), "failed", "0x04000010 (the 2nd fill's 3:4 at "
                            "K 4) or 0x02000010 (the 1st's at K 2) [infer]"),
               "FF2-TICK": (tick_or(TICK), "failed", "bits 23:0 = 0, top byte 1-4 (a tick) [infer; "
                            "held only under H-RACE]"),
               "FF2-OTHER": (other(M1W, W_FILL4, W_FILL2, TICK), "printed", "any other word")}
    elif m == "T2":
        out = {"T2-SAME": (sa1(W_TRI3), "held", "0x02400000 (T's read, E1193; the 3:22 at K 2) "
                           "[HW once; H-TRI, H-FIRST]"),
               "T2-34": (sa1(W_TRI2), "failed", "0x02000010 (the triangle's 3:4, X's variant) "
                         "[infer; H-RACE allows it]"),
               "T2-KEEP": (sa1(M1W), "failed", "M1 [infer]"),
               "T2-OTHER": (other(W_TRI3, W_TRI2, M1W), "printed", "any other word")}
    elif m == "TF2":
        out = {"TF2-SAME": (sa1(W_TRI3), "held", "0x02400000 (TF's read, E1195) [HW once; H-TRI, "
                            "H-FIRST]"),
               "TF2-FILL": (sa1(W_FILL8), "failed", "0x08000010 (the fill's 3:4 at K 8) [infer; "
                            "H-RACE allows it]"),
               "TF2-KEEP": (sa1(M1W), "failed", "M1 [infer]"),
               "TF2-OTHER": (other(W_TRI3, W_FILL8, M1W), "printed", "any other word")}
    elif m == "TT":
        out = {"TT-LAST": (sa1(W_TRI8, W_TRI8B), "held", "0x08400000 (or its 3:4 variant "
                           "0x08000010) [infer, H-TRI]"),
               "TT-FIRST": (sa1(W_TRI3, W_TRI2), "failed", "0x02400000 (or 0x02000010) [infer; "
                            "held under H-FIRST]"),
               "TT-KEEP": (sa1(M1W), "failed", "M1 [infer]"),
               "TT-OTHER": (other(W_TRI8, W_TRI8B, W_TRI3, W_TRI2, M1W), "printed",
                            "any other word")}
    elif m == "F3":
        out = {"F3-KEEP": (sa1(M1W), "held", "M1 (as LF, E1200, and FF) [infer, H-TRI]"),
               "F3-TICK": (sa1(W_TICK1), "failed", "0x01000000 (as F, E1187) [infer; H-RACE "
                           "allows it]"),
               "F3-FILL": (sa1(W_FILL2), "failed", "0x02000010 (the fill's 3:4 at K 2) [infer]"),
               "F3-OTHER": (other(M1W, W_TICK1, W_FILL2), "printed", "any other word")}
    elif m == "F2B":
        return {
            "F2b-SAME": (sa1(W_END5), "held", "0x05400000 (F2's read, E1196) [HW once; H-KC, "
                                              "H-TRI]"),
            "F2b-TICK": (sa1(W_TICK1), "failed", "0x01000000 [infer; H-RACE]"),
            "F2b-FILL": (sa1(W_FILL2), "failed", "0x02000010 [infer]"),
            "F2b-OTHER": (other(W_END5, W_TICK1, W_FILL2), "printed", "any other word"),
            "F2b-QUIET": ({"snap9:0x0c08": "0x0"}, "held", "snap9 BIF_FAULT 0"),
        }
    elif m == "LF2":
        return {
            "LF2-SA1": (sa1(M1W), "held", "post sa1 = M1 [HW once, E1200; H-TRI]"),
            "LF2-SA0": ({"postsa0": hexw(2)}, "held", "post sa0 = 0x00000002 [HW once, E1200]"),
            "LF2-SA2": ({"sa2shape": "TIMER"}, "held", "post sa2 top byte 0x01, bits 23:0 < "
                         "400000, != 0x061a70 [HW once, E1200]"),
            "LF2-TICK": ({"postsa1": hexw(W_TICK1)}, "failed", "post sa1 = 0x01000000 (F's "
                          "word) [infer; H-RACE]"),
            "LF2-AOTHER": ({"sa02kind": "@notin:LF"}, "printed", "any other sa0, sa2"),
            "LF2-PAGE": (page_rule("LF2-PAGE", "held", ""), "held", "job 2 not done; K5 "
                         "BIF_FAULT CID 15 at the H-SA0 rule's page (design §0.4)"),
            "LF2-EARLY0": ({"j2": "notdone", "j2fault": page(0)}, "held", "the same at page 0 "
                           "[HW once; H-SA0 with LF2-SA0, H-HIST]"),
            "LF2-EARLY1": ({"j2": "notdone", "j2fault": "@post1"}, "failed", "the same at post "
                           "sa1's page"),
            "LF2-SERVE": ({"j2": "done"}, "failed", "job 2 done [HW against: E1176, E1178, "
                           "E1183, E1185, E1198, E1200]"),
        }
    elif m == "LT":
        return {
            "LT-SA1": (sa1(W_TRI3), "held", "post sa1 = 0x02400000 [HW once, T E1193; H-TRI]"),
            "LT-TRIPLE": ({"postsa0": hexw(0), "sa2shape": "TIMER"}, "held", "post sa0 = 0; sa2 "
                          "top byte 0x01, bits 23:0 < 400000 [infer, LC's triple]"),
            "LT-ONE": ({"postsa0": "@V0", "postsa2": "@V2"}, "failed", "post sa0 = V0 and sa2 = "
                       "V2 (the triangle writes attribute 1 alone) [infer]"),
            "LT-AOTHER": ({"sa02kind": "@notin:TRIPLE,ONE"}, "printed", "any other sa0, sa2"),
            "LT-PAGE": (page_rule("LT-PAGE", "held", ""), "held", "job 2 not done; K5 BIF_FAULT "
                        "CID 15 at the H-SA0 rule's page (design §0.4)"),
            "LT-HIST": ({"j2": "notdone", "j2fault": page(0), "postsa0": "@V0"}, "failed",
                        "the same at page 0 while post sa0 = V0 [infer; held under H-HIST]"),
            "LT-SERVE": ({"j2": "done"}, "failed", "job 2 done"),
        }
    elif m == "LFF":
        return {
            "LFF-SA1": (sa1(M1W), "held", "post sa1 = M1 [HW once, FF]"),
            "LFF-SA0": ({"postsa0": hexw(2)}, "held", "post sa0 = 2 [infer, LF: the last fill's "
                        "write]"),
            "LFF-V0": ({"postsa0": "@V0"}, "failed", "post sa0 = V0 [infer]"),
            "LFF-PAGE": (page_rule("LFF-PAGE", "held", ""), "held", "job 2 not done; K5 "
                         "BIF_FAULT CID 15 at the H-SA0 rule's page (design §0.4)"),
            "LFF-HIST": ({"j2": "notdone", "j2fault": page(0), "postsa0": "@V0"}, "failed",
                         "page 0 with post sa0 = V0 [infer; held under H-HIST]"),
        }
    else:
        raise KeyError(m)
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
JOBCTL = {
    "W": [],
    "LF2": [("j2rec:done", "done", "J2: job 2 done (its record)"),
            ("j2rec:slot0", f"0x{M6:08x}", "J2: job 2's slot 6 marker M6 (its record)"),
            ("j2rec:slot1", "@runid2", "J2: job 2's slot 6 run id (its record)")],
}
JOBCTL["LT"] = JOBCTL["LFF"] = JOBCTL["LF2"]
for _m in READS:
    JOBCTL[_m] = []


def controls(m):
    return COMMON + ([] if m == "W" else [DR, DK]) + JOBCTL[m]


def design(m, st):
    sec = {"W": "§3.1", "FF2": "§3.2", "T2": "§3.2", "TF2": "§3.2", "TT": "§3.2", "F3": "§3.2",
           "F2B": "§3.3", "LF2": "§3.4", "LT": "§3.5", "LFF": "§3.6"}[m]
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
