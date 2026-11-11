# SPDX-License-Identifier: MIT
"""r4blayout.py: the one source of R4b (round 4, decision 10 "reruns", session B: a replicate of FCF's stop, Q152).

It imports R3k-events' `r3layout.py` byte for byte (the page layout of ring_exit.s, the stop signature registers, the readers of
the two debugfs dumps) and replaces only what is the session's own: the module, the session and its laptop directory, the one
stage `fr`, its rows and E817's values that the predictions freeze.  The generator, the runner, the guard and the scorer import
this file and nothing else for those names.

E817 (R3k stage f, dataset edm-closing-r3k-events, out/f): row FCF (ACT 3: cfi.global, idf, wdf, nop.end) ran once, job `fcf`,
the sixth job after the stage's arm; it stopped the tick; its replicate `fcf-r2` was not run ("a stopped row is never
replicated").  Its kept neighbours: `fb`, `fb-r2` (ACT 5, the same pass with the phas end: kept) before it, `fph`, `fph-r2`
(ACT 4: kept) after it, and the cont4 control `fc4`, `fc4-r2` (ACT 6: kept).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from r3layout import *  # noqa: F401,F403,E402
import r3layout as _R3  # noqa: E402

# ---- the module and the session ---------------------------------------------------------------------------------------------
EXPECT_SRCV = "99CD90DA26E3AFF9C450517"      # fork resgx545 a2788bd8 (round 3 + four region-header arrays); loaded = installed = this
OLD_SRCVS = ("230E0EF50FFFD606C53AE3C", "B21FDA82BD5E5CB5A627E3B")    # E817's module and the one before it: refused
FW_SHA256 = _R3.FW_SHA256                     # the stock firmware the kernel's cont4 is tied to (E817's env.json)
KO_SHA256 = None                              # not known offline: the lead records the installed file's sha256 by hand
SESSIONS = {"r4b": ["fr"]}
DIR_OF = {"r4b": "r4b"}                       # the laptop's ~/r4b (inputs) and ~/r4b-out (results); no other session uses them
STAGES = ["fr"]
SESSION_OF = {"fr": "r4b"}
RING_ARM = _R3.RING_ARM
STAGE_INFO = {
    # budget: the stops the stage takes and goes on (each only in a row that may stop); a stop in any other row ends the stage.
    # per_job_reset False: a reset and the arm only at each block start (and a re-arm after a stop), as E817's stage f
    "fr": {"blob": "ring_exit", "arm": RING_ARM, "gate": None, "budget": 3, "per_job_reset": False, "ops": ["act"], "alarm": 720},
}
BLOB_OF = {st: i["blob"] for st, i in STAGE_INFO.items()}
ARM_OF = {st: i["arm"] for st, i in STAGE_INFO.items()}
GATE_OF = {}
STOP_BUDGET = {st: i["budget"] for st, i in STAGE_INFO.items()}
PER_JOB_RESET = {st: i["per_job_reset"] for st, i in STAGE_INFO.items()}
BLOBS = ("ring_exit",)
CONT4_BLOBS = ("ring_exit",)
STR_OF = {}
ACT_OF_STAGE = {"fr": (_R3.ACT_CFI, _R3.ACT_PHAS, _R3.ACT_BOTH, _R3.ACT_CONT4)}
EXIT_INDEX = 0x1974                           # E817 arm.json: exit_index 6516, the arm line "exit 0x1974"

# the debugfs knobs this session never writes, and the value each reads at the preflight and after the stage (the new module's
# defaults: render_rgn_arrays is 0, automatic, since a2788bd8; it was 1 on 230E0EF5)
KNOB_DEFAULTS = {"hold_recovery": "N", "render_rgn_arrays": "0x00000000", "render_pb_pages": "0x00000422", "kick_no_bump": "N"}


# ---- the rows ------------------------------------------------------------------------------------------------------------------
def _act(act, label, block, reps=1, run_if=None, may_stop=False, group=None, block_start=False):
    d = {"op": "act", "kind": 0 if act == 0 else 1, "act": act, "count": 0 if act == 0 else 1, "trigger": "none", "reps": reps,
         "label": label, "open_ms": 20, "may_stop": may_stop, "group": group, "block": block, "block_start": block_start}
    if run_if:
        d["run_if"] = run_if
    return d


# Three BLOCKS (the user's decision, 2026-11-11).  A block is E817's stage f from its arm to fcf, job for job: a reset and the arm,
# then e0, fc4, fc4-r2, fb, fb-r2, fcfN, with no reset between them (E817 out/f stage.json: e0, fc4, fc4-r2, fb, fb-r2, fcf).  Then,
# if fcfN stopped, the recovery (signature twice, P3, dumps, reset, fill, triangle, health) and a re-arm; then fkN, E817's first job
# after its re-arm (fph: idf, wdf, phas end, nop.end; kept in E817).  The next block runs only if fkN kept the tick.
def _block(b):
    after = {} if b == 1 else {"run_if": f"all_kept:FK{b - 1}:1"}
    return {f"B{b}E0": _act(0, "control", b, block_start=True, **after),
            f"B{b}FC4": _act(_R3.ACT_CONT4, "control", b, reps=2, **after),
            f"B{b}FB": _act(_R3.ACT_BOTH, "control", b, reps=2, run_if=f"all_kept:B{b}FC4:2"),
            f"FCF{b}": _act(_R3.ACT_CFI, "heldout" if b == 1 else "replicate", b, run_if=f"all_kept:B{b}FB:2", may_stop=True,
                            group="FCF"),
            f"FK{b}": _act(_R3.ACT_PHAS, "control", b)}


BLOCKS = (1, 2, 3)
ROW_SPEC = {"fr": {k: v for b in BLOCKS for k, v in _block(b).items()}}
ROW_ORDER = {st: list(rows) for st, rows in ROW_SPEC.items()}
FCF_ROWS = [r for r, s in ROW_SPEC["fr"].items() if s["group"] == "FCF"]
CONTROL_ROWS = [r for r, s in ROW_SPEC["fr"].items() if s["label"] == "control"]
E817_SEQ = ["e0", "fc4", "fc4-r2", "fb", "fb-r2", "fcf"]          # E817's jobs from its arm to fcf (out/f stage.json)
E817_AFTER_STOP = "fph"                                            # its first job after fcf's stop and the re-arm

# ---- E817's values (the frozen predictions take them from here; the scorer reads them from predictions/fr.tsv) ---------------
E817_FCF = {"clkstat": 0x000CCFA0, "event_status": 0x20000000, "read_minus_write": 0, "dword14": 0, "flag": _R3.SKIP_FLAG,
            "act_seen": _R3.ACT_CFI, "p3_answered": "no", "entries": 4}
E817_KEPT_GAP = (25000 - 50, 25000 + 50)     # fc4 +24994 +24995, fb +24995 +24995, fph +24994 +24995
E817_E0_ENTRIES = (12, 16)                   # e0: 14 entries (14 +-2), on the grid, nothing acted


def rep_name(row, k):
    return row.lower() + ("" if k == 0 else f"-r{k + 1}")
