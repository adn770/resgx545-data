# Q289 fold check (round 6, 2026-11-12): every case of the two kept DOUTU1 sweeps of the fill
# (resgx545-data pds/end-of-tile/values-doutu1-{x,y}/raw.txt), not only the eight class checks
# of closing6/rank/eot_hash.py: the poke's XOR constant in field units (x: bits 11:3, y: bits
# 21:12), the image predicted under M-OR, M-ADD and M-XOR (eot_hash.py's models: the tile t of
# the 64 x 32 fill, 32 x 16 tiles, stores at (op(2t, f)) >> 1 in half-tile units, nothing when
# outside, 0xdeadbeef where nothing is stored), hashed with sgxfive_hash_dwords (FNV-1a 64 over
# the dwords, row after row) and compared with the hash the tool printed. Also counts the jobs
# that were not `ok` and those with `outside` above 0. Usage:
#   python3 eot_all.py DATA/pds/end-of-tile > eot_all.out
import re
import sys


def h(px):
    v = 0xcbf29ce484222325
    for d in px:
        for b in range(4):
            v ^= (d >> (8 * b)) & 0xff
            v = (v * 0x100000001b3) & 0xffffffffffffffff
    return v


W, H, TW, TH = 64, 32, 32, 16
OPS = {"OR": lambda a, b: a | b, "ADD": lambda a, b: a + b, "XOR": lambda a, b: a ^ b}


def img(fx, fy, op):
    st = set()
    for tx in range(W // TW):
        for ty in range(H // TH):
            nx, ny = op(2 * tx, fx) >> 1, op(2 * ty, fy) >> 1
            if nx < W // TW and ny < H // TH:
                st.add((nx, ny))
    return [0xff336699 if (x // TW, y // TH) in st else 0xdeadbeef
            for y in range(H) for x in range(W)]


def cases(path):
    cur = None
    for line in open(path):
        if line.startswith("=== case "):
            if cur:
                yield cur
            cur = {"case": line[9:].strip()}
        elif cur is not None:
            m = re.match(r"job: (\S+)", line)
            if m:
                cur["job"] = m.group(1)
            m = re.match(r"target: \S+ hash (0x[0-9a-f]+)", line)
            if m:
                cur["hash"] = int(m.group(1), 16)
            m = re.match(r"outside: (\d+)", line)
            if m:
                cur["out"] = int(m.group(1))
    if cur:
        yield cur


root = sys.argv[1]
memo = {}
for axis, shift in (("x", 3), ("y", 12)):
    cs = list(cases(f"{root}/values-doutu1-{axis}/raw.txt"))
    tally = {k: 0 for k in OPS}
    notok = outside = 0
    fs = []
    for c in cs:
        if c.get("job") != "ok":
            notok += 1
        if c.get("out", 0) > 0:
            outside += 1
        m = re.search(r"\^=(0x[0-9a-f]+)$", c["case"])
        f = 0 if c["case"] == "baseline" else int(m.group(1), 16) >> shift
        if c["case"] != "baseline" and (int(m.group(1), 16) & ((1 << shift) - 1)):
            raise SystemExit(f"{c['case']}: low bits set")
        fs.append(f)
        fx, fy = (f, 0) if axis == "x" else (0, f)
        for name, op in OPS.items():
            k = (fx, fy, name)
            if k not in memo:
                memo[k] = h(img(fx, fy, op))
            tally[name] += memo[k] == c.get("hash")
    print(f"{axis} sweep: {len(cs)} cases (field values {min(fs)} to {max(fs)}), not ok {notok}, "
          f"outside > 0 {outside}")
    for name in OPS:
        print(f"  M-{name}: {tally[name]} of {len(cs)} hashes reproduced")
