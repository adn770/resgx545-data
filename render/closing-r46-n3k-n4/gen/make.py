#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of the r46-n3k-* sessions (closing29/n3k/design.md: which page land's stop
keeps, whether two fills write attribute 1, and B5/B6; §10: the user's decisions A=a, B=b, C=a, D=a,
E=a, F=b, every session on the r46-kernel module). One session per step, STEP below says which:
B5 (stage b5: crumb3 with emitsb_sb043s, sideband 0x043, job 1 the emit, job 2 the after-read on
a GETMISCINFO kick, then the gate), B6 (stage b6: the same with emitsb_sb803s, sideband 0x803),
N1 (wa zff2 wb lff2: a plant (row W, mark), crumbz after fill,fill, a plant, land after fill,fill;
ends in LFF2's stop), N2 (wc lff3), N3 (wd lf3f: land after fill,fill,fill), N4 (we q2: landq, no
draws), N5 (wf r: landr), N6 (wg p: landp), N7 (wh r2), N8 (wi p2). Built on the r45-n3j-*
generator. Writes tables/STAGE.txt, predictions/STAGE.tsv for each stage and gen/constants.txt;
every input is read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Every stage (flagged, on_stop "end", #limit 0) arms its blob once (slot 0, entry 0, pdsat=fw14)
and runs one row: job 1 is command 1 (`"ticks": true`, 200 ms, no kick; the fill 0xdeadc0de in
slots 2-5 and dwords 128-223 first, as B11); the land rows' job 2 is command 6 on the next tick
pass; the B rows' job 2 is command 6 on a GETMISCINFO kick (round 41's row C). The outcomes are
frozen per stage (design §4, §10); the scorer derives the quantities they name (score/score.py)
from the kept files, each job-scoped control and reading from that job's own record, never from
the row-end page.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

STEP = "N4"
# the blob of each step: the B rows arm the after-read blob of their form (round 46, resgx545
# r46-n3k 4f9c1ea1: emitsb_sbc43s but the emit word); every N row emitsb_sbc43s (round 45's)
FORMS = {"B5": ("sb043", 0x043), "B6": ("sb803", 0x803)}
FORM, SIDEBAND = FORMS.get(STEP, ("sbc43", 0xC43))
BLOB, BASE_BLOB = f"emitsb_{FORM}s", f"emitsb_{FORM}"
W_KEYS = (("own_gate", "none"), ("end_draws", "none"))


def rkeys(draws):
    return (("begin_draws", draws), ("own_gate", "none"))


def lkeys(draws):
    return (("begin_draws", draws),)


# the stages of each step (design §2, §10 run order): stage, model, image, the stage's keys
# (session.toml), the row's jobs ("j1": command 1; "tick": command 6 on the next tick pass;
# "kick": command 6 on a GETMISCINFO kick)
STAGES = {
    "B5": [("b5", "B5", "crumb3", (("on_gate_fail", "score"),), ("j1", "kick"))],
    "B6": [("b6", "B6", "crumb3", (("on_gate_fail", "score"),), ("j1", "kick"))],
    "N1": [("wa", "W", "mark", W_KEYS, ("j1",)),
           ("zff2", "ZFF2", "crumbz", rkeys("fill,fill"), ("j1",)),
           ("wb", "W", "mark", W_KEYS, ("j1",)),
           ("lff2", "LFF2", "land", lkeys("fill,fill"), ("j1", "tick"))],
    "N2": [("wc", "W", "mark", W_KEYS, ("j1",)),
           ("lff3", "LFF3", "land", lkeys("fill,fill"), ("j1", "tick"))],
    "N3": [("wd", "W", "mark", W_KEYS, ("j1",)),
           ("lf3f", "LF3F", "land", lkeys("fill,fill,fill"), ("j1", "tick"))],
    "N4": [("we", "W", "mark", W_KEYS, ("j1",)),
           ("q2", "Q2", "landq", lkeys("none"), ("j1", "tick"))],
    "N5": [("wf", "W", "mark", W_KEYS, ("j1",)),
           ("r", "R", "landr", lkeys("none"), ("j1", "tick"))],
    "N6": [("wg", "W", "mark", W_KEYS, ("j1",)),
           ("p", "P", "landp", lkeys("none"), ("j1", "tick"))],
    "N7": [("wh", "W", "mark", W_KEYS, ("j1",)),
           ("r2", "R2", "landr", lkeys("none"), ("j1", "tick"))],
    "N8": [("wi", "W", "mark", W_KEYS, ("j1",)),
           ("p2", "P2", "landp", lkeys("none"), ("j1", "tick"))],
}
STEPS = tuple(STAGES)
READS = ("ZFF2",)                                   # crumbz: one quiet job after draws
LANDS = ("LFF2", "LFF3", "LF3F", "Q2", "R", "P", "R2", "P2")   # two jobs, the early stop
FILLS = ("LFF2", "LFF3", "LF3F")                    # land after fills: DR and DK scored
PAGES = ("Q2", "R", "P", "R2", "P2")                # no draws: the page rows (DR, DK printed)
BROWS = ("B5", "B6")                                # the sideband rows
# the plant stage right before a read or land stage in the same attempt (design §2): the page
# rows print it (their images write sa0 and sa1 themselves), the others read it
PLANT = {"zff2": "wa", "lff2": "wb", "lff3": "wc", "lf3f": "wd", "q2": "we", "r": "wf", "p": "wg",
         "r2": "wh", "p2": "wi"}
