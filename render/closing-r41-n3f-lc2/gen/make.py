#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: the generator of the r41-n3f-* sessions (closing29/n3f/design.md §3, N3f: what an
own-task emit with sideband bit 10 leaves behind that breaks the next fill). One session per
step, STEP below says which: H1 (stage c, the control C, then stage x, row X), H2 (stage y, row
Y), H3 (stage lc, row LC), H4 (stage t, row T); the user's decisions of 2026-11-20 (A-F (a)).
LC2 is H3's row LC again with control E0 read from job 1's record (E0_AT).
Built on the r40-n3e-* generator (row B11's arm, page, fill and controls). Writes
tables/STAGE.txt, predictions/STAGE.tsv for each stage and gen/constants.txt; every input is
read at the commits session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Every stage (flagged, on_stop "end") arms its blob once (slot 0, entry 0) and runs one row: job 1
is B11's command 1 (`"ticks": true`, 200 ms, no kick; the fill 0xdeadc0de in slots 2-5 and dwords
128-223 first); job 2 (C, X, Y, LC) and job 3 (LC) are command 6, the after-read (dwords 224-255
filled first and read as result slots 40-47; M6 and the run id in slot 6): on a GETMISCINFO kick
in C, X and Y, on the next tick pass in LC (job 2) and after a 2 s sleep (job 3). T is job 1 only,
its gate the triangle first. The outcomes are frozen per stage (design §3.2-§3.5); the scorer
derives the quantities they name (score/score.py) from the kept files.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402

STEP = "LC2"
# the stages of each step (design §3.6): stage, model prefix, blob, form=, image, gate order,
# on_gate_fail, the row's jobs ("j1": command 1; "kick": command 6 on a GETMISCINFO kick; "tick":
# command 6 on the next tick pass; "sleep": command 6 after sleep_ms)
STAGES = {
    "H1": [("c", "C", "emitsb14s", "fw14", "crumb3", "fill,tri", None, ("j1", "kick")),
           ("x", "X", "emitsb_sbc43s", "sbc43", "crumb3", "fill,tri", "score", ("j1", "kick"))],
    "H2": [("y", "Y", "emitsb_sb403s", "sb403", "crumb3", "fill,tri", "score", ("j1", "kick"))],
    "H3": [("lc", "LC", "emitsb_sbc43s", "sbc43", "land", "fill,tri", "score",
            ("j1", "tick", "sleep"))],
    "H4": [("t", "T", "emitsb_sbc43s", "sbc43", "crumb3", "tri,fill", "score", ("j1",))],
}
# LC2 (r41-n3f-lc2): H3's row LC again, everything H3's but control E0's read point (E0_AT)
STAGES["LC2"] = STAGES["H3"]
STEPS = tuple(STAGES)
WHEN = {"H1": "first of round 41 (decision B (a)): stage c, the control, then stage x; C failing "
              "in any way stops everything",
        "H2": "after H1 (decision C (a)): bit 10 without bits 6 and 11",
        "H3": "after H1 and H2, its own session (decision D (a)): land with 0xc43, the timer "
              "running; the highest risk",
        "H4": "last of round 41, its own session (decision F (a)): the triangle first"}
WHEN["LC2"] = ("a rerun of H3 with control E0 fixed, its own session; land with 0xc43, the "
               "timer running; the highest risk")
SIDEBAND = {"fw14": 0x843, "sbc43": 0xC43, "sb403": 0x403}
BASE = {"emitsb14s": "emitsb14d", "emitsb_sbc43s": "emitsb_sbc43", "emitsb_sb403s": "emitsb_sb403"}
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
# B11's measured fault (n3e §0.2, both attempts): the gate's fill, BIF_INT_STAT and BIF_FAULT
FILL_FAULT = (0x000D0400, 0x0004300F)
T_PAGE = 0x01555000                       # row T: the render queue's head (B11's pa3, sa15)
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


