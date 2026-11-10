# SPDX-License-Identifier: MIT
"""C3 layout (L3b, Q158 + Q124's residual): the results page (own_res, 1024 dwords), the jobs, the limits.

One module, standard library only, imported by the generator (Mac), the laptop runner (copied to ~/r3xc3/gen/) and the scorer
(Mac).  Frozen with everything else (run/freeze_c3.sh).  A copy of the protocol words of closing2/r3-events/gen/r3layout.py
(CMD, STATE, RUNID, ECHO, the tick, the stop signature) and the words of start.s, the only task of C3.

start.s (one entry, own_arm slots=0x1 entry=0, as alias.s):
  cmd 0  a plain pass: counted, the closed task called at once
  cmd 1  the WRITER: sa63 = the host's marker, r20, r21, i0, i1 = the host's markers, p0..p3 = the host's flags, the record, the
         reader armed (cmd = 9), the closed task called.  The ONLY sa register it writes is sa63 (R2-1 b: sa63, sa64, sa65 only;
         sa100, sa127, sa20 and sa24 of Q158's text are READ, never written)
  cmd 9  the READER: stores the entry values of pclink, p0..p3, r20, r21, i0, i1, then sa63, sa64, sa65, sa100, sa127, sa20,
         sa24, pa0..pa2 and the pass count; cmd = 0
"""

PAGE_DWORDS = 1024
INITFILL = 0xDEADC0DE
MAGIC = 0x4E574F53

CMD, STATE, RUNID, OVERLAP, ECHO = 1, 2, 3, 4, 5
WINDOW = 6                       # unused by start.s; the runner's arm check reads it (0 after the arm)
STATE_IDLE, STATE_BUSY, STATE_DONE = 0, 1, 2

TICK_UNITS = 25000
TIMER_HZ = 24.9366e6
TICK_PA0 = 0x2

# start.s words
A_M = 11                         # the marker for sa63 (cmd 1)
A_RI = 12                        # r20, r21, i0, i1 markers (dwords 12..15)
PF = 24                          # p0..p3 flags at the writer's tail call (dwords 24..27; nonzero = set)
A_PASS = 20                      # passes of the task (every pass, any command)
CMD_W, CMD_READ = 1, 9
WR = 64                          # the writer's record, 16 dwords:
WR_FIELDS = ["pa0", "pa1", "pa2", "sa63_before", "sa63_written", "sa63_readback"]
WR_DONE = WR + 15                # the arm block stores the run id here: a flag that stays (cmd 9 lasts one tick)
RD = 96                          # the reader's record, 24 dwords:
RD_FIELDS = ["pclink", "p0", "p1", "p2", "p3", "r20", "r21", "i0", "i1", "sa63", "sa64", "sa65", "sa100", "sa127", "sa20",
             "sa24", "pa0", "pa1", "pa2", "pass"]
RD_N = 24
RD_PASS = RD_FIELDS.index("pass")

# What each start.s command may write (the guard compares the assembled code with this): sa63 in the writer and nothing else.
CMD_SA = {CMD_W: ["sa63"], CMD_READ: []}
SA_ALLOWED = {"sa63"}            # (R2-1 b allows sa63, sa64, sa65; C3 needs only sa63)
SA_READ = ("sa63", "sa64", "sa65", "sa100", "sa127", "sa20", "sa24")

# jobs
ROWS = ("S0", "N", "F", "L", "R")
PERTURB = {"S0": "none", "N": "gap", "F": "fill", "L": "reload", "R": "reset"}
GAP_MS = 1200                    # E536's gap reader
# the p flags of the writer by repetition (p0, p1, p2, p3): E536's (0, 0, 1, 1); p2 = p3 = 0 with p1 = 1; p2 = 1, p3 = 0
FLAGS = [(0, 0, 1, 1), (0, 1, 0, 0), (1, 0, 1, 0)]

# the stop signature (E537, p1130-b2-variants/tailpair-stop1-regs.txt)
REG_CLKSTAT, REG_SERV_EVENT, REG_EVENT_TIMER, REG_EVENT_STATUS = 0x0008, 0x0B14, 0x0ACC, 0x012C
REG_STATUS2, REG_BIF_INT, REG_TIMER = 0x0118, 0x0C04, 0x0144
SIG_REGS = (REG_CLKSTAT, REG_SERV_EVENT, REG_EVENT_TIMER, REG_EVENT_STATUS, REG_STATUS2, REG_BIF_INT, 0x0B20, 0x0C08)
CLK_IDLE = 0x20
E537_SIG = {"clkstat": 0x000CCFA0, "serv_event": 0x000009E0, "event_timer": 0x01038EC3, "event_status": 0x20000000}
SERV_EMPTY_BIT = 16

# E533's markers (state.s), what the controls of E536 read after a reset and a reload: i0, i1, sa100, sa127 (E536's claim)
E533 = {"i0": 0xB5000020, "i1": 0xB5000021, "sa100": 0xA5000064, "sa127": 0xA500007F}


def reg_of(name):
    """sa63 -> 63."""
    return int(name[2:])
