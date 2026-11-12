# SPDX-License-Identifier: MIT
"""r5layout.py (r6-held part P, session r6hp): the one source of r6-held's part P (round 6, Q111's CR_DPM_TASK_STATE row on the new
kernel).  The file keeps R5-events' name (closing5/r5-events/gen/r5layout.py, published edm/closing-r5-events) so that every module
copied from there imports it unchanged; its content is part P's: the module, the session and its laptop directories, the one stage p1
and its rows, the peek.

It imports R3k-events' `r3layout.py` byte for byte (the page layout, the stop signature registers, the readers of the two debugfs dumps,
the tick words).

What part P asks (plan: closing6/rank/rank-round6.md section 4 "Q111 (E855's row), K1" and session B; DECISIONS-R6.md R6-3 (a), R6-4 (a)):

  p1  timer_clock 0 (the firmware's 400000): B0 + B1P x2, E855's h1 job again (ring_skip3p, byte for byte) on the new kernel (fork
      r6-kernel 3f0b3e74, debugfs `peek`: one read of CR_DPM_TASK_STATE 0x0694).  A B1P stop is the PREDICTED outcome (E855: 3 of 3):
      each is signed, read with the peek BEFORE any write, recovered (reset, gate, health) and the stage goes on.  H-R6 (E855: the
      lockup path writes CR_DPM_TASK_STATE = 2 before its poll) against H-IDLE (the stop leaves 0x0694 as the arm's read).
  The stage ends with timer_clock 0 read back, a reset and the tick on the 25000-unit grid again (clock_back, as R5-events).
  Q294 has no rows (its pysgx oracle did not separate the words: r6-held/private/o3/RESULT.md, data-private).

[infer] marks readings that rest on the kept records and were not run; the predictions say which.
"""
import pathlib
import re as _re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from r3layout import *  # noqa: F401,F403,E402
import r3layout as _R3  # noqa: E402

# ---- the module and the session ---------------------------------------------------------------------------------------------
EXPECT_SRCV = "41E2F5C756F96D20F7109A4"      # fork r6-kernel 3f0b3e74 (the lead's build, 2026-11-12); loaded = installed = this
OLD_SRCVS = ("99CD90DA26E3AFF9C450517", "230E0EF50FFFD606C53AE3C", "B21FDA82BD5E5CB5A627E3B")   # rgn4 and older: refused
KO_SHA256_BUILT = "8a32dada935e8a293b7be03c5d1938cc31093fea4b356ed41f9cb476d421576a"   # gma500_gfx.ko as built (the lead)
FW_SHA256 = _R3.FW_SHA256
KO_SHA256 = None                              # not known offline: the lead records the installed file's sha256 by hand
SESSION = "r6hp"
LAPTOP_DIR = "scratch/r6h/p/stage"           # ~/scratch/r6h/p/stage (the staged tree), ~/scratch/r6h/p/out/ATTEMPT (results): round 6's rule
OUT_DIR = "scratch/r6h/p/out"
WORK_DIR = "scratch/tmp"                      # per-job work directories: mktemp -d ~/scratch/tmp/r6hp.XXXXXX, removed once the job is kept
WORK_PREFIX = "r6hp."
MIN_FREE_MB = 300                             # free space on ~ before each job (round 6: at least 200; r6-render4x's 300)
MARK = "resgx545 r6hp"                        # the kernel-log marker prefix (the runner writes `MARK what run`)
TOOL_NAME = "sgxfive-test-s1b"                # E855's tool (sha256 46a2d063...): the B1P rows replicate E855 with it
KNOB_DEFAULTS = {"hold_recovery": "N", "render_rgn_arrays": "0x00000000", "render_pb_pages": "0x00000422", "kick_no_bump": "N",
                 "timer_clock": "0x00000000", "render_tail_room": "0x00000000"}
