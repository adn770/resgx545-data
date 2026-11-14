"""POST HOC (after the run, not frozen): what addr5's type rows (types 1, 3, 4 with u mode 4) read.
Neither T-MODE0 nor T-OFFSET held: every pixel is 0x68xxxxxx, not a name. Per pixel: the names n
whose bytes halved, rounded up ((b + 1) >> 1 a byte, a 50/50 blend with a zero dword), give the
pixel, and n less the reference's name of the same pixel."""
import collections, gzip, os, re, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(KP, "out/20261114-054258/addr5")


def px(name):
    t = gzip.open(os.path.join(D, name + ".txt.gz"), "rt").read()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()]
            for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", t, re.M)}
    return [v for y in sorted(rows) for v in rows[y]]


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


for ty in (1, 3, 4):
    a, r = px(f"addr5-ty{ty}-u4"), px(f"addr5-ty{ty}-u0")
    off = collections.Counter()
    exact = 0
    names = collections.Counter()
    for p, (v, ref) in enumerate(zip(a, r)):
        lo = (v & 0xFFFF) * 2
        cands = [n for n in range(max(lo - 2, 0), lo + 2) if half(0xD0000000 | n) == v]
        exact += bool(cands)
        if cands:
            off[tuple(n - (ref & 0x0FFFFFFF) for n in cands)] += 1
            names[tuple(cands)] += 1
    print(f"type {ty}: {exact}/2048 pixels are a named dword's bytes halved (rounded up); "
          f"distinct values {len(set(a))}; reference distinct {len(set(r))}")
    print("   name less the reference's name (candidates), most common:", off.most_common(6))
    xs = [min(c) for c in names]
    print("   names read: %d to %d" % (min(xs), max(xs)))
    # one row of pixels: the value against x and against the reference
    print("   row 0 names (lowest candidate):", [min(n for n in range(((v & 0xFFFF) * 2) - 2,
          ((v & 0xFFFF) * 2) + 2) if half(0xD0000000 | n) == v) for v in a[:16]])
    print("   rows equal down the fill:", all(a[64 * y:64 * y + 64] == a[:64] for y in range(32)))
