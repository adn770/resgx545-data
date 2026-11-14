# SPDX-License-Identifier: MIT
"""model.py: r16-mte's rows and frozen forms of Q116 (the MTE state's region clip, presence bit 7,
two words after the pixel programs: E347, E348). Standard library only; the generator, the scorer,
the mock and the tests import it (frozen with the session).

Frame. Every pixel is (x, y) of the probe's `row y:` lines, y the target's memory row. The tool's
viewport has a positive y scale (render.c sgxfive_tri_block: vp3 = H / 2), and its CPU reference
puts window y at memory row y (sgxfive_tri_check, unflipped; every diff-0 tri job, e.g. r13-flag's
f3-shape-a: 0 wrong, "2709 if flipped"). E348's closed-driver words are y up with a positive scale
too (vp2 = y + h / 2), so its "rows counted from the bottom of the GL target" are window rows from
y = 0: our memory rows from 0 [infer]. That is H-TILECLIP's origin here; H-FLIP counts the tile
rows from the target's last tile row (the plan's literal "from the bottom" in memory).

Clip words (E348): c0 = enable << 31 | first column << 16 | last column (15:0), c1 = first row <<
16 | last row. Forms of the region a clip keeps (origin x bound x unit, and H-NOCLIP):
  H-TILECLIP  tiles of 32 x 16, first <= tile <= last, rows from memory row 0      (frozen, E348)
  H-EXCL      the same with the last bound exclusive
  H-FLIP      tile rows counted from the last tile row of the target (ceil(H / 16) - 1 - y // 16)
  H-FLIPEXCL  both
  H-PIXEL     the fields as pixel bounds (inclusive), rows from 0; H-PIXEXCL, H-PIXFLIP (row H-1-y),
              H-PIXFLIPEXCL
  H-NOCLIP    the words read and ignored
Outside the kept region: H-BG (the background object writes the pixel: 0xff203040, frozen) or
H-UNTOUCHED (left at the target's sentinel 0xdeadbeef). Enable (c0 bit 31): H-EN (clear: no clip,
frozen), H-ALWAYS (the bounds apply whatever bit 31), H-OFFDROP (clear: the object is dropped).

The object: the full triangle (--tri-full: (0, 0), (3W, 0), (0, 3H), every pixel) or the tool's
default triangle (v64 (8, 8), (56, 20), (20, 56) scaled by W / 64, H / 64): render.c's
sgxfive_tri_expect, 1 inside, 0 outside, -1 within a pixel of an edge (either colour)."""
import hashlib

GREEN, BG, SENTINEL = 0xFF00FF00, 0xFF203040, 0xDEADBEEF
CODE = {GREEN: "G", BG: "B", SENTINEL: "S"}
TW, TH = 32, 16

FORMS = ("H-TILECLIP", "H-EXCL", "H-FLIP", "H-FLIPEXCL", "H-PIXEL", "H-PIXEXCL", "H-PIXFLIP",
         "H-PIXFLIPEXCL", "H-NOCLIP")
OUTSIDES = ("H-BG", "H-UNTOUCHED")
ENABLES = ("H-EN", "H-ALWAYS", "H-OFFDROP")
FROZEN = ("H-TILECLIP", "H-BG", "H-EN")
# the frozen hypothesis' rivals, each one dimension away (scored and frozen per row)
RIVALS = tuple((f, "H-BG", "H-EN") for f in FORMS[1:]) + (
    ("H-TILECLIP", "H-UNTOUCHED", "H-EN"), ("H-TILECLIP", "H-BG", "H-ALWAYS"),
    ("H-TILECLIP", "H-BG", "H-OFFDROP"))


def combo_name(c):
    return "+".join(h[2:] for h in c)


def clip_words(c0, c1):
    """(enable, first column, last column, first row, last row)"""
    return c0 >> 31, (c0 >> 16) & 0x7FFF, c0 & 0xFFFF, c1 >> 16, c1 & 0xFFFF


