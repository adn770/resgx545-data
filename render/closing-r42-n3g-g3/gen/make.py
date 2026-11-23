#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of the r42-n3g-* sessions (closing29/n3g/design.md §3, N3g: where sa13's
page comes from, bit 10 with bits 1:0 = 2, and `land` with V0/V2). One session per step, STEP below
says which: G1 (stage c, the build control C, then stage m, row M), G2 (stage s, row S, then stage
q, row Q), G3 (stage lv, row LV); the user's decisions of 2026-11-21 (A-F (a)). Built on the
r41-n3f-* generator (rows C, X, Y and LC). Writes tables/STAGE.txt, predictions/STAGE.tsv for
each stage and gen/constants.txt; every input is read at the commits session.toml's [freeze]
names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Every stage (flagged, on_stop "end") arms its blob once (slot 0, entry 0) and runs one row: job 1
is command 1 (`"ticks": true`, 200 ms, no kick; the fill 0xdeadc0de in slots 2-5 and dwords
128-223 first, as B11); job 2 is command 6, the after-read (dwords 224-255 filled first and read
as result slots 40-47; M6 and the run id in slot 6) on a GETMISCINFO kick in C, M, S and Q, on
the next tick pass in LV, whose job 3 is command 6 again after a 2 s sleep. The gate is the fill
first everywhere. The outcomes are frozen per stage (design §3.1-§3.5); the scorer derives the
quantities they name (score/score.py) from the kept files, each job-scoped control and after-read
from that job's own record, never from the row-end page.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

STEP = "G3"
# the stages of each step (design §3, run order §6): stage, model, blob, form=, image, gate order,
# on_gate_fail, the row's jobs ("j1": command 1; "kick": command 6 on a GETMISCINFO kick; "tick":
# command 6 on the next tick pass; "sleep": command 6 after sleep_ms)
STAGES = {
    "G1": [("c", "C", "emitsb14s", "fw14", "crumb3", "fill,tri", None, ("j1", "kick")),
           ("m", "M", "emitsb_sbc43s", "sbc43", "mark", "fill,tri", "score", ("j1", "kick"))],
    "G2": [("s", "S", "emitsb14s", "fw14", "crumb3", "fill,tri", None, ("j1", "kick")),
           ("q", "Q", "emitsb_sb402s", "sb402", "crumb3", "fill,tri", "score", ("j1", "kick"))],
    "G3": [("lv", "LV", "emitsb_sbc43s", "sbc43", "landv", "fill,tri", "score",
            ("j1", "tick", "sleep"))],
}
STEPS = tuple(STAGES)
WHEN = {"G1": "first of round 42, right after the one-shot boot of the r42-kernel module (decision "
              "C (a)): stage c, the build control, then stage m; C failing in any way stops the "
              "round",
        "G2": "after G1 (decision C (a)): stage s (row C again, after M's resets), then stage q "
              "(sb402); s failing as a control stops the session",
        "G3": "last of round 42, its own session (decision D (a)): landv with 0xc43, the timer "
              "running; the highest risk"}
SIDEBAND = {"fw14": 0x843, "sbc43": 0xC43, "sb402": 0x402}
BASE = {"emitsb14s": "emitsb14d", "emitsb_sbc43s": "emitsb_sbc43", "emitsb_sb402s": "emitsb_sb402"}
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
MAGIC = 0x4E574F53        # page dword 0, the kernel's header (PG)
M1, X0, M4, S1, M6 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306
FILL = 0xDEADC0DE
FILL_AT, FILL_N = 0x48, 16                # slots 2-5 (dwords 72-87)
SURVEY_FILL_AT, SURVEY_FILL_N = 128, 96   # dwords 128-223 (B11's)
PRE_AT, POST_SA_AT, POST_PA_AT, AFTER_AT = 128, 160, 192, 224
AFTER_SLOTS = list(range(40, 48))         # dwords 224-255 as result slots (0x40 + 4 s)
SLOT6 = 0x40 + 4 * 6                      # M6 and the run id (dwords 88-89)
TIMEOUT_MS, SLEEP_MS = 200, 2000
T3 = 0x005A3305
# mark's markers (design §2 item 2, decision B (a)): M13 to attribute 13, M1 to attribute 1
MK13, MK1 = 0x005D3000, 0x005D1000
# the odd post pa that never changed in nine kept rows (design §0.1, L to LC2) [HW, printed]
ODD_PA = {1: 0x00043000, 3: 0x01555620, 5: 0x00000000, 7: 0x03C3CDAC, 9: 0xDC531A54,
          11: 0x5D50716F, 13: 0x82E151B5, 15: 0x11B5D77A}
