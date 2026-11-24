#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of the r44-n3i-* sessions (closing29/n3i/design.md §3, N3i: what the client
draws write into attribute 1, and land's early stop with a planted sa1). One session per step, STEP
below says which: N1 (stages wa ft wb ff wc t wd tf f2: a plant (row W, mark) then a read after
the draw sequence fill,tri / fill,fill / tri / tri,fill with crumb3, then F2, a read with no plant),
N2 (wl, row W; lm, row LM: land on W's bank with no draws), N3 (wf, row W; lf, row LF: land after
one fill); the user's decisions A-E all (a) of 2026-11-23. Built on the r43-n3h-* generator. Writes
tables/STAGE.txt, predictions/STAGE.tsv for each stage and gen/constants.txt; every input is read at
the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Every stage (flagged, on_stop "end", #limit 0) arms emitsb_sbc43s once (slot 0, entry 0, form sbc43,
pdsat=fw14) and runs one row: job 1 is command 1 (`"ticks": true`, 200 ms, no kick; the fill
0xdeadc0de in slots 2-5 and dwords 128-223 first, as B11); the land rows' job 2 is command 6 on the
next tick pass. The outcomes are frozen per stage (design §3.1-§3.5); the scorer derives the
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

STEP = "N1"
BLOB, BASE_BLOB, FORM, SIDEBAND = "emitsb_sbc43s", "emitsb_sbc43", "sbc43", 0xC43
# the stages of each step (design §3, run order §6): stage, model, image, the stage's keys
# (session.toml), the row's jobs ("j1": command 1; "tick": command 6 on the next tick pass).
# K8 (round 44): a read stage's begin_draws is the draw sequence it reads after; own_gate none
W_KEYS = (("own_gate", "none"), ("end_draws", "none"))


def rkeys(draws):
    return (("begin_draws", draws), ("own_gate", "none"))


STAGES = {
    "N1": [("wa", "W", "mark", W_KEYS, ("j1",)),
           ("ft", "FT", "crumb3", rkeys("fill,tri"), ("j1",)),
           ("wb", "W", "mark", W_KEYS, ("j1",)),
           ("ff", "FF", "crumb3", rkeys("fill,fill"), ("j1",)),
           ("wc", "W", "mark", W_KEYS, ("j1",)),
           ("t", "T", "crumb3", rkeys("tri"), ("j1",)),
           ("wd", "W", "mark", W_KEYS, ("j1",)),
           ("tf", "TF", "crumb3", rkeys("tri,fill"), ("j1",)),
           ("f2", "F2", "crumb3", rkeys("fill"), ("j1",))],
    "N2": [("wl", "W", "mark", W_KEYS, ("j1",)),
           ("lm", "LM", "land", (("begin_draws", "none"),), ("j1", "tick"))],
    "N3": [("wf", "W", "mark", W_KEYS, ("j1",)),
           ("lf", "LF", "land", (("begin_draws", "fill"),), ("j1", "tick"))],
}
STEPS = tuple(STAGES)
READS = ("FT", "FF", "T", "TF", "F2")        # one quiet job after a draw sequence
LANDS = ("LM", "LF")                         # land: two jobs, the early stop
# the plant stage right before a read stage in the same attempt (design §2: the pairing WA-FT,
# WB-FF, WC-T, WD-TF; WL-LM, WF-LF); F2 has none (design §3.3)
PLANT = {"ft": "wa", "ff": "wb", "t": "wc", "tf": "wd", "lm": "wl", "lf": "wf"}
# the begin draws each read stage declares (DR reads that the health mark names them at try 1)
DRAWS = {st: dict(keys)["begin_draws"] for st, m, image, keys, jobs in sum(STAGES.values(), [])
         if "begin_draws" in dict(keys)}
