import sys
sys.dont_write_bytecode = True
sys.path.insert(0, ".")
import q107_rule as R

D = "/Users/jtorra/src/resgx545-data/dpm/partial-model-batch/dumps/"
C1, C26 = D + "depth-safe.c1/", D + "depth-safe.c26/"
Z = ".depth.1.bin.gz"
# (cell, {run: g33 path}, {run: g1 path})
CELLS = [
    ("z05-0x23", {1: C1 + "dp-z05-g33-0x23-r1" + Z, 2: C1 + "dp-z05-g33-0x23-r2" + Z},
     {1: C1 + "dp-z05-g1-0x23-r1" + Z, 2: C1 + "dp-z05-g1-0x23-r2" + Z}),
    ("z05-0x28", {1: C1 + "dp-z05-g33-0x28-r1" + Z, 2: C1 + "dp-z05-g33-0x28-r2" + Z},
     {1: C1 + "dp-z05-g1-0x28-r1" + Z, 2: C1 + "dp-z05-g1-0x28-r2" + Z}),
    ("z05-0x30", {1: C1 + "dp-z05-g33-0x30-r1" + Z, 2: C1 + "dp-z05-g33-0x30-r2" + Z},
     {1: C1 + "dp-z05-g1-0x30-r1" + Z, 2: C1 + "dp-z05-g1-0x30-r2" + Z}),
    ("ramp-0x28", {1: C26 + "dp-ramp-g33-0x28-r1" + Z, 2: C26 + "dp-ramp-g33-0x28-r2" + Z},
     {1: C26 + "dp-ramp-g1-0x28-r1" + Z, 2: C26 + "dp-ramp-g1-0x28-r2" + Z}),
    ("ramp-0x30", {1: C1 + "dp-ramp-g33-0x30-r1" + Z, 2: C26 + "dp-ramp-g33-0x30-r2" + Z},
     {1: C26 + "dp-ramp-g1-0x30-r1" + Z, 2: C26 + "dp-ramp-g1-0x30-r2" + Z}),
]
MODELS = ("RULE", "R-FIRST", "R-RASTER", "R-ZEROFIX")


PAD = (None,) * (1700 * 512)


def score(pred, got, mask=0xFFFFFFFF):
    # scorer-side handling (not a rule change): a predicted dword whose source tile lies beyond the
    # G = 33 dump's window (slot >= 1568) is None = cannot tell, and is left out of the counts
    pred = {i: v for i, v in pred.items() if v is not None}
    ok = sum(1 for i, v in pred.items() if got[i] & mask == v & mask)
    slots = {}
    for i, v in pred.items():
        slots.setdefault(i // 512, True)
        if got[i] & mask != v & mask:
            slots[i // 512] = False
    return ok, len(pred), sum(slots.values()), len(slots)


def stats(d):
    z = sum(1 for v in d if v == 0)
    neg = sum(1 for v in d if v >> 31)
    return f"zero {z} signed {neg}"


print("## pairs: G = 1 dump predicted from the G = 33 dump (run 1 of the cell, and run 2)")
tot = {m: [0, 0, 0] for m in MODELS}  # dumps held, dumps, dwords ok
for cell, g33s, g1s in CELLS:
    gs = {r: R.load(p) for r, p in g33s.items()}
    print(f"\n# {cell}: G33 r1 vs r2 equal dwords {sum(a == b for a, b in zip(gs[1], gs[2]))}"
          f"/{len(gs[1])}; G33 r1 {stats(gs[1])}")
    for r, p in g1s.items():
        got = R.load(p)
        print(f"  G1 r{r}: {stats(got)}; slots 0-125 zero dwords "
              f"{sum(1 for v in got[:126*512] if v == 0)}; dwords from 126*512 non-zero "
              f"{sum(1 for v in got[126*512:] if v != 0)} of {len(got)-126*512}")
        for src in (1, 2):
            for m in MODELS:
                pred = R.predict(tuple(gs[src]) + PAD, R.W, R.H, 1, m)
                ok, n, so, sn = score(pred, got)
                mk = score(pred, got, 0x7FFFFFFF)
                held = ok == n
                print(f"    from G33 r{src} {m:10s}: full {ok}/{n} slots {so}/{sn} "
                      f"{'HELD' if held else 'FAILED'}; sign-masked {mk[0]}/{mk[1]}")
                if src == 1:
                    t = tot[m]; t[0] += held; t[1] += 1; t[2] += ok
print("\n## totals (source G33 r1, 10 G=1 dumps; 64512 scored dwords each)")
for m in MODELS:
    print(f"{m}: held {tot[m][0]} of {tot[m][1]} dumps; dwords ok {tot[m][2]}")

print("\n## bridge controls (E489, non overflow, 1024x768): G0/G1/G2 from G33, same axis")
B = "/Users/jtorra/src/resgx545-data/zls/store-layout-dumps/dumps/"
for ax in ("x", "y"):
    g33 = R.load(B + f"fit-1024x768-G33-ramp{ax}.bin.gz")
    for g in (0, 1, 2):
        got = R.load(B + f"fit-1024x768-G{g}-ramp{ax}.bin.gz")
        for m in MODELS:
            pred = R.predict(tuple(g33) + PAD, R.W, R.H, g, m)
            ok, n, so, sn = score(pred, got)
            print(f"  ramp{ax} G{g} {m:10s}: {ok}/{n} slots {so}/{sn} {'HELD' if ok == n else 'FAILED'}")