SNAP_PIN = "data:render/closing-r35-sa/out/20261118-085610/a/c0a-k.snap0.regs.gz"


def row_name(stage):
    return f"{stage}1-a"


def arm(form, image):
    return f"slots=0x1 entry=0 pds={image} pdsat=fw14 form={form}"


def job(kind):
    fill = ", ".join([str(FILL)] * FILL_N)
    if kind == "j1":
        survey = ", ".join([str(FILL)] * SURVEY_FILL_N)
        return ('{"cmd": 1, "params": {"%d": [%s], "%d": [%s]}, "timeout_ms": %d, "ticks": true}'
                % (FILL_AT, fill, SURVEY_FILL_AT, survey, TIMEOUT_MS))
    after = ", ".join([str(FILL)] * 32)
    extra = {"kick": ', "kick": "miscinfo"', "tick": "", "sleep": f', "sleep_ms": {SLEEP_MS}'}[kind]
    return ('{"cmd": 6, "params": {"%d": [%s]}, "timeout_ms": %d, "ticks": true%s, "slots": [%s]}'
            % (AFTER_AT, after, TIMEOUT_MS, extra, ", ".join(map(str, AFTER_SLOTS))))


def args(jobs):
    return job(jobs[0]) if len(jobs) == 1 else "[" + ", ".join(job(k) for k in jobs) + "]"


def page13(w):
    return f"cid15 page 0x{w & ~0xFFF:08x}"


def c_outcomes():
    return {
        "C-SAME": ({"j2": "done", "after2": "SAME"}, "held",
                   "job 2 done; after sa0-31 = job 1's pre (E1173)"),
        "C-DIFF": ({"j2": "done", "after2": "DIFF"}, "failed", "after differs from pre"),
        "C-NOKICK": ({"j2": "notdone"}, "failed", "job 2 not done 200 ms after its kick"),
        "C-GATE": ({"gate1": "exact", "gate2": "exact"}, "held",
                   "the gate's fill and triangle exact (E1173)"),
    }


