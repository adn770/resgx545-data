# SPDX-License-Identifier: MIT
"""read.py: r13-dpm's reader of one job's output (the tool's text and regtimeline's block).

  nparts  the stretches of 0x0658 bit 0 (a partial render each; E1019's count)
  knob    0x0624 at the first line from `start` whose 0x0724 low half is not 0 (r8-ldpm's proof)
  clr     the lines with 0x0748 bit 2 clear
  pulses  the runs of consecutive such lines
  n       the timeline's lines
  gmax    the highest 0x072c high half (the global page count)
  hi10    the highest 0x0710 high half (STATUS2's, E1019's H0: 0)
  vals    {register: sorted distinct values} of 0x0700, 0x070c, 0x0710, 0x0720 to 0x0728
A capture cut mid-line, or one without the registers, reads nothing (void)."""
from __future__ import annotations

VALREGS = (0x700, 0x70C, 0x710, 0x720, 0x724, 0x728)


def hx(s: str) -> int:
    return int(s, 16)


def parse(text: str):
    """(regs, rows, start) of the first timeline block; start None for a cut line."""
    regs, rows, start = None, [], 0
    for ln in text.splitlines():
        if ln.startswith("timeline: regs"):
            if regs is not None:
                break
            p = ln.split()
            i = p.index("samples")
            regs = [hx(x) for x in p[2:i]]
            if "start" in p:
                start = int(p[p.index("start") + 1])
            continue
        if regs is not None and ln.startswith("tl "):
            p = ln.split()
            if len(p) != 2 + len(regs):
                return regs, rows, None
            rows.append((int(p[1]), dict(zip(regs, (hx(x) for x in p[2:])))))
    return regs, rows, start


def reading(text: str) -> dict:
    regs, rows, start = parse(text)
    if start is None:
        return dict(void="capture cut")
    need = (0x658, 0x624, 0x724, 0x72C, 0x748, 0x710)
    if not regs or not rows or any(r not in regs for r in need):
        return dict(void="no timeline")
    nparts, on = 0, False
    for _, v in rows:
        x = bool(v[0x658] & 1)
        nparts += x and not on
        on = x
    knob = next((v[0x624] for t, v in rows if t >= start and (v[0x724] & 0xFFFF) != 0), None)
    clear = [not v[0x748] & 4 for _, v in rows]
    pulses = sum(1 for i, c in enumerate(clear) if c and (i == 0 or not clear[i - 1]))
    vals = {r: sorted({v[r] for _, v in rows}) for r in VALREGS if r in regs}
    return dict(void=None, nparts=nparts, knob=knob, clr=sum(clear), pulses=pulses, n=len(rows),
                gmax=max((v[0x72C] >> 16) & 0xFFFF for _, v in rows),
                hi10=max((v[0x710] >> 16) & 0xFFFF for _, v in rows), vals=vals)


def words(r: dict) -> dict:
    """The `k=v` reading of the runner's hooks (run/hooks.sh rd_words), from a reading."""
    if r.get("void"):
        return {}
    out = {"nparts": str(r["nparts"]), "clr": str(r["clr"]), "pulses": str(r["pulses"]),
           "gmax": f"0x{r['gmax']:x}"}
    if r["knob"] is not None:
        out["knob"] = f"0x{r['knob']:x}"
    return out