# the build control (design §10.3): the first plant on the r46-kernel module in the run order
BUILD_CONTROL = "wa"
# the begin draws each stage declares (DR reads that the health mark names them at try 1; the B
# rows keep the kit's default fill,tri)
DRAWS = {st: dict(keys).get("begin_draws", "fill,tri")
         for st, m, image, keys, jobs in sum(STAGES.values(), []) if m != "W"}
# the end draws of a stage (K9's end KC): a plant none, a Z stage and a B stage the default, a land
# stage stops
ENDS = {st: ("none" if m == "W" else "fill,tri" if m in READS + BROWS else None)
        for st, m, image, keys, jobs in sum(STAGES.values(), [])}
WHEN = {
    "B5": "first after the one-shot boot onto the r46-kernel module and the srcversion check "
          "(decision F (b), design §10.3): quiet expected",
    "B6": "after B5 (design §10.3): quiet expected",
    "N1": "after B6: the plant wa (the build control on the new module), crumbz after fill-fill, "
          "a plant, land after fill-fill; ends in LFF2's planned stop",
    "N2": "after N1: wc plants M1, lff3 runs land after fill-fill a third time and ends in the "
          "runner's planned stop",
    "N3": "after N2: wd plants M1, lf3f runs land after fill-fill-fill and ends in the planned "
          "stop",
    "N4": "after N3: we plants M1, q2 runs landq with no draws (Q's second read) and ends in the "
          "planned stop",
    "N5": "after N4: wf plants M1, r runs landr with no draws (sa0 0x04400000 over sa1 M1) and "
          "ends in the planned stop",
    "N6": "after N5: wg plants M1, p runs landp with no draws (sa0 V0, sa1 0x005d2000) and ends "
          "in the planned stop",
    "N7": "after N6 (decision E (a)): wh plants M1, r2 is R's second read; ends in the planned "
          "stop",
    "N8": "last (decision E (a)): wi plants M1, p2 is P's second read; ends in the planned stop",
}
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
Q0, L4 = 0x005D2000, 0x04400000           # landq's and landp's Q0; landr's sa0 word
SNAP_PIN = "data:render/closing-r45-n3j-n4/out/20261124-210745/wi/wi1-a.snap0.regs.gz"


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
    kick = ', "kick": "miscinfo"' if kind == "kick" else ""
    return ('{"cmd": 6, "params": {"%d": [%s]}, "timeout_ms": %d, "ticks": true%s, "slots": [%s]}'
            % (AFTER_AT, after, TIMEOUT_MS, kick, ", ".join(map(str, AFTER_SLOTS))))


def args(jobs):
    return job(jobs[0]) if len(jobs) == 1 else "[" + ", ".join(job(k) for k in jobs) + "]"


def hexw(w):
    return f"0x{w:08x}"


def pg(w):
    return f"cid15 page 0x{w & ~0xFFF:08x}"


def sa1(*ws):
    """postsa1 equal to one word, or any of several (the design's `or`)."""
    return {"postsa1": hexw(ws[0]) if len(ws) == 1 else "@any:" + ",".join(map(hexw, ws))}


def other(*ws):
    return {"postsa1": "@notany:" + ",".join(map(hexw, ws))}


W_FILL1, W_FILL2, W_FILL3 = 0x02000010, 0x04000010, 0x06000010   # the n-th fill's 3:4 (H-KC)


