"""The macrotile rule of the UAPI header (E331) and the word fields (E247, E257), used by the
11.26 generator and by the recompute script.  Nothing here touches the laptop.

CR_TE_MTILE1 (0x0208): bit 31 (four macrotiles across), 29:22 B1, 19:12 B2, 7:0 B3.
CR_TE_MTILE2 (0x020c): 30:22 B1, 20:12 B2, 8:0 B3.   (field widths: E247, which bits take a write)
Read through E331/E257/E339 as the three tile boundaries between four macrotile columns (rows),
which the rule sets to mx, 2 mx, 3 mx for n = 4 and to mx, mx, mx for n = 2 [infer: Q100].
CR_TE_MACROTILE_STRIDE: 16 per 4x4-tile block, i.e. mx * my tiles for rounded macrotiles.
"""

TILE_W, TILE_H = 32, 16
N4_AREA = 640 * 480


def ceil_div(a, b):
    return -(-a // b)


def rule(w, h, unit=4, n4_area=N4_AREA, area_factor=1):
    """(tx, ty, n, mx, my) of the single-sampled rule (unit 4, factor 1) or a variant:
    unit = the rounding of a macrotile's width and height in tiles, area_factor = what the area
    is multiplied by before the n = 4 test."""
    tx, ty = ceil_div(w, TILE_W), ceil_div(h, TILE_H)
    n = 4 if w * h * area_factor >= n4_area else 2
    mx = ceil_div(ceil_div(tx, n), unit) * unit
    my = ceil_div(ceil_div(ty, n), unit) * unit
    return tx, ty, n, mx, my


def mtile1(b1, b2, b3, flag):
    return (flag << 31) | (b1 << 22) | (b2 << 12) | b3


def mtile2(b1, b2, b3):
    return (b1 << 22) | (b2 << 12) | b3


def fields1(v):
    return (v >> 31) & 1, (v >> 22) & 0xff, (v >> 12) & 0xff, v & 0xff


def fields2(v):
    return (v >> 22) & 0x1ff, (v >> 12) & 0x1ff, v & 0x1ff


def words(w, h, **kw):
    """(mtile1, mtile2, stride) of a rule variant."""
    tx, ty, n, mx, my = rule(w, h, **kw)
    b = (1, 2, 3) if n == 4 else (1, 1, 1)
    return (mtile1(mx * b[0], mx * b[1], mx * b[2], 1 if n == 4 else 0),
            mtile2(my * b[0], my * b[1], my * b[2]), mx * my)


def selftest():
    # the words E257 read at eight sizes, and E331's samples
    want = {(64, 64): (0x01004004, 0x01004004, 0x10), (96, 64): (0x01004004, 0x01004004, 0x10),
            (256, 256): (0x01004004, 0x02008008, 0x20), (512, 512): (0x02008008, 0x04010010, 0x80),
            (1024, 768): (0x82010018, 0x03018024, 0x60), (1366, 768): (0x83018024, 0x03018024, 0x90),
            (2048, 2048): (0x84020030, 0x08040060, 0x200), (4096, 4096): (0x88040060, 0x100800c0, 0x800)}
    for (w, h), v in want.items():
        assert words(w, h) == v, (w, h, [hex(x) for x in words(w, h)])
    # the closed driver's 4x words at 64x64 are the 1x words shifted right by one, stride by two
    r = words(64, 64)
    assert (r[0] >> 1, r[1] >> 1, r[2] >> 2) == (0x802002, 0x802002, 4)
    # unit 2 reproduces them at 64x64 as well: a 2 x 2-tile macrotile, stride 4
    assert words(64, 64, unit=2) == (0x802002, 0x802002, 4)
    return True


if __name__ == "__main__":
    print("rules selftest:", selftest())
