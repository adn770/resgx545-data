# SPDX-License-Identifier: MIT
"""R3x-events layout (round 3, L3; a copy of closing2/r3-events/gen/r3layout.py with the additions at the end)

Original docstring: R3-events layout (S2b's s2layout.py plus the words of alias.s and ring_skip.s): the results page (own_res, 1024
dwords), the stages, the limits.

One module, standard library only, imported by the generator (Mac), the laptop runner (copied to ~/r3ev/gen/) and the
scorer (Mac).  Frozen with everything else (run/freeze_r3.sh).  Dword indices of the results page, as the tasks'
`stad [r1,+#N]` (r1 = res + 0) and `stad [r2,+#N]` (r2 = the slot's ring base) address them.

R3 additions (the rest is S2b's, byte for byte, so that ring_hold.blob keeps its page):
  SKIP, SKIPPED    ring_skip.s (stage b): the host's count of plain ticks to skip, the task's count of skipped passes
  PASS             ring_skip.s and alias.s count every pass of slot 0 in dword 20 (as ring_hold's slot 0)
  A_*              alias.s (stage a): the marker the host hands the writer, the r/i markers of A6, the writer's
                   record (WR_*), the reader's record (RD_*)
"""

PAGE_DWORDS = 1024
INITFILL = 0xDEADC0DE            # the landed runner's fill; a dword still holding it was not written
MAGIC = 0x4E574F53               # dword 0 after a good arm (fwtask_run.cmd_arm checks it)

# host <-> task protocol (dwords 1 to 5 as the landed fwtask_run.py)
CMD, STATE, RUNID, OVERLAP, ECHO = 1, 2, 3, 4, 5
WINDOW = 6                       # 0 closed (tail call at once), 1 filtered (no plain tick), 2 every pass
N_ITER = 10                      # slow loop count (hold blob, cmd 1)
MARK = 11                        # E2a: the value cmd 2 / cmd 3 write to sa67 / sa68
PFLAGS = 12                      # E2a writer: p0..p3 at its tail call = (dword != 0), dwords 12..15
DROP = 16                        # +slot: passes that found the slot's ring full
PASS = 20                        # +slot: passes of each slot (hold blob)
OVL = 24                         # +slot: 1 when a pass found STATE busy (hold blob)
HOLD_ENTRY, HOLD_EXIT = 32, 33   # CR_TIMER at the slow loop's start and end (hold blob)
OVL_LOG = 40                     # +4*slot: pa0, pa1, pa2, CR_TIMER of the last busy-finding pass of that slot

# E2a areas (pa_read.s, pa_write.s): A = cmd 1 pass, B = the next pass (cmd 9), C = same-pass read-back of a write
AREA_A, AREA_B = 64, 96
AREA_FIELDS = ["pa0", "pa1", "pa2", "pa3", "pa4", "sa64", "sa65", "sa66", "sa67", "sa68", "sa0", "timer"]
AREA_C = 80                      # 80 pa3 81 sa67 (cmd 2); 82 pa4 83 sa68 (cmd 3)

# the ring: one ladder of rungs per slot, 8 dwords a rung: flag, pa0, pa1, pa2, CR_TIMER
RING_BASE = {0: 256, 1: 384, 2: 448, 3: 512}     # dwords (bytes 0x400, 0x600, 0x700, 0x800)
RUNGS = {0: 16, 1: 8, 2: 8, 3: 8}
RUNG = 8
RING_END = 576

STATE_IDLE, STATE_BUSY, STATE_DONE, STATE_NEXT = 0, 1, 2, 3

TICK_UNITS = 25000               # CR_TIMER counts per tick: 24.937 MHz / 997.46 Hz (E009) = 25001
TIMER_HZ = 24.9366e6             # E009 (corrected for the laptop clock)
NS_PER_ITER = (62, 69)           # E539: 62 to 69 ns an iteration of the slow loop at n = 100000
N_MAX = 1_600_000                # the runner refuses a larger n (about 110 ms at 69 ns)