WHEN = {"N1": "first of round 44 (decision E (a)): four plants and the reads after fill-tri, "
              "fill-fill, tri and tri-fill, then F2 with no plant; all quiet, no planned stop; "
              "no build, no boot",
        "N2": "after N1 (decision E (a)): wl plants M1, lm runs land on that bank with no draws "
              "and ends in the runner's planned stop (row LM); no build, no boot",
        "N3": "after N2 (decision E (a); LM-V0 is LF's premise): wf plants M1, lf runs land after "
              "one fill and ends in the runner's planned stop (row LF); no build, no boot"}
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
SNAP_PIN = "data:render/closing-r43-n3h-n1/out/20261123-164401/w/w1-a.snap0.regs.gz"


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


EVT_WORDS = (0x04400000, 0x04000010)
KEEP_WORD = MK1
# every word a read stage's outcomes name (X-OTHER is any other post sa1)
READ_WORDS = {
    "FT": (MK1,) + EVT_WORDS,
    "FF": (MK1, 0x02000000, 0x01000000, 0x04000010),
    "T": (MK1, 0x03400000, 0x03000010) + EVT_WORDS + (0x02400000, 0x02000010),
    "TF": (MK1, 0x04000000, 0x01000000, 0x08000010) + EVT_WORDS,
}


