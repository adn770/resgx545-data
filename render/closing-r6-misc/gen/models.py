"""models.py: r6-misc's frozen models (round 6 session A of closing6/rank/rank-round6.md, DECISIONS-R6 R6-2 a).
Pure functions, no I/O; the generator, the scorers, the fake laptop and the tests all import this one file (frozen with them).

Q289 (transfer; E876, post hoc on the kept 64 x 32 sweeps; held out here).  The fill's end-of-tile DOUTU1 x field (bits 11:3) or
    y field (bits 21:12) poked by XOR with a constant whose value in field units is f (x: V / 8, y: V / 0x1000).  Reading f in
    half-tile units, tile t (per axis, 32 x 16 tiles) is stored at op(2t, f) >> 1, and nothing is stored where that lies outside
    the target; unstored pixels keep the tool's sentinel 0xdeadbeef.  M-OR: op = |; M-ADD: op = +; M-XOR (refuted by E876, kept
    as the scorer's negative control).  The tool prints the target's FNV-1a 64 hash over its dwords row after row
    (libsgxfive sgxfive_hash_dwords, poke.c:127), the count of pixels that differ from the CPU reference and the dwords written
    outside the target.
Q287 (zls; E730, E831): r3_geo.py, a byte copy of round 3's published model (render/closing-r3-geo-c/gen/r3_geo.py), gives the
    band rules A, FLOOR, ROUND, CEIL, RSTRICT, the depth pages, the depth control word and the dump reader.
Q086 (ta; E507, E511, E824): rules1126.py, a byte copy of E511's published rules (ta/mtile-msaa-risky/analysis/rules.py), gives
    the single-sampled rule's words (R) and the field readers.  H-COV [infer, post hoc on E511's 6 jobs, 6 of 6]: a 4x render
    with poked macrotile words completes iff the macrotile grid the words describe covers the target's 1x tile grid on both axes,
    the covered extent being B3 + B1 tiles (the last boundary plus one more macrotile of the first's size; n = 2: 2 mx, n = 4:
    4 mx); otherwise the job faults on the 3D side (E511: BIF_INT_STAT 0x90100 at 0x10000012..0x10000016).  Rival H-ANY: with
    the four region-header arrays every word set completes (the reading E824 opened, "the skipped cases can now run").
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import os  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r3_geo as G  # noqa: E402
import rules1126 as RU  # noqa: E402

# ---------------------------------------------------------------------------------------------------------------- Q289
COLOUR, SENT = 0xFF336699, 0xDEADBEEF
TW, TH = 32, 16
OPS = {"OR": lambda a, b: a | b, "ADD": lambda a, b: a + b, "XOR": lambda a, b: a ^ b}
UNIT = {"x": 8, "y": 0x1000}


def fnv(dwords):
    v = 0xCBF29CE484222325
    for d in dwords:
        for b in range(4):
            v ^= (d >> (8 * b)) & 0xFF
            v = (v * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return v


def fill_tiles(w, h, axis, f, op):
    """The set of (tile x, tile y) places stored under the model, for a poke of f field units on one axis."""
    nx, ny = w // TW, h // TH
    st = set()
    for tx in range(nx):
        for ty in range(ny):
            px = OPS[op](2 * tx, f) >> 1 if axis == "x" else tx
            py = OPS[op](2 * ty, f) >> 1 if axis == "y" else ty
            if px < nx and py < ny:
                st.add((px, py))
    return st


def fill_image(w, h, axis, f, op):
    st = fill_tiles(w, h, axis, f, op)
    return [COLOUR if (x // TW, y // TH) in st else SENT for y in range(h) for x in range(w)]


def fill_predict(w, h, axis, f, op):
    """(hash, wrong pixels, unwritten tile columns (x) or rows (y)) of one model."""
    img = fill_image(w, h, axis, f, op)
    n = w // TW if axis == "x" else h // TH
    st = fill_tiles(w, h, axis, f, op)
    places = {p[0] for p in st} if axis == "x" else {p[1] for p in st}
    return fnv(img), sum(1 for v in img if v != COLOUR), [t for t in range(n) if t not in places]


def poke_field(axis, value):
    assert value % UNIT[axis] == 0
    return value // UNIT[axis]


def fill_args(w, h, axis=None, value=None):
    a = "fill --width %d --height %d --stride %d" % (w, h, 4 * w)
    if axis:
        a += " --poke 'pds:pixev:12^=0x%x'" % value
    return a


# ---------------------------------------------------------------------------------------------------------------- Q287
ZW = 34


def depth_args(w, h, ramp):
    """E730/E831's isp-a-guard row, token for token, at another size (r3_geo's pitch and pages)."""
    z = G.RAMP_X if ramp == "x" else G.RAMP_Y
    return ("tri --keep-overflow --wait-ms 20000 --width %d --height %d --tri-full --tri-z %s --depth --depth-ctl 0x%x "
            "--depth-fill 0xdeadbeef --depth-dump \"$W/depth\" --depth-pages %d --poke blk:1=0x00400200"
            % (w, h, z, G.depth_ctl(w), G.depth_pages(w, h)))


def band(rule, w, h):
    return G.band_set(rule, w, h)


def set_sha(pts):
    return G.set_sha(pts)


# ---------------------------------------------------------------------------------------------------------------- Q086
POS = 0xEAA26E26
TILES_4X = lambda w, h: (-(-w // 32), -(-h // 16))  # noqa: E731  (the 1x tile grid: E511's fit)


def q086_words(w, h, kp):
    """(mtile1, mtile2, stride) the job runs with: the kpoked words over the rule's (R)."""
    r = RU.words(w, h)
    return kp.get(143, r[0]), kp.get(144, r[1]), kp.get(146, r[2])


def coverage(m1, m2):
    f1, f2 = RU.fields1(m1), RU.fields2(m2)
    return f1[3] + f1[1], f2[2] + f2[0]


def hcov_completes(w, h, kp):
    m1, m2, _ = q086_words(w, h, kp)
    cx, cy = coverage(m1, m2)
    tx, ty = TILES_4X(w, h)
    return tx <= cx and ty <= cy


def q086_args(w, h, kp):
    a = ("tri --tri-full --keep-going --wait-ms 20000 --pixels --width %d --height %d --max-width %d --max-height %d --aa4 "
         "--poke cmd:1=0xe0000000 --poke cmd:10=0x%x --poke cmd:13=0x80000002 --poke cmd:16=0x%x" % (w, h, w, h, POS, POS))
    for i in sorted(kp):
        a += " --kpoke-render 1:ta:%d=0x%08x" % (i, kp[i]) if i != 146 else " --kpoke-render 1:ta:146=0x%x" % kp[i]
    return a


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()
