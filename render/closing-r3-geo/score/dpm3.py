"""DPM readers of R3, the Python twin of run/dpm_read.awk (the laptop-side runner reads the same quantities in awk and picks the
next bisect cell from them; tests/test_awk_reader.py makes both read the same jobs).  Pure functions over a kept stage directory.

A job's reading (as R1's `e1_measure`, unchanged rules):
  nparts   partial renders = rising edges of 0x0658 bit 0
  thr0     the 0x0724 low half at the first partial render's start (the first abort's status)
  peaks    the peak 0x0724 low half of each TA run (a stretch outside a partial render)
  reach    the second TA run's peak reaches thr0 (the run after the first abort climbed to the same ceiling)
  valid    reach and nparts > 1 (R1's rule: a single abort whose retry does not reach thr0 says nothing about the raise)
  raised   dword 38 of the control block (buf09) is 0x20
  counts   0x072c low half in the sample just before each abort's rising edge (H-last's variable)
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

from r1lib import Kept, knob_value, reg_series, timeline  # noqa: E402


def counts_before_aborts(tl):
    """[count] before each rising edge of 0x0658 bit 0, the whole-job peak, the second-run count and the ambiguity flag (the
    count changed between the last two samples before the last edge)."""
    if not tl or "0x072c" not in tl[0]:
        return None
    s58, s2c = reg_series(tl, "0x0658"), reg_series(tl, "0x072c")
    edges = [i for i in range(len(s58)) if s58[i] & 1 and (i == 0 or not s58[i - 1] & 1)]
    before = [s2c[max(i - 1, 0)] & 0xffff for i in edges]
    amb = bool(edges and edges[-1] >= 2 and s2c[edges[-1] - 1] != s2c[edges[-1] - 2])
    return dict(before=before, peak=max((v & 0xffff) for v in s2c), amb=amb)


def runs_of(tl):
    """(status at each partial render's start, peak status of each TA run), as r1lib.runs."""
    regs, rows = tl
    ip, ist = regs.index("0x0658") + 1, regs.index("0x0724") + 1
    prs, peaks, cur, inpr = [], [], 0, False
    for r in rows:
        if r[ip] & 1:
            if not inpr:
                prs.append(r[ist] & 0xffff)
                peaks.append(cur)
                cur = 0
                inpr = True
            continue
        inpr = False
        cur = max(cur, r[ist] & 0xffff)
    peaks.append(cur)
    return prs, peaks


def read_job(k: Kept, n: str, knob_proof: bool = True) -> dict:
    """The reading of one job, or {'void': reason, ...}.  The knob proof is the job's own first 0x0624 value against the P that
    cases.tsv recorded (P - 0x22); a P of "-" skips it."""
    c = k.case(n)
    P = c.get("P", "-")
    v = k.void(n)
    if v:
        return dict(void=v, P=P)
    txt = k.out(n)
    tl = timeline(txt)
    if tl is None:
        return dict(void="no timeline", P=P)
    got = knob_value(tl, txt)
    if got is None:
        return dict(void="no status rise: the job's 0x0624 value is unknown", P=P)
    if knob_proof and P not in ("-", "") and got != int(P, 16) - 0x22:
        return dict(void=f"knob did not land: 0x0624 {got:#x}, wanted {int(P, 16) - 0x22:#x}", P=P)
    ctl = k.buf09(n)
    if ctl is None:
        return dict(void="no control block kept", P=P)
    prs, peaks = runs_of(tl)
    thr0 = prs[0] if prs else None
    reach = bool(thr0 is not None and len(peaks) > 1 and peaks[1] >= thr0)
    cnt = counts_before_aborts(tl)
    return dict(void=None, P=P, knob=got, tl=tl, txt=txt, nparts=len(prs), thr0=thr0, peaks=peaks, reach=reach,
                valid=bool(reach and len(prs) > 1), raised=ctl[38] == 0x20, dw36=ctl[36], dw37=ctl[37], dw38=ctl[38], cnt=cnt,
                need=max(peaks) if peaks else None)


def cls_of(j: dict) -> str:
    """R raise, N none, V void."""
    if j.get("void") or not j["valid"]:
        return "V"
    return "R" if j["raised"] else "N"


# ------------------------------------------------------------------------------------------------ the bisect
def bracket(obs: dict):
    """obs {thr0: 'R'|'N'|'V'} -> (lo, hi, why): lo the highest raise, hi the lowest silent cell above it.  why is "" for a usable
    bracket (hi - lo > 1), else the reason the bisect cannot go on: 'closed' (exact), 'no raise', 'no silent cell above', or
    'not monotone' (a silent cell below a raise)."""
    R = [t for t, c in obs.items() if c == "R"]
    N = [t for t, c in obs.items() if c == "N"]
    if not R:
        return None, None, "no raise"
    lo = max(R)
    if any(t < lo for t in N):
        return lo, None, "not monotone"
    up = [t for t in N if t > lo]
    if not up:
        return lo, None, "no silent cell above"
    hi = min(up)
    return lo, hi, ("closed" if hi - lo <= 1 else "")


def pick(obs: dict):
    """The next bisect cell (thr0) or (None, why): the integer midpoint lo + (hi - lo) // 2; a void cell inside the bracket ends the
    bisect."""
    lo, hi, why = bracket(obs)
    if why:
        return None, why
    if any(c == "V" and lo < t < hi for t, c in obs.items()):
        return None, "void cell inside the bracket"
    return lo + (hi - lo) // 2, ""


def flip_of(obs: dict):
    """(last raise, first silent above it, kind): kind 'exact' when adjacent, 'bracket' when not, 'none' otherwise."""
    lo, hi, why = bracket(obs)
    if why == "closed":
        return lo, hi, "exact"
    if why == "":
        return lo, hi, "bracket"
    return lo, hi, why
