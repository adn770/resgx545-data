"""models.py: r7-geo's frozen models (round 7 session r7-geo of closing7/rank/rank-round7.md R7-2..R7-5, DECISIONS-R7 R7-2 a,
R7-7 a).  Pure functions, no I/O (but the byte copies it imports); the generator, the scorers, the fake laptop and the tests all
import this one file, frozen with them.  numpy (the session venv's; scratch, as HACKING allows for session scripts).

Q206 both-axes clause (transfer; E876, E884; stage xf).  The fill's end-of-tile DOUTU1 (pds:pixev dword 12) XORed with V, whose
    bits 11:3 are the x field (V_x / 8 half-tile units) and bits 21:12 the y field (V_y / 0x1000).  E884 (held out, single axis):
    tile t of an axis is stored at (2t | f) >> 1 (M-OR), nothing outside the target, unstored pixels keep 0xdeadbeef.
    H-INDEP: both fields act, each axis by M-OR independently.  H-XFIRST: only the x field acts when both move.  H-YFIRST (the
    other one-field reading, frozen beside it as a rival the scorer can pick): only the y field acts.
Q283 / Q178 texture types (texture; E725, E567, E894; stage tx).  E725's map-texture fill: a 64 x 32 fill, pixel (x, y) samples
    texel (x mod w, y mod h) of a w x h texture (repeat), the scratch buffer's dword i is 0xD0000000 | i, so a pixel that reads a
    texel names its offset.  Types 1 and 3: RASTERW (offset (y mod h) w + (x mod w), E725 held out at 8 to 32 wide).  Type 4
    rivals: S32 (stride 32, E725 fitted), SMAXW (stride max(32, w)), S2WCAP (stride min(2 w, 64): Q283's own rival), RASTERW,
    RASTER2W (stride 2 w, E725's frozen "raster w" for type 4).  Type 5 (E894 [infer]): H-STEP, 0 where x mod w < w / 2 and
    0x0000ffff above, constant in y and independent of the texture memory; rival H-FIX16 (the step of E567's 16 x 16 at every
    size: x mod 16 < 8); the memory controls at 16 x 16 (the texture zeroed, all ones) against H-MEM (the image follows the
    memory: any difference from the plain 16 x 16 image).
Q262 / Q240 coverage, depth and iteration (isp; E606, E607, E680; stages zd, zf).  Coverage: E606's rule (the vertices on the 1/256
    grid, the exact centre test, an edge owns a sample on it iff dy < 0, or dy == 0 and dx > 0 after one winding) = model1140.py's
    coverage (a byte copy of resgx545-data isp/coverage-envelope/recompute/model1140.py) with no rounding (vertices on the grid).
    The colour image is 0xff00ff00 where covered and 0xff203040 elsewhere; the tool prints its FNV-1a 64 hash (fnv) and the count of
    triangle pixels.  Depth (E606, E465's layout, pitch G = tiles across - 1, r3_geo.py a byte copy of round 3's): the whole tile
    area of the target is written (no 0xdeadbeef left in it), nothing outside it; a dword is below 1.0 iff its pixel is covered;
    a covered pixel holds the plane through the vertices' (x, y, z) at the pixel centre within 3 units of 2^-23 (DEPTH_TOL) where
    the plane's gradient |dz/dx| + |dz/dy| is below 0.03 (every case here is generated so).  Iteration (E606's I0 probe): pa0 is
    the plane of the vertices' clip z (2 z - 1) at the centre within 4 units (ITER_TOL) where the value range per root area is
    below 0.05 (every case here is generated so); uncovered pixels keep 0xff203040.
Q260 negative coordinates (isp; E683, E681, E607; stage zs).  Vertices in 1/4096 pixel (tool --tri-unit 12); every coordinate is put
    on the 1/256 grid by a rounding of n (1/4096 units, g = 16), then E606's exact test.  HU: floor((n + 8) / 16) (E607, E681 at
    x >= 0).  HA: HU for n >= 0, floor((n + 7) / 16) for n < 0 (half away from zero, E683's best; at 1/4096 it IS the threshold
    7/16 of E683's scan, so H-T7 is not a separate rival here).  SETUP(c): HU for n >= 0, floor((n + c) / 16) for n < 0 with one c
    in 0..15 fitted on the -0.5 x sweeps only (c = 8 is HU, c = 7 is HA) and scored on every other sweep.  FAR: HU, except a
    coordinate beyond the far edge (x > W, y > H) rounded half down (the positive mirror of HA's sign rule); only the far-side
    sweeps separate it.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import os  # noqa: E402
import random  # noqa: E402
from fractions import Fraction  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model1140 as CV  # noqa: E402
import r3_geo as G  # noqa: E402
import texbuild as TB  # noqa: E402
import texcatalog as TC  # noqa: E402

GREEN, BG, FILL, ONE = 0xFF00FF00, 0xFF203040, 0xDEADBEEF, 0x3F800000
U = 2.0 ** -23
DEPTH_TOL, ITER_TOL = 3.0, 4.0
GRAD_MAX, RANGE_MAX = 0.03, 0.05


def fnv(dwords):
    """libsgxfive sgxfive_hash_dwords: FNV-1a 64 over the dwords' bytes, little endian, row after row."""
    v, mask = 0xCBF29CE484222325, 0xFFFFFFFFFFFFFFFF
    for b in np.asarray(dwords, dtype="<u4").tobytes():
        v = ((v ^ b) * 0x100000001B3) & mask
    return v


