"""common helpers for c8-q078: reading kept dumps and the inverse map of the counting fill."""
import gzip, re
D = "/Users/jtorra/src/resgx545-data/"
R9 = D + "render/closing-r9-x/out/20261113-081821/t3/"
P32 = D + "texture/p1132/tx-lod/"

def pixels(path):
    out = {}
    for ln in gzip.open(path, "rt"):
        m = re.match(r"probe \S+: row (\d+): (.*)", ln)
        if m:
            out[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    rows = [out[y] for y in sorted(out)]
    assert len(rows) == 32 and all(len(r) == 64 for r in rows), (path, len(rows))
    return [v for r in rows for v in r]   # raster, 2048

def morton(x, y, side):
    """E561 tile law (sides above 16: 16x16 tiles raster x first; inside a tile y on even bits, x odd)."""
    def inner(x, y, n):
        i = 0
        for b in range(n.bit_length() - 1):
            i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
        return i
    if side <= 16:
        return inner(x, y, side)
    tpr = side // 16
    return ((y // 16) * tpr + x // 16) * 256 + inner(x % 16, y % 16, 16)

def inverse(side=64):
    inv, off = {}, 0
    levels = []
    s, l = side, 0
    while True:
        levels.append((l, s, off))
        for y in range(s):
            for x in range(s):
                inv[off + morton(x, y, s)] = (l, x, y)
        off += s * s
        if s == 1:
            break
        s //= 2; l += 1
    return inv, levels
