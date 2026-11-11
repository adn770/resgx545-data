# SPDX-License-Identifier: MIT
"""r4layout.py: the one source of R4-events (round 4, session r4-events: stages kb2, kp, e3p).

It imports R3k-events' `r3layout.py` byte for byte (the page layout, the stop signature registers, the readers of the two debugfs
dumps, the tick words) and replaces only what is the session's own: the module, the session and its laptop directories, the three
stages, their rows, the new constants.  The generator, the runner, the guard and the scorer import this file and nothing else for
those names.

What the session asks (plan: closing4/events/exp-events-r4.md, section 4; decisions of 2026-11-11: row Q4 yes x2 last in kb2, no sa65
single-bit rows, no firmware `str` row at all):

  kb2  Q290: the ring ends over the kick.  ring_hold.blob (S2b's bytes), the writes (`kicker =0x42`, `kick_no_bump`) made BEFORE the
       window opens and the `miscinfo` call started 1 ms after it, so that the kick's write falls about 8 ms after the first ring entry
       (E816 G0: the entry came 6.70 ms after the call's stamp) with about 7 ticks before it and 6 after.  Rows G0P (control), Q2P,
       Q3P, Q4 (Q3P, then a second window and one ordinary miscinfo).  0 stops predicted, a tick stop ends the stage.
  kp   Q152: a kick pass ended with the phase end.  ring_exit2.blob (ring_exit.s plus a KIND 2 kick pass, ACT 4 only).  Rows E0, FK
       (controls), KP.  0 or 1 stop (KP may stop; a stop of E0 or FK ends the stage).
  e3p  Q166, Q111: the slot 3 pass ended with the phase end.  ring_skip3p.blob (ring_skip3.s without its `str`, the skipped pass ended
       idf, wdf, phas end, nop.end).  Rows B0 (control), B1P x3, hold_recovery Y, the host's CLEAR (kregnow 0x0134, bits 15 and 18).  LAST.

[infer] marks readings that rest on the kept records and were not run; the predictions say which.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from r3layout import *  # noqa: F401,F403,E402
import r3layout as _R3  # noqa: E402

# ---- the module and the session ---------------------------------------------------------------------------------------------
EXPECT_SRCV = "99CD90DA26E3AFF9C450517"      # fork resgx545 a2788bd8 (rgn4); loaded = installed = this (handover 2026-11-11)
OLD_SRCVS = ("230E0EF50FFFD606C53AE3C", "B21FDA82BD5E5CB5A627E3B")
FW_SHA256 = _R3.FW_SHA256
KO_SHA256 = None                              # not known offline: the lead records the installed file's sha256 by hand
SESSION = "r4e"
LAPTOP_DIR = "r4e-run"                        # ~/r4e-run (inputs) and ~/r4e-out/ATTEMPT (results): the session's prefix is ~/r4e-
OUT_DIR = "r4e-out"
MARK = "resgx545 r4e"                         # the kernel-log marker prefix (the runner writes `MARK what run`)
KNOB_DEFAULTS = {"hold_recovery": "N", "render_rgn_arrays": "0x00000000", "render_pb_pages": "0x00000422", "kick_no_bump": "N"}
STAGES = ["kb2", "kp", "e3p"]
SESSIONS = {"r4e": STAGES}
DIR_OF = {"r4e": LAPTOP_DIR}
SESSION_OF = {st: "r4e" for st in STAGES}
RING_ARM = _R3.RING_ARM
STAGE_INFO = {
    # budget: the stops the stage takes and goes on (the next one ends it, exit 8).  gate: the previous stage's kept stage.json.
    "kb2": {"blob": "ring_hold", "arm": RING_ARM, "gate": None, "budget": 0, "per_job_reset": True, "ops": ["kicker2"], "alarm": 420},
    "kp": {"blob": "ring_exit2", "arm": RING_ARM, "gate": "kb2", "budget": 1, "per_job_reset": False, "ops": ["act"], "alarm": 420},
    "e3p": {"blob": "ring_skip3p", "arm": RING_ARM, "gate": "kp", "budget": 0, "per_job_reset": True, "ops": ["skip3p"], "alarm": 600},
}
BLOB_OF = {st: i["blob"] for st, i in STAGE_INFO.items()}
ARM_OF = {st: i["arm"] for st, i in STAGE_INFO.items()}
GATE_OF = {st: i["gate"] for st, i in STAGE_INFO.items() if i["gate"]}
STOP_BUDGET = {st: i["budget"] for st, i in STAGE_INFO.items()}
PER_JOB_RESET = {st: i["per_job_reset"] for st, i in STAGE_INFO.items()}
BLOBS = ("ring_hold", "ring_exit2", "ring_skip3p")
GENERATED_BLOBS = ("ring_exit2", "ring_skip3p")             # ring_hold is S2b's, byte for byte
CONT4_BLOBS = ()
STR_OF = {}                                                 # no firmware `str` in any blob of this session (R4-7)
HOLD_SHA = "fa0f79dbb5864187516febf9c96f6ceea944e5abf6ae69b5acbeb9ac8a0ac168"

# ---- ring_exit2.s (stage kp): KIND 1 plain tick pass, KIND 2 kick pass (pa0 = 0, pa1[23:0] = 0x100), ACT 4 only ------------------------
ACT_OF_STAGE = {"kp": (_R3.ACT_PHAS,)}
ACT_ENDS_OWN = (_R3.ACT_PHAS,)
ACT_ENDS_TAIL = ()
KIND_TICK, KIND_KICK = 1, 2

# ---- stage kb2 -----------------------------------------------------------------------------------------------------------------
KB2_PRE_MS = 1                   # the `miscinfo` call starts 1 ms after the window opens (the writes were made before it)
KB2_POST_MS = 5                  # after the call returns (the ring is long full by then)
KB2_AFTER_MS = 8.0               # "after the kick" with no kick entry: entries stamped later than the call's start stamp + 8.0 ms
KB2_BEFORE_MS = 5.0              # "before the kick" with no kick entry: entries stamped earlier than the call's start stamp + 5.0 ms (the write is 6.7 ms on, E816)
KB2_MIN_AFTER = 3                # G0P control: at least 3 ticks after the kick entry, else the timing design is wrong (the stage stops)
UNITS_PER_MS = _R3.TIMER_HZ / 1000.0                       # CR_TIMER units a millisecond (24.9366 MHz)
KB2_SIG_N, KB2_SIG_GAP = 2, 0.03  # the signature x2 after a call that timed out (USE0_SERV_EVENT bit 16)
KB2_Q4_PRE_MS = 1                # Q4's second window: the ordinary call starts 1 ms after it opens

# ---- stage kp / e3p ------------------------------------------------------------------------------------------------------------
KP_PRE_MS = 0                    # KP: KIND, ACT, COUNT are written BEFORE the window opens and the kick follows it at once (room for 4 ticks after it)
FK_PRE_MS = 3                    # E0 and FK: as E817 and E830 (pre_ms 3)
KP_MIN_AFTER = 4                 # KP kept needs at least 4 ticks after the kick entry in the 16-rung ring (cannot tell below)
E3P_WATCH_MS = 50
E3P_SLOT3_WAIT_S = 4.0           # bounded wait for the slot 3 entry in the page (the fill's render and its end-of-render event)
E3P_CLEAR_VALUES = (_R3.CLEAR_BITS[0], _R3.CLEAR_BITS[1])  # bit 15 (a zero bit), bit 18 (PIXELBE_END_RENDER): CLEAR 0x0134 only, by the host
E3P_READ_MS = {"bit15": (1, 3), "bit18": (1, 3, 20)}      # reads after each write, measured from the write
E3P_MIN_WATCH = 5                # fewer watch reads than this: the level reading cannot tell


# ---- the rows ------------------------------------------------------------------------------------------------------------------
def _kicker2(label, reps, set_kicker=None, no_bump=False, second=False):
    return {"op": "kicker2", "set_kicker": set_kicker, "no_bump": no_bump, "kick": True, "second_kick": second, "reps": reps,
            "label": label}


def _act(kind, act, count, label, reps, **kw):
    d = {"op": "act", "kind": kind, "act": act, "count": count, "trigger": "none", "reps": reps, "label": label, "open_ms": 20,
         "pre_ms": FK_PRE_MS, "may_stop": False, "reset_arm": False}
    d.update(kw)
    return d


def _skip3p(label, reps, skip):
    return {"op": "skip3p", "skip": skip, "reps": reps, "label": label}


ROW_SPEC = {
    "kb2": {"G0P": _kicker2("control", 2),
            "Q2P": _kicker2("heldout", 3, set_kicker=_R3.KICKER_WORD),
            "Q3P": _kicker2("heldout", 3, no_bump=True),
            "Q4": _kicker2("heldout", 2, no_bump=True, second=True)},
    "kp": {"E0": _act(0, 0, 0, "control", 1),
           "FK": _act(KIND_TICK, _R3.ACT_PHAS, 1, "control", 1),
           "KP": _act(KIND_KICK, _R3.ACT_PHAS, 1, "heldout", 2, trigger="miscinfo", pre_ms=KP_PRE_MS, may_stop=True, reset_arm=True)},
    "e3p": {"B0": _skip3p("control", 1, 0),
            "B1P": _skip3p("heldout", 3, 1)},
}
ROW_ORDER = {st: list(rows) for st, rows in ROW_SPEC.items()}


def rep_name(row, k):
    return row.lower() + ("" if k == 0 else f"-r{k + 1}")


# ---- readings the runner (laptop) and the scorer (Mac) share -------------------------------------------------------------------
def slot_entries(page, slot):
    """[(flag, pa0, pa1, pa2, stamp)] of one slot's ring in rung order (flag 0 is an empty rung); stdlib only, for the runner too."""
    out = []
    for j in range(RUNGS[slot]):
        o = RING_BASE[slot] + RUNG * j
        if page[o]:
            out.append((page[o],) + tuple(page[o + 1:o + 5]))
    return out


def is_kick_entry(e):
    return e[1] == 0 and (e[2] & LOW24) == KICK_LOW


def is_tick_entry(e):
    return is_plain_tick(e[1], e[2])
