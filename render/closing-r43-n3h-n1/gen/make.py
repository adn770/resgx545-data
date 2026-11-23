#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of the r43-n3h-* sessions (closing29/n3h/design.md §3, N3h: who writes
attribute 1, what the tick pass reads, which pass faults). One session per step, STEP below says
which: N1 (stage w, row W: plant M1 with mark, no gate and no end draws; then stage v, row V:
landv with no begin draws, the tick pass), N2 (stage w2, row W2 = W; then stage f, row F: crumb3
after the fill alone, a kick-only job, then command 6 on a kick); the user's decisions A-E (a) of
2026-11-23. Built on the r42-n3g-* generator (rows M, LV). Writes tables/STAGE.txt,
predictions/STAGE.tsv for each stage and gen/constants.txt; every input is read at the commits
session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Every stage (flagged, on_stop "end", #limit 0) arms emitsb_sbc43s once (slot 0, entry 0, form
sbc43, pdsat=fw14) and runs one row: job 1 is command 1 (`"ticks": true`, 200 ms, no kick; the
fill 0xdeadc0de in slots 2-5 and dwords 128-223 first, as B11); V's job 2 is command 6 on the next
tick pass; F's job 2 is kick-only (K6: no command, a GETMISCINFO kick, 50 ms, expect notdone) and
its job 3 command 6 on a GETMISCINFO kick. The outcomes are frozen per stage (design §3.1-§3.4);
the scorer derives the quantities they name (score/score.py) from the kept files, each
job-scoped control and reading from that job's own record, never from the row-end page.
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
# the stages of each step (design §3, run order §6): stage, model, image, the stage's K7 keys
# (session.toml), the row's jobs ("j1": command 1; "tick": command 6 on the next tick pass;
# "kickonly": K6's kick-only job; "kick": command 6 on a GETMISCINFO kick)
W_KEYS = (("own_gate", "none"), ("end_draws", "none"))
STAGES = {
    "N1": [("w", "W", "mark", W_KEYS, ("j1",)),
           ("v", "V", "landv", (("begin_draws", "none"),), ("j1", "tick"))],
    "N2": [("w2", "W", "mark", W_KEYS, ("j1",)),
           ("f", "F", "crumb3", (("begin_draws", "fill"), ("on_gate_fail", "score")),
            ("j1", "kickonly", "kick"))],
}
STEPS = tuple(STAGES)
# the stage whose W-SA1 a later stage's attribute-1 outcomes need (design §3.2, §3.4)
PLANT = {"v": "w", "f": "w2"}
WHEN = {"N1": "first of round 43 (decision E (a)): stage w plants M1, stage v reads it with no "
              "draws between and ends in the runner's planned stop (V-EARLY1); no build, no boot",
        "N2": "after N1 (decision E (a)): stage w2 plants M1 again (N1's recovery draws rewrite "
              "it), stage f after the fill alone, its kick-only job and job 3; ends in K-STALL's "
              "stop or the gate's planned fault"}
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
MAGIC = 0x4E574F53        # page dword 0, the kernel's header (PG)
M1, X0, M4, S1, M6 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306
FILL = 0xDEADC0DE
FILL_AT, FILL_N = 0x48, 16                # slots 2-5 (dwords 72-87)
SURVEY_FILL_AT, SURVEY_FILL_N = 128, 96   # dwords 128-223 (B11's)
PRE_AT, POST_SA_AT, POST_PA_AT, AFTER_AT = 128, 160, 192, 224
AFTER_SLOTS = list(range(40, 48))         # dwords 224-255 as result slots (0x40 + 4 s)
TIMEOUT_MS, KICK_ONLY_MS = 200, 50
T3 = 0x005A3305
MK13, MK1 = 0x005D3000, 0x005D1000        # mark's markers: M13 to attribute 13, M1 to attribute 1
V1 = 0x32005000                           # the boot's #11 attribute 1 (H-BOOT, E002)
SNAP_PIN = "data:render/closing-r42-n3g-g1/out/20261122-160857/m/m1-a.snap0.regs.gz"


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
    if kind == "kickonly":
        return ('{"cmd": 0, "kick": "miscinfo", "expect": "notdone", "timeout_ms": %d}'
                % KICK_ONLY_MS)
    after = ", ".join([str(FILL)] * 32)
    extra = {"kick": ', "kick": "miscinfo"', "tick": ""}[kind]
    return ('{"cmd": 6, "params": {"%d": [%s]}, "timeout_ms": %d, "ticks": true%s, "slots": [%s]}'
            % (AFTER_AT, after, TIMEOUT_MS, extra, ", ".join(map(str, AFTER_SLOTS))))