def e348_clear(w, h):
    """E348's clear block clip over 222 target sizes: 0x80000000 | (W - 1) / 32, (H - 1) / 16"""
    return 0x80000000 | (w - 1) // 32, (h - 1) // 16


# name, set, W, H, full triangle, (c0, c1) or None (no --blk-add), what it is for
ROWS = (
    ("g-clear-64", "control", 64, 64, True, e348_clear(64, 64),
     "gate: E348's clear clip of the whole 64 x 64 target, equal to the no-clip image"),
    ("g-twin-64", "control", 64, 64, True, None, "the gate's no-clip twin (block 0xdf43)"),
    ("vp64-e348", "heldout", 64, 64, True, (0x80010001, 0x00010003),
     "E348's viewport 40,20,16,30 triangle clip: column 1, rows 1 to 3"),
    ("p64-c0-r23", "heldout", 64, 64, True, (0x80000000, 0x00020003), "one column, rows 2 to 3"),
    ("p64-c01-r0", "heldout", 64, 64, True, (0x80000001, 0x00000000), "two columns, row 0"),
    ("p128-c12-r12", "heldout", 128, 128, True, (0x80010002, 0x00010002),
     "columns 1 to 2, rows 1 to 2 of 8 (the plan's asymmetric rows)"),
    ("p128-c3-r04", "heldout", 128, 128, True, (0x80030003, 0x00000004),
     "the last column, rows 0 to 4"),
    ("e128-on-full", "heldout", 128, 128, True, e348_clear(128, 128),
     "enable set, the whole target's clip"),
    ("e128-off", "heldout", 128, 128, True, (0x00010002, 0x00020004),
     "enable clear (bit 31), a partial range: H-EN against H-ALWAYS, H-OFFDROP"),
    ("s128-tri", "heldout", 128, 128, False, (0x80000001, 0x00010003),
     "the default triangle (not full) cut by the clip edge mid-triangle"),
    ("p256-c2-r39", "heldout", 256, 256, True, (0x80020002, 0x00030009),
     "one column, rows 3 to 9 of 16"),
    ("p256-c56-r1015", "heldout", 256, 256, True, (0x80050006, 0x000A000F),
     "columns 5 to 6, rows 10 to 15 (the last rows)"),
    ("m256-c34-r59", "heldout", 256, 256, True, (0x80030004, 0x00050009),
     "four macrotiles (boundaries at column 4, row 8): columns 3 to 4, rows 5 to 9"),
    ("e100x60-c23-r23", "heldout", 100, 60, True, (0x80020003, 0x00020003),
     "100 x 60 (E348's size): the edge tiles, column 3 (4 pixels) and row 3 (12 rows)"),
    ("z128-empty", "heldout", 128, 128, False, (0x80030003, 0x00040007),
     "LAST: a clip that holds no tile of the default triangle (no region list of the object)"),
)
NAMES = tuple(r[0] for r in ROWS)


def row(name):
    r = ROWS[NAMES.index(name)]
    return dict(name=r[0], set=r[1], w=r[2], h=r[3], full=r[4], clip=r[5], why=r[6])


