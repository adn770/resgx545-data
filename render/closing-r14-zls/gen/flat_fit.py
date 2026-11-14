#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""flat_fit.py: the builder's offline look at E1031's flat block (plan section 5: fit it before
the freeze, or freeze "readings only"). Reads E1031's kept zf-flat-f6 dump at the frozen
data commit (gen/pins.py) and prints what zflat's frozen rivals rest on:
  1. the four 512-dword blocks hold the same 44 dwords (176 bytes, the last 16 zero);
  2. the bytes are 0x00, 0x3f, 0x9e, 0xc0 only; 0x9e 16 times (one a tile row, every row of the
     tile one depth), 0x3f 17 times, 0xc0 15 times, at irregular gaps (12, 10, 2 bytes): no fixed
     record length, so no layout rule is fitted (the frozen rivals FL-CONST, FL-SHAPE are
     structural);
  3. bytes 0 to 15 are E1015's F6C group 0 for v = 0.5 (c7_rule.f6c_group: the word 0x3f000000
     at dwords 0 and 3, row 0's record 0x9e v 0x00 at byte 6): FL-HEAD.
No result here is a claim; the frozen rows decide. Run: python3 gen/flat_fit.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import z14 as Z  # noqa: E402

FLAT = "data:render/closing-r13-zls/out/20261113-213117/zfmt/zf-flat-f6.depth.1.bin.gz"


def main():
    b = pins.blob(FLAT)
    blocks = [b[2048 * k:2048 * k + 4 * Z.FLAT_N] for k in range(4)]
    print("1. blocks alike:", all(x == blocks[0] for x in blocks),
          "; changed dwords a block:",
          [sum(1 for v in Z.dwords(b[2048 * k:2048 * k + 2048]) if v != Z.FILL_DEAD) for k in range(4)])
    s = blocks[0]
    print("   bytes 160-175 zero:", s[160:176] == bytes(16))
    print("2. distinct bytes:", sorted(f"{x:#04x}" for x in set(s)))
    for v in (0x9E, 0x3F, 0xC0):
        p = [i for i, x in enumerate(s) if x == v]
        print(f"   {v:#04x}: {len(p)} at {p}; gaps {[p[i + 1] - p[i] for i in range(len(p) - 1)]}")
    print("3. bytes 0-15 = F6C group 0 head for 0.5:", Z.dwords(s[:16]) == Z.f6c_head(0x3F000000))


if __name__ == "__main__":
    main()
