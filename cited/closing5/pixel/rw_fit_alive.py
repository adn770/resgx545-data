# SPDX-License-Identifier: MIT
"""Round 5 planning, offline (2026-11-12).  Q230 / E842: is the frozen analysis of g4-rw still alive?
The frozen rule (score/rwfam.py of render/closing-r4-pixel): a model counts only after 30 of 30 on the FIT
half.  19 FIT words were read (E842).  A frozen model that misses one of those 19 can never reach 30 of 30,
whatever the 11 unread FIT words are.  This script uses the FIT words ONLY (the HELD OUT words are not
touched: the frozen test stays clean if it is ever completed).  Standard library; imports the frozen rwfam.
  python -I rw_fit_alive.py > rw_fit_alive.out"""
import collections
import gzip
import pathlib
import re
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path.home() / "src/resgx545-data/render/closing-r4-pixel"
sys.path.insert(0, str(R4 / "score"))
import rwfam  # noqa: E402

rows = []
for ln in (R4 / "out/20261111-210423/score-g4-rw.txt").read_text().splitlines():
    m = re.match(r"(rw-\d+)\s+(\d)\s+(\S+)\s+(0x\w+)\s+(0x\w+)\s+(0x\w+|-)\s+(\S+)\s+(FIT|HELD OUT)\s", ln)
    if m:
        rows.append((m[1], int(m[2]), m[3], int(m[4], 16), int(m[5], 16), None if m[6] == "-" else int(m[6], 16), m[8]))
fit = [(w, got) for _, _, _, w, rz, got, half in rows if half == "FIT" and got is not None]
print(f"table rows parsed {len(rows)}; FIT words read {len(fit)}; RZ + 1 among them {sum(1 for _, _, _, w, rz, got, h in rows if h == 'FIT' and got is not None and got == rz + 1)}")
mods = rwfam.models()
best = []
alive = []
fam_best = collections.defaultdict(int)
for name, (fam, fn) in mods.items():
    n = rwfam.fits(fn, fit)
    best.append((n, name))
    fam_best[fam] = max(fam_best[fam], n)
    if n == len(fit):
        alive.append(name)
print(f"{len(mods)} frozen models; fitting all {len(fit)} read FIT words: {len(alive)} {alive}")
print("best per family (of %d):" % len(fit), dict(sorted(fam_best.items())))
print("top 10:", sorted(best, reverse=True)[:10])