# words of the tick (E532; S2 run 1).  S2 run 1 (post hoc, see PREFLIGHT section 7): pa1[31:24] is a count K that
# every event carries (2 after the arm, +1 a GETMISCINFO kick), NOT event bits; the kick is pa0 = 0, pa1 = (K << 24)
# | 0x100; pa2 is EVENT_TIMER at the event (bits 31:24 = 0x01, bits 23:0 counting down from 400000 core clocks,
# E009), which reads 400000 - 16 = 0x061a70 on a tick.  E538's "kick" words (pa1 0x03000000) were the tick after.
TICK_PA0, TICK_PA1, PA2_CONST = 0x2, 0x02000000, 0x01061A70
COUNT_MASK, LOW24 = 0xFF000000, 0x00FFFFFF
KICK_LOW = 0x100
EVT_RELOAD = 400000              # HostCtl dword 6, core clocks a tick (E009); CR_TIMER = core / 16


def count_of(pa1):
    return pa1 >> 24


def is_kick(pa0, pa1):
    """S2 run 1 (fit, 3 kicks): a host GETMISCINFO kick's words."""
    return pa0 == 0 and (pa1 & LOW24) == KICK_LOW


def evt_ok(pa2):
    """pa2 in EVENT_TIMER's format and range (E009): bits 31:24 = 0x01, bits 23:0 below the reload 400000."""
    return pa2 >> 24 == 0x01 and 0 < (pa2 & LOW24) < EVT_RELOAD

# E146: PDS #13 dispatch. m = pa1 & 0xffffff; bit 8 -> general; a group only if m has no other bit and pa0 == 0
GROUPS = {3: 0x00400090, 1: 0x00000200, 2: 0x00300400}


def pds_slot(pa0, pa1):
    """The slot PDS #13 starts for the words (E146): 0 general, 1 bit 9, 2 bits 21 20 10, 3 bits 22 7 4."""
    m = pa1 & 0xFFFFFF
    if m & 0x100:
        return 0
    for slot in (3, 1, 2):          # E146's test order: 0x00400090, 0x200, 0x00300400
        g = GROUPS[slot]
        if m & g:
            return slot if (m & ~g) == 0 and pa0 == 0 else 0
    return 0


def is_plain_tick(pa0, pa1):
    """The filter of window 1: a pass with pa0 == 2 and no bit in pa1[23:0] is not logged (pa1[31:24] is the count,
    S2 run 1; the first filter masked bit 25 only, so every tick after a kick passed it)."""
    return (pa1 & LOW24) == 0 and pa0 == 2


# S2 run 3 (fit, 12 holds of n = 10000 to 1500000): the hold lasts 1.5 n + 15 CR_TIMER units (within 2), and starts
# 64 to 70 units after the tick that carries the command; so the exit lands 1.5 n + 81 +- 4 units after that tick.
HOLD_PER_ITER, HOLD_FIXED, HOLD_START = 1.5, 15, 67
TICKS_QUEUED_PA2 = 0x01061A74     # run 3: the ticks queued behind a hold read 400000 - 12 (a served tick 400000 - 16)
QUEUE_CAP = 4                     # run 3: four entries after every hold of 6, 18 and 90 ticks (fit)


def hold_units_of(n):
    return HOLD_PER_ITER * n + HOLD_FIXED


def n_for_ticks(H):
    """n whose exit lands mid-period after H held ticks: ((H + 0.5) * 25000 - 82) / 1.5, rounded (the coordinator's
    formula, from 1.5 n + 15 and a start 67 units after the tick)."""
    return round(((H + 0.5) * TICK_UNITS - 82) / HOLD_PER_ITER)


def iter_ms(n):
    """(low, high) milliseconds of n iterations of the slow loop (E539)."""
    return n * NS_PER_ITER[0] / 1e6, n * NS_PER_ITER[1] / 1e6


# ---- R3 additions ---------------------------------------------------------------------------------------------------
SKIP, SKIPPED = 7, 8             # ring_skip.s: plain ticks still to skip (host writes, task decrements); skipped so far
SKIP_FLAG = 3                    # a skipped pass's rung flag (a logged pass's is 1)

