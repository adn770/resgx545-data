#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round 10 seeds, Q177: the offset (dwords) each rival gives at the proposed held-out sizes, and
mode 5's past-the-texture reads (fitted on E957 + bd-hb-ns-uv5: left 5 W + 52 + t, right
6 W + 52 + t, t the row inside the texture)."""
SIZES = [(8, 32), (32, 8), (16, 64), (64, 16), (64, 64), (4, 4), (16, 32), (32, 16)]
print("W x H   H-W 8W+52  H-H 8H+52  H-SQ 8 sqrt(WH)+52  H-WH 8(W+H)/2+52")
for w, h in SIZES:
    sq = 8 * (w * h) ** 0.5 + 52
    print(f"{w:2d}x{h:<3d}  {8 * w + 52:9d}  {8 * h + 52:9d}  {sq:17.1f}  {4 * (w + h) + 52:16d}")
print("mode 5 (H-B5): left of the texture 5 W + 52 + t, right 6 W + 52 + t (t inside [0, H))")
for w, h in ((16, 32), (32, 16)):
    print(f"{w}x{h}: left {5 * w + 52}..{5 * w + 52 + h - 1}, right {6 * w + 52}..{6 * w + 52 + h - 1}")
