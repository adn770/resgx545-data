#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of the round 46 addendum sessions r46-n3k-n9 ... -n16 (closing29/n3k/design.md
§11: after N1-N4, which candidate decides the stop page; the user's decisions G=a, H=a, I=a, J=a,
K=a; every session on the r46-kernel module, srcversion 10BBF3BF, this boot). One session per step,
STEP below says which: N9 (w9 lfk: a plant (row W, mark), land after one fill; ends in LFK's stop),
N10 (w10 ltk: land after one triangle), N11 (w11 lfk2: LFK's second read), N13 (w13 r: N5's stages
byte for byte, landr, plus E12 and R-SUM), N14 (w14 p: N6's, landp, plus E12 and P-SUM), N15 (w15
r2), N16 (w16 p2), N12 (w12 lfkp: LFK's stage after the K pad run outside the session, control
PAD; last on this boot). Built on round 46's generator (closing29/r46-n3k-logs/sessgen). Writes
tables/STAGE.txt, predictions/STAGE.tsv for each stage and gen/constants.txt; every input is read
at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Every stage (flagged, on_stop "end", #limit 0) arms emitsb_sbc43s once (slot 0, entry 0,
pdsat=fw14, form=sbc43) and runs one row: job 1 is command 1 (`"ticks": true`, 200 ms, no kick;
the fill 0xdeadc0de in slots 2-5 and dwords 128-223 first, as B11); the land rows' job 2 is command
6 on the next tick pass. The outcomes are frozen per stage (design §11.4); the scorer derives the
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

STEP = "N10"
# every addendum row arms emitsb_sbc43s (round 45's, as N1-N8)
FORM, SIDEBAND = "sbc43", 0xC43
BLOB, BASE_BLOB = f"emitsb_{FORM}s", f"emitsb_{FORM}"
W_KEYS = (("own_gate", "none"), ("end_draws", "none"))


def lkeys(draws):
    return (("begin_draws", draws),)


# the stages of each step (design §11.3): stage, model, image, the stage's keys (session.toml),
# the row's jobs ("j1": command 1; "tick": command 6 on the next tick pass)
STAGES = {
    "N9": [("w9", "W", "mark", W_KEYS, ("j1",)),
           ("lfk", "LFK", "land", lkeys("fill"), ("j1", "tick"))],
    "N10": [("w10", "W", "mark", W_KEYS, ("j1",)),
            ("ltk", "LTK", "land", lkeys("tri"), ("j1", "tick"))],
    "N11": [("w11", "W", "mark", W_KEYS, ("j1",)),
            ("lfk2", "LFK2", "land", lkeys("fill"), ("j1", "tick"))],
    "N12": [("w12", "W", "mark", W_KEYS, ("j1",)),
            ("lfkp", "LFKP", "land", lkeys("fill"), ("j1", "tick"))],
    "N13": [("w13", "W", "mark", W_KEYS, ("j1",)),
            ("r", "R", "landr", lkeys("none"), ("j1", "tick"))],
    "N14": [("w14", "W", "mark", W_KEYS, ("j1",)),
            ("p", "P", "landp", lkeys("none"), ("j1", "tick"))],
    "N15": [("w15", "W", "mark", W_KEYS, ("j1",)),
            ("r2", "R2", "landr", lkeys("none"), ("j1", "tick"))],
    "N16": [("w16", "W", "mark", W_KEYS, ("j1",)),
            ("p2", "P2", "landp", lkeys("none"), ("j1", "tick"))],
}
STEPS = tuple(STAGES)
READS = ()                                          # no quiet read stage in the addendum
LANDS = ("LFK", "LTK", "LFK2", "LFKP", "R", "P", "R2", "P2")   # two jobs, the early stop
FILLS = ("LFK", "LTK", "LFK2", "LFKP")              # land after draws: DR and DK scored
PAGES = ("R", "P", "R2", "P2")                      # no draws: the page rows (DR, DK printed)
BROWS = ()                                          # no sideband rows
# the plant stage right before a land stage in the same attempt (design §11.3): the page rows
# print it (their images write sa0 and sa1 themselves), the others read it
PLANT = {"lfk": "w9", "ltk": "w10", "lfk2": "w11", "lfkp": "w12", "r": "w13", "p": "w14",
         "r2": "w15", "p2": "w16"}
# no build control in the addendum (WA was round 46's, design §10.3; the plants are row W)
BUILD_CONTROL = None
# PAD (design §11.4, K11): the read stage's KC begin N0 at least this (above LFF's 818)
PADS = {"lfkp": 830}
# the begin draws each stage declares (DR reads that the health mark names them at try 1)
DRAWS = {st: dict(keys).get("begin_draws", "fill,tri")
         for st, m, image, keys, jobs in sum(STAGES.values(), []) if m != "W"}
# the end draws of a stage (K9's end KC): a plant none, a land stage stops
ENDS = {st: ("none" if m == "W" else None)
        for st, m, image, keys, jobs in sum(STAGES.values(), [])}
WHEN = {
    "N9": "first of the addendum, on the boot N1-N4 ran on (module 10BBF3BF, sa12 = V0 since B6; "
          "design §11.3): w9 plants M1, lfk runs land after one fill and ends in the planned stop",
    "N10": "after N9: w10 plants M1, ltk runs land after one triangle and ends in the planned "
           "stop",
    "N11": "after N10: w11 plants M1, lfk2 is LFK's second read; ends in the planned stop",
    "N13": "after N11 (decision I (a)): w13 plants M1, r runs landr with no draws (N5's stages "
           "byte for byte, plus E12 and R-SUM) and ends in the planned stop",
    "N14": "after N13: w14 plants M1, p runs landp with no draws (N6's stages byte for byte, plus "
           "E12 and P-SUM) and ends in the planned stop",
    "N15": "after N14 (decision J (a)): w15 plants M1, r2 is R's second read; ends in the planned "
           "stop",
    "N16": "after N15 (decision J (a)): w16 plants M1, p2 is P's second read; ends in the planned "
           "stop",
    "N12": "LAST on this boot (decision H (a)), after N16: the K pad (pad.sh, 250 client fills, "
           "outside the session, before staging) lifts K above 830; w12 plants M1, lfkp runs land "
           "after one fill and ends in the planned stop",
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
T22 = 0x02400000                          # the triangle's 3:22 word at K 2 (LT E1215, ZT E1221)
SUM_R, SUM_P = 0x36404000, 0x64008000     # C-E0+'s A0 = sa0 + sa12: L4 + V0 (R), V0 + V0 (P)
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
    return ('{"cmd": 6, "params": {"%d": [%s]}, "timeout_ms": %d, "ticks": true, "slots": [%s]}'
            % (AFTER_AT, after, TIMEOUT_MS, ", ".join(map(str, AFTER_SLOTS))))


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


def e12(x):
    return {f"{x}-E12": ({"postsa12": "@V0"}, "held", "post sa12 = V0 (B6's pa0 still there) [HW, "
                         "10 reads on this boot]; failed: the row's C-E0 column cannot tell")}


def outcomes(m):
    """{name: ({quantity: value}, prediction, meaning)}: the frozen outcomes of a model (design
    §4.2, §4.8, §4.9 and §11.4); a prediction "printed" is an outcome printed and never scored."""
    if m == "W":
        return {
            "W-SA1": ({"postsa1": hexw(MK1)}, "held", "job 1's post sa1 = M1 0x005d1000 [HW, 29 "
                      "of 29 plants so far]"),
            "W-SA13": ({"postsa13": hexw(MK13), "postpa1": hexw(MK13)}, "held",
                       "job 1's post sa13 = M13 and pa1 = M13 [HW]"),
            "W-QUIET": ({"snap9:0x0c08": "0x0"}, "held",
                        "snap9 BIF_FAULT 0 (control B as a scored outcome) [HW]"),
            "W-FAULT": ({"fault1": "yes"}, "failed",
                        "a BIF fault after job 1 (snap9 or the disarm's dump)"),
        }
    if m in ("LFK", "LFK2", "LFKP"):
        x = m
        why = {"LFK": "[held under C-FILL]", "LFK2": "[held under C-FILL]",
               "LFKP": "[held under C-K, and under C-FILL]"}[m]
        m1 = {"LFK": "[C-E0, C-BOOT, C-MOD; C-K if K is below its value]",
              "LFK2": "[C-E0, C-BOOT, C-MOD; C-K if K is below its value]",
              "LFKP": "[C-E0, C-BOOT, C-MOD]"}[m]
        out = {
            f"{x}-SA": ({"postsa1": hexw(MK1), "sa02kind": "@in:LF"}, "held",
                        "sa0 = 2, sa1 = M1, sa2 timer [HW: LF, LF2, ZF, and with 2-3 fills "
                        "n1-n3]"),
        }
        out.update(e12(x))
        out.update({
            f"{x}-PAGE0": ({"j2": "notdone", "j2fault": pg(0)}, "failed", "job 2 not done; "
                           f"BIF_FAULT list 15 at page 0 {why}"),
            f"{x}-M1": ({"j2": "notdone", "j2fault": pg(MK1)}, "held", "the same at 0x005d1000 "
                        + m1),
            f"{x}-OTHER": ({"j2fault": "@faultnotin:" + pg(0) + "," + pg(MK1)}, "printed",
                           "a fault at any other page"),
            f"{x}-SERVE": ({"j2": "done"}, "failed", "job 2 done [HW against: 14 of 14 land "
                           "rows]"),
        })
        return out
    if m == "LTK":
        out = {
            "LTK-SA": ({"postsa1": hexw(T22), "sa02kind": "@in:TRIPLE"}, "held",
                       "sa0 = 0, sa1 = 0x02400000, sa2 timer [HW: LT, ZT]"),
        }
        out.update(e12("LTK"))
        out.update({
            "LTK-PAGE0": ({"j2": "notdone", "j2fault": pg(0)}, "failed", "job 2 not done; "
                          "BIF_FAULT list 15 at page 0 [held under C-FILL]"),
            "LTK-SA1": ({"j2": "notdone", "j2fault": pg(T22)}, "held", "the same at 0x02400000 "
                        "(0x0240000f) [C-E0, C-E0+, C-MOD; (ii)]"),
            "LTK-PAST": ({"j2fault": "@notin:" + pg(0) + "," + pg(T22)}, "failed",
                         "no fault at page 0 or 0x02400000 (done, or elsewhere) [held if it is "
                         "mapped]"),
            "LTK-SERVE": ({"j2": "done"}, "failed", "job 2 done"),
        })
        return out
    if m in ("R", "R2"):
        x = m
        out = {
            f"{x}-WRITE": ({"j1": "DONE", "postsa0": hexw(L4), "postsa1": hexw(MK1)}, "held",
                           "job 1 done; sa0 = 0x04400000, sa1 = M1 [infer: Q-WRITE's douta, "
                           "E1233]"),
            f"{x}-LOW": ({"j2": "notdone", "j2fault": pg(MK1)}, "held", "job 2 not done; "
                         "BIF_FAULT 0x005d100f (list 15, M1's page) [infer, R-LOW]"),
            f"{x}-SA0": ({"j2": "notdone", "j2fault": pg(L4)}, "failed", "the same at 0x0440000f "
                         "(sa0's page) [held under R-SA0 and R-SA0']"),
            f"{x}-OTHER": ({"j2fault": "@faultnotin:" + ",".join(pg(w) for w in (MK1, L4, SUM_R))},
                           "printed", "a fault at any other page (sa2's, sa13's, page 0; not the "
                           "SUM page)"),
            f"{x}-SERVE": ({"j2": "done"}, "failed", "job 2 done [HW against: every land row]"),
        }
        out.update(e12(x))
        out[f"{x}-SUM"] = ({"j2": "notdone", "j2fault": pg(SUM_R)}, "failed", "job 2 not done; "
                           "list 15 at 0x36404000 (sa0 + sa12) [C-E0+, A0 first, unmapped]")
        return out
    if m in ("P", "P2"):
        x = m
        out = {
            f"{x}-WRITE": ({"j1": "DONE", "postsa0": "@V0", "postsa1": hexw(Q0),
                            "postsa2": "@V2"}, "held", "job 1 done; sa0 = V0, sa1 = Q0, sa2 = V2 "
                           "[infer: landv's, landq's douta]"),
            f"{x}-UNMAP": ({"j2": "notdone", "j2fault": pg(Q0)}, "held", "job 2 not done; "
                           "BIF_FAULT 0x005d200f (list 15) [infer, §0.3 (ii); R-LOW]"),
            f"{x}-MAPPED": ({"j2fault": "@notin:" + pg(Q0)}, "failed", "no fault at 0x005d2000: "
                            "job 2 done, or a fault elsewhere [held under R-SA0]"),
            f"{x}-OTHER": ({"j2fault": "@faultnotin:" + pg(Q0) + "," + pg(SUM_P)}, "printed",
                           "a fault at another page (printed with -MAPPED; not the SUM page)"),
        }
        out.update(e12(x))
        out[f"{x}-SUM"] = ({"j2": "notdone", "j2fault": pg(SUM_P)}, "failed", "job 2 not done; "
                           "list 15 at 0x64008000 (V0 + V0) [C-E0+, A0 first, unmapped]")
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
PAD = ("pad", "ok", "PAD: the KC begin N0 of the read stage is at least 830, above LFF's 818 "
                    "(K11; design §11.4); failed: LFKP's C-K column cannot tell")
J2 = [("j2rec:done", "done", "J2: job 2 done (its record)"),
      ("j2rec:slot0", f"0x{M6:08x}", "J2: job 2's slot 6 marker M6 (its record)"),
      ("j2rec:slot1", "@runid2", "J2: job 2's slot 6 run id (its record)")]


def controls(m):
    """DR and DK: scored in the land rows after draws; printed in the page rows (no draws of their
    own, design §4.8, §4.9); PAD in LFKP only (design §11.4)."""
    return COMMON + ([DR, DK] if m in READS + FILLS else []) + ([PAD] if m == "LFKP" else []) \
        + (J2 if m in LANDS + BROWS else [])


def design(m, st):
    sec = {"W": "§4.2, §11.4", "LFK": "§11.4", "LFK2": "§11.4", "LTK": "§11.4", "LFKP": "§11.4",
           "R": "§4.8, §11.4", "R2": "§4.8, §11.4", "P": "§4.9, §11.4",
           "P2": "§4.9, §11.4"}[m]
    return f"n3k design {sec} ({st.upper()})"


def keys_text(keys):
    return ", ".join(f'{k} = "{v}"' for k, v in keys)


JOB_WORDS = {"j1": "command 1 with ticks on the timer pass",
             "tick": "command 6 on the next tick pass"}


def tables():
    out = {}
    for st, m, image, keys, jobs in STAGES[STEP]:
        t = [f"#stage {st}", "#limit 0",
             f"# {st}: N3k row {m} (closing29/n3k/design.md), the task {BLOB} armed once",
             f"# ({arm(image)}; {keys_text(keys)}); one row of {len(jobs)} "
             f"job{'s' * (len(jobs) > 1)}: " + ", ".join(JOB_WORDS[k] for k in jobs) + ";",
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
            f"Q0 0x{Q0:08x}", f"L4 0x{L4:08x}", f"T22 0x{T22:08x}", f"SUM_R 0x{SUM_R:08x}",
            f"SUM_P 0x{SUM_P:08x}",
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