# alias.s (stage a): commands (dword CMD), the host's markers, the writer's and the reader's records
A_M = 11                         # the marker for sa63 (cmd 1, 7), sa65 (cmd 3)
A_RI = 12                        # cmd 6: r20, r21, i0, i1 markers (dwords 12..15)
A_PASS = 20                      # passes of the task (every pass, any command)
CMD_A1, CMD_A2, CMD_A3, CMD_A4, CMD_A5, CMD_A6, CMD_RESTORE63, CMD_READ = 1, 2, 3, 4, 5, 6, 7, 9
WR = 64                          # the writer's record, 16 dwords:
WR_FIELDS = ["pa0", "pa1", "pa2", "sa63_before", "sa64_before", "sa65_before", "written", "readback", "readback2"]
WR_DONE = WR + 15                # the arm block (every writer) stores the run id here: a flag that stays (cmd 9 lasts one tick)
RD = 96                          # the reader's record, 16 dwords:
RD_FIELDS = ["pclink", "p0", "p1", "p2", "p3", "r20", "r21", "i0", "i1", "sa64", "sa65", "sa63", "pa0", "pa1", "pa2", "pass"]

# What each alias.s command may write (the guard compares the assembled code with this; R2-1 b allows sa63, sa64, sa65 in
# A1-A6 and nothing else).  r20, r21, i0, i1 and the predicates are not sa registers.
CMD_SA = {CMD_A1: ["sa63"], CMD_A2: ["sa65"], CMD_A3: ["sa65"], CMD_A4: ["sa64"], CMD_A5: ["sa64"], CMD_A6: [],
          CMD_RESTORE63: ["sa63"], CMD_READ: []}      # alias.s (closing2); alias2 adds CMD_SA2 below
SA_ALLOWED = {"sa63", "sa64", "sa65"}

# the stop signature (E537, p1130-b2-variants/tailpair-stop1-regs.txt): registers of the `regs` file
REG_CLKSTAT, REG_SERV_EVENT, REG_EVENT_TIMER, REG_EVENT_STATUS = 0x0008, 0x0B14, 0x0ACC, 0x012C   # 0x0008 is read only
REG_STATUS2, REG_BIF_INT, REG_TIMER = 0x0118, 0x0C04, 0x0144
SIG_REGS = (REG_CLKSTAT, REG_SERV_EVENT, REG_EVENT_TIMER, REG_EVENT_STATUS, REG_STATUS2, REG_BIF_INT, 0x0B20, 0x0C08)
CLK_IDLE = 0x20                  # the clock status register 0x0008 when idle (E537's note); E537's stop read 0x000CCFA0
E537_SIG = {"clkstat": 0x000CCFA0, "serv_event": 0x000009E0, "event_timer": 0x01038EC3, "event_status": 0x20000000}
SERV_EMPTY_BIT = 16              # USE0_SERV_EVENT bit 16: EMPTY

K7_HOLD_TICKS = 90               # S2b's e4l: n = n_for_ticks(90) = 1508279, a 90.5 ms hold


def sa_of(name):
    """sa63 -> 63."""
    return int(name[2:])


# =====================================================================================================================
# R3k additions (round 3, kernel batch, sessions K0 and K1 on the new module).  Everything the generator, the runner, the
# scorer and the guard must agree on lives here, once.  K0 = ~/r3k0 (stages k0f k0t k0c k0h: the re-baseline), K1 = ~/r3kev
# (stages f t kb e2b e3h e3a e3b).  The framework is closing3/r3x-events (L3) with the old stages h, c, e, d dropped: their
# blobs alias2 and ring_hold (and the rows C0, C1, H0, H1) come back in K0 as controls with L3's frozen outcomes.
# =====================================================================================================================
EXPECT_SRCV = "230E0EF50FFFD606C53AE3C"      # the new module (fork resgx545-r3 8fc748b0); preflight: loaded = installed = this
OLD_SRCV = "B21FDA82BD5E5CB5A627E3B"         # the module of rounds 1 to 3 (L1, L2, L3): never accepted here
KO_SHA256 = "06bf58db6e1c78f2bd9858bcc7b9e63d752786e098e50b5c67345ce69f2ceb78"   # cachix's gma500_gfx.ko (recorded, not a condition)
FW_SHA256 = "6a00268e9d4ca552c02e52651a42a2b4db3887d7fe626f209888369985162b0a"   # the cut firmware the kernel's cont4 is tied to

