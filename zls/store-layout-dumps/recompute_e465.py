#!/usr/bin/env python3
"""Recompute E465's address rule from the stored depth dumps (11.24), written independently of the
run script (store-layout.sh): no code of it is reused, the tile order is built from a bit list,
and the check runs in both directions.

usage: recompute_e465.py DUMPDIR [OUTPUT.TXT-of-the-run]

DUMPDIR holds <case>-<W>x<H>-G<g>-ramp{x,y}.bin.gz, the raw depth buffers (little-endian dwords) of
two jobs per case: one whose triangle depth ramps across x, one across y (z = 0.25 + 0.5 * x / 3W
resp. y / 3H, x and y in pixels, sampled at the pixel centre), the buffer pre-filled with
0xdeadbeef. The rule under test (E465): the 32 x 16 tile (tx, ty) of a W x H target starts at dword
512 * (ty * (G + 1) + tx), and the dword index inside the tile has the bits y0 x0 y1 x1 y2 x2 y3 x3
x4 from the lowest.

Per case it prints: the stored dwords, how many decode to a pixel whose rule address is the dword's
own, how many do not, the background-depth ones, and (for G + 1 >= tiles per row, where no two
tiles share an address) the other direction: of the pixels of the target, how many have their own
ramp values at their rule address.
"""
import array, glob, gzip, os, re, struct, sys

FILL = 0xDEADBEEF
BG = 0x3F800000
ORDER = [("y", 0), ("x", 0), ("y", 1), ("x", 1), ("y", 2), ("x", 2), ("y", 3), ("x", 3), ("x", 4)]


def in_tile_table():
    """TILE[ly][lx] = the dword index inside a 32 x 16 tile, from the bit list ORDER."""
    t = [[0] * 32 for _ in range(16)]
    for ly in range(16):
        for lx in range(32):
            v = 0
            for pos, (axis, bit) in enumerate(ORDER):
                src = lx if axis == "x" else ly
                v += ((src >> bit) & 1) << pos
            t[ly][lx] = v
    assert sorted(v for row in t for v in row) == list(range(512))     # a permutation
    return t


TILE = in_tile_table()


def rule(x, y, g):
    return 512 * ((y >> 4) * (g + 1) + (x >> 5)) + TILE[y & 15][x & 31]


def load(path):
    a = array.array("I")
    with gzip.open(path, "rb") as fh:
        a.frombytes(fh.read())
    return a


def flt(v):
    return struct.unpack("<f", struct.pack("<I", v))[0]


def decode(v, scale):
    """(pixel index or None) of a stored ramp dword: z = 0.25 + 0.5 * (p + 0.5) / (3 * size)."""
    p = (flt(v) - 0.25) * 6 * scale
    q = round(p - 0.5)
    return q if abs(p - 0.5 - q) <= 0.05 else None


def case(dd, name, w, h, g):
    ax = load(os.path.join(dd, "%s-%dx%d-G%d-rampx.bin.gz" % (name, w, h, g)))
    ay = load(os.path.join(dd, "%s-%dx%d-G%d-rampy.bin.gz" % (name, w, h, g)))
    assert len(ax) == len(ay)
    tw, th = (w + 31) // 32, (h + 15) // 16
    n = ok = bad = bg = undecodable = 0
    und_vals = {}
    slots = set()
    for i, vx in enumerate(ax):
        if vx == FILL:
            continue
        vy = ay[i]
        n += 1
        slots.add(i >> 9)
        if vx == BG and vy == BG:
            bg += 1
            continue
        px, py = decode(vx, w), decode(vy, h)
        if px is None or py is None:
            undecodable += 1
            und_vals[(vx, vy)] = und_vals.get((vx, vy), 0) + 1
            continue
        if rule(px, py, g) == i:
            ok += 1
        else:
            bad += 1
    want = {ty * (g + 1) + tx for ty in range(th) for tx in range(tw)}
    # the other direction, where no two tiles share an address
    back = back_bad = None
    if g + 1 >= tw:
        back = back_bad = 0
        for y in range(h):
            for x in range(w):
                i = rule(x, y, g)
                if ax[i] != FILL and decode(ax[i], w) == x and decode(ay[i], h) == y:
                    back += 1
                else:
                    back_bad += 1
        back_bad_n = back_bad
    return dict(n=n, ok=ok, bad=bad, bg=bg, und=undecodable, slots=len(slots), want=len(want),
                slotset=slots == want, und_vals=und_vals, window=512 * ((th - 1) * (g + 1) + tw), back=back,
                back_bad=back_bad)


def main():
    dd = sys.argv[1]
    ref = {}
    if len(sys.argv) > 2:
        for l in open(sys.argv[2]):
            m = re.match(r"(fit|ho) (\d+)x(\d+) G=(\d+) .*changed (\d+), slots (\d+), .*not at the "
                         r"predicted address (\d+), background outside the target (\d+)", l)
            if m:
                k = (m[1], int(m[2]), int(m[3]), int(m[4]))
                ref[k] = tuple(int(m[i]) for i in (5, 6, 7, 8))
    names = sorted(glob.glob(os.path.join(dd, "*-rampx.bin.gz")))
    mism = 0
    for p in names:
        m = re.match(r"(fit|ho)-(\d+)x(\d+)-G(\d+)-rampx", os.path.basename(p))
        name, w, h, g = m[1], int(m[2]), int(m[3]), int(m[4])
        r = case(dd, name, w, h, g)
        line = ("%-3s %4dx%-4d G=%-3d stored %7d | at the rule's address %7d, not %6d, background %5d, "
                "undecodable %d | slots %d of %d (sets equal %s)" % (
                    name, w, h, g, r["n"], r["ok"], r["bad"], r["bg"], r["und"], r["slots"],
                    r["want"], r["slotset"]))
        if r["back"] is not None:
            line += " | pixels at their address %d, not %d" % (r["back"], r["back_bad"])
        k = (name, w, h, g)
        if k in ref:
            # the run script counts every dword it cannot place as "not at the predicted address"
            same = (r["n"], r["slots"], r["bad"] + r["und"], r["bg"]) == ref[k]
            line += " | run script's line: %s" % ("same" if same else "DIFFERS %r" % (ref[k],))
            mism += not same
        print(line, flush=True)
        if r["und_vals"]:
            top = sorted(r["und_vals"].items(), key=lambda kv: -kv[1])[:3]
            print("      undecodable dwords (x-ramp value, y-ramp value: count): " + ", ".join(
                "0x%08x, 0x%08x: %d" % (a, b, c) for (a, b), c in top) +
                  " (%d distinct pairs)" % len(r["und_vals"]), flush=True)
    print("cases %d, differing from the run script's lines: %d" % (len(names), mism))


if __name__ == "__main__":
    main()
