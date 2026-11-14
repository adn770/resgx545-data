#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/sa0_posthoc.py: post hoc (after the run, not frozen) reading of u-sa0, the uadd row that
failed H-ZX: which pair's value each stored dword and each o0 holds, under H-ZX and H-SX."""
import gzip
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import rule as R  # noqa: E402

R1S = [0x8000, 0x8001, 0xABCD, 0xFFFF, 0x7FFF, 0xFFFF8000, 0x1234FEDC, 0xFFFFFFFF]
R2S = [0x8000, 0x7FFF0000, 0x1, 0xFFFFFFFF, 0x8001, 0x12345678, 0x80000000, 0x00010000]
text = gzip.open(os.path.join(KP, "out/20261114-092913/uadd/u-sa0.txt.gz"), "rt").read()
zx = [R.iaddu32(a, b, "H-ZX") for a, b in zip(R1S, R2S)]
sx = [R.iaddu32(a, b, "H-SX") for a, b in zip(R1S, R2S)]


def which(v):
    return ", ".join([f"H-ZX of pair {k}" for k, z in enumerate(zx) if z == v]
                     + [f"H-SX of pair {k}" for k, s in enumerate(sx) if s == v]) or "no pair"


for m in re.finditer(r"scratch \+0x([0-9a-f]+) 0x([0-9a-f]{8})", text):
    k, v = int(m.group(1), 16) // 4, int(m.group(2), 16)
    print(f"dword {k} (pair {k}): 0x{v:08x} = {which(v)}{'' if v == zx[k] else '  <- not its own pair'}")
o0 = re.search(r"o0 mixed (.*)", text).group(1)
print("o0 (the last mov r3, sa0 of each instance):", o0)
for v, n in re.findall(r"0x([0-9a-f]{8}) x(\d+)", o0):
    print(f"  0x{v} x{n}: {which(int(v, 16))}")