SESSIONS = {"k0": ["k0f", "k0t", "k0c", "k0h"], "kev": ["f", "t", "kb", "e2b", "e3h", "e3a", "e3b"]}
DIR_OF = {"k0": "r3k0", "kev": "r3kev"}                  # laptop directories (results in ~/r3k0-out, ~/r3kev-out)
STAGES = SESSIONS["k0"] + SESSIONS["kev"]
SESSION_OF = {st: s for s, sts in SESSIONS.items() for st in sts}
RING_ARM = "slots=0xf entry=0,1,2,3"
ONE_ARM = "slots=0x1 entry=0"
STAGE_INFO = {
    # blob, arm, gate (the previous stage's kept stage.json), stop budget (stops the stage takes and goes on; the next one ends it,
    # exit 8), reset + arm before every job, ops the stage may use, driver alarm (s)
    "k0f": {"blob": None, "arm": None, "gate": None, "budget": 0, "per_job_reset": True, "ops": ["defaults"], "alarm": 240},
    "k0t": {"blob": None, "arm": None, "gate": "k0f", "budget": 0, "per_job_reset": True, "ops": ["tooljob"], "alarm": 420},
    "k0c": {"blob": "alias2", "arm": ONE_ARM, "gate": "k0t", "budget": 0, "per_job_reset": False, "ops": ["alias2"], "alarm": 300},
    "k0h": {"blob": "ring_hold", "arm": RING_ARM, "gate": "k0c", "budget": 0, "per_job_reset": True, "ops": ["holdsig", "kicker"],
            "alarm": 420},
    "f": {"blob": "ring_exit", "arm": RING_ARM, "gate": "k0h", "budget": 1, "per_job_reset": False, "ops": ["act"], "alarm": 480},
    "t": {"blob": "ring_timer", "arm": RING_ARM, "gate": "f", "budget": 1, "per_job_reset": False, "ops": ["act"], "alarm": 480},
    "kb": {"blob": "ring_hold", "arm": RING_ARM, "gate": "t", "budget": 0, "per_job_reset": True, "ops": ["kicker"], "alarm": 600},
    "e2b": {"blob": "pa_write2", "arm": ONE_ARM, "gate": "kb", "budget": 0, "per_job_reset": False, "ops": ["pawrite"], "alarm": 480},
    "e3h": {"blob": None, "arm": None, "gate": "e2b", "budget": 0, "per_job_reset": True, "ops": ["clear_host"], "alarm": 480},
    "e3a": {"blob": "strclr", "arm": RING_ARM, "gate": "e3h", "budget": 0, "per_job_reset": True, "ops": ["clear_fw"], "alarm": 480},
    "e3b": {"blob": "ring_skip3", "arm": RING_ARM, "gate": "e3a", "budget": 2, "per_job_reset": True, "ops": ["skip3"], "alarm": 900},
}
BLOB_OF = {st: i["blob"] for st, i in STAGE_INFO.items()}
ARM_OF = {st: i["arm"] for st, i in STAGE_INFO.items()}
GATE_OF = {st: i["gate"] for st, i in STAGE_INFO.items() if i["gate"]}
STOP_BUDGET = {st: i["budget"] for st, i in STAGE_INFO.items()}
PER_JOB_RESET = {st: i["per_job_reset"] for st, i in STAGE_INFO.items()}
BLOBS = ("alias2", "ring_hold", "ring_exit", "ring_timer", "pa_write2", "strclr", "ring_skip3")
GENERATED_BLOBS = ("alias2", "ring_exit", "ring_timer", "pa_write2", "strclr", "ring_skip3")     # ring_hold is S2b's, byte for byte

# alias2.s (stage k0c): the commands of alias.s (1-7, 9) and three more; the host's words
W65, W64 = 9, 10                 # dwords: sa65's word (cmd 10, 11), sa64's word (cmd 11)
NPASS = 7                        # cmd 12: passes still to write sa64 = pa0 & ~2 (the host writes N, the task counts down)
CMD_WORD65, CMD_E537, CMD_RUN64 = 10, 11, 12
CMD_SA2 = dict(CMD_SA)
CMD_SA2.update({CMD_WORD65: ["sa65"], CMD_E537: ["sa63", "sa64", "sa65"], CMD_RUN64: ["sa64"]})
SA_ALLOWED2 = {"sa63", "sa64", "sa65"}
WR_X = WR + 9                    # cmd 11's extra record: sa63 written, sa63 read back, sa64 written, sa64 read back
WR_X_FIELDS = ["sa63_w", "sa63_rb", "sa64_w", "sa64_rb"]

