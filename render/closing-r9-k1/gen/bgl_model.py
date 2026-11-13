# SPDX-License-Identifier: MIT
"""gen/bgl_model.py: r9-k1's frozen model of Q190's layered background (closing9/k1/exp-k1-r9.md
section 3; decisions K-1..K-6 (a)). Standard library only. gen/make.py draws the rows and the
predictions from it, score/score.py scores the kept records with it, mock/world.py paints its
images with it; the freeze pins it with the predictions.

The scene: the 64 x 64 one-triangle render (E590), the triangle 0xff00ff00, the library's
background 0xff203040 without the layer. The scored pixels are the 3034 background pixels of the
hardware's own image (gen/bgmask.txt, from E590's kept control b66f1-control-1, pinned; E437's
1062 triangle pixels): never the library mock's 2998 (its rasteriser is not the hardware's).

The kernel's one-layer object (fork fafea977), words 0-22: 0-2 the user's PDS words, 3-8 the
layer's coordinates (u0, v0, u1, v1, u2, v2 under H-VM: 0, 0, 1.0, 0, 0, 1.0), 9 = 0, 10 = 0x202
(the format word), 11-14 = 0, 15-22 the target rectangle's vertices in E590's encoding (TL, TR, BL
as 24-bit fixed point, 8 fraction bits, offset 4096; analysis/bg_geometry.py of
isp/bg-object-pokes, shifted by six words).

Models of a layer-sampling (L-TEX) image, each a texel map over the scored pixels:
  H-VM      coordinates vertex-major (TL, TR, BL), the plane anchored at the render box's corners
            (0, 0), (W, 0), (0, H) (H-VBOX): attribute = the plane at the pixel centre (x + 0.5,
            y + 0.5); texel = (floor(64 u), floor(64 v)), nearest
  H-VPLANE  as H-VM, the plane anchored at the vertices words 15-22 give (E590's decoding) [infer]
  H-LM      component-major: u0, u1, u2 = words 3, 4, 5; v0, v1, v2 = words 6, 7, 8
  H-SWAP    as H-VM with u and v exchanged
  H-NOREAD  the poke is not read: the control's image (identity texels)
  H-NONE    the layer's coordinates are not iterated: one texel everywhere ("const")
  H-17      the object read with the 17-word layout: coordinates from words 9-14 (0, 0x202, 0...):
            texel (0, 0) everywhere ("const:0,0")
  H-NOTEX   no pixel is a texel ("notex": the texel not delivered, Q066 word 1 at 0 rows)
A pixel whose 64 u or 64 v lies within 1/64 of a texel boundary (an edge) or outside [1/64,
64 - 1/64] (out of range: wrap and clamp are not modelled) is not predicted by that model."""
import gzip
import hashlib
import math
import os
import re
import struct
from fractions import Fraction

W = H = 64
SRC = 0x3e800000                # render_bg_src: 8 MiB above the general heap's first page
OBJ_OFF = 0x463000              # the background object in debugfs render_param's dump (E590)
TRI = 0xff00ff00                # the triangle's colour
BG = 0xff203040                 # the library's background (no layer)
HASH_OFF = "0x99385a04ee01c585"  # the layerless control's target hash (E590, 169 of 169)
ONE = 0x3f800000
# the layered object the kernel builds (fafea977), words 3-22; 0-2 are the user's (EDM-rewritten)
CTRL = {3: 0, 4: 0, 5: ONE, 6: 0, 7: 0, 8: ONE, 9: 0, 10: 0x202, 11: 0, 12: 0, 13: 0, 14: 0,
        15: 0x00100000, 16: 0x1000, 17: 0, 18: 0x10400010, 19: 0, 20: 0x00104000, 21: 0x1000,
        22: 0}
EDGE = Fraction(1, 64)          # in texels: E437's exactness, 2^-12 in coordinates at 64
RAW_TOL = 2.0 ** -12            # L-RAW: |read - model| in coordinate units
MIN_SCORED = 256                # a texel-map verdict needs at least this many predicted pixels
RIGHT_MISS = Fraction(1, 100)   # right: at most 1 % of the predicted pixels differ
WRONG_MISS = Fraction(1, 10)    # wrong: more than 10 % differ; between: cannot tell
RAW_RIGHT = 3000                # L-RAW and POS: right at >= 3000 of 3034 (plan H-POS)
RAW_WRONG = 2730                # wrong below 90 % (2730 of 3034); between: cannot tell
TEX_MODELS = ("H-VM", "H-VPLANE", "H-LM", "H-SWAP", "H-NOREAD", "H-NONE", "H-17", "H-NOTEX")
SPECIAL = {"H-NONE": "const", "H-17": "const:0,0", "H-NOTEX": "notex"}
HERE = os.path.dirname(os.path.abspath(__file__))
MASK = os.path.join(HERE, "bgmask.txt")


# ---- numbers ---------------------------------------------------------------------------------
def f32(b):
    return struct.unpack("<f", struct.pack("<I", b & 0xffffffff))[0]


