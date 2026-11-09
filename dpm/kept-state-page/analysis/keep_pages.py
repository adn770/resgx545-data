#!/usr/bin/env python3
"""Explore the kept TA data of the keep-closed jobs: per case, the dwords of each 4 KiB page that are non-zero (or, for
a ramped page 3, differ from 0xa5000000 + i). python3 -B analysis/keep_pages.py DIR"""
import gzip, pathlib, struct, sys
d = pathlib.Path(sys.argv[1])
for p in sorted(d.glob("*.kept.bin.gz")):
    b = gzip.open(p).read()
    name = p.name[:-len(".kept.bin.gz")]
    if not b: print(name, "empty"); continue
    w = struct.unpack("<%dI" % (len(b) // 4), b)
    out = []
    for pg in range(len(w) // 1024):
        page = w[pg * 1024:(pg + 1) * 1024]
        if "ramp" in name and pg == 3:
            ch = [(i, v) for i, v in enumerate(page) if v != 0xa5000000 + i]
            out.append("p3 ramp-changed %d" % len(ch))
            if ch: out.append("   idx %s" % [i for i, _ in ch]); out.append("   vals %s" % ["%08x" % v for _, v in ch])
        else:
            nz = [(i, v) for i, v in enumerate(page) if v]
            if nz: out.append("p%d nonzero %d: %s" % (pg, len(nz), ["%d:%08x" % (i, v) for i, v in nz[:12]]))
    print(name, len(b), "bytes"); [print("  " + o) for o in out]
