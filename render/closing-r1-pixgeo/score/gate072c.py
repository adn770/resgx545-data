"""The 0x072c gate (decision R2-13 b), evaluated offline over the kept files of a trial job.  run/lib_r1.sh gate_check
is the same rule in shell (the laptop-side decision); tests/test_gate.py feeds both the same synthetic jobs.

CR_DPM_GLOBAL_PAGE_STATUS (0x072c, read-only, glossary G0828, "DPM global-list pages: total and TA") has been seen as
0x10001, 0x40004, 0x50005 (E358, E438, E443): both halves are small page counts.  A trial job (u-ctl-1 with U = 19, then
u-ctl-2a with U = 29, each adding 0x072c to its register timeline) is CLEAN iff ALL of:
  G1  the job completed in the normal classes: class `ok` (rc 0, or rc 3 with "scene overflowed"), no hang/fault line;
  G2  its kernel-log slice (after the case marker, before any reset) holds no line but our own markers;
  G3  the timeline header lists 0x072c and the job has at least 10 timeline rows;
  G4  every 0x072c sample is plausible: not 0xffffffff, not 0xdeadbeef, high half <= 0x40, low half <= 0x40, and at
      least one sample has a non-zero low half (the register is alive, not stuck at 0);
  G5  the 0x0724 low-half peak equals the control's frozen U (the extra reads did not disturb the DPM);
  G6  a plain 64x64 triangle drew exactly right after the job WITHOUT a reset (the machine is healthy).
Only a pass of both trial jobs lets the remaining DPM jobs sample 0x072c; a fail leaves them without it (the stage goes
on: the gate protects the readings, and a hang or fault stops the stage anyway).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import re  # noqa: E402

MAX_PAGES = 0x40
MIN_ROWS = 10


def column(text, reg):
    """The hex strings of one register's column of the `tl` rows, or None if the header lacks it."""
    m = re.search(r"^timeline: regs (.*?) samples", text or "", re.M)
    if not m or reg not in m[1].split():
        return None
    i = m[1].split().index(reg)
    return [ln.split()[2 + i] for ln in (text or "").splitlines() if ln.startswith("tl ")]


def gate_check(txt, dmesg, cls, expect_u, health_first):
    """(clean, [reasons it is not])."""
    why = []
    if cls != "ok":
        why.append(f"G1: class {cls}")
    own = [ln for ln in (dmesg or "").splitlines() if ln.strip() and "resgx545" not in ln]
    if own:
        why.append(f"G2: kernel log lines in the job's slice: {own[:2]}")
    c72 = column(txt, "0x072c")
    c24 = column(txt, "0x0724")
    if c72 is None or c24 is None:
        why.append("G3: no 0x072c (or 0x0724) in the timeline header")
        return False, why
    if len(c72) < MIN_ROWS:
        why.append(f"G3: only {len(c72)} timeline rows")
    vals = [int(v, 16) for v in c72]
    bad = [f"{v:#x}" for v in vals if v in (0xffffffff, 0xdeadbeef) or v >> 16 > MAX_PAGES or v & 0xffff > MAX_PAGES]
    if bad:
        why.append(f"G4: implausible 0x072c values {sorted(set(bad))[:4]}")
    if not any(v & 0xffff for v in vals):
        why.append("G4: 0x072c never non-zero")
    peak = max((int(v, 16) & 0xffff for v in c24), default=0)
    if expect_u is not None and peak != expect_u:
        why.append(f"G5: the 0x0724 peak is {peak}, the control's U is {expect_u}")
    if not health_first:
        why.append("G6: the plain triangle did not draw right after the job without a reset")
    return not why, why
