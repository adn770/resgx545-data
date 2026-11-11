# SPDX-License-Identifier: MIT
"""r4tl.py: the timeline reader of the Q082 stages of R4-pixel (standard library only).  It reads the regtimeline a job kept inside
NAME.txt.gz (registers 0x0008 CLKGATESTATUS, 0x0118 EVENT_STATUS2, 0x012c): the burst B, a tile's time, the longest run of the TA's
clocks L, the time of bit 6 and bit 7, and applies the two frozen rules of round 4's offline readings (resgx545 5a13042: hw_spec
EVENT_STATUS2 readings of 2026-11-11, E805 to E807 corrections, sgx-pipe `events::status2_bit6`):

  BIT7 (TA, vertex loops)  with L the longest run of samples whose 0x0008 equals 0x000ccff8: bit 7 set iff L >= 129.5 us; L below
                           122 us is clear and L above 136 us is set, in between is the EDGE (not scored).  Once set, bit 7 shows
                           118 to 138 us after that run began.  [data on E807's 74 jobs: SEMI; the rule is held out by q4-v]
  BIT6 (pixel, fills)      tau = (B - 60.2) / 4 (a tile's time of a 64 x 32 fill, four tiles): clear below 118 us, set above 132 us,
                           EDGE between (the same edge as sgx-pipe's events::status2_bit6, which the test reads from the source).

Edges and the 118..138 latch window are frozen here.  A run's length is (first sample after the run) - (first sample of the run).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import re  # noqa: E402

IDLE_CG, TICK_CG, TA_CG = 0x20, 0xccfa0, 0xccff8
BIT7_EDGE = (122.0, 136.0)          # L us: clear below, set above, the edge between
BIT7_THRESHOLD = 129.5
LATCH7 = (118.0, 138.0)             # us from the start of the run to bit 7 in every set job
BIT6_EDGE = (118.0, 132.0)          # tile time us
B0, TILES = 60.2, 4.0
CLEAR, SET, EDGE = "clear", "set", "edge"


def parse(txt):
    """(regs, rows): the regs of the `timeline:` header ('0x0008', ...) and rows (t_ns, [values]) of the `tl` lines, or (None, [])."""
    m = re.search(r"^timeline: regs (.*?) samples", txt or "", re.M)
    if not m:
        return None, []
    rows = []
    for ln in txt.splitlines():
        if ln.startswith("tl "):
            p = ln.split()
            try:
                rows.append((int(p[1]), [int(x, 16) for x in p[2:]]))
            except ValueError:
                return None, []
    return m[1].split(), rows


def _idx(regs, name):
    return regs.index(name) if regs and name in regs else None


def ta_run(txt):
    """{'L', 'start', 'end', 'bit7', 't7', 'd7', 'n'} of the longest contiguous run of samples with 0x0008 == 0x000ccff8 (L = 0.0 and
    start None if there is none), or None if the text holds no timeline with 0x0008 and 0x0118.  d7 = t7 - start (us) or None."""
    regs, rows = parse(txt)
    i8, i118 = _idx(regs, "0x0008"), _idx(regs, "0x0118")
    if i8 is None or i118 is None or not rows:
        return None
    best, cur = None, None
    for t, v in rows:
        if v[i8] == TA_CG:
            if cur is None:
                cur = t
        elif cur is not None:
            if best is None or t - cur > best[1] - best[0]:
                best = (cur, t)
            cur = None
    if cur is not None:                       # a run still open at the last sample: its length stops there
        t = rows[-1][0]
        if best is None or t - cur > best[1] - best[0]:
            best = (cur, t)
    t7 = next((t for t, v in rows if v[i118] & 0x80), None)
    if best is None:
        return dict(L=0.0, start=None, end=None, bit7=t7 is not None, t7=None if t7 is None else t7 / 1000.0, d7=None, n=0)
    return dict(L=(best[1] - best[0]) / 1000.0, start=best[0] / 1000.0, end=best[1] / 1000.0, bit7=t7 is not None,
                t7=None if t7 is None else t7 / 1000.0, d7=None if t7 is None else (t7 - best[0]) / 1000.0,
                n=sum(1 for t, v in rows if best[0] <= t < best[1]))


def bit7_rule(L):
    """The frozen TA rule: CLEAR (L < 122), SET (L > 136) or EDGE."""
    return CLEAR if L < BIT7_EDGE[0] else SET if L > BIT7_EDGE[1] else EDGE


def tile_time(B):
    return (B - B0) / TILES


def bit6_rule(tau):
    """The frozen fill rule on a tile's time: CLEAR below 118 us, SET above 132 us, EDGE between."""
    return CLEAR if tau < BIT6_EDGE[0] else SET if tau > BIT6_EDGE[1] else EDGE


def verdict(rule, bit):
    """True / False / None (edge: not scored) for an observed bit against the rule's word."""
    if rule == EDGE:
        return None
    return (rule == SET) == bool(bit)