def default_vertices(w, h):
    """render.c sgxfive_tri_default: v64 scaled, in 1/16 pixel"""
    v64 = ((8, 8), (56, 20), (20, 56))
    return tuple((x * 16 * w // 64, y * 16 * h // 64) for x, y in v64)


def tri_expect(v, x, y):
    """render.c sgxfive_tri_expect, line for line: 1 inside, 0 outside, -1 within 1 px of an edge"""
    px, py = x * 16 + 8, y * 16 + 8
    area = (v[1][0] - v[0][0]) * (v[2][1] - v[0][1]) - (v[1][1] - v[0][1]) * (v[2][0] - v[0][0])
    near = False
    for i in range(3):
        p0, p1 = v[i], v[(i + 1) % 3]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        e = dx * (py - p0[1]) - dy * (px - p0[0])
        if area < 0:
            e = -e
        if e * e < 256 * (dx * dx + dy * dy):
            near = True
        elif e < 0:
            return 0
    return -1 if near else 1


_OBJ = {}


def object_map(r):
    """per pixel 1 / 0 / -1 (raster order)"""
    key = (r["w"], r["h"], r["full"])
    if key not in _OBJ:
        w, h = r["w"], r["h"]
        if r["full"]:
            _OBJ[key] = (1,) * (w * h)
        else:
            v = default_vertices(w, h)
            _OBJ[key] = tuple(tri_expect(v, x, y) for y in range(h) for x in range(w))
    return _OBJ[key]


def kept(form, words, w, h, x, y):
    """whether the clip's region under form holds pixel (x, y)"""
    return keep_x(form, words, w, x) and keep_y(form, words, h, y)


def _in(form, a, b, c):
    return a <= c < b if "EXCL" in form else a <= c <= b


def keep_x(form, words, w, x):
    if form == "H-NOCLIP":
        return True
    return _in(form, words[1], words[2], x if form.startswith("H-PIX") else x // TW)


def keep_y(form, words, h, y):
    if form == "H-NOCLIP":
        return True
    if form.startswith("H-PIX"):
        cy = h - 1 - y if "FLIP" in form else y
    else:
        cy = (h + TH - 1) // TH - 1 - y // TH if "FLIP" in form else y // TH
    return _in(form, words[3], words[4], cy)


_PRED = {}


def predict(r, combo):
    """the allowed codes per pixel: 'G', 'B', 'S' or 'g' (G or B: an edge pixel), raster order"""
    key = (r["w"], r["h"], r["full"], r["clip"], tuple(combo))
    if key in _PRED:
        return _PRED[key]
    form, outside, enable = combo
    w, h = r["w"], r["h"]
    obj = object_map(r)
    clip = r["clip"]
    words = clip_words(*clip) if clip else None
    drop = False
    if words is None or (words[0] == 0 and enable == "H-EN"):
        form = "H-NOCLIP"
    elif words[0] == 0 and enable == "H-OFFDROP":
        drop = True
    kx = [keep_x(form, words, w, x) for x in range(w)]
    out_code = "S" if outside == "H-UNTOUCHED" else "B"
    inside = {1: "B" if drop else "G", 0: "B", -1: "B" if drop else "g"}
    out = []
    for y in range(h):
        ky = keep_y(form, words, h, y)
        base = y * w
        out.append("".join(inside[obj[base + x]] if ky and kx[x] else out_code for x in range(w)))
    _PRED[key] = "".join(out)
    return _PRED[key]


def allowed(p):
    return {"G": "G", "B": "B", "S": "S", "g": "GB"}[p]


def matches(pred, obs):
    """obs: a code string (G, B, S, X); True when every pixel is one the prediction allows"""
    if obs is None or len(obs) != len(pred):
        return False
    if "g" not in pred:
        return pred == obs
    return all(o == p or (p == "g" and o in "GB") for p, o in zip(pred, obs))


def parts(a, b):
    """pixels two predictions cannot share (their allowed sets disjoint)"""
    return sum(1 for p, q in zip(a, b) if not set(allowed(p)) & set(allowed(q)))


def codes(px):
    return "".join(CODE.get(v, "X") for v in px)


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def partial(r):
    """a row whose clip is enabled and keeps part of the target under the frozen form (not the
    empty-clip row, which keeps none of the object)"""
    if not r["clip"] or not r["clip"][0] >> 31:
        return False
    p = predict(r, FROZEN)
    return "B" in p and "G" in p and r["name"] != "z128-empty"


def args(r):
    a = "probe --tri pixel --temps 32 --pixels --width %d --height %d" % (r["w"], r["h"])
    if r["full"]:
        a += " --tri-full"
    if r["clip"]:
        a += " --blk-add 7=0x%08x,0x%08x" % r["clip"]
    return a + ' "$S/bins/pix_green.bin"'
