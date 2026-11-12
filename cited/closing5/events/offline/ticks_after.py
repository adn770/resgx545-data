#!/usr/bin/env python3
"""ticks_after.py: from a kept job record (JSON with "page") of the ring task: the slot 0 ring (16 rungs of 8 dwords at dword 256:
flag, pa0, pa1, pa2, CR_TIMER), the slot 3 ring (dword 512), the 'ring full' counters (dwords 16..19) and the slot 0 pass counter
(dword 20).  Prints the slot 0 passes after the fill's kick entry: logged ticks + passes counted with the ring full.
Usage: ticks_after.py JOB.json [...]"""
import json, sys
def rungs(page, base, n):
    out = []
    for i in range(n):
        f, pa0, pa1, pa2, tim = page[base + 8 * i: base + 8 * i + 5]
        if f: out.append((f, pa0, pa1, pa2, tim))
    return out
for p in sys.argv[1:]:
    rec = json.load(open(p))
    page = rec["page"] if isinstance(rec, dict) else rec
    s0, s3 = rungs(page, 256, 16), rungs(page, 512, 8)
    kick = [i for i, r in enumerate(s0) if r[1] == 0 and (r[2] & 0xffffff) == 0x100]
    print(f"== {p}")
    print(f"   window {page[6]} skip flag {page[7]} skipped {page[8]} full counters (slots 0..3) {page[16:20]} slot 0 passes {page[20]}")
    print(f"   slot 0 ring: {len(s0)} rungs, kick entries at {kick}; slot 3 ring: {[(r[0], hex(r[2]), r[4]) for r in s3]}")
    if len(kick) != 1:
        print("   cannot tell: not exactly one kick entry in the ring"); continue
    k = kick[0]
    after = s0[k + 1:]
    gaps = [after[i][4] - (after[i - 1][4] if i else s0[k][4]) for i in range(len(after))]
    ticks = sum(1 for r in after if r[1] == 2)
    print(f"   ticks before the kick {k}, after it in the ring {ticks} (all pa0 2: {ticks == len(after)}), gaps in CR_TIMER units {gaps}")
    if s3:
        print(f"   kick entry to slot 3 entry: {s3[0][4] - s0[k][4]} units ({(s3[0][4] - s0[k][4]) / 25:.0f} us)")
    print(f"   slot 0 passes after the kick entry: {ticks} logged + {page[16]} with the ring full = {ticks + page[16]}"
          + ("" if len(s0) == 16 else "  (the ring is not full: the counter must be 0)"))
