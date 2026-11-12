# SPDX-License-Identifier: MIT
# Q142, round 7 fold (r7-fold-rank): H-GRID and the H-HALF control as predictors of the TA data
# (the region headers from dword 4096) that CR_TE_AA bits 30 and 31 give, from the TA data of the
# CR_TE_AA 0x20000000 job of the same size (E504's dumps, resgx545-data isp/msaa-te-dumps).
# Standard library only. Read-only over the data.
#
# H-GRID (frozen 2026-11-12 before te-m2-e0-128x128 was opened):
#  - bit 31 halves the region's width (32 -> 16 pixels), bit 30 its height (16 -> 8): the region
#    grid doubles along x with bit 31 and along y with bit 30; a macrotile keeps its pixel area and
#    its number (word bits 15:12), so it holds (mx << b31) x (my << b30) regions;
#  - word 0's position fields count in 16 pixels (bits 23:16, x) and 8 pixels (bits 11:0, y) at
#    every setting (2 per 32 x 16 region at 0x20000000, as the sgx-pipe writer has it);
#  - a macrotile's headers are written in 4 x 4-region sub-blocks, sub-blocks in raster order
#    (x fastest), regions in raster order inside one (x fastest); at 0x20000000 the macrotile is
#    one sub-block, the writer's raster order;
#  - flags as the writer's (E177, E178, E652): 0x02 outside the target, 0x08 a target region
#    without a stream, 0x04 the first and 0x10 the last target header of a macrotile in header
#    order, 0x80 with 0x10 in the last macrotile that has target regions;
#  - a fine region has a stream when its 0x20000000 parent region has one (the input's pointer);
#  - streams are allocated per macrotile in the writer's walk (blocks of 2 regions across and 4
#    down in raster order, regions raster inside), in fine regions; 0x80 bytes a stream; the
#    macrotiles with streams in raster order (rows outer), each starting a new 0x1000 page and
#    taking as many pages as its streams fill (32 streams a page), from the input's first page.
# H-HALF (the control, refuted at 64 x 64 by the entry count): the input's headers with the
#  position field of the doubled axis halved, no new regions, the same pointers.
import gzip
import struct
import sys

DUMPS = 'isp/msaa-te-dumps/dumps/'
HEADERS = 4096          # dword offset of the first region header in the TA data dump
TADATA_LEN = 6144
STREAM_AT, STEP, PAGE = 0x2000, 0x80, 0x1000