def bits(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def frac(b):
    v = f32(b)
    return None if math.isnan(v) or math.isinf(v) else Fraction(v)


def texel(x, y):
    """The tool's source texel (sgxfive_bgl_texel): check byte, y, x."""
    return ((x ^ y ^ 0xa5) & 0xff) << 24 | (y & 0xfff) << 12 | (x & 0xfff)


def decode(v):
    """(tx, ty) of a pixel that is a texel of the 64 x 64 source, else None."""
    tx, ty = v & 0xfff, v >> 12 & 0xfff
    if tx >= W or ty >= H or v >> 24 != (tx ^ ty ^ 0xa5) & 0xff:
        return None
    return tx, ty


# ---- the scene -------------------------------------------------------------------------------
def mask_lines_from_rows(rows):
    """gen/bgmask.txt's lines from a layerless tri --pixels image ({y: [values]}): '.' the
    background, '#' the triangle, '?' anything else."""
    out = []
    for y in range(H):
        out.append("".join("." if v == BG else "#" if v == TRI else "?"
                           for v in rows[y]))
    return out


def load_mask(path=MASK):
    """The scored pixels: [(x, y)] of the hardware's background, row-major."""
    lines = open(path).read().split()
    return [(x, y) for y in range(H) for x in range(W) if lines[y][x] == "."]


def tri_rows(text):
    """{y: [int]} of a tri --pixels output (`row Y: 0x...`)."""
    out = {}
    for m in re.finditer(r"^row (\d+): (.*)$", text, re.M):
        out[int(m[1])] = [int(v, 16) for v in m[2].split()]
    return out


def probe_rows(text):
    """{y: [int]} of a probe --pixels output (`probe NAME: row Y: hex ...`)."""
    out = {}
    for m in re.finditer(r"^probe [A-Za-z0-9_.-]+: row (\d+): (.*)$", text, re.M):
        out[int(m[1])] = [int(v, 16) for v in m[2].split()]
    return out


def obj(pokes):
    """The object's words 3-22 after the pokes ({word: value})."""
    o = dict(CTRL)
    o.update(pokes)
    return o


def decoded_vertices(o):
    """TL, TR, BL in pixels from words 15-22 (E590's bg_geometry.py, six words on)."""
    def pt(y, x):
        return (Fraction(x - 0x100000, 256), Fraction(y - 0x100000, 256))
    tl = pt(o[15] & 0xffffff, (o[15] >> 24) | (o[16] & 0xffff) << 8)
    tr = pt((o[17] >> 16) | (o[18] & 0xff) << 16, o[18] >> 8)
    bl = pt(o[20] & 0xffffff, (o[20] >> 24) | (o[21] & 0xffff) << 8)
    return tl, tr, bl


BOX = ((Fraction(0), Fraction(0)), (Fraction(W), Fraction(0)), (Fraction(0), Fraction(H)))


def plane(verts, vals, px, py):
    """The value at (px, py) of the plane through vals at the three vertices; None if
    degenerate or a value is not a number."""
    if any(v is None for v in vals):
        return None
    (x0, y0), (x1, y1), (x2, y2) = verts
    ux, uy, vx, vy = x1 - x0, y1 - y0, x2 - x0, y2 - y0
    det = ux * vy - uy * vx
    if det == 0:
        return None
    dx, dy = px - x0, py - y0
    a = (dx * vy - dy * vx) / det
    b = (ux * dy - uy * dx) / det
    return vals[0] + (vals[1] - vals[0]) * a + (vals[2] - vals[0]) * b


def coords(model, o):
    """((u0, u1, u2), (v0, v1, v2)) as Fractions, and the vertices, under a plane model."""
    w = {k: frac(o[k]) for k in range(3, 9)}
    if model == "H-LM":
        u, v = (w[3], w[4], w[5]), (w[6], w[7], w[8])
    else:
        u, v = (w[3], w[5], w[7]), (w[4], w[6], w[8])
    if model == "H-SWAP":
        u, v = v, u
    verts = decoded_vertices(o) if model == "H-VPLANE" else BOX
    return u, v, verts


def _tex_index(t):
    """floor(t) of a texel coordinate 64 u, or None at an edge or out of range."""
    if t is None or t < EDGE or t > W - EDGE:
        return None
    f = math.floor(t)
    if t - f < EDGE or f + 1 - t < EDGE:
        return None
    return f


def predict_tex(model, pokes, mask):
    """{(x, y): (tx, ty)} of the predicted pixels, or SPECIAL[model] (a string)."""
    if model in SPECIAL:
        return SPECIAL[model]
    o = obj({} if model == "H-NOREAD" else pokes)
    u, v, verts = coords("H-VM" if model == "H-NOREAD" else model, o)
    out = {}
    for x, y in mask:
        px, py = Fraction(2 * x + 1, 2), Fraction(2 * y + 1, 2)
        pu, pv = plane(verts, u, px, py), plane(verts, v, px, py)
        tx = _tex_index(None if pu is None else pu * W)
        ty = _tex_index(None if pv is None else pv * H)
        if tx is not None and ty is not None:
            out[(x, y)] = (tx, ty)
    return out


def map_id(pred):
    """The frozen form of a prediction: 'sha256:HEX16/N' of a texel map, or the special word."""
    if isinstance(pred, str):
        return pred
    text = "".join("%d,%d:%d,%d\n" % (x, y, *pred[(x, y)]) for x, y in sorted(pred))
    return "sha256:%s/%d" % (hashlib.sha256(text.encode()).hexdigest()[:16], len(pred))


def differ(a, b):
    """Pixels two texel maps both predict and disagree on, and how many both predict."""
    if isinstance(a, str) or isinstance(b, str):
        return None, None
    both = [p for p in a if p in b]
    return sum(1 for p in both if a[p] != b[p]), len(both)


def score_tex(pred, image, mask):
    """(state, scored, matched): state True (right), False (wrong) or None, of an observed
    image ({y: [int]}) against a prediction."""
    got = {}
    for x, y in mask:
        row = image.get(y)
        if row is None or x >= len(row):
            return None, 0, 0
        got[(x, y)] = decode(row[x])
    if isinstance(pred, str):
        if pred == "notex":
            m = sum(1 for p in mask if got[p] is None)
        else:
            want = (0, 0)
            if pred == "const":
                cnt = {}
                for p in mask:
                    if got[p] is not None:
                        cnt[got[p]] = cnt.get(got[p], 0) + 1
                want = max(cnt, key=cnt.get) if cnt else None
            m = sum(1 for p in mask if got[p] is not None and got[p] == want)
        n = len(mask)
    else:
        n = len(pred)
        m = sum(1 for p, t in pred.items() if got[p] == t)
    if n < MIN_SCORED:
        return None, n, m
    miss = Fraction(n - m, n)
    return (True if miss <= RIGHT_MISS else False if miss > WRONG_MISS else None), n, m


# ---- the raw reads (L-RAW, POS) -------------------------------------------------------------
RAW_MODELS = {
    # name: (component the shader writes: 0 pa0 / 1 pa1) -> the expected value at (x, y)
    "H-ITER": lambda c, x, y: (x + 0.5) / W if c == 0 else (y + 0.5) / H,
    "H-SWAP": lambda c, x, y: (y + 0.5) / H if c == 0 else (x + 0.5) / W,
    "H-LM": lambda c, x, y: (y + 0.5) / H,          # u = v = the y plane at the control
    "H-17": lambda c, x, y: 0.0,
}


def score_raw(model, comp, image, mask):
    """(state, matched) of an L-RAW image (f32 bits) against a model ('H-NONE': one value)."""
    vals = []
    for x, y in mask:
        row = image.get(y)
        if row is None or x >= len(row):
            return None, 0
        vals.append((x, y, row[x]))
    if model == "H-NONE":
        cnt = {}
        for _, _, v in vals:
            cnt[v] = cnt.get(v, 0) + 1
        m = max(cnt.values())
    else:
        f = RAW_MODELS[model]
        m = 0
        for x, y, v in vals:
            g = f32(v)
            if not math.isnan(g) and abs(g - f(comp, x, y)) <= RAW_TOL:
                m += 1
    return (True if m >= RAW_RIGHT else False if m < RAW_WRONG else None), m


def score_pos(image, mask):
    """(state, matched): POS (E442's primary, pix_pa0): pa0 = f32(x + 0.5) exactly (E437)."""
    m = 0
    for x, y in mask:
        row = image.get(y)
        if row is None or x >= len(row):
            return None, 0
        m += row[x] == bits(x + 0.5)
    return (True if m >= RAW_RIGHT else False if m < RAW_WRONG else None), m


# ---- the kept dumps --------------------------------------------------------------------------
def object_words(param):
    """Words 0-22 of the background object in a render_param dump (bytes), or None."""
    if param is None or len(param) < OBJ_OFF + 23 * 4:
        return None
    return list(struct.unpack_from("<23I", param, OBJ_OFF))


def rd_word(words_text, n):
    """rd:N of a --words file (`rd:N=0x...`), or None."""
    m = re.search(r"^rd:%d=(0x[0-9a-fA-F]+)$" % n, words_text, re.M)
    return int(m[1], 16) if m else None


def bg_layers(words_text):
    """The layer count of the object's tag: rd:18 (SGX_RENDER_RD_BGTAG 0x48) bits 30:25."""
    v = rd_word(words_text, 18)
    return None if v is None else v >> 25 & 0x3f


def gz(path):
    """A kept file's bytes (plain or .gz), or None."""
    if os.path.exists(path + ".gz"):
        return gzip.open(path + ".gz").read()
    if os.path.exists(path):
        return open(path, "rb").read()
    return None
