# SPDX-License-Identifier: MIT
"""read.py: r14-dpm's reader of one job's output (the tool's text and regtimeline's block over the
one register 0x0748).

  n       the timeline's lines (a line per change of 0x0748)
  clr     the lines from the command's start on with 0x0748 bit 2 clear
  pulses  the runs of consecutive such lines (a run is one clear event)
  widths  the clear runs' lengths in ns (to the next line, or to the end of the capture)
  period  the sampling period in ns: the capture's length / its samples (`end` over `samples`)
  short   1 when the period is at most SHORT_NS, the premise of R-PULSE (a pulse the sampler can see)
A capture cut mid-line, or one without 0x0748 or its samples, reads nothing (void).
Samples before the command's `start` (the 0.3 s lead) are not events of the job."""
from __future__ import annotations

SHORT_NS = 1000          # E1032's 16-register period was 7.5 us; 3 registers read 1.4 us


def hx(s: str) -> int:
    return int(s, 16)


def parse(text: str):
    """(regs, rows, start, end, samples) of the first timeline block; start None for a cut line."""
    regs, rows, start, end, samples = None, [], 0, 0, 0
    for ln in text.splitlines():
        if ln.startswith("timeline: regs"):
            if regs is not None:
                break
            p = ln.split()
            i = p.index("samples")
            regs = [hx(x) for x in p[2:i]]
            samples = int(p[i + 1])
            if "start" in p:
                start = int(p[p.index("start") + 1])
            if "end" in p:
                end = int(p[p.index("end") + 1])
            continue
        if regs is not None and ln.startswith("tl "):
            p = ln.split()
            if len(p) != 2 + len(regs):
                return regs, rows, None, end, samples
            rows.append((int(p[1]), dict(zip(regs, (hx(x) for x in p[2:])))))
    return regs, rows, start, end, samples


def reading(text: str) -> dict:
    regs, rows, start, end, samples = parse(text)
    if start is None:
        return dict(void="capture cut")
    if not regs or not rows or 0x748 not in regs or samples <= 0 or end <= 0:
        return dict(void="no timeline")
    period = int(end / samples)
    clear = [(t >= start and not v[0x748] & 4) for t, v in rows]
    pulses = sum(1 for i, c in enumerate(clear) if c and (i == 0 or not clear[i - 1]))
    widths = []
    for i, c in enumerate(clear):
        if c and (i == 0 or not clear[i - 1]):
            j = i
            while j + 1 < len(rows) and clear[j + 1]:
                j += 1
            widths.append((rows[j + 1][0] if j + 1 < len(rows) else end) - rows[i][0])
    return dict(void=None, n=len(rows), clr=sum(clear), pulses=pulses, widths=widths, period=period,
                short=int(period <= SHORT_NS))


def words(r: dict) -> dict:
    """The `k=v` reading of the runner's hooks (run/hooks.sh rd_words), from a reading."""
    if r.get("void"):
        return {}
    return {"clr": str(r["clr"]), "pulses": str(r["pulses"]), "period": str(r["period"]),
            "short": str(r["short"])}