# the ring tasks of stages f and t (ring_exit.s, ring_timer.s): S2's ring plus KIND, ACT, COUNT and the acted pass (slot 0, window 2)
KIND, ACT = 9, 10                # KIND 1 plain tick pass; ACT see below
COUNT, ACTED = SKIP, SKIPPED     # dwords 7, 8: passes still to act on (host writes), passes acted on (task counts)
ACT_SEEN = 13                    # the ACT the task acted with on its last acted pass (the task's own record: the host wrote it)
SKIP_FLAG = 3                    # an acted pass that ends in our own code (nop.end) is logged with flag 3
TAIL_FLAG = 4                    # a pass that ends in a tail call (cont4: the real exit; ACT 7: str, then the closed task) flag 4
RING_FLAGS = (0, 1, SKIP_FLAG, TAIL_FLAG)
# ring_exit.s: how the acted tick pass ends (the exit of the closed tasks is cfi.global, idf, wdf, phas, nop.end: readings R-1)
ACT_CFI, ACT_PHAS, ACT_BOTH, ACT_CONT4 = 3, 4, 5, 6      # own end + cfi only, + phas only, + both (the exact replica), tail to the exit
# ring_timer.s: the str of CR_EVENT_TIMER (0x0acc) the closed tick handler also writes (E155: `or r0, r0, #0x01000000` of HostCtl
# dword 6 = 400000, `str #691, r0`, `mov pa2, r0`), then the pass goes on to the closed task (7) or ends in our own code (8)
ACT_STR_TAIL, ACT_STR_END = 7, 8
TIMER_STR_WORD = 0x01000000 | EVT_RELOAD                  # 0x01061a80: the word the closed handler stores (ticks read it 16 units later)
ACT_OF_STAGE = {"f": (ACT_CFI, ACT_PHAS, ACT_BOTH, ACT_CONT4), "t": (ACT_STR_TAIL, ACT_STR_END)}
ACT_ENDS_OWN = (ACT_CFI, ACT_PHAS, ACT_BOTH, ACT_STR_END)  # the closed task is never called: flag 3
ACT_ENDS_TAIL = (ACT_CONT4, ACT_STR_TAIL)                  # flag 4
ACT_SLOT = 2                     # (L3's X1: the tail call to slot 2; not in this session)

# E537's writer (cmd 4 of state3.s; b2-markers.json, first writer; E537 correction note)
E537 = {"sa63": 0xD7C5F5AE, "sa64": 0xB0150D9D, "sa65": 0xB009C5DC, "r20": 0xF8A4AC80, "r21": 0xFCF393C8, "i0": 0xA958E53C,
        "i1": 0xD90C0733}
E537_SA65_BIT8_CLEAR = 0xB009C4DC
TESTED_PA1_MASK = 0x00780790     # pa1 bits some code of the ukernel tests (R-4)
ASSERT_WORD = 0xAD002600         # HostCtl dword 14 after the routine at 0x0-0x5 ran (0a, R-3); 0 on every healthy and E793 dump
HC_ASSERT_DWORD = 14
P3_MS = 500                      # the kernel's miscinfo timeout: a read that takes this long or fails is "not answered"

# stage kb / k0h G0 (Q290): the kicker word W (debugfs kicker), the CCB write offset ccbctl[0] and the one-shot kick_no_bump
KICKER_FILE, KICK_NO_BUMP_FILE = "kicker", "kick_no_bump"
KICKER_WORD = 0x42               # Q1, Q2: the word `kicker =0x42` sets (K0 + 0x40 with K0 = 2)
KICKER_RE = r"^kicker (\d+) ccbctl (\d+) (\d+) kicks (\d+)\s*$"

# stage e2b (Q098, the write direction): pa_write2.s = E2a's pa_write.s (cmd 1 read, 2 mov sa67, 3 mov sa68, 9 the next pass's read)
# plus cmd 4 (mov pa3), 5 (mov pa4), 6 (mov pa2), each read back through the pa and its alias in the same pass
PW_M = 11                        # the marker (dword 11, as E2a's A_M)
PW_FLAGS = 12                    # dwords 12..15: p0..p3 at the tail of a writer (E536's 0, 0, 1, 1)
PW_A, PW_B, PW_C = 64, 96, 80    # area A (cmd 1 and every writer's pre-state), area B (cmd 9), same-pass read-backs
PW_FIELDS = ["pa0", "pa1", "pa2", "pa3", "pa4", "sa64", "sa65", "sa66", "sa67", "sa68", "sa0", "timer"]
PW_C_OF = {2: (80, "pa3", "sa67"), 3: (82, "pa4", "sa68"), 4: (80, "pa3", "sa67"), 5: (82, "pa4", "sa68"), 6: (84, "pa2", "sa66")}
PW_CMD_READ, PW_CMD_NEXT = 1, 9
PW_SA = {1: [], 2: ["sa67"], 3: ["sa68"], 4: [], 5: [], 6: [], 9: []}           # what each command writes (sa)
PW_PA = {1: [], 2: [], 3: [], 4: ["pa3"], 5: ["pa4"], 6: ["pa2"], 9: []}        # ... and (pa): never pa0, pa1 (R3-K3)
E748 = {"pa0": 0x2, "pa1": 0x02000000, "pa2": 0x01061A70, "pa3": 0x04000004, "pa4": 0x00030001,
        "sa64": 0x2, "sa65": 0x02000000, "sa66": 0x01061A70, "sa67": 0x04000004, "sa68": 0x00030001, "sa0": 0x32004000}
