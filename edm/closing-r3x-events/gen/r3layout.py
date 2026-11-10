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
# R3x additions (round 3, L3, session of stages h, c, e, d).  Everything the generator, the runner, the scorer and the guard
# must agree on lives here, once.
# =====================================================================================================================
EXPECT_SRCV = "B21FDA82BD5E5CB5A627E3B"      # the module this session is prepared for (preflight: loaded = installed = this)
STAGES = ["h", "c", "e", "d"]
BLOB_OF = {"h": "ring_hold", "c": "alias2", "e": "ring_end", "d": "alias2"}
ARM_OF = {"h": "slots=0xf entry=0,1,2,3", "c": "slots=0x1 entry=0", "e": "slots=0xf entry=0,1,2,3", "d": "slots=0x1 entry=0"}
GATE_OF = {"c": "h", "e": "c", "d": "e"}
STOP_BUDGET = {"h": 0, "c": 1, "e": 1, "d": 1}   # stops a stage may take and go on; the next one ends it (exit 8).  c, e, d: the second
                                 # stop ends the stage, cap 2 (R3-E2); h: no stop is expected, the first ends it (cap 1, the design table)
PER_JOB_RESET = {"h": True, "c": False, "e": False, "d": True}   # reset + arm before every job (h, d) or once per stage (c, e)

# alias2.s (stages c, d): the commands of alias.s (1-7, 9) and three more; the host's words
W65, W64 = 9, 10                 # dwords: sa65's word (cmd 10, 11), sa64's word (cmd 11)
NPASS = 7                        # cmd 12: passes still to write sa64 = pa0 & ~2 (the host writes N, the task counts down)
CMD_WORD65, CMD_E537, CMD_RUN64 = 10, 11, 12
CMD_SA2 = dict(CMD_SA)
CMD_SA2.update({CMD_WORD65: ["sa65"], CMD_E537: ["sa63", "sa64", "sa65"], CMD_RUN64: ["sa64"]})
SA_ALLOWED2 = {"sa63", "sa64", "sa65"}
WR_X = WR + 9                    # cmd 11's extra record: sa63 written, sa63 read back, sa64 written, sa64 read back
WR_X_FIELDS = ["sa63_w", "sa63_rb", "sa64_w", "sa64_rb"]

# ring_end.s (stage e): ring_skip.s's ring plus KIND, ACT and the acted pass; COUNT and ACTED are ring_skip's SKIP and SKIPPED
KIND, ACT = 9, 10                # KIND 1 plain tick pass, 2 kick pass; ACT 1 own end (idf, wdf, nop.end), 2 tail call cont2 (slot 2)
COUNT, ACTED = SKIP, SKIPPED     # dwords 7, 8: passes still to act on (host writes), passes acted on (task counts)
TAIL_FLAG = 4                    # an acted pass's rung flag: 3 own end (SKIP_FLAG), 4 tail call to the fast-path task of slot 2
RING_FLAGS = (0, 1, SKIP_FLAG, TAIL_FLAG)
ACT_SLOT = 2                     # R-2: slot 2 (0xace) is the shortest path to the exit with no group bit set (17 + 5 instructions)

# E537's writer (cmd 4 of state3.s; b2-markers.json, first writer; E537 correction note): the words D4 re-runs
E537 = {"sa63": 0xD7C5F5AE, "sa64": 0xB0150D9D, "sa65": 0xB009C5DC, "r20": 0xF8A4AC80, "r21": 0xFCF393C8, "i0": 0xA958E53C,
        "i1": 0xD90C0733}
E537_SA65_BIT8_CLEAR = 0xB009C4DC
# pa1 bits some code of the ukernel tests (R-4: the union of the masks is 0x00780790 = bits 4, 7, 8, 9, 10, 19, 20, 21, 22):
# a bit outside it has no code of any kind (C3's "no handler" bits)
TESTED_PA1_MASK = 0x00780790
ASSERT_WORD = 0xAD002600         # HostCtl dword 14 after the routine at 0x0-0x5 ran (0a, R-3); 0 on every healthy and E793 dump
HC_ASSERT_DWORD = 14
P3_MS = 500                      # the kernel's miscinfo timeout: a read that takes this long or fails is "not answered"

# the rows (one source for the generator, the runner, the guard and the scorer).  w65: None, {"lit": v} or {"k": 1, "or": v}
# (v | the count byte K read from ccbctl[0] before the job, << 24).
ROW_SPEC = {
    "h": {"H0": {"hold": False, "reps": 3, "label": "control"}, "H1": {"hold": True, "reps": 3, "label": "heldout"}},
    "c": {"C0": {"cmd": 0, "reps": 2, "label": "fit"},
          "C1": {"cmd": CMD_WORD65, "w65": {"k": 1, "or": 0x00800000}, "reps": 3, "label": "heldout"},
          "C2": {"cmd": CMD_WORD65, "w65": {"lit": 0xB0000000}, "reps": 2, "label": "heldout"},
          "C3": {"cmd": CMD_WORD65, "w65": {"k": 1, "or": 0x0001C04C}, "reps": 2, "label": "heldout"},
          "C4": {"cmd": CMD_WORD65, "w65": {"k": 1, "or": 0x00080000}, "reps": 2, "label": "heldout"},
          "C5": {"cmd": CMD_RUN64, "npass": 50, "reps": 2, "label": "heldout"}},
    "e": {"E0": {"kind": 0, "act": 0, "count": 0, "trigger": "none", "reps": 2, "label": "control", "open_ms": 20},
          "X1": {"kind": 1, "act": 2, "count": 1, "trigger": "none", "reps": 2, "label": "heldout", "open_ms": 20},
          "X20": {"kind": 1, "act": 2, "count": 20, "trigger": "none", "reps": 2, "label": "heldout", "open_ms": 30,
                  "run_if": "all_kept:X1:2"},
          "B3": {"kind": 2, "act": 1, "count": 1, "trigger": "miscinfo", "reps": 1, "label": "heldout", "open_ms": 40}},
    "d": {"D0": {"cmd": 0, "reps": 1, "label": "control"},
          "D1": {"cmd": CMD_WORD65, "w65": {"lit": E537_SA65_BIT8_CLEAR}, "reps": 3, "label": "heldout", "rep_if": "all_kept:D1:1"},
          "D2": {"cmd": CMD_WORD65, "w65": {"k": 1, "or": 0x100}, "reps": 1, "label": "heldout"},
          "D3": {"cmd": CMD_WORD65, "w65": {"lit": E537["sa65"]}, "reps": 1, "label": "fit"},
          "D4": {"cmd": CMD_E537, "reps": 1, "label": "heldout", "run_if": "all_kept:D3:1"}},
}
ROW_ORDER = {st: list(rows) for st, rows in ROW_SPEC.items()}


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