def outcomes(m):
    """{name: ({quantity: value}, prediction, meaning)}: the frozen outcomes of a model (design
    §4.2-§4.9, §10.1); a prediction "printed" is an outcome printed and never scored."""
    if m == "W":
        return {
            "W-SA1": ({"postsa1": hexw(MK1)}, "held", "job 1's post sa1 = M1 0x005d1000 [HW, 24 "
                      "runs E1184-E1232]"),
            "W-SA13": ({"postsa13": hexw(MK13), "postpa1": hexw(MK13)}, "held",
                       "job 1's post sa13 = M13 and pa1 = M13 [HW]"),
            "W-QUIET": ({"snap9:0x0c08": "0x0"}, "held",
                        "snap9 BIF_FAULT 0 (control B as a scored outcome) [HW]"),
            "W-FAULT": ({"fault1": "yes"}, "failed",
                        "a BIF fault after job 1 (snap9 or the disarm's dump)"),
        }
    if m == "ZFF2":
        return {
            "ZFF2-KEEP": ({"zffkind": "KEEP"}, "held", "sa1 = M1, sa0 = 2, sa2 timer [HW 3 reads: "
                          "E1191, E1202, E1227; H-TRI]"),
            "ZFF2-FILL2": ({"zffkind": "FILL2"}, "failed", "sa1 = 0x04000010, sa0 = 0, sa2 timer "
                           "[held under H-RACE]"),
            "ZFF2-OTHER": ({"zffkind": "OTHER"}, "printed", "any other sa0, sa1, sa2"),
            "ZFF2-QUIET": ({"snap9:0x0c08": "0x0"}, "held", "snap9 BIF_FAULT 0 [HW, E1227]"),
            "ZFF2-FAULT": ({"fault1": "yes"}, "failed", "a BIF fault after job 1 (snap9 or the "
                           "disarm's dump): stop for the user"),
        }
    if m in ("LFF2", "LFF3"):
        x = m
        return {
            f"{x}-KEEP": (sa1(MK1), "held", "sa1 = M1 [infer, H-TRI; crumb3/crumbz 3 of 3, land "
                          "after one fill 2 of 2]"),
            f"{x}-FILL2": (sa1(W_FILL2), "failed", "sa1 = 0x04000010 (the 2nd fill's 3:4 at K 4) "
                           "[held under H-FL; LFF E1217]"),
            f"{x}-FILL1": (sa1(W_FILL1), "failed", "sa1 = 0x02000010 (the 1st fill's 3:4 at K 2)"),
            f"{x}-OTHER": (other(MK1, W_FILL2, W_FILL1), "printed", "any other sa1"),
            f"{x}-SA0": ({"sa02kind": "@in:LF"}, "held", "sa0 = 2, sa2 timer (a slot-0 entry, as "
                         "ZFF, LF) [infer, with -KEEP]"),
            f"{x}-TRIPLE": ({"sa02kind": "@in:TRIPLE"}, "failed", "sa0 = 0, sa2 timer (the 3:4 "
                            "entry's triple, as LFF) [held under H-FL]"),
            f"{x}-PAGE0": ({"j2": "notdone", "j2fault": pg(0)}, "held", "job 2 not done; "
                           "BIF_FAULT list 15 at page 0 [HW 6 of 6 with sa0 < page]"),
            f"{x}-SERVE": ({"j2": "done"}, "failed", "job 2 done [HW against: every land row]"),
        }
    if m == "LF3F":
        return {
            "LF3F-KEEP": (sa1(MK1), "held", "sa1 = M1 [infer, H-TRI]"),
            "LF3F-SECOND": (sa1(W_FILL2), "failed", "sa1 = 0x04000010 (the 2nd draw's 3:4, as "
                            "LFF and X) [held under H-FL2]"),
            "LF3F-LAST": (sa1(W_FILL3), "failed", "sa1 = 0x06000010 (the 3rd fill's 3:4 at K 6) "
                          "[held under H-FLL]"),
            "LF3F-FIRST": (sa1(W_FILL1), "failed", "sa1 = 0x02000010"),
            "LF3F-OTHER": (other(MK1, W_FILL2, W_FILL3, W_FILL1), "printed", "any other sa1"),
            "LF3F-PAGE0": ({"j2": "notdone", "j2fault": pg(0)}, "held", "job 2 not done; page 0 "
                           "[infer: every fill leaves sa0 below a page]"),
            "LF3F-SERVE": ({"j2": "done"}, "failed", "job 2 done"),
        }
    if m == "Q2":
        return {
            "Q2-WRITE": ({"j1": "DONE", "postsa0": hexw(Q0), "postsa1": hexw(MK1)}, "held",
                         "job 1 done; sa0 = Q0, sa1 = M1 [HW, E1233]"),
            "Q2-SAME": ({"j2": "notdone", "j2fault": pg(MK1)}, "held", "job 2 not done; "
                        "BIF_FAULT list 15 at 0x005d1000 [HW once, E1233]"),
            "Q2-SA0": ({"j2": "notdone", "j2fault": pg(Q0)}, "failed", "the same at 0x005d2000"),
            "Q2-OTHER": ({"j2fault": "@faultnotin:" + pg(Q0) + "," + pg(MK1)}, "printed",
                         "any other page"),
            "Q2-SERVE": ({"j2": "done"}, "failed", "job 2 done"),
        }
    if m in ("R", "R2"):
        x = m
        return {
            f"{x}-WRITE": ({"j1": "DONE", "postsa0": hexw(L4), "postsa1": hexw(MK1)}, "held",
                           "job 1 done; sa0 = 0x04400000, sa1 = M1 [infer: Q-WRITE's douta, "
                           "E1233]"),
            f"{x}-LOW": ({"j2": "notdone", "j2fault": pg(MK1)}, "held", "job 2 not done; "
                         "BIF_FAULT 0x005d100f (list 15, M1's page) [infer, R-LOW]"),
            f"{x}-SA0": ({"j2": "notdone", "j2fault": pg(L4)}, "failed", "the same at 0x0440000f "
                         "(sa0's page) [held under R-SA0 and R-SA0']"),
            f"{x}-OTHER": ({"j2fault": "@faultnotin:" + pg(MK1) + "," + pg(L4)}, "printed",
                           "a fault at any other page (sa2's, sa13's, page 0)"),
            f"{x}-SERVE": ({"j2": "done"}, "failed", "job 2 done [HW against: every land row]"),
        }
    if m in ("P", "P2"):
        x = m
        return {
            f"{x}-WRITE": ({"j1": "DONE", "postsa0": "@V0", "postsa1": hexw(Q0),
                            "postsa2": "@V2"}, "held", "job 1 done; sa0 = V0, sa1 = Q0, sa2 = V2 "
                           "[infer: landv's, landq's douta]"),
            f"{x}-UNMAP": ({"j2": "notdone", "j2fault": pg(Q0)}, "held", "job 2 not done; "
                           "BIF_FAULT 0x005d200f (list 15) [infer, §0.3 (ii); R-LOW]"),
            f"{x}-MAPPED": ({"j2fault": "@notin:" + pg(Q0)}, "failed", "no fault at 0x005d2000: "
                            "job 2 done, or a fault elsewhere [held under R-SA0]"),
            f"{x}-OTHER": ({"j2fault": "@faultnotin:" + pg(Q0)}, "printed",
                           "a fault at another page (printed with -MAPPED)"),
        }
    if m in BROWS:
        x = m
        out = {
            f"{x}-NEVER": ({"start": "NEVER"}, "failed", "S1 fill, T running: the program never "
                           "started [HW against: bits 1:0 = 3, E1164, E1162]"),
            f"{x}-T1": ({"start": "T1"}, "failed", "T 0, S1 fill: stopped at a douta"),
            f"{x}-T2": ({"start": "T2"}, "failed", "T 0x200, S1 fill: stopped at the doutu"),
            f"{x}-T3": ({"start": "T3"}, "failed", "T 0x005a3305, S1 fill: entry 1 never stored"),
            f"{x}-E1": ({"start": "E1"}, "failed", "S1, no M4: entry 1 started, stopped after S1"),
            f"{x}-DONE": ({"start": "DONE"}, "held", "S1, M4 with the run id, state 2 [infer: "
                          "today's rule, bits 1:0 = 3 run the program to done, E1162-E1172]"),
            f"{x}-RUN": ({"start": "@in:T1,T2,T3,E1,DONE"}, "held", "any of T1..DONE [infer, "
                         "the rule]"),
            f"{x}-HID": ({"prepost": "SAME"}, "held", "post sa0-sa31 = pre sa0-sa31 [HW for "
                         "0x843 and 0x003, E1162, E1164; infer here]"),
            f"{x}-SAME": ({"j2": "done", "after2": "@in:PRE,BOTH"}, "held", "job 2 done; its "
                          "after-read = job 1's pre sa0-sa31 [HW for 0x843, C E1173; infer: no "
                          "bit 10]"),
            f"{x}-REBASE": ({"j2": "done", "after2": "POST"}, "failed", "job 2 done; after = "
                            "job 1's post, post != pre [held with bit 10: X, Y E1174, E1175]"),
            f"{x}-AOTHER": ({"j2": "done", "after2": "OTHER"}, "printed", "job 2 done; after "
                            "neither pre nor post"),
            f"{x}-NOKICK": ({"j2": "notdone"}, "failed", "job 2 not done 200 ms after its kick"),
            f"{x}-GATE": ({"gate1": "exact", "gate2": "exact"}, "held", "the gate's fill and "
                          "triangle exact [HW for 0x843, C E1173; B1's post E1164]"),
            f"{x}-FILL": ({"gate1": "@notin:exact"}, "failed", "the gate's fill not exact (a "
                          "fault, a hang) [held with bit 10: X-FILL, Y-FILL E1174, E1175]"),
            f"{x}-QUIET": ({"snap9:0x0c08": "0x0"}, "held", "snap9 BIF_FAULT 0 after the row"),
            f"{x}-LAND4": ({"landing": "EVERY4"}, "printed", "V0 at pa0, pa4, pa8, pa12 and V2 "
                           "at pa2, pa6, pa10, pa14 (as 0x003, E1164)"),
            f"{x}-LANDNONE": ({"landing": "NONE"}, "printed", "no V0 or V2 in pa0-pa15 (as "
                              "0x843, E1162)"),
        }
        return out
    raise KeyError(m)