# the outcomes of each model (design §3.1-§3.5): {name: ({quantity: value}, prediction, meaning)};
# the quantities are the scorer's derived readings (score.py readings_of). A prediction "printed"
# is an outcome the design prints and never scores (S-OTHER, Q-OTHER)
def outcomes(m):
    if m == "C":
        return c_outcomes()
    if m == "M":
        return {
            "M-PA": ({"postpa1": f"0x{MK13:08x}"}, "held",
                     "job 1's post pa1 = M13 0x005d3000 (attribute 13 -> pa 13 - 12)"),
            "M-SA13": ({"after2sa13": f"0x{MK13:08x}"}, "held", "job 2's after sa13 = M13"),
            "M-SA1": ({"after2sa1": f"0x{MK1:08x}"}, "held",
                      "job 2's after sa1 = M1 0x005d1000 (H-BLOCK; failed under H-COPY)"),
            "M-REBASE": ({"j2": "done", "after2": "REBASE"}, "held",
                         "job 2's after = job 1's post in all 32 (E1174)"),
            "M-FILL": ({"gate1page": page13(MK13)}, "held",
                       "the gate's fill faults, CID 15, at page 0x005d3000 (= M13)"),
            "M-FILL43": ({"gate1page": page13(0x43000), "after2sa13": f"0x{MK13:08x}"}, "failed",
                         "the fill faults at page 0x00043000 with sa13 = M13 (the page is not "
                         "sa13)"),
            "M-FILLM1": ({"gate1page": page13(MK1)}, "failed",
                         "the fill faults at page 0x005d1000 (= M1: sa1 read first)"),
            "M-FILLOK": ({"gate1": "exact"}, "failed", "the gate's fill exact"),
            "M-NOKICK": ({"j2": "notdone"}, "failed", "job 2 not done 200 ms after its kick"),
        }
    if m == "S":
        keep = {f"postpa{k}": f"0x{v:08x}" for k, v in ODD_PA.items() if k != 1}
        return {
            "S-KEEP": ({"postpa1": f"0x{MK13:08x}", **keep}, "held",
                       "job 1's post pa1 = M13, the other odd pa as in nine kept rows (§0.1)"),
            "S-BACK": ({"postpa1": "0x00043000"}, "failed",
                       "job 1's post pa1 = 0x00043000 (a writer we do not run restores it)"),
            "S-OTHER": ({"postpa1": f"@notof:0x{MK13:08x},0x00043000"}, "printed",
                        "another word in pa1"),
            **c_outcomes(),
        }
    if m == "Q":
        rep = {f"postsa{k}": "@V0" for k in (4, 8, 12)} | {f"postsa{k}": "@V2" for k in (6, 10, 14)}
        return {
            "Q-REBASE": ({"j2": "done", "after2": "REBASE"}, "held",
                         "job 2's after = job 1's post in all 32, post != pre"),
            "Q-REP": (rep, "held",
                      "post sa4 = sa8 = sa12 = V0, sa6 = sa10 = sa14 = V2 (E1168, E1175)"),
            "Q-FILL": ({"gate1page": "@post13"}, "held",
                       "the gate's fill faults, CID 15, at the page of job 1's post sa13"),
            "Q-NONE": ({"j2": "done", "after2": "NONE", "gate1": "exact"}, "failed",
                       "after = pre and the gate exact (bit 10 acts only with bits 1:0 = 3)"),
            "Q-OTHER": ({"j2": "done", "after2": "OTHER"}, "printed",
                        "any other after (printed with indices)"),
        }
    return {
        "LV-V": ({"postsa0": "@V0", "postsa2": "@V2"}, "held",
                 "job 1's post sa0 = V0 and sa2 = V2 (H-BLOCK; LC2 read 0 and 0x01030b00)"),
        "LV-EARLY0": ({"early0": "yes"}, "failed",
                      "a stop, BIF_FAULT page 0 (CID 15), after job 1, before job 2"),
        "LV-EARLY": ({"early": "yes"}, "failed",
                     "any other stop or CID-15 fault after job 1 before the gate (weak)"),
        "LV-REBASE": ({"j2": "done", "after2": "REBASE"}, "held",
                      "job 2's after = job 1's post (as X, the tick running)"),
        "LV-HEAL": ({"j3": "done", "heal": "yes"}, "failed",
                    "job 3's after sa13 = pre sa13 (0)"),
        "LV-FILL": ({"gate1page": "@post13"}, "held if reached",
                    "the gate's fill faults, CID 15, at the page of job 1's post sa13"),
        "LV-FILLOK": ({"gate1": "exact"}, "failed",
                      "the gate's fill exact (the stopped tick of crumb3 is needed)"),
    }