STAGES = ["p1"]
SESSIONS = {"r6hp": STAGES}
DIR_OF = {"r6hp": LAPTOP_DIR}
SESSION_OF = {st: "r6hp" for st in STAGES}
RING_ARM = _R3.RING_ARM
STAGE_INFO = {
    # budget: the stops the stage takes and goes on (one per B1P job: a stop is the prediction there; a stop past it ends the stage,
    # exit 8).  No gate: the stage is the part's only one.
    "p1": {"blob": "ring_skip3p", "arm": RING_ARM, "gate": None, "budget": 2, "per_job_reset": True, "ops": ["hjob"], "alarm": 600},
}
BLOB_OF = {st: i["blob"] for st, i in STAGE_INFO.items()}
ARM_OF = {st: i["arm"] for st, i in STAGE_INFO.items()}
GATE_OF = {st: i["gate"] for st, i in STAGE_INFO.items() if i["gate"]}
STOP_BUDGET = {st: i["budget"] for st, i in STAGE_INFO.items()}
PER_JOB_RESET = {st: i["per_job_reset"] for st, i in STAGE_INFO.items()}
BLOBS = ("ring_skip3p",)
GENERATED_BLOBS = ()                                        # ring_skip3p is R4-events' bytes (E836), reused byte for byte
CONT4_BLOBS = ()
STR_OF = {}                                                 # no firmware `str` in the blob (laptop rule: 0x0814 / 0x0a78 only; none needed)
SKIP3P_SHA = "3b35d3af206b9b21302cf4b70f7bd64af7d840ebd744f6c067f8b2819e406b49"   # closing4/r4-events/bins/ring_skip3p.blob (E836)

# ---- the clock knob (E084: the tick lasts HostCtl dword 6 cycles of a 399.0 MHz clock; CR_TIMER counts 1/16 of it) ---------------
FW_CLOCK = 400000                    # dword 6 when timer_clock is 0 (the kernel's SGX_CLOCK_HZ / 1000, fork a2788bd8 sgxfive.c 500-501)
CLOCKS = (0,)                        # part P writes timer_clock 0 only (p1 runs at the firmware's default; clock_back writes 0 too)
CORE_HZ = 399.0e6


def eff_clock(v):
    """HostCtl dword 6 for a timer_clock knob value (0: the default)."""
    return v or FW_CLOCK


def knob_text(v):
    """What the debugfs x32 file reads back after `v` was written (the kernel prints 0x%08x)."""
    return f"0x{v:08x}"


def gap_units(v):
    """The tick's period in CR_TIMER units: dword 6 / 16 (25000, 50000, 100000)."""
    return eff_clock(v) // 16


GAP_TOL = {0: 10, 800000: 20, 1600000: 40}                  # the plan's tolerances (25000 +-10, 50000 +-20, 100000 +-40)


def rate_hz(v):
    return CORE_HZ / eff_clock(v)


def rate_band(v):
    """The tick rate a healthy firmware shows at clock v: +-10% of 399.0 MHz / dword 6 (E084: 997.48, 498.76 Hz; 249.4 Hz untested)."""
    r = rate_hz(v)
    return (0.9 * r, 1.1 * r)