def sha_list(dwords):
    return hashlib.sha256(",".join("%08x" % (int(d) & 0xFFFFFFFF) for d in dwords).encode()).hexdigest()


def sha_text(t):
    return hashlib.sha256(t.encode()).hexdigest()


# ================================================================================================================ Q206 (xf)
FCOL = 0xFF336699
TW, TH = 32, 16
UNIT = {"x": 8, "y": 0x1000}


def split_poke(v):
    """(x field, y field) in half-tile units of a DOUTU1 XOR value."""
    return (v & 0xFF8) // 8, (v & 0x3FF000) // 0x1000


def fill_tiles(w, h, fx, fy, model):
    """The (tile x, tile y) places stored for a poke of fx, fy field units: model INDEP | XFIRST | YFIRST | OR1 (one axis)."""
    if model == "XFIRST" and fx:
        fy = 0
    if model == "YFIRST" and fy:
        fx = 0
    nx, ny = w // TW, h // TH
    st = set()
    for tx in range(nx):
        for ty in range(ny):
            px, py = (2 * tx | fx) >> 1, (2 * ty | fy) >> 1
            if px < nx and py < ny:
                st.add((px, py))
    return st


def fill_image(w, h, fx, fy, model):
    st = fill_tiles(w, h, fx, fy, model)
    return [FCOL if (x // TW, y // TH) in st else FILL for y in range(h) for x in range(w)]


def fill_predict(w, h, v, model):
    fx, fy = split_poke(v)
    img = fill_image(w, h, fx, fy, model)
    return fnv(img), sum(1 for p in img if p != FCOL)


def fill_args(w, h, v=None):
    a = "fill --width %d --height %d --stride %d" % (w, h, 4 * w)
    if v:
        a += " --poke 'pds:pixev:12^=0x%x'" % v
    return a


# ================================================================================================================ textures (tx)
T0_REP = TC.T0_REP
T3_TW = 0x00800800


def tex_spec(ty, w, h, inject=None):
    """E725's spec of a type-ty w x h texture read through window(w, h) (catalog.window: texel (x mod w, y mod h) at pixel (x, y))."""
    u, v = TC.window(w, h)
    s = dict(base=0, t0=T0_REP, t1=TC.t1tw(w, h, 12, ty), t3=T3_TW, u=u, v=v, ins="none")
    if inject:
        s["inject"] = {str(k): val for k, val in inject.items()}
    return s


def tex_text(template, spec):
    pre, setup, smp = TB.case_inputs(spec)
    return template.replace("{PRE}", pre).replace("{SETUP}", setup).replace("{SMP}", smp)


STRIDES = {"RASTERW": lambda w: w, "RASTER2W": lambda w: 2 * w, "S32": lambda w: 32, "SMAXW": lambda w: max(32, w),
           "S2WCAP": lambda w: min(2 * w, 64), "FIX16": lambda w: 16}
TYPE_HYPS = {1: ("RASTERW", "S32", "FIX16"), 3: ("RASTERW", "S32", "FIX16"),
             4: ("S32", "SMAXW", "S2WCAP", "RASTERW", "RASTER2W")}


def tex_image(hyp, w, h):
    """The 64 x 32 fill (raster order) under a layout hypothesis."""
    if hyp == "FIX16":
        return [0xD0000000 | ((y % h) % 16) * 16 + (x % w) % 16 for y in range(32) for x in range(64)]
    s = STRIDES[hyp](w)
    return [0xD0000000 | ((y % h) * s + (x % w)) for y in range(32) for x in range(64)]


def type5_image(hyp, w):
    if hyp == "H-STEP":
        return [0 if (x % w) < w // 2 else 0x0000FFFF for y in range(32) for x in range(64)]
    if hyp == "H-FIX16":
        return [0 if (x % 16) < 8 else 0x0000FFFF for y in range(32) for x in range(64)]
    raise ValueError(hyp)


# ================================================================================================================ coverage
def cover(v256, w, h):
    """E606's coverage of a triangle with vertices on the 1/256 grid: (h, w) bool."""
    return CV.coverage(np.asarray(v256, dtype=np.int64).reshape(3, 2), 8, w, h, "NONE")


def image_hash(cov):
    """The tool's hash of the colour image (0xff00ff00 covered, 0xff203040 not); None above 4 M pixels (the generator does not
    hash 4096 x 4096: the triangle count and the depth dump decide those)."""
    if cov.size > 4 * 1024 * 1024:
        return None
    return fnv(np.where(cov.ravel(), GREEN, BG).astype("<u4"))


def cov_sha(cov):
    """sha256 of a covered image's bytes (one byte a pixel, 1 covered, row after row): the scorers compare images by it."""
    return hashlib.sha256(np.asarray(cov, dtype=np.uint8).tobytes()).hexdigest()


# ---- rounding of 1/4096 coordinates (Q260)
def rnd(n, variant, far=None, c=None):
    """n: integer in 1/4096 pixel -> 1/256.  far: the far edge in 1/4096 (W or H) for FAR."""
    n = int(n)
    if variant == "HU":
        return (n + 8) // 16
    if variant == "HA":
        return (n + 8) // 16 if n >= 0 else (n + 7) // 16
    if variant == "SETUP":
        return (n + 8) // 16 if n >= 0 else (n + c) // 16
    if variant == "FAR":
        return -((-n + 8) // 16) if far is not None and n > far else (n + 8) // 16
    raise ValueError(variant)


RIVALS = ("HU", "HA", "FAR")          # plus SETUP(c), c fitted by the scorer


def cover4096(v4096, w, h, variant, c=None):
    v = [rnd(n, variant, far=(w if i % 2 == 0 else h) * 4096, c=c) for i, n in enumerate(v4096)]
    return cover(v, w, h)


# ---- depth and iteration planes (E606)
def plane(v256, vals):
    """(a, b, c) of the plane val = a x + b y + c through the vertices (x, y in pixels)."""
    p = [(Fraction(v256[2 * i], 256), Fraction(v256[2 * i + 1], 256), Fraction(vals[i])) for i in range(3)]
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = p
    d = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    a = ((z1 - z0) * (y2 - y0) - (z2 - z0) * (y1 - y0)) / d
    b = ((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / d
    return a, b, z0 - a * x0 - b * y0


def gradient(v256, z):
    a, b, _ = plane(v256, z)
    return float(abs(a) + abs(b))


def area_px(v256):
    x0, y0, x1, y1, x2, y2 = [Fraction(t, 256) for t in v256]
    return abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2


def value_range_per_root_area(v256, z):
    cz = [2 * t - 1 for t in z]
    ar = float(area_px(v256))
    return (max(cz) - min(cz)) / ar ** 0.5 if ar > 0 else float("inf")


def plane_image(v256, vals, w, h):
    a, b, c = (float(t) for t in plane(v256, vals))
    ys, xs = np.mgrid[0:h, 0:w]
    return a * (xs + 0.5) + b * (ys + 0.5) + c


def depth_index(w, h):
    """(h, w) dword index of each pixel in E465's layout at pitch G = tiles across - 1 (r3_geo.dword_index, vectorised)."""
    g = G.pitch_g(w)
    ys, xs = np.mgrid[0:h, 0:w]
    lx, ly = xs % 32, ys % 16
    low = np.zeros((h, w), dtype=np.int64)
    for k, (arr, b) in enumerate([(ly, 0), (lx, 0), (ly, 1), (lx, 1), (ly, 2), (lx, 2), (ly, 3), (lx, 3)]):
        low |= ((arr >> b) & 1) << k
    low |= ((lx >> 4) & 1) << 8
    return 512 * ((ys // 16) * (g + 1) + xs // 32) + low


def tile_area_words(w, h):
    """The dwords of the tile area (every tile the target touches), as a sorted index array."""
    aw, ah = G.area(w, h)
    return np.sort(depth_index(aw, ah).ravel()) if G.pitch_g(aw) == G.pitch_g(w) else None


def f32(u):
    return np.asarray(u, dtype=np.uint32).view(np.float32).astype(np.float64)


# ---- random triangles (E606's generator, gen_p1138.py's tri_box made to fit small targets)
def zs_flat(r, v256, lim):
    """three depths (multiples of 1/1024 in (0, 1)) whose plane's gradient is below 0.03 and, if lim, whose clip-z range per root
    area is below 0.05; None if none was found in 400 draws."""
    for _ in range(400):
        z0 = r.randrange(51, 972)
        span = r.choice([0, 1, 2, 4, 8, 16, 32])
        zz = [z0, z0 + r.randint(-span, span), z0 + r.randint(-span, span)]
        if min(zz) < 1 or max(zz) > 1023:
            continue
        z = [Fraction(t, 1024) for t in zz]
        if gradient(v256, z) >= GRAD_MAX * 0.95:
            continue
        if lim and value_range_per_root_area(v256, z) >= RANGE_MAX * 0.95:
            continue
        return z
    return None


def tri_case(r, w, h, cls):
    """vertices (1/256) inside the target, a box of span 1 to 4 (small) or 8 to 40 pixels (medium, clipped to the target less 4 on
    each axis), a non-zero area, at least one pixel centre covered (the depth and iteration need one); depths flat enough for
    E606's tolerance."""
    while True:
        if cls == "small":
            sx = sy = r.choice([1.0, 2.0, 3.0, 4.0])
        else:
            lx, ly = min(40.0, w - 4.0, w / 3.0 if w >= 24 else w - 4.0), min(40.0, h - 4.0, h / 3.0 if h >= 24 else h - 4.0)
            sx, sy = r.uniform(min(8.0, lx), lx), r.uniform(min(8.0, ly), ly)
        sx, sy = min(sx, w - 4.0), min(sy, h - 4.0)
        bx, by = r.uniform(2, w - sx - 2), r.uniform(2, h - sy - 2)
        v = []
        for _ in range(3):
            v += [int((bx + r.uniform(0, sx)) * 256), int((by + r.uniform(0, sy)) * 256)]
        if area_px(v) * 256 * 256 < 64:      # at least 1/1024 px^2: not degenerate
            continue
        if not cover(v, w, h).any():     # a triangle that covers no pixel centre tests no depth: drawn again
            continue
        z = zs_flat(r, v, lim=True)
        if z is not None:
            return v, z


def ztext(z):
    return ",".join("%.10f" % float(t) for t in z)


def depth_args(w, h, v, z, pixels):
    return ("tri --keep-overflow --wait-ms 20000 --width %d --height %d --tri-v %s --tri-z %s --depth --depth-ctl 0x%x "
            "--depth-fill 0xdeadbeef --depth-dump \"$W/depth\" --depth-pages %d --poke blk:1=0x00400200%s"
            % (w, h, ",".join(map(str, v)), ztext(z), G.depth_ctl(w), G.depth_pages(w, h), " --pixels" if pixels else ""))


def iter_args(w, h, v, z):
    return ("probe --tri pixpds:12 --temps 32 --pixels --width %d --height %d --tri-v %s --tri-z %s --vtx-coords 2 "
            "--slot pixel=\"$S/pix_pa0.bin\" --slot vtxuse=\"$S/vtx_attr_zx.bin\" \"$S/p1138-it-a0__0.bin\""
            % (w, h, ",".join(map(str, v)), ztext(z)))


# ---- Q260 sweeps
SW, SH = 512, 256                      # the sweeps' target (E683's and E680's fit size)
# the pixel centre C each sweep aims through, along the swept axis: the nearest on-screen centre (1 pixel from -0.5, 4 from
# -3.5, 1 from +0.5, 1 from the far side W + 0.5 / H + 0.5) or 100 pixels away (-64.5 -> 35.5, +64.5 -> 164.5)
POSITIONS = (-0.5, -3.5, -64.5, 0.5, 64.5, "far")


def aim(pos, n):
    """(the swept coordinate in pixels, the aimed centre's pixel index, C's offset on the other axis in pixels); n: W or H."""
    p = n + 0.5 if pos == "far" else pos
    c = {-0.5: 0, -3.5: 0, -64.5: 35, 0.5: 1, 64.5: 164}.get(pos, n - 1)
    off = 30 if pos in (-64.5, 64.5) else 3
    return p, c, off


def sweep_case(pos, axis, d, W=SW, H=SH):
    """One step of a Q260 sweep: vertex A's swept coordinate is p * 4096 + 8 + d (1/4096 pixel; d = 0 the tie 1/512 above the grid
    point p), its other coordinate the centre of pixel 40; the edge A-B aimed through the pixel centre C (aim()), B = C + 2 (C - A_tie)
    on the ray beyond C (on the 1/256 grid: C is on it and 2 (C - A_tie) is a multiple of 16); the third vertex T 40 pixels beyond B
    on the swept axis, level with A.  Every coordinate but A's swept one is on the 1/256 grid.  The six coordinates in 1/4096."""
    p, c, off = aim(pos, W if axis == "x" else H)
    g = int(round(p * 4096))
    tie, at = g + 8, g + 8 + d
    c_main, other = c * 4096 + 2048, 40 * 4096 + 2048
    c_other = other + off * 4096
    b_main, b_other = c_main + 2 * (c_main - tie), c_other + 2 * (c_other - other)
    t_main = b_main + (40 if b_main >= c_main else -40) * 4096
    if axis == "x":
        return [at, other, b_main, b_other, t_main, other]
    return [other, at, b_other, b_main, other, t_main]


def sweep_args(W, H, v):
    return "tri --keep-overflow --wait-ms 20000 --width %d --height %d --tri-unit 12 --tri-v %s --pixels" % (W, H, ",".join(map(str, v)))


def grid16(n):
    return (int(n) + 8) // 16 * 16


def nontie_case(r, W=SW, H=SH):
    """E683's construction with exactly one coordinate off the 1/256 grid, negative, its fraction away from the tie (n mod 16 not
    0, 7, 8 or 9): A, a pixel centre C on screen, B = C + 2 (C - A) put on the grid (the edge passes within 1/4096 pixel of C), a
    third vertex 20 to 40 pixels off the line; the other five coordinates on the grid."""
    while True:
        axis = r.choice("xy")
        mag = r.choice([r.uniform(0.01, 2.0), r.uniform(2.0, 30.0), r.uniform(30.0, 100.0)])
        n = -int(mag * 4096)
        if (n % 16) in (0, 7, 8, 9):
            continue
        no = H if axis == "x" else W
        oth = r.randrange(40, no - 40) * 4096 + 2048
        cm = r.randrange(0, 24) * 4096 + 2048
        co = oth + r.randrange(-6, 7) * 4096
        bm, bo = grid16(cm + 2 * (cm - n)), grid16(co + 2 * (co - oth))
        side = r.choice([-1, 1]) * r.randrange(20, 40) * 4096
        tm, to = grid16((n + bm) // 2), oth + side
        v = [n, oth, bm, bo, tm, to] if axis == "x" else [oth, n, bo, bm, to, tm]
        a2 = (v[2] - v[0]) * (v[5] - v[1]) - (v[4] - v[0]) * (v[3] - v[1])
        if abs(a2) < 20 * 4096 * 4096:
            continue
        if sum(1 for x in v if x % 16) == 1:
            return v, axis