def load(data, name, kind):
    b = gzip.open(f'{data}/{DUMPS}{name}.{kind}.txt.gz').read()
    return list(struct.unpack(f'<{len(b) // 4}I', b[:len(b) // 4 * 4]))


def tiling(w, h):
    """The library's macrotile geometry (sgx-pipe ta::tiling): n macrotiles a row, mx x my regions."""
    tx, ty = -(-w // 32), -(-h // 16)
    n = 4 if w * h >= 640 * 480 else 2
    up4 = lambda v: (v + 3) & ~3
    return n, up4(-(-tx // n)), up4(-(-ty // n))


def coarse_streams(tadata, w, h):
    """{(column, row) of a 32 x 16 region: has a stream} read from a 0x20000000 job's TA data."""
    n, mx, my = tiling(w, h)
    out = {}
    for m in range(n * n):
        for i in range(mx * my):
            idx = m * mx * my + i
            c, r = (m // n) * mx + i % mx, (m % n) * my + i // mx
            out[(c, r)] = tadata[HEADERS + 3 * idx + 1] != 0
    return out


def walk(mx, my):
    o = []
    for br in range(-(-my // 4)):
        for bc in range(-(-mx // 2)):
            for r in range(4 * br, min(4 * br + 4, my)):
                for c in range(2 * bc, min(2 * bc + 2, mx)):
                    o.append((c, r))
    return o


def h_grid(tadata, w, h, aa):
    """The predicted TA data (TADATA_LEN dwords) for CR_TE_AA `aa` from the 0x20000000 job's."""
    b31, b30 = aa >> 31 & 1, aa >> 30 & 1
    n, mx, my = tiling(w, h)
    fx, fy = mx << b31, my << b30
    rw, rh = 32 >> b31, 16 >> b30
    parent = coarse_streams(tadata, w, h)
    first_page = min((v for k, v in enumerate(tadata[HEADERS + 1::3]) if v), default=STREAM_AT)
    first_page &= ~(PAGE - 1)

    def glob(m, c, r):
        return (m // n) * fx + c, (m % n) * fy + r

    def inside(m, c, r):
        gc, gr = glob(m, c, r)
        return gc * rw < w and gr * rh < h

    def stream(m, c, r):
        gc, gr = glob(m, c, r)
        return inside(m, c, r) and parent[(gc >> b31, gr >> b30)]

    order = sorted(((c, r) for r in range(fy) for c in range(fx)),
                   key=lambda p: (p[1] // 4, p[0] // 4, p[1] % 4, p[0] % 4))
    # stream addresses
    addr, page = {}, first_page
    for mrow in range(n):
        for mcol in range(n):
            m = mcol * n + mrow
            k = 0
            for c, r in walk(fx, fy):
                if stream(m, c, r):
                    addr[(m, c, r)] = page + STEP * k
                    k += 1
            if k:
                page += PAGE * -(-k // (PAGE // STEP))
    last_macro = max((m for m in range(n * n) if any(inside(m, c, r) for c, r in order)),
                     default=None)
    out = [0] * TADATA_LEN
    idx = 0
    for m in range(n * n):
        ins = [p for p in order if inside(m, *p)]
        for c, r in order:
            gc, gr = glob(m, c, r)
            f = 0
            if not inside(m, c, r):
                f |= 0x02
            elif not stream(m, c, r):
                f |= 0x08
            if ins and ins[0] == (c, r):
                f |= 0x04
            if ins and ins[-1] == (c, r):
                f |= 0x10
                if m == last_macro:
                    f |= 0x80
            word = f << 24 | (gc * rw // 16) << 16 | m << 12 | ((gr * rh // 8) & 0xfff)
            at = HEADERS + 3 * idx
            out[at] = word
            if (m, c, r) in addr:
                out[at + 1] = addr[(m, c, r)]
            idx += 1
    return out, sorted(addr.values())


def h_half(tadata, w, h, aa):
    """The control: the input's headers with the doubled axis' position field halved."""
    b31, b30 = aa >> 31 & 1, aa >> 30 & 1
    out = list(tadata[:TADATA_LEN])
    n, mx, my = tiling(w, h)
    for idx in range(n * n * mx * my):
        at = HEADERS + 3 * idx
        v = out[at]
        x, y = v >> 16 & 0xff, v & 0xfff
        if b31:
            x >>= 1
        if b30:
            y >>= 1
        out[at] = (v & ~0x00ff0fff) | x << 16 | y
    ptrs = sorted(p for p in out[HEADERS + 1::3] if p)
    return out, ptrs


def write(path, words, ptrs):
    with open(path, 'w') as f:
        f.write('# pointers ' + ' '.join(f'{p:#x}' for p in ptrs) + '\n')
        for i, v in enumerate(words):
            if v:
                f.write(f'{i} {v:08x}\n')


if __name__ == '__main__':
    a = sys.argv
    if len(a) != 8 or a[1] != 'predict':
        sys.exit('usage: q142_grid.py predict DATA BASE W H AA OUTPREFIX')
    data, base, w, h, aa, out = a[2], a[3], int(a[4]), int(a[5]), int(a[6], 0), a[7]
    t = load(data, base, 'tadata')
    # self-check on the input: the coarse model (bits 30/31 clear) must give the input back
    same, _ = h_grid(t, w, h, 0x20000000)
    bad = [i for i in range(TADATA_LEN) if same[i] != t[i]]
    print(f'input {base}: the 0x20000000 model differs from the input in {len(bad)} dwords')
    g, gp = h_grid(t, w, h, aa)
    write(out + '.grid.txt', g, gp)
    hw_, hp = h_half(t, w, h, aa)
    write(out + '.half.txt', hw_, hp)
    print(f'H-GRID: {sum(1 for v in g if v)} non-zero dwords, {len(gp)} streams; '
          f'H-HALF: {sum(1 for v in hw_ if v)} non-zero dwords, {len(hp)} streams')
