#!/usr/bin/env python3
"""R10-A design aid: stage dcmp's rows (Q241's compares 2, 3, 5, 6 against equal depths; Q243's NaN,
infinity and negative loaded depths under every compare) and each rival's drawn count of 2048
(E977's z243 form: 64 x 32, a flat --tri-full at depth t, the depth buffer filled with L, loaded
with bits 1 and 14 and stored). Modes in GL order (E282: 0 never, 1 less, 4 greater, 7 always
measured; 2 equal, 3 lequal, 5 notequal, 6 gequal [infer]). A row is worth running only if two
rivals part on it; the table prints that."""
import struct, math
def f(u): return struct.unpack("<f", struct.pack("<I", u))[0]
OPS = {0: lambda a, b: False, 1: lambda a, b: a < b, 2: lambda a, b: a == b, 3: lambda a, b: a <= b,
       4: lambda a, b: a > b, 5: lambda a, b: a != b, 6: lambda a, b: a >= b, 7: lambda a, b: True}
def ieee(m, t, L):
    a, b = f(t), f(L)
    if math.isnan(b): return m in (5, 7)
    return OPS[m](a, b)
RIV = {
 "H-UBITS": lambda m, t, L: OPS[m](t, L),                       # unsigned compare of the bit patterns (E977 [infer])
 "H-ABS": lambda m, t, L: OPS[m](t & 0x7FFFFFFF, L & 0x7FFFFFFF),  # sign cleared, then unsigned (E664's refusal note)
 "H-IEEE": ieee,                                                  # float compare, NaN unordered
 "H-CLAMP0": lambda m, t, L: ieee(m, t, 0 if (L >> 31) else L),   # a negative loaded depth read as 0.0 (E287's triangle side)
}
ROWS = []
EQ = 0x3F000000
for m in range(8): ROWS.append((f"eq-m{m}", m, EQ, EQ))
for tag, L in (("up1", 0x3F000001), ("dn1", 0x3EFFFFFF), ("nan", 0x7FC00000), ("inf", 0x7F800000)):
    for m in (2, 3, 5, 6): ROWS.append((f"{tag}-m{m}", m, EQ, L))
for tag, L in (("neg25", 0xBE800000), ("neg75", 0xBF400000)):
    for m in (1, 2, 4): ROWS.append((f"{tag}-m{m}", m, EQ, L))
for tag, L in (("z0-neg25", 0xBE800000), ("z0-negz", 0x80000000)):
    for m in (1, 2, 4): ROWS.append((tag + f"-m{m}", m, 0x00000000, L))
print("row | mode | t | L | " + " | ".join(RIV) + " | parts")
told = 0
for n, m, t, L in ROWS:
    v = {k: 2048 if r(m, t, L) else 0 for k, r in RIV.items()}
    parts = len(set(v.values())) > 1
    told += parts
    print(f"{n} | {m} | {t:#010x} | {L:#010x} | " + " | ".join(str(x) for x in v.values()) + f" | {'yes' if parts else '-'}")
print(f"{len(ROWS)} rows, {told} part at least two rivals; the eq-m0..m7 and up1/dn1 rows test the GL order")
