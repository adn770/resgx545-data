# post hoc: score H-STRIDE with y (value at dword 96y+x == control value at pixel (x,y)) for the
# E997 linear dumps against E977's control dumps (twiddled, same format), over the 96 x 48 area.
import gzip, struct
R9 = "/Users/jtorra/src/resgx545-data/render/closing-r9-x/out/20261113-081821/zls/"
R10 = "/Users/jtorra/src/resgx545-data/render/closing-r10-x/out/20261113-101116/zbits/"
def idx(x, y):  # copied from closing-r10-st1 gen/st1.py in_tile_index
    x, y = x & 31, y & 15; i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8
def load(p):
    b = gzip.open(p).read(); return struct.unpack("<%dI" % (len(b) // 4), b)
for lin, ctl in (("zb-clr-f0", "z242-c-f0"), ("zb-all-f0", "z242-c-f0"), ("zb-all-f1", "z242-c-f1")):
    L, C = load(R10 + lin + ".depth.1.bin.gz"), load(R9 + ctl + ".depth.1.bin.gz")
    pix = {(x, y): C[512 * ((y // 16) * 3 + x // 32) + idx(x, y)] for y in range(48) for x in range(96)}
    ys = sum(1 for y in range(48) for x in range(96) if L[96 * y + x] == pix[(x, y)])
    # x only: row-independent check: value equals control's value at (x, y') for the best y'?
    best = {}
    for y in range(48):
        for x in range(96):
            ys_match = [yy for yy in range(48) if pix[(x, yy)] == L[96 * y + x]]
            best[(x, y)] = ys_match
    xs = sum(1 for k, v in best.items() if v)
    unique = sum(1 for k, v in best.items() if len(v) == 1)
    exact = sum(1 for k, v in best.items() if k[1] in v and len(v) == 1)
    print(lin, "vs", ctl, ": H-STRIDE with y", ys, "/ 4608; value exists in control column x:", xs,
          "; value names a unique y:", unique, "and that y is the row:", exact)
# power of the y reading: shift the row used for the control pixel by d
for lin, ctl in (("zb-clr-f0", "z242-c-f0"), ("zb-all-f1", "z242-c-f1")):
    L, C = load(R10 + lin + ".depth.1.bin.gz"), load(R9 + ctl + ".depth.1.bin.gz")
    pix = {(x, y): C[512 * ((y // 16) * 3 + x // 32) + idx(x, y)] for y in range(48) for x in range(96)}
    print(lin, "match count with control row y+d:",
          {d: sum(1 for y in range(48) for x in range(96) if 0 <= y + d < 48 and L[96 * y + x] == pix[(x, y + d)]) for d in (-8, -1, 0, 1, 8, 16)})
