#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""Phase 11.35: what the temps-fresh runs read, job by job, against each job's own marker.

    recompute_temps.py TABLE.toml DATADIR

TABLE is the table that ran (probes/usse/temps-fresh-{a,b,c}.toml), DATADIR its dataset
directory (DATA/usse/temps-fresh-a). For every job, in the order it ran: the marker half it wrote
(the upper half of its first marker, or the whole marker of table c), the values it read (pixel
and shown dwords), how many carry its half, how many another half (and whose: the half of an
earlier job of the run, or a leftover of an older run), how many have a register number other than
the one they were stored for (a wrap), the dwords the tool counted and did not show, and the job
time. A job that wrote no marker to the register it reads (the i0-i3 job reads r123) reports
what it read.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "usse-asm"))
import probe  # noqa: E402

WRITE = re.compile(r"mov\.skipinv r(\d+), #0x([0-9A-Fa-f]{8})")
STORE = re.compile(r"stad \[r1,\+#(\d+)\], (\w+)")


def jobs(table: pathlib.Path):
    src = ROOT / "probes" / "usse" / "templates"
    for p in probe.load(table):
        tmpl = (src / p.source).read_text()
        for i, case in enumerate(p.cases):
            yield p, i, probe.render(p, case, tmpl)


def main(argv: list[str]) -> int:
    table, data = pathlib.Path(argv[0]), pathlib.Path(argv[1])
    halves: list[int] = []
    totals = {"own": 0, "earlier": 0, "other": 0, "wrap": 0, "jobs": 0}
    for p, i, text in jobs(table):
        raw = (data / p.name / "raw.txt").read_text()
        obs = probe.parse(raw)[f"{p.name}__{i}"]
        t = re.search(rf"probe {p.name}__{i}: job time: (\d+) us", raw)
        writes = {int(r): int(v, 16) for r, v in WRITE.findall(text)}
        regs = {r: v for r, v in writes.items() if r >= 2 and v >> 16 != 0x5CAF}
        half = (min(regs.values()) >> 16) if regs and p.source == "temps.s" else None
        if half is None and p.source == "temps_phas.s":
            half = int(p.cases[i][2], 0)         # the whole marker
        seen = ([("pixel", obs.o0)] if obs.o0 is not None else
                [("pixel", v) for v, _ in obs.mixed]) + \
            [(f"+0x{o:03x}", v) for o, v in obs.scratch]
        own = earlier = other = wrap = 0
        stores = {int(n): r for n, r in STORE.findall(text)}
        for k, (where, v) in enumerate(seen):
            if p.source == "temps_phas.s":
                own += v == half
                earlier += v != half and v in halves
                other += v != half and v not in halves
                continue
            reg = stores.get((int(where[3:], 16) // 4) if where != "pixel" else -1)
            if v >> 16 == half:
                own += 1
                if reg and reg.startswith("r") and v & 0xffff != int(reg[1:]) and where != "pixel":
                    wrap += 1
            elif v >> 16 in halves:
                earlier += 1
            else:
                other += 1
        if half is not None:
            halves.append(half)
        totals["jobs"] += 1
        for k, n in (("own", own), ("earlier", earlier), ("other", other), ("wrap", wrap)):
            totals[k] += n
        hv = f"0x{half:08x}" if half is not None and p.source == "temps_phas.s" else \
            (f"0x{half:04x}" if half is not None else "none")
        print(f"{len(halves):2} {p.name}[{i}] marker {hv}: pixel "
              f"{'mixed' if obs.o0 is None else f'0x{obs.o0:08x}'}, {len(obs.scratch)} dwords shown "
              f"+ {obs.more} more, own {own}, earlier-job {earlier}, other {other}, wrap {wrap}, "
              f"failed {obs.failed is not None}, time {t.group(1) if t else '?'} us")
    print(f"total: {totals['jobs']} jobs; values with the job's own half {totals['own']}, with "
          f"an earlier job's half {totals['earlier']}, other {totals['other']}, wrapped "
          f"{totals['wrap']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