# the outcomes of each model (design §3.2-§3.5): {name: ({quantity: value}, prediction, meaning)};
# the quantities are the scorer's derived readings (score.py readings_of)
def outcomes(m):
    if m == "C":
        return {
            "C-SAME": ({"j2": "done", "after2": "SAME"}, "held",
                       "job 2 done; after sa0-31 = job 1's pre (D0: shared, unchanged)"),
            "C-DIFF": ({"j2": "done", "after2": "DIFF"}, "failed", "after differs from pre"),
            "C-NOKICK": ({"j2": "notdone"}, "failed", "job 2 not done 200 ms after its kick"),
            "C-GATE": ({"gate1": "exact", "gate2": "exact"}, "held",
                       "the gate's fill and triangle exact (as B0)"),
        }
    if m in ("X", "Y"):
        f = f"fault 0x{FILL_FAULT[0]:08x} 0x{FILL_FAULT[1]:08x}"
        return {
            f"{m}-REBASE": ({"j2": "done", "after2": "REBASE"}, "held",
                            "after sa0-31 = job 1's post sa0-31 (sa1 0x04400000, sa13 0x43000)"),
            f"{m}-HIGH": ({"j2": "done", "after2": "HIGH"}, "failed",
                          "after sa0-11 = pre, sa12-31 = post (H-HIGH)"),
            f"{m}-NONE": ({"j2": "done", "after2": "NONE"}, "failed", "after = pre (H-NONE)"),
            f"{m}-OTHER": ({"j2": "done", "after2": "OTHER"}, "failed",
                           "any other after (printed with indices)"),
            f"{m}-KICKFAULT": ({"j2": "notdone", "kick": "cid15"}, "failed",
                               "job 2 not done, a BIF fault, CID 15 (page printed; 0x04400000 = "
                               "sa1)"),
            f"{m}-NOKICK": ({"j2": "notdone", "kick": "none"}, "failed",
                            "job 2 not done, no fault"),
            f"{m}-FILL": ({"gate1": f, "devcd": f[6:]}, "held",
                          "the gate's fill faults 0xd0400 at 0x0004300f, the devcoredump's BIF "
                          "words alike"),
        }
    if m == "LC":
        return {
            "LC-EARLY": ({"early": "yes"}, "held",
                         "a stop or a BIF fault (CID 15) after job 1, before the gate"),
            "LC-REBASE": ({"early": "no", "after2": "REBASE"}, "held if not LC-EARLY",
                          "job 2's after = job 1's post"),
            "LC-HEAL": ({"j3": "done", "heal": "yes"}, "failed",
                        "job 3's after sa13 = pre sa13 (0)"),
            "LC-FILL": ({"gate1page": "@post13"}, "held if reached",
                        "the gate's fill faults, CID 15, at the page of job 1's post sa13"),
            "LC-FILLOK": ({"gate1": "exact"}, "failed",
                          "the gate's fill exact (would say: bit 10 + stopped timer)"),
        }
    return {
        "T-HEAD": ({"gate1page": f"cid15 page 0x{T_PAGE:08x}"}, "held",
                   "the triangle faults, CID 15, page 0x01555000 (the render queue's head)"),
        "T-OTHER": ({"gate1page": "@fault-other"}, "failed",
                    "the triangle faults at another page (printed; 0x04400000 = sa1)"),
        "T-HANG": ({"gate1": "hang"}, "failed", "the triangle times out, no fault"),
        "T-OK": ({"gate1": "exact"}, "failed",
                 "the triangle exact (would say: the break is transfer-only)"),
    }


# the controls of every stage (all can fail): B11's PG, E0 (E0_AT), T0 and B, and J1 (job 1 DONE:
# its markers with job 1's run id, done in its record; else CANNOT TELL and stop, design §3.1)
# E0 is read where E0_AT says: "page" (H1-H4) reads slot 1 and the cmd word on the page dumped
# after the row; "j1rec" (LC2) reads them in job 1's record, as fwtask_run.py read them when job 1
# ended and before job 2 was posted (its `slot`, dwords 0x44-0x47, and `cmd_after`): in H3 job 2
# was posted (cmd word 6) and never served, so the page's cmd word was job 2's, not job 1's
E0_AT = {"H1": "page", "H2": "page", "H3": "page", "H4": "page", "LC2": "j1rec"}
E0 = {"page": [("res:0x44", f"0x{M1:08x}", "E0: entry 0 ran job 1 (slot 1 marker)"),
               ("res:0x45", "@runid1", "E0: entry 0 ran job 1 (slot 1 run id)"),
               ("res:0x1", "0x0", "E0: cmd 0 (entry 0 cleared it)")],
      "j1rec": [("j1rec:slot0", f"0x{M1:08x}", "E0: entry 0 ran job 1 (slot 1 marker, job 1's "
                 "record: as job 1 ended, before job 2 was posted)"),
                ("j1rec:slot1", "@runid1", "E0: entry 0 ran job 1 (slot 1 run id, job 1's "
                 "record)"),
                ("j1rec:cmd", "0x0", "E0: cmd 0 (entry 0 cleared it; job 1's record's "
                 "cmd_after, read before job 2 was posted)")]}
CONTROLS = [("res:0x0", f"0x{MAGIC:08x}", "PG: the page is ours and was read"),
            *E0[E0_AT[STEP]],
            ("snap0:0x0acc", "running", "T0: the tick's timer running before the command"),
            ("snap9:0x0c08", "0x0", "B: no BIF fault after the row (a fault is read by the "
                                    "outcomes that name it)"),
            ("j1", "DONE", "J1: job 1 DONE (X0, S1, M4 with its run id, done)")]


def design(m):
    return {"C": "n3f design §3.2 (C)", "X": "n3f design §3.2 (X)", "Y": "n3f design §3.3 (Y)",
            "LC": "n3f design §3.4 (LC)", "T": "n3f design §3.5 (T)"}[m]


def tables():
    out = {}
    for st, m, blob, form, image, order, ogf, jobs in STAGES[STEP]:
        t = [f"#stage {st}", "#limit 0",
             f"# {st}: N3f row {m} (closing29/n3f/design.md), the task {blob} armed once",
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
            f"M6 0x{M6:08x}", f"T3 0x{T3:08x}", f"PRE {PRE_AT}", f"POST_SA {POST_SA_AT}",
            f"POST_PA {POST_PA_AT}", f"AFTER {AFTER_AT}"]
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