PW_MARK = {"s": 0x5A670001, "c4": 0x5A430004, "c5": 0x5A440005, "c6": 0x5A420006, "z67": 0x04000004, "z68": 0x00030001}

# stages e3h / e3a (Q166, CLEAR2 against the latch STATUS2 bit 6) and e3b (CLEAR and Q111's level-or-pulse clause)
REG_STATUS2_OFF = 0x0118
S2_IDLE, S2_LATCH = 0x400, 0x440
CLEAR2_BITS = (0x8000, 0x40)                 # bit 15 (a zero bit), bit 6 (the latched one): the only values ever written to CLEAR2
CLEAR_BITS = (0x8000, 0x40000)               # bit 15, bit 18 (PIXELBE_END_RENDER): the values written to CLEAR in e3b
CLEAR_TIMER_BIT = 0x20000000                 # bit 29 (TIMER), only by the host, only after a stop (e3b)
E3_STEPS = [("fill",), ("wait", 1.0), ("clear2", 0x8000), ("clear2", 0x40), ("fill",)]     # steps 1 to 5 of a round
LOOP_PROG = "loop-b16-i56"                   # 56 iterations: STATUS2 bit 6 sets (E431, E769); our own source
SC_CMD, SC_VAL = 1, 11                       # strclr.s / ring_skip3.s: the command (dword 1: 1 = str #69, 2 = str #77) and its value
SC_CMD_CLEAR2, SC_CMD_CLEAR = 1, 2
SKIP3 = 7                                    # ring_skip3.s: the skip-once flag the host writes (dword 7), SKIPPED (dword 8) the task's
SKIP3_WORD_BIT = 0x10                        # the fill's end-of-render event: slot 3, pa0 = 0, pa1[23:0] = 0x10 (E747)
E3B_WATCH_MS = 50

# ---- the rows ----------------------------------------------------------------------------------------------------------------
# one source for the generator, the runner, the guard and the scorer.  `op` is the job's operation; `label` control / fit / heldout;
# `reps`; `run_if` (`all_kept:ROW:N`: at least N jobs of ROW ran and every one that ran kept the tick); `rep_after_stop` (e3b: the
# replicates of a row that stopped still run: its budget is the stage's).
def _act(kind, act, count, label, reps, **kw):
    d = {"op": "act", "kind": kind, "act": act, "count": count, "trigger": "none", "reps": reps, "label": label, "open_ms": 20}
    d.update(kw)
    return d


def _kick(label, reps, set_kicker=None, no_bump=False, kick=False):
    return {"op": "kicker", "set_kicker": set_kicker, "no_bump": no_bump, "kick": kick, "reps": reps, "label": label}


TOOL_ARGS_GD = ["probe", "--temps", "8", "--pixels", "--tri", "vtxuse", "--width", "64", "--height", "64", "--vtx-coords", "2",
                "--dump-render", "$W/dump", "--slot", "pixel=$S/pix_green.bin", "$S/dd-p1__0.bin"]