def args(jobs):
    return job(jobs[0]) if len(jobs) == 1 else "[" + ", ".join(job(k) for k in jobs) + "]"


def page(w):
    return f"cid15 page 0x{w & ~0xFFF:08x}"


# the outcomes of each model (design §3.1-§3.4): {name: ({quantity: value}, prediction, meaning)};
# the quantities are the scorer's derived readings (score.py readings_of). A prediction "printed"
# is an outcome the design prints and never scores (V-OTHER, F-OTHER)
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
    if m == "V":
        return {
            "V-KEEP": ({"sa1kind": "M1"}, "held", "job 1's post sa1 = M1 (H-EVT: no client "
                       "event since W)"),
            "V-EVT": ({"sa1kind": "@in:EVT4,EVT22"}, "failed",
                      "post sa1 an event word: bits 31:24 in 1-15, bits 23:0 = 0x000010 or "
                      "0x400000"),
            "V-V1": ({"sa1kind": "V1"}, "failed",
                     "post sa1 = 0x32005000 (V1: the boot's #11 writes attribute 1, H-BOOT)"),
            "V-OTHER": ({"sa1kind": "OTHER"}, "printed", "any other post sa1 (H-EMIT)"),
            "V-V": ({"postsa0": "@V0", "postsa2": "@V2", "postsa13": f"0x{MK13:08x}"}, "held",
                    "post sa0 = V0 and sa2 = V2; post sa13 = M13"),
            "V-EARLY1": ({"j2": "notdone", "j2fault": "@post1"}, "held",
                         "job 2 not done; its K5 BIF_FAULT CID 15 at job 1's post sa1 page"),
            "V-EARLY13": ({"j2": "notdone", "j2fault": "@post13"}, "failed",
                          "the same at the page of post sa13 (M13)"),
            "V-EARLY0": ({"j2": "notdone", "j2fault": page(0)}, "failed", "the same at page 0"),
            "V-SERVE": ({"j2": "done"}, "failed", "job 2 done"),
        }
    return {
        "F-FILL4": ({"sa1kind": "EVT4"}, "held",
                    "job 1's post sa1 an event word, bits 23:0 = 0x000010 (H-EVT, E747)"),
        "F-KEEP": ({"sa1kind": "M1"}, "failed",
                   "post sa1 = M1 (the fill does not write it; the triangle does)"),
        "F-OTHER": ({"sa1kind": "@notin:EVT4,M1"}, "printed",
                    "any other post sa1 (0x400000 in bits 23:0 included)"),
        "K-QUIET": ({"j2pre": "0x0"}, "held", "job 2's K5 pre BIF_FAULT 0"),
        "K-KICK": ({"j2kick": "@post13"}, "held",
                   "job 2's K5 mid or post: CID 15 at post sa13's page (M13)"),
        "K-KICKOK": ({"j2post": "0x0"}, "failed", "job 2's K5 post BIF_FAULT 0"),
        "K-REPLY": ({"j2reply": "answered"}, "held", "job 2's kick answered (GETMISCINFO line)"),
        "K-STALL": ({"j3": "notdone", "j3reply": "error"}, "held",
                    "job 3 not done, its kick not answered (500 ms)"),
        "K-SERVE": ({"j3": "done", "after3": "REBASE"}, "failed",
                    "job 3 done, its after-read = job 1's post"),
        "F-GATE": ({"gate1page": "@post13"}, "held if reached",
                   "if reached, the gate's fill faults, CID 15, at post sa13's page"),
    }


