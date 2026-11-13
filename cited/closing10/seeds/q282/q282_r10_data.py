"""Build per-channel tables for the r9-x srgb jobs: corners (bytes), weights (1/64), hw half."""
import sys, gzip, re
sys.dont_write_bytecode = True
R = "/Users/jtorra/src/resgx545-data/render/closing-r9-x"
sys.path.insert(0, R + "/gen")
import srgb as S
OUT = R + "/out/20261113-081821/srgb/"
def kept(name):
    t = gzip.open(OUT + name + ".txt.gz", "rt").read()
    rows = {int(m.group(1)): [int(x, 16) for x in m.group(2).split()]
            for m in re.finditer(r"row (\d+): ([0-9a-fA-F ]+)$", t, re.M)}
    return [v for y in sorted(rows) for v in rows[y]]
def spec(name):
    ra, rb = S.pair_rows(9051), S.pair_rows(9052)
    return {"srgb-a1": S.spec_a(ra), "srgb-a2": S.spec_a(rb),
            "srgb-b1": S.spec_b(S.pair_rows(9053)), "srgb-b2": S.spec_b(S.pair_rows(9054)),
            "srgb-c1": S.spec_a(ra, 21), "srgb-c2": S.spec_a(rb, 43)}[name]
def rows(name):
    """list of (ch, [b00,b10,b01,b11], ix, iy, hw_half) per pixel/channel"""
    sp, px = spec(name), kept(name)
    assert len(px) == 2048
    out = []
    for p in range(2048):
        t, ix, iy = S.footprint(sp, p % 64, p // 64)
        for c in (0, 1):
            out.append((c, [(v >> 8 * c) & 255 for v in t], ix, iy, (px[p] >> 16 * c) & 0xFFFF))
    return out
if __name__ == "__main__":
    for n in ("srgb-a1", "srgb-b1", "srgb-c1"):
        r = rows(n); print(n, len(r), r[:3], r[200:203])