TOOL_ARGS_PX = ["probe", "--tri", "pixel", "--temps", "32", "--width", "16", "--height", "16", "--tri-full", "$S/pix_green.bin"]
# L1 g-dd dd-p1 (closing3/r3-geo/out/g-dd/raw.sha256) and L2 q-t t-ctl-green-16x16 (closing3/r3-pixel/out/.../q-t), kept outputs
GD_FROZEN = {"lines_sha256": "e4eee6634cdfd55524b73effb69dec99135e66d75280092dd19b3b2b88355fe9",
             "param_sha256": "4b8fec7532b896d5723636912c8b07c2ad7bb129fd2b34c8d6877db4f9ac0552",
             "tadata_sha256": "e05c220a2ed1f6b353aed82d157117a97648a4a5c74ba82bfce5550bd75cda4c",
             "o0_line": "o0 mixed 0xff203040 x3622 0xff00ff00 x474", "rc": 0}
PX_FROZEN = {"o0_line": "o0 0xff00ff00 (256 of 256)", "status2": [0x400, 0x400], "rc": 0}

ROW_SPEC = {
    "k0f": {"F0": {"op": "defaults", "reps": 1, "label": "control"}},
    "k0t": {"GD": {"op": "tooljob", "tool": "r1", "args": TOOL_ARGS_GD, "frozen": GD_FROZEN, "reps": 1, "label": "control"},
            "PX": {"op": "tooljob", "tool": "r1", "args": TOOL_ARGS_PX, "frozen": PX_FROZEN, "reps": 1, "label": "control"}},
    "k0c": {"C0": {"op": "alias2", "cmd": 0, "reps": 1, "label": "control"},
            "C1": {"op": "alias2", "cmd": CMD_WORD65, "w65": {"k": 1, "or": 0x00800000}, "reps": 1, "label": "control"}},
    "k0h": {"H0": {"op": "holdsig", "hold": False, "reps": 1, "label": "control"},
            "H1": {"op": "holdsig", "hold": True, "reps": 1, "label": "control"},
            "G0": _kick("control", 1, kick=True)},
    "f": {"E0": _act(0, 0, 0, "control", 1),
          "FC4": _act(1, ACT_CONT4, 1, "control", 2),
          "FB": _act(1, ACT_BOTH, 1, "heldout", 2, run_if="all_kept:FC4:1"),
          "FCF": _act(1, ACT_CFI, 1, "heldout", 2, run_if="all_kept:FB:1"),
          "FPH": _act(1, ACT_PHAS, 1, "heldout", 2, run_if="all_kept:FB:1")},
    "t": {"E0": _act(0, 0, 0, "control", 1),
          "T1": _act(1, ACT_STR_TAIL, 1, "control", 2),
          "T2": _act(1, ACT_STR_END, 1, "heldout", 2, run_if="all_kept:T1:1")},
    "kb": {"Q0": _kick("fit", 3),
           "Q1": _kick("heldout", 3, set_kicker=KICKER_WORD),
           "Q2": _kick("heldout", 3, set_kicker=KICKER_WORD, kick=True),
           "Q3": _kick("heldout", 3, no_bump=True, kick=True)},
    "e2b": {"R": {"op": "pawrite", "cmd": 1, "marker": None, "reps": 3, "label": "fit"},
            "S": {"op": "pawrite", "cmd": 2, "marker": PW_MARK["s"], "reps": 1, "label": "control"},
            "C4": {"op": "pawrite", "cmd": 4, "marker": PW_MARK["c4"], "reps": 3, "label": "heldout"},
            "C5": {"op": "pawrite", "cmd": 5, "marker": PW_MARK["c5"], "reps": 3, "label": "heldout"},
            "C6": {"op": "pawrite", "cmd": 6, "marker": PW_MARK["c6"], "reps": 3, "label": "heldout"},
            "Z67": {"op": "pawrite", "cmd": 2, "marker": PW_MARK["z67"], "reps": 1, "label": "control"},
            "Z68": {"op": "pawrite", "cmd": 3, "marker": PW_MARK["z68"], "reps": 1, "label": "control"}},
    "e3h": {"HR": {"op": "clear_host", "reps": 3, "label": "heldout"}},
    "e3a": {"FR": {"op": "clear_fw", "reps": 3, "label": "heldout"}},
    "e3b": {"B0": {"op": "skip3", "skip": 0, "reps": 3, "label": "control"},
            "B1": {"op": "skip3", "skip": 1, "reps": 1, "label": "heldout"},
            "B2": {"op": "skip3", "skip": 1, "fw_clear": True, "reps": 1, "label": "heldout", "run_if": "all_kept:B1:1"}},
}
ROW_ORDER = {st: list(rows) for st, rows in ROW_SPEC.items()}
# the firmware `str` register indices (byte offset / 4) each blob may carry (the landed verifier allows #69, #77, #691 and nothing else)
STR_OF = {"ring_timer": [691, 691], "strclr": [69], "ring_skip3": [77]}
CONT4_BLOBS = ("ring_exit",)               # blobs with a `@patch cont4` triple: the arm line must name a non-zero exit index
# stage k0f: every new debugfs file and the default it reads right after a reset (fork resgx545-r3, commits 6 to 10)
K0F_DEFAULTS = {"kick_no_bump": "N", "render_rgn_arrays": "0x00000001", "render_pb_pages": "0x00000422", "hold_recovery": "N"}
K0F_FILES = ("kicker", "kick_no_bump", "kregnow", "render_rgn_arrays", "render_pb_pages", "hold_recovery", "own_code", "own_arm", "own_res",
             "regs", "status", "miscinfo", "reset", "load", "boot")