# the controls of every stage (all can fail, design §3): row-scoped PG (page dword 0), T0 (snap0's
# timer running), B (BIF_FAULT 0 in snap9; a fault is read by the outcomes that name it);
# job-scoped, read in that job's record and never on the row-end page (the H3 slip, E1176): E0
# from job 1's record (slot 1 = M1 and run id 1, cmd_after 0), J1 job 1 DONE (X0, S1, M4 with
# its run id, its record done; else CANNOT TELL and stop the session); V: J2 job 2's record (done,
# slot 6 = M6 and run id 2); F: J2 job 2's record in the kick-only shape (not done, cmd_after 0,
# kicked), J3 job 3's (done, slot 6 = M6 and run id 3). Only PG, E0, T0 and J1 decide the RULE
COMMON = [("res:0x0", f"0x{MAGIC:08x}", "PG: the page is ours and was read"),
          ("j1rec:slot0", f"0x{M1:08x}", "E0: entry 0 ran job 1 (slot 1 marker, job 1's record)"),
          ("j1rec:slot1", "@runid1", "E0: entry 0 ran job 1 (slot 1 run id, job 1's record)"),
          ("j1rec:cmd", "0x0", "E0: cmd 0 (entry 0 cleared it; job 1's record's cmd_after)"),
          ("snap0:0x0acc", "running", "T0: the tick's timer running before the command"),
          ("snap9:0x0c08", "0x0", "B: no BIF fault after the row (a fault is read by the "
                                  "outcomes that name it)"),
          ("j1", "DONE", "J1: job 1 DONE (X0, S1, M4 with its run id, done)")]
JOBCTL = {
    "W": [],
    "V": [("j2rec:done", "done", "J2: job 2 done (its record)"),
          ("j2rec:slot0", f"0x{M6:08x}", "J2: job 2's slot 6 marker M6 (its record)"),
          ("j2rec:slot1", "@runid2", "J2: job 2's slot 6 run id (its record)")],
    "F": [("j2rec:done", "notdone", "J2: the kick-only job 2 not done (its record)"),
          ("j2rec:cmd", "0x0", "J2: job 2 wrote no command (its record's cmd_after 0)"),
          ("j2rec:kicked", "yes", "J2: job 2 kicked (its record's kick)"),
          ("j3rec:done", "done", "J3: job 3 done (its record)"),
          ("j3rec:slot0", f"0x{M6:08x}", "J3: job 3's slot 6 marker M6 (its record)"),
          ("j3rec:slot1", "@runid3", "J3: job 3's slot 6 run id (its record)")],
}


def controls(m):
    return COMMON + JOBCTL[m]


def design(m, st):
    return {"W": f"n3h design §3.{1 if st == 'w' else 3} ({st.upper()})",
            "V": "n3h design §3.2 (V)", "F": "n3h design §3.4 (F)"}[m]


def keys_text(keys):
    return ", ".join(f'{k} = "{v}"' for k, v in keys)


def tables():
    out = {}
    for st, m, image, keys, jobs in STAGES[STEP]:
        t = [f"#stage {st}", "#limit 0",
             f"# {st}: N3h row {st.upper()} (closing29/n3h/design.md), the task {BLOB} armed once",
             f"# ({arm(image)}; {keys_text(keys)}); one row of {len(jobs)} "
             f"job{'s' * (len(jobs) > 1)}: "
             + ", ".join({"j1": "command 1 with ticks on the timer pass",
                          "tick": "command 6 on the next tick pass",
                          "kickonly": "a kick-only job (no command, a GETMISCINFO kick)",
                          "kick": "command 6 on a GETMISCINFO kick"}[k] for k in jobs) + ";",
             "# any stop ends the session" + ("; the gate's failure is the planned end"
                                               if dict(keys).get("on_gate_fail") else ""),
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