# the controls of every stage (all can fail, design §4.1): row-scoped PG (page dword 0), T0
# (snap0's timer running), B (BIF_FAULT 0 in snap9; a fault is read by the outcomes that name
# it), DR (the declared begin draws ran at try 1, each exact), DK (K9: the begin command count);
# job-scoped, read in that job's record and never on the row-end page (the H3 slip, E1176): E0
# from job 1's record (slot 1 = M1 and run id 1, cmd_after 0), J1 job 1 DONE (X0, S1, M4 with its
# run id, its record done; else CANNOT TELL and stop the session); two-job rows: J2 job 2's record
# (done, slot 6 = M6 and run id 2). PLANT and SV are read by the scorer (no tsv value).
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
J2 = [("j2rec:done", "done", "J2: job 2 done (its record)"),
      ("j2rec:slot0", f"0x{M6:08x}", "J2: job 2's slot 6 marker M6 (its record)"),
      ("j2rec:slot1", "@runid2", "J2: job 2's slot 6 run id (its record)")]


def controls(m):
    """DR and DK: scored in ZFF2 and the land rows after fills; printed in the page rows and the
    B rows (no draws of their own, design §4.7-§4.9)."""
    return COMMON + ([DR, DK] if m in READS + FILLS else []) + (J2 if m in LANDS + BROWS else [])


