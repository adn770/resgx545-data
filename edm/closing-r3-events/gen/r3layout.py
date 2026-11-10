# SPDX-License-Identifier: MIT
"""R3-events layout (S2b's s2layout.py plus the words of alias.s and ring_skip.s): the results page (own_res, 1024
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
          CMD_RESTORE63: ["sa63"], CMD_READ: []}
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