# ---- R-6 / E353 / E836: the 3D lockup check and its marks ---------------------------------------------------------------------
HC_LOCKUPS = 3                       # HostCtl dword 3 ui32uKernelDetectedLockups (+1 at a lockup, R-6 (i))
HC_HWR_RATE = 5                      # HostCtl dword 5 ui32HWRecoverySampleRate (the kernel writes 10)
HC_CLOCK = 6                         # HostCtl dword 6 ui32uKernelTimerClock (the timer_clock knob, E084)
HC_IFLAGS = 8                        # HostCtl dword 8 ui32InterruptFlags (|= 1 at a lockup, R-6 (i))
HC_ICLEAR = 9                        # HostCtl dword 9 ui32InterruptClearFlags
HC_TICKS = 12
TA_COUNT3D = 57                      # TA3DCtl dword 57: the 3D tick counter (+1 a tick, 0 at the 10th; R-6 (i))
TA_SIG3D = 58                        # TA3DCtl dword 58: the 3D register signature (stored at every sample, R-6 (i))
TA_CTX3D = 28                        # TA3DCtl dword 28: the 3D render context the render kick writes (R-6)
HWR_RATE = 10                        # HostCtl dword 5 as the kernel writes it (HC_HWR_SAMPLE_RATE, a constant)
LOCKUP_TICKS = 2 * HWR_RATE          # 20: tick 10 stores the signature, tick 20 compares (R-6 (i), S0)
REG_DPM_TASK_STATE = 0x0694          # CR_DPM_TASK_STATE: 2 after the lockup (E855's [RE] reading); the regs file lists it as `skip`
PEEK_FILE = "peek"                   # debugfs peek (fork r6-kernel db7faabc, 0600): its offset defaults to 0x0694 and is NEVER written here
PEEK_RE = r"^reg 0x0694 0x[0-9a-f]{8}$"   # the one line a cat of it prints (seq_printf "reg 0x%04x 0x%08x")
PEEK_TIMEOUT = (5, 10)               # `timeout -k 5 10 cat peek`: a bounded read
PEEK_DPM_LOCKUP = 2                  # H-R6: the lockup path writes CR_DPM_TASK_STATE = 2 before its poll (E855, its [RE] row)