K0F_KREGNOW_ROWS = 6                       # clkgatectl2, host enable2, host enable, dpm task fields, bif ctrl, bif int stat (the two clear rows are write-only)
K0F_KREGNOW_ABSENT = (0x0114, 0x0134)       # never shown when the file is read
K0F_KREGNOW_PRESENT = (0x0c00, 0x0c04)
RUN_IF_RE = r"^all_kept:([A-Za-z0-9]+):(\d)$"


def word65(spec, K):
    """The sa65 word of a row for the count byte K (None: no word)."""
    if not spec:
        return None
    if "lit" in spec:
        return spec["lit"]
    return ((K & 0xFF) << 24) | spec["or"]


def rep_name(row, k):
    return row.lower() + ("" if k == 0 else f"-r{k + 1}")


def signed8(v):
    """A difference of two 8-bit offsets as -128..127."""
    return ((v + 128) & 0xFF) - 128


# ---- readers of the two debugfs dumps (stdlib only: the laptop runner and the Mac scorer both use them) -----------------------
import re as _re  # noqa: E402


def parse_regs(text):
    """({reg offset: value}, {hostctl dword: value}, [ccbctl dword 0, dword 1] or None) from a `regs` file.  ccbctl[0] is the
    kernel's write offset (= the count byte K of the events), ccbctl[1] the EDM's read offset (E537 read 3 after 2: read = write + 1)."""
    out, hc, cc = {}, {}, {}
    for line in text.splitlines():
        m = _re.match(r"reg (0x[0-9a-f]+) (0x[0-9a-f]+)$", line)
        if m:
            out[int(m.group(1), 16)] = int(m.group(2), 16)
        m = _re.match(r"hostctl (0x[0-9a-f]+) (0x[0-9a-f]+)$", line)
        if m:
            hc[int(m.group(1), 16) // 4] = int(m.group(2), 16)
        m = _re.match(r"ccbctl (0x[0-9a-f]+) (0x[0-9a-f]+)$", line)
        if m:
            cc[int(m.group(1), 16) // 4] = int(m.group(2), 16)
    return out, hc, ([cc.get(0), cc.get(1)] if cc else None)


def parse_status(text):
    """({reg: value}, {hostctl dword: value}, [ccbctl 0, ccbctl 1] or None, ccb_sent or None) from a `status` file (the dump the
    landed hang_dump keeps as NAME-status.txt: `reg 0x008 = 0x...`, `hostctl[ 8]: bb bb ...` eight dwords a row, `ccbctl[ 0]: ...`)."""
    out, hc, cc, sent = {}, {}, {}, None
    for line in text.splitlines():
        m = _re.match(r"reg (0x[0-9a-f]+) = (0x[0-9a-f]+)$", line)
        if m:
            out[int(m.group(1), 16)] = int(m.group(2), 16)
            continue
        m = _re.match(r"(hostctl|ccbctl)\[\s*(\d+)\]:\s+((?:[0-9a-f]{2}\s*)+)$", line)
        if m:
            bs = bytes(int(x, 16) for x in m.group(3).split())
            first = int(m.group(2))
            for i in range(len(bs) // 4):
                v = int.from_bytes(bs[4 * i:4 * i + 4], "little")
                (hc if m.group(1) == "hostctl" else cc)[first + i] = v
            continue
        m = _re.search(r"ccb_sent (\d+)", line)
        if m:
            sent = int(m.group(1))
    return out, hc, ([cc.get(0), cc.get(1)] if cc else None), sent

