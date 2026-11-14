# SPDX-License-Identifier: MIT
"""fold/dumpcheck.py: the 4608 band dwords of every depth row's kept dump against the frozen
per-dword file of H-POLYCLIP and of H-POLYCLIP-NR (predictions/zcut/NAME.MODEL.txt): exact words
mismatching and the largest deviation of a drawn dword from the plane (float).
  python3 -B fold/dumpcheck.py > fold/dumpcheck.out"""
import gzip
import os
import struct
import sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import zcut as Z  # noqa: E402

A = os.path.join(KP, "out/20261114-073059/zcut")
for n in ("zcut-ctl-zhi", "zcut-ctl-zlo", "zcut-hi1", "zcut-hi2", "zcut-hi3", "zcut-lo1", "zcut-lo2", "zcut-lo3"):
    b = gzip.open(os.path.join(A, n + ".depth.1.bin.gz")).read()
    w = struct.unpack("<%dI" % (len(b) // 4), b)
    for m in ("H-POLYCLIP", "H-POLYCLIP-NR"):
        p = os.path.join(KP, "predictions/zcut/%s.%s.txt" % (n, m))
        if not os.path.exists(p):
            continue
        z = Z.zparse(open(p).read())
        bad = dev = 0
        for i, (k, v) in z["dwords"].items():
            if k == "eq":
                bad += w[i] != v
            else:
                dev = max(dev, abs(struct.unpack("<f", struct.pack("<I", w[i]))[0] - v))
        print("%s %s: %d dwords, %d exact words differ, max drawn deviation %.2e" % (n, m, len(z["dwords"]), bad, dev))
