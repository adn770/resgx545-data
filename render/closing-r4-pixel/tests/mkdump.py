#!/usr/bin/env python3
"""mkdump.py N OUTPREFIX: write OUTPREFIX.param.bin and OUTPREFIX.tadata.bin, a REAL kept vertex-loop object dump (E784's v-i880) whose
three depth words are rewritten to 0x3f200000 + N (N = 0 reads E784's no-loop control), for the fake tool of tests/run_mock.sh: the
scorers' real pbdump decode then reads the loop proof of the mock's jobs."""
import gzip
import pathlib
import struct
import sys

fx = pathlib.Path(__file__).resolve().parent / "fixtures/e784"
n, out = int(sys.argv[1]), sys.argv[2]
p = gzip.open(fx / "v-i880.v-i880__0.param.bin.gz").read()
t = gzip.open(fx / "v-i880.v-i880__0.tadata.bin.gz").read()
p = p.replace(struct.pack("<I", 0x3f200370), struct.pack("<I", 0x3f200000 + n))
pathlib.Path(out + ".param.bin").write_bytes(p)
pathlib.Path(out + ".tadata.bin").write_bytes(t)