def parse_peek(text):
    """The value of a peek read (int), or None when the text is not the one line `reg 0x0694 0x%08x`."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if len(lines) != 1 or not _re.match(PEEK_RE, lines[0].strip()):
        return None
    return int(lines[0].split()[2], 16)
EVENT_BIT6 = 0x40                    # EVENT_STATUS bit 6 DPM_STATE_CLEAR: the lockup path polls it (R-6 (ii))
BIT18 = 0x40000
STOP_STATUS_H3 = 0x20000000          # EVENT_STATUS at a stop after the host cleared bit 18 (bit 29, the timer, alone)

# ---- the jobs ---------------------------------------------------------------------------------------------------------------
H_CLEAR_VALUES = (_R3.CLEAR_BITS[0], _R3.CLEAR_BITS[1])     # bit 15 (a zero bit), bit 18 (PIXELBE_END_RENDER): CLEAR 0x0134 only, by the host
H_READ_MS_LATE = {"bit15": (1, 3), "bit18": (1, 3, 20)}     # h1 (R4's e3p): after the watch, from each write
H_READ_MS_EARLY = {"bit15": (1, 3), "bit18": (1, 3)}        # h3: at the slot 3 entry, before the watch
H_SLOT3_WAIT_S = 4.0                 # bounded wait for the slot 3 entry in the page (the fill's render and its end-of-render event)
H_MIN_WATCH = 5                      # fewer watch reads than this: the level reading cannot tell
H_MIN_TICKS = 3                      # fewer ring ticks after the fill's kick than this: tick_gap cannot tell
WATCH_MS = {0: 50, 800000: 100, 1600000: 150}               # the stop is predicted 20, 40, 80 ms after the kick (H-TICKS)
TOOL_WAIT_S = 6                      # the tool is collected (then killed) this long after the job; R4's value


def _h(label, reps, skip, clock, clears="none"):
    """One row: skip 0 (B0) or 1, the clock knob, the clears: none, late (after the watch: h1) or early (at the slot 3 entry: h3)."""
    d = {"op": "hjob", "skip": skip, "timer_clock": clock, "clears": clears if skip else "none", "reps": reps, "label": label,
         "watch_ms": WATCH_MS[clock], "may_stop": bool(skip), "rep_after_stop": bool(skip)}
    d["miscinfo_after_clears"] = clears == "early"
    return d


ROW_SPEC = {
    "p1": {"B0": _h("control", 1, 0, 0),
           "B1P": _h("heldout", 2, 1, 0, clears="late")},
}
ROW_ORDER = {st: list(rows) for st, rows in ROW_SPEC.items()}
CLOCK_GROUP = {}                     # one clock: a failed B0 voids the stage's rows


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
    return e[1] == TICK_PA0


def count_after_kick(page):
    """(ticks_after_kick, info, why-not): the slot 0 rungs with pa0 2 after the FIRST kick entry of the ring (the fill's), plus page
    dword 16 (DROP: slot 0 passes that found the ring full; asm/ring_skip3p.s counts them only with the window open).  Cannot tell
    when no kick entry is in the ring, or when the ring is full and a second kick entry is not in it (a later kick would then be in
    the counter); h3's miscinfo must be in the ring (its control)."""
    s0 = slot_entries(page, 0)
    kicks = [i for i, e in enumerate(s0) if is_kick_entry(e)]
    if not kicks:
        return None, {}, "the fill's kick entry is not in the slot 0 ring"
    k = kicks[0]
    after = s0[k + 1:]
    ticks = [e for e in after if is_tick_entry(e)]
    gaps = [b[4] - a[4] for a, b in zip(ticks, ticks[1:])]
    info = {"before": sum(1 for e in s0[:k] if is_tick_entry(e)), "ring_after": len(ticks), "drop": page[DROP],
            "kicks": len(kicks), "full": len(s0) == RUNGS[0], "gaps": gaps}
    return len(ticks) + page[DROP], info, None


def tick_gap(page):
    """The median gap of the slot 0 ring's consecutive tick entries (a kick entry between two ticks breaks the pair), before and after
    the fill's kick alike: the plan's `tick_gap`, in CR_TIMER units.  None with fewer than H_MIN_TICKS ticks in the ring."""
    s0 = slot_entries(page, 0)
    if sum(1 for e in s0 if is_tick_entry(e)) < H_MIN_TICKS:
        return None
    gaps = [(b[4] - a[4]) & 0xFFFFFFFF for a, b in zip(s0, s0[1:]) if is_tick_entry(a) and is_tick_entry(b)]
    if not gaps:
        return None
    g = sorted(gaps)
    return g[len(g) // 2]


def parse_marks(text):
    """{'hc': {dword: value}, 'ta': {dword: value}, 'sw_events': n, 'regs': {offset: value}} from a `status` file (hang_dump's
    NAME-status.txt or the record's text): `hostctl[ 8]: bb ...`, `ta3dctl[56]: bb ...` (bytes, little endian), `reg 0x12c = 0x...`
    and the first line's `sw_events N`.  None for a text that is not a status file."""
    if not text or "hostctl[" not in text:
        return None
    hc, ta, regs, sw = {}, {}, {}, None
    for line in text.splitlines():
        m = _re.match(r"(hostctl|ta3dctl)\[\s*(\d+)\]:\s+((?:[0-9a-f]{2}\s*)+)$", line)
        if m:
            bs = bytes(int(x, 16) for x in m.group(3).split())
            first = int(m.group(2))
            for i in range(len(bs) // 4):
                (hc if m.group(1) == "hostctl" else ta)[first + i] = int.from_bytes(bs[4 * i:4 * i + 4], "little")
            continue
        m = _re.match(r"reg (0x[0-9a-f]+) = (0x[0-9a-f]+)$", line)
        if m:
            regs[int(m.group(1), 16)] = int(m.group(2), 16)
            continue
        m = _re.search(r"\bsw_events (\d+)", line)
        if m and sw is None:
            sw = int(m.group(1))
    return {"hc": hc, "ta": ta, "sw_events": sw, "regs": regs}


def regs_value(text, off):
    """('value', int) / ('skip', None) / ('absent', None) for one register of a `regs` file."""
    for line in (text or "").splitlines():
        m = _re.match(r"reg (0x[0-9a-f]+) (0x[0-9a-f]+|skip)$", line)
        if m and int(m.group(1), 16) == off:
            return ("skip", None) if m.group(2) == "skip" else ("value", int(m.group(2), 16))
    return ("absent", None)


def is_marked(m, base_lockups=0):
    """The lockup marks of a status dump (the runner's stop rule and the scorer's H-HWR rows): dword 3 above the arm's, dword 8 bit 0."""
    if not m:
        return False
    return (m["hc"].get(HC_LOCKUPS, 0) - base_lockups) >= 1 and bool(m["hc"].get(HC_IFLAGS, 0) & 1)