def read_common(m):
    return {
        "X-QUIET": ({"snap9:0x0c08": "0x0"}, "held", "snap9 BIF_FAULT 0 (control B as a scored "
                                                      "outcome)"),
        "X-KEEP": (sa1(MK1), "failed", "post sa1 = M1: the draws did not write it [HW for a fill, "
                                      "E1187; infer for a triangle, the seven FT rows]"),
        "X-OTHER": ({"postsa1": "@notany:" + ",".join(map(hexw, READ_WORDS[m]))}, "printed",
                    "any word the stage's outcomes do not name"),
    }


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
    if m == "FT":
        out = {"FT-SAME": (sa1(*EVT_WORDS), "held", "0x04400000 or 0x04000010 [HW: the seven "
                                                    "rows of §0.1]")}
    elif m == "FF":
        out = {"FF-N": (sa1(0x02000000), "held", "0x02000000 [infer, H-N; H-ACC alike]"),
               "FF-LAST": (sa1(0x01000000), "failed", "0x01000000 [infer, H-LAST]"),
               "FF-K": (sa1(0x04000010), "failed", "0x04000010 [infer, H-K]")}
    elif m == "T":
        out = {"T-N": (sa1(0x03400000, 0x03000010), "held", "0x03400000 or 0x03000010 [infer, "
                                                          "H-N; H-ACC alike]"),
               "T-LAST": (sa1(*EVT_WORDS), "failed", "0x04400000 or 0x04000010 [infer, H-LAST]"),
               "T-K": (sa1(0x02400000, 0x02000010), "failed", "0x02400000 or 0x02000010 [infer, "
                                                            "H-K]")}
    elif m == "TF":
        out = {"TF-N": (sa1(0x04000000), "held", "0x04000000 [infer, H-N; H-ACC alike]"),
               "TF-LAST": (sa1(0x01000000), "failed", "0x01000000 [infer, H-LAST]"),
               "TF-K": (sa1(0x08000010), "failed", "0x08000010 [infer, H-K]"),
               "TF-TRI": (sa1(*EVT_WORDS), "failed", "0x04400000 or 0x04000010 (the triangle's "
                                                    "word survives the fill) [infer]")}
    elif m == "F2":
        return {
            "F2-N": (sa1(0x01000000), "held", "0x01000000 (F again, whatever the word before) "
                                              "[HW, E1187; infer]"),
            "F2-ACC": (sa1(0x09000000), "failed", "0x09000000 [infer, H-ACC]"),
            "F2-K": (sa1(0x02000010), "failed", "0x02000010 [infer, H-K]"),
            "F2-PRIOR": (sa1(*EVT_WORDS), "failed", "0x04400000 or 0x04000010 (the fill did not "
                                                    "write it) [HW against: E1187]"),
            "F2-OTHER": ({"postsa1": "@notany:" + ",".join(map(hexw, (
                0x01000000, 0x09000000, 0x02000010) + EVT_WORDS))}, "printed", "any other"),
            "F2-QUIET": ({"snap9:0x0c08": "0x0"}, "held", "snap9 BIF_FAULT 0"),
        }
    elif m == "LM":
        return {
            "LM-V0": ({"postsa0": "@V0", "postsa2": "@V2"}, "held",
                      "job 1's post sa0 = V0 and sa2 = V2 (kept from WL) [infer, as E1185]"),
            "LM-KEEP": ({"postsa1": hexw(MK1)}, "held", "post sa1 = M1 [HW, E1185]"),
            "LM-EARLY1": ({"j2": "notdone", "j2fault": "@post1"}, "held",
                          "job 2 not done; K5 BIF_FAULT CID 15 at post sa1's page (M1) [infer]"),
            "LM-EARLY0": ({"j2": "notdone", "j2fault": page(0)}, "failed",
                          "the same at page 0 [infer; held under H-IMG]"),
            "LM-EARLY13": ({"j2": "notdone", "j2fault": "@post13"}, "failed",
                           "the same at post sa13's page (M13) [HW against: E1185]"),
            "LM-SERVE": ({"j2": "done"}, "failed", "job 2 done [HW against: E1176, E1178, "
                                                    "E1183, E1185]"),
            "LM-OTHER": ({"j2": "notdone", "j2fault": "@other"}, "printed",
                         "any other fault page"),
        }
    elif m == "LF":
        return {
            "LF-SA1": ({"postsa1": hexw(0x01000000)}, "held", "post sa1 = 0x01000000 [HW once, "
                                                              "E1187]"),
            "LF-EVT": ({"sa02kind": "EVT"}, "held", "post sa0 = 0; sa2 = 0x01xxxxxx, bits 23:0 "
                                                    "< 400000, != 0x061a70 [infer]"),
            "LF-TICK": ({"sa02kind": "TICK"}, "failed", "post sa0 = 2 and sa2 = 0x01061a70 (a "
                                                        "tick's words, E746) [infer]"),
            "LF-ONE": ({"sa02kind": "ONE"}, "failed", "post sa0 = V0 and sa2 = V2 (the fill "
                                                      "writes attribute 1 alone) [infer]"),
            "LF-AOTHER": ({"sa02kind": "OTHER"}, "printed", "any other sa0, sa2"),
            "LF-EARLY0": ({"j2": "notdone", "j2fault": page(0)}, "held",
                          "job 2 not done; K5 BIF_FAULT CID 15 at page 0 [infer, H-SA0 with "
                          "LF-EVT]"),
            "LF-EARLY1": ({"j2": "notdone", "j2fault": "@post1"}, "failed",
                          "the same at page 0x01000000 (post sa1) [infer; held under LF-ONE]"),
            "LF-SERVE": ({"j2": "done"}, "failed", "job 2 done"),
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
JOBCTL = {
    "W": [],
    "LM": [("j2rec:done", "done", "J2: job 2 done (its record)"),
           ("j2rec:slot0", f"0x{M6:08x}", "J2: job 2's slot 6 marker M6 (its record)"),
           ("j2rec:slot1", "@runid2", "J2: job 2's slot 6 run id (its record)")],
}
JOBCTL["LF"] = JOBCTL["LM"]
for _m in READS:
    JOBCTL[_m] = []


def controls(m):
    return COMMON + ([] if m == "W" else [DR]) + JOBCTL[m]


def design(m, st):
    sec = {"W": "§3.1", "FT": "§3.2", "FF": "§3.2", "T": "§3.2", "TF": "§3.2", "F2": "§3.3",
           "LM": "§3.4", "LF": "§3.5"}[m]
    return f"n3i design {sec} ({st.upper()})"


def keys_text(keys):
    return ", ".join(f'{k} = "{v}"' for k, v in keys)


def tables():
    out = {}
    for st, m, image, keys, jobs in STAGES[STEP]:
        t = [f"#stage {st}", "#limit 0",
             f"# {st}: N3i row {m} (closing29/n3i/design.md), the task {BLOB} armed once",
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
