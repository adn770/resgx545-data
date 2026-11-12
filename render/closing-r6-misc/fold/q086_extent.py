# SPDX-License-Identifier: MIT
"""Post hoc (r6-misc fold, 2026-11-12): in each kept q086 job, the pixel values inside and outside the
rectangle the words' macrotile grid covers (B3 + B1 tiles of 32 x 16 per axis, gen/models.py's
coverage(), as the scorer prints it), from the job's --pixels rows.  Not frozen: read after the
verdict.  Usage: q086_extent.py ATTEMPT_DIR (out/20261112-144153)."""
import collections
import gzip
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "gen"))
sys.dont_write_bytecode = True
import models as M  # noqa: E402


def kpokes(args):
    return {int(i): int(v, 16) for i, v in re.findall(r"--kpoke-render 1:ta:(\d+)=(0x[0-9a-f]+)", args)}


def main(att):
    d = os.path.join(att, "q086")
    lines = open(os.path.join(d, "cases.tsv")).read().splitlines()
    hdr = lines[0].split("\t")
    for ln in lines[1:]:
        c = dict(zip(hdr, ln.split("\t")))
        w, h = (int(re.search(r"--%s (\d+)" % k, c["args"]).group(1)) for k in ("width", "height"))
        m1, m2, _ = M.q086_words(w, h, kpokes(c["args"]))
        cx, cy = M.coverage(m1, m2)
        rx, ry = min(w, 32 * cx), min(h, 16 * cy)
        rows = {}
        for t in gzip.open(os.path.join(d, c["name"] + ".txt.gz"), "rt"):
            m = re.match(r"row (\d+): (.*)", t)
            if m:
                rows[int(m.group(1))] = m.group(2).split()
        ins, out = collections.Counter(), collections.Counter()
        for y, r in rows.items():
            for x, v in enumerate(r):
                (ins if x < rx and y < ry else out)[v] += 1
        print("%-18s %-6s cover %2d,%2d tiles = %4d x %3d px | inside %s | outside %s" % (
            c["name"], c["class"], cx, cy, rx, ry, dict(sorted(ins.items())), dict(sorted(out.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
