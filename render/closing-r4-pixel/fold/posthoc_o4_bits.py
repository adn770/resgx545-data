# SPDX-License-Identifier: MIT
"""Post hoc (2026-11-11, at the fold; not frozen, not a result): the low 6 bits, the tag and the marker of
every non-background word of p4-o4's kept images.  Run from anywhere with the scratch venv:
  python -I fold/posthoc_o4_bits.py > fold/posthoc_o4_bits.txt"""
import collections
import gzip
import pathlib
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R4 / "score"))
import r4lib as L  # noqa: E402

out = R4 / "out/20261111-205726/p4-o4"
tags_all = collections.Counter()
for f in sorted(out.glob("c-*.txt.gz")):
    g = L.rows_of(gzip.open(f).read().decode())
    low = collections.Counter(v & 0x3f for r in g for v in r if v != L.BG)
    mk = collections.Counter((v & 0xffff) >> 6 for r in g for v in r if v != L.BG)
    tags_all.update(v & 15 for r in g for v in r if v != L.BG)
    print(f.name[:-7], "low6", {hex(k): n for k, n in sorted(low.items())}, "marker", {hex(k): n for k, n in mk.most_common(2)})
print("tags over all jobs", dict(sorted(tags_all.items())))
