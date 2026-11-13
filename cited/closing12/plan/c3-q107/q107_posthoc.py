"""[post hoc] for each slot of the G = 1 dump: which G33 tile (if any) holds its 512 dwords.
Read after the freeze; not a prediction. Tiles at G33 slot >= 1568 lie outside the dump."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, ".")
import q107_rule as R

D = "/Users/jtorra/src/resgx545-data/dpm/partial-model-batch/dumps/"
for tag, g33p, g1p in (("z05-0x30", "depth-safe.c1/dp-z05-g33-0x30-r1", "depth-safe.c1/dp-z05-g1-0x30-r1"),
                       ("ramp-0x28", "depth-safe.c26/dp-ramp-g33-0x28-r1", "depth-safe.c26/dp-ramp-g1-0x28-r1"),
                       ("z05-0x23", "depth-safe.c1/dp-z05-g33-0x23-r1", "depth-safe.c1/dp-z05-g1-0x23-r1")):
    g33 = R.load(D + g33p + ".depth.1.bin.gz")
    g1 = R.load(D + g1p + ".depth.1.bin.gz")
    rank = R.header_rank(R.W, R.H)
    own = R.owners(R.W, R.H, 1, rank, True)
    tl = {}
    for r in range(48):
        for c in range(32):
            s = 34 * r + c
            if 512 * (s + 1) <= len(g33):
                tl[tuple(g33[512 * s:512 * s + 512])] = (c, r)
    res = {"zero": 0, "owner": 0, "other-tile": 0, "no-tile": 0, "owner-oow": 0}
    rows = []
    for s in range(126):
        v = tuple(g1[512 * s:512 * s + 512])
        c, r = own[s]
        if not any(v):
            res["zero"] += 1; k = "zero"
        elif 34 * r + c >= 1568:
            res["owner-oow"] += 1; k = "owner-oow"
        elif v in tl:
            if tl[v] == (c, r):
                res["owner"] += 1; k = "owner"
            else:
                res["other-tile"] += 1; k = "other-tile" + str(tl[v])
        else:
            res["no-tile"] += 1; k = "no-tile"
        rows.append((s, (c, r), k))
    print(tag, res)
    print("  first 40 slots (slot, owner, finding):", rows[:40])
    print("  slot 60-125 findings:", [(s, o, k) for s, o, k in rows[60:126] if k not in ("owner",)][:30])
