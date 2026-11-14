#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/compare_tadata.py KEPT_DIR: the junk rows' TA data and parameter buffer against fl-ctl's,
dump by dump (tri.1 after the kick, before the fill; tri.2 after render 2; tri the final), and
page 6's ramp dwords. Standard library only; reads the kept fl/ files."""
import gzip
import os
import struct
import sys

d = sys.argv[1]


def rd(n):
    return gzip.open(os.path.join(d, n + ".gz")).read()


for name in ("tri.1", "tri.2", "tri"):
    c = rd(f"fl-ctl.{name}.tadata.bin")
    p6 = c[6 * 4096:7 * 4096]
    print(f"{name}: {len(c) // 4096} pages; fl-ctl page 6 holds "
          f"{sum(1 for i in range(0, 4096, 4) if p6[i:i + 4] != bytes(4))} non-zero dwords")
    for r in "ab":
        j = rd(f"fl-junk-{r}.{name}.tadata.bin")
        dw = [i // 4 for i in range(0, len(c), 4) if c[i:i + 4] != j[i:i + 4]]
        pages = sorted({i // 1024 for i in dw})
        ramp = sum(1 for i in range(1024) if struct.unpack("<I", j[6 * 4096 + 4 * i:6 * 4096 + 4 * i + 4])[0]
                   == 0xa5000000 + i)
        par = rd(f"fl-junk-{r}.{name}.param.bin") == rd(f"fl-ctl.{name}.param.bin")
        print(f"  fl-junk-{r}: {len(dw)} dwords differ from fl-ctl, pages {pages}; page 6 ramp dwords "
              f"{ramp} of 1024; parameter buffer equal: {par}")
