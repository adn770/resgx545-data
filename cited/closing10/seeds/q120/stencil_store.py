#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Q121 seed: what the stencil load and store dumps of the r9-x zst jobs hold per format (python -I -B)."""
import gzip
import numpy as np

D = "/Users/jtorra/src/resgx545-data/render/closing-r9-x/out/20261113-081821/zst"


def ld(name, kind, sz):
    return np.frombuffer(gzip.open(f"{D}/z120-{name}-{sz}.{kind}.1.bin.gz").read(), dtype="<u4")


for sz, tiles in (("s", 4), ("m", 9)):
    for f in ("ctl", "f3", "f4", "f5", "f6", "f7"):
        ld_ = ld(f, "stencil", sz)
        st = ld(f, "stencil-store", sz)
        idx = np.arange(len(ld_), dtype=np.uint32)
        nz = np.nonzero(st)[0]
        print(f"{sz} {f}: load==index {int((ld_ == idx).sum())}/{len(ld_)}; store nonzero {len(nz)}; "
              f"store==index at nonzero {int((st[nz] == idx[nz]).sum())}; store==load (all) {int((st == ld_).sum())}; "
              f"store last nonzero {int(nz.max()) if len(nz) else None}; tiles*128 = {tiles * 128}")