# the controls of every stage (all can fail, design §3): row-scoped PG (page dword 0), T0 (snap0's
# timer running), B (BIF_FAULT 0 in snap9; a fault is read by the outcomes that name it); job-scoped,
# read in that job's record and never on the row-end page (the H3 slip, E1176): E0 from job 1's
# record (slot 1 = M1 and run id 1, cmd_after 0), J1 job 1 DONE (X0, S1, M4 with its run id, its
# record done; else CANNOT TELL and stop the ladder), J2 from job 2's record (done, slot 6 = M6
# and run id 2: the after-read outcomes cannot tell without it, the rule does not need it)
CONTROLS = [("res:0x0", f"0x{MAGIC:08x}", "PG: the page is ours and was read"),
            ("j1rec:slot0", f"0x{M1:08x}", "E0: entry 0 ran job 1 (slot 1 marker, job 1's record)"),
            ("j1rec:slot1", "@runid1", "E0: entry 0 ran job 1 (slot 1 run id, job 1's record)"),
            ("j1rec:cmd", "0x0", "E0: cmd 0 (entry 0 cleared it; job 1's record's cmd_after)"),
            ("snap0:0x0acc", "running", "T0: the tick's timer running before the command"),
            ("snap9:0x0c08", "0x0", "B: no BIF fault after the row (a fault is read by the "
                                    "outcomes that name it)"),
            ("j1", "DONE", "J1: job 1 DONE (X0, S1, M4 with its run id, done)"),
            ("j2rec:done", "done", "J2: job 2 done (its record)"),
            ("j2rec:slot0", f"0x{M6:08x}", "J2: job 2's slot 6 marker M6 (its record)"),
            ("j2rec:slot1", "@runid2", "J2: job 2's slot 6 run id (its record)")]


def design(m):
    return {"C": "n3g design §3.1 (C)", "M": "n3g design §3.2 (M)", "S": "n3g design §3.3 (S)",
            "Q": "n3g design §3.4 (Q)", "LV": "n3g design §3.5 (LV)"}[m]


def tables():
    out = {}
    for st, m, blob, form, image, order, ogf, jobs in STAGES[STEP]:
        t = [f"#stage {st}", "#limit 0",
             f"# {st}: N3g row {m} (closing29/n3g/design.md), the task {blob} armed once",
             f"# ({arm(form, image)}); one row of {len(jobs)} job{'s' * (len(jobs) > 1)}: "
             + ", ".join({"j1": "command 1 with ticks on the timer pass",
                          "kick": "command 6 on a GETMISCINFO kick",
                          "tick": "command 6 on the next tick pass",
                          "sleep": f"command 6 after {SLEEP_MS} ms"}[k] for k in jobs) + ";",
             f"# the gate {order}" + ("; its failure is the planned end (on_gate_fail score)"
                                       if ogf else "; any stop ends the session"),
             f"{row_name(st)}|fit|flagged|-|owntask|{args(jobs)}"]
        out[f"tables/{st}.txt"] = "\n".join(t) + "\n"
    return out


def predictions():
    out = {}
    for st, m, blob, form, image, order, ogf, jobs in STAGES[STEP]:
        n = row_name(st)
        p = [HEAD]
        for model, (qs, pred, meaning) in outcomes(m).items():
            for q, v in qs.items():
                p.append(f"{n}\t{q}\t{v}\t{model}\tfit\t{design(m)}: {meaning} "
                         f"[predicted: {pred}]\n")
        for q, v, why in CONTROLS:
            p.append(f"{n}\t{q}\t{v}\tCTL\tfit\t{design(m)} {why}\n")
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
    for st, m, blob, form, image, order, ogf, jobs in STAGES[STEP]:
        out.append(f"STAGE {st} {m} BLOB {blob} BASE {BASE[blob]} SIDEBAND 0x{SIDEBAND[form]:03x} "
                   f"ARM {arm(form, image)} GATE {order} ON_GATE_FAIL {ogf or 'stop'} "
                   f"JOBS {','.join(jobs)}")
    out += [f"M1 0x{M1:08x}", f"X0 0x{X0:08x}", f"M4 0x{M4:08x}", f"S1 0x{S1:08x}",
            f"M6 0x{M6:08x}", f"T3 0x{T3:08x}", f"M13 0x{MK13:08x}", f"MK1 0x{MK1:08x}",
            f"PRE {PRE_AT}", f"POST_SA {POST_SA_AT}", f"POST_PA {POST_PA_AT}", f"AFTER {AFTER_AT}"]
    out += [f"ODD_PA{k} 0x{v:08x}" for k, v in ODD_PA.items()]
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
