#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Q284, round 9 offline (decision S-2 a, record E951): E930's post hoc 32 x 32 cube-face index
against E561's twiddle law, by enumeration (standard library, no data read).
  E923 / E930: the face-local index is the Morton interleave of (s, t) with t in bit 0, s in bit 1;
     at 32 x 32 E930 read bit 8 from bit 4 of s (the coordinate in the odd bits) and bit 9 from
     bit 4 of t (post hoc, 4831 of 4831 predicted pixels of three jobs).
  E561: a twiddled 32-bit texture is tiles of min(w, 16) x min(h, 16) texels, the interleave inside
     a tile with Y in bit 0 and X in bit 1, the tiles in raster order with x first (32 x 32: i8 =
     x4, i9 = y4; 64 x 64: i8, i9 = x4, x5; i10, i11 = y4, y5).
With s as X and t as Y the two are compared at every (s, t) of a face of 32 and of 64, and at 64
against the rivals of the round 9 seeds plan: H-PAIRSWAP (pairs above bit 7 as (x4, y4, x5, y5))
and H-MORTON (the plain 6-bit Morton).
    python3 -I -B e561_vs_e930.py > e561_vs_e930.out"""


def morton(s, t, bits):
    i = 0
    for b in range(bits):
        i |= (t >> b & 1) << (2 * b) | (s >> b & 1) << (2 * b + 1)
    return i


def e561(x, y, n):
    tw = min(n, 16)
    tiles_x = n // tw
    return (x // tw + (y // tw) * tiles_x) * tw * tw + morton(x % tw, y % tw, tw.bit_length() - 1)


def e930_32(s, t):
    return morton(s & 15, t & 15, 4) | (s >> 4 & 1) << 8 | (t >> 4 & 1) << 9


def pairswap(s, t, n):
    i = morton(s & 15, t & 15, 4)
    k = 8
    for b in range(4, n.bit_length() - 1):
        i |= (s >> b & 1) << k | (t >> b & 1) << (k + 1)
        k += 2
    return i


for n in (16, 32):
    same = sum(e561(s, t, n) == (e930_32(s, t) if n == 32 else morton(s, t, 4)) for s in range(n) for t in range(n))
    print(f"{n} x {n}: E561's index equals the face rule's (E923 at 16, E930's post hoc form at 32) at {same} of {n * n} (s, t)")
n = 64
for name, f in (("H-PAIRSWAP", lambda s, t: pairswap(s, t, 64)), ("H-MORTON", lambda s, t: morton(s, t, 6))):
    same = sum(e561(s, t, n) == f(s, t) for s in range(n) for t in range(n))
    print(f"64 x 64: E561's index equals {name} at {same} of {n * n} (s, t): a 64 x 64 face parts them")
print("32 x 32: H-PAIRSWAP equals E561 at %d of 1024" % sum(e561(s, t, 32) == pairswap(s, t, 32) for s in range(32) for t in range(32)))
