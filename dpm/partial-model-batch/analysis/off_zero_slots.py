"""Offline (landed E489 dumps): where the zero dwords of the overflowed 4096x4096 store lie, by slot."""
import array, gzip
D = "/Users/jtorra/src/resgx545-data/zls/store-layout-dumps/dumps/"
FILL = 0xDEADBEEF
for g in (0, 1):
    for ax in ("x", "y"):
        a = array.array("I")
        a.frombytes(gzip.open(D + f"ho-4096x4096-G{g}-ramp{ax}.bin.gz").read())
        slots = len(a) // 512
        whole, part, zero_total, stored = [], [], 0, 0
        for s in range(slots):
            blk = a[s * 512:(s + 1) * 512]
            z = sum(1 for v in blk if v == 0)
            st = sum(1 for v in blk if v != FILL)
            zero_total += z
            stored += st
            if z == 512:
                whole.append(s)
            elif z:
                part.append((s, z, st))
        print(f"G{g} ramp{ax}: dwords {len(a)}, stored {stored}, zero {zero_total}, whole-zero slots {len(whole)}, partial {len(part)}")
        if whole:
            print("  whole-zero slots", whole[:4], "...", whole[-4:], "contiguous", whole == list(range(whole[0], whole[0] + len(whole))))
        print("  partial (slot, zeros, stored)", part[:6])