def design(m, st):
    sec = {"W": "§4.2", "ZFF2": "§4.3", "LFF2": "§4.4", "LFF3": "§4.4", "LF3F": "§4.5",
           "Q2": "§4.7", "R": "§4.8", "R2": "§4.8", "P": "§4.9", "P2": "§4.9", "B5": "§10.1",
           "B6": "§10.1"}[m]
    return f"n3k design {sec} ({st.upper()})"


def keys_text(keys):
    return ", ".join(f'{k} = "{v}"' for k, v in keys)


JOB_WORDS = {"j1": "command 1 with ticks on the timer pass",
             "tick": "command 6 on the next tick pass",
             "kick": "command 6 on a GETMISCINFO kick"}


def tables():
    out = {}
    for st, m, image, keys, jobs in STAGES[STEP]:
        t = [f"#stage {st}", "#limit 0",
             f"# {st}: N3k row {m} (closing29/n3k/design.md), the task {BLOB} armed once",
             f"# ({arm(image)}; {keys_text(keys)}); one row of {len(jobs)} "
             f"job{'s' * (len(jobs) > 1)}: " + ", ".join(JOB_WORDS[k] for k in jobs) + ";",
             "# any stop ends the session" + ("; the gate's failure is the planned end "
                                              "(on_gate_fail score)" if m in BROWS else ""),
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
            f"Q0 0x{Q0:08x}", f"L4 0x{L4:08x}",
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
