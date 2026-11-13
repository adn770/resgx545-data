#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round 10 seeds, Q120 offline look: r9-x zst dumps (E978), formats 0 and 3 to 7 at 64 x 32;
the changed dwords of each depth dump (fill 0xdeadbeef) in tile-slot order, first words."""
import gzip
import struct
import sys

D = "/Users/jtorra/src/resgx545-data/render/closing-r9-x/out/20261113-081821/zst"
sz = sys.argv[1] if len(sys.argv) > 1 else "s"


def words(name, kind):
    b = gzip.open(f"{D}/z120-{name}-{sz}.{kind}.1.bin.gz").read()
    return list(struct.unpack(f"<{len(b) // 4}I", b))


for f in ("ctl", "f3", "f4", "f5", "f6", "f7"):
    d = words(f, "depth")
    ch = [i for i, v in enumerate(d) if v != 0xDEADBEEF]
    print(f"== {f}: {len(d)} dwords, {len(ch)} changed, first {ch[:3]} last {ch[-3:]}")
    runs = []
    s = p = None
    for i in ch:
        if s is None:
            s = p = i
        elif i == p + 1:
            p = i
        else:
            runs.append((s, p))
            s = p = i
    if s is not None:
        runs.append((s, p))
    print("   runs:", runs[:12], "..." if len(runs) > 12 else "")
    for a, _ in runs[:2]:
        print("   @%d:" % a, " ".join("%08x" % d[i] for i in range(a, a + 16)))
