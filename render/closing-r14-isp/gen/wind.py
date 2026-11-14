# SPDX-License-Identifier: MIT
"""wind.py: stage wind (Q241; E998, E977, E287, E981), round 14 plan section 2.

E998's form (E977's z242-c-f0 row: 80 x 40, the triangle (0,0), (2W,0), (0,2H) at depths 1, 0, 1,
CR_ISP_ZLSCTL 0x00171014 (float, pitch G 2), the depth buffer pre-filled 0xdeadbeef and dumped,
ISP word 0 through `--poke blk:1`: 0x00400200 is the compare less with the depth written), with
every row also printing its pixels.

- Bits 15, 16, 17 of ISP word 0, each set alone, on the triangle with its vertex order reversed
  ((0,0), (0,2H), (2W,0), depths 1, 1, 0). Frozen: H-CULL (each bit removes one winding and E998
  saw the other: the reversed triangle draws E977's ramp, its kept dump, drawn count and hash)
  against H-KILL (any triangle removed: E998's kept x-w0b15 dump, no pixel).
- A depth outside [0, 1] under the compare always with the depth written (ISP word 0 0x01c00200:
  under less with the background's 1.0 a depth above 1 never passes, whatever is done to it):
  zhi, depths 1.25, 0.25, 1.25 (z = 1.25 - x/160 at the centre, above 1 for x + 0.5 < 40);
  zlo, 0.25, -0.75, 0.25 (z = 0.25 - x/160, below 0 for x + 0.5 > 40). No pixel centre lies within
  0.003 of 0 or 1. Frozen per dword of the three tile columns and rows (96 x 48, E465's layout at
  G 2, all inside the store band x + 0.5 < 100, y + 0.5 < 50, E730) and per target pixel (drawn):
  H-CLAMP (the depth clamped to [0, 1]: stored 1.0 or 0.0, drawn), H-ZCLIP (pixels past [0, 1]
  removed: the background's 1.0, not drawn), H-RAW (the plane's float stored as it is, drawn),
  H-ABS (as H-RAW with the sign cleared, E987's background rule; zlo only).
- Controls that can fail: the reversed triangle with bits 15 to 17 clear (draws E977's ramp),
  E998's bit 15 replicate (no pixel), and the compare always with writes at E977's depths 1, 0, 1
  (E977's ramp: the premise of the two depth rows)."""
import struct

MAIN = ("tri --keep-going --wait-ms 20000 --width 80 --height 40 --max-width 80 --max-height 40 "
        "--tri-v %s --tri-z %s --depth --depth-ctl 0x00171014 --depth-fill 0xdeadbeef "
        '--depth-dump "$W" --poke blk:1=0x%08x --pixels')
FWD, REV = "0,0,40960,0,0,20480", "0,0,0,20480,40960,0"
LESS, ALWAYS = 0x00400200, 0x01C00200
E977 = "data:render/closing-r9-x/out/20261113-081821/zls/z242-c-f0"
E998 = "data:render/closing-r10-x/out/20261113-101116/isp0x/x-w0b15"
HASH_RAMP, HASH_BG = "0xafb12e5a2a9a6725", "0x56053161ef809725"
W, H, TW, TH, G = 80, 40, 96, 48, 2
ONE, ZERO, BG_FILL = 0x3F800000, 0x00000000, 0xDEADBEEF
TOL = 2.0 ** -20                 # E977's ramp: within 2^-23 of the plane at every centre (tests)
ZMODELS = ("H-CLAMP", "H-ZCLIP", "H-RAW", "H-ABS")

# name, set, vertex order, ISP word 0, depths (in the vertex order), kept (the frozen reading)
ROWS = (
    ("wind-ctl-rev", "control", REV, LESS, "1,1,0", "ramp"),
    ("wind-ctl-b15", "control", FWD, LESS | 1 << 15, "1,0,1", "none"),
    ("wind-ctl-always", "control", FWD, ALWAYS, "1,0,1", "ramp"),
    ("wind-rev-b15", "heldout", REV, LESS | 1 << 15, "1,1,0", "cull"),
    ("wind-rev-b16", "heldout", REV, LESS | 1 << 16, "1,1,0", "cull"),
    ("wind-rev-b17", "heldout", REV, LESS | 1 << 17, "1,1,0", "cull"),
    ("wind-zhi", "heldout", FWD, ALWAYS, "1.25,0.25,1.25", "z"),
    ("wind-zlo", "heldout", FWD, ALWAYS, "0.25,-0.75,0.25", "z"),
)


def args(r):
    name, st, order, isp0, z, kind = r
    return MAIN % (order, z, isp0)


def knobs(r):
    return "expectdiff reads:job,drawn,depth_changed" if r[1] == "control" else "expectdiff"


def in_tile_index(x, y):
    x, y, i = x & 31, y & 15, 0
    for b in range(4):
        i |= ((y >> b) & 1) << (2 * b) | ((x >> b) & 1) << (2 * b + 1)
    return i | ((x >> 4) & 1) << 8


def store_dword(x, y, g=G):
    """sgx-pipe zls.rs store_dword (E465): 512 (ty (G + 1) + tx) + the in-tile index"""
    return 512 * ((y >> 4) * (g + 1) + (x >> 5)) + in_tile_index(x, y)


def inside(x, y):
    """the centre of (x, y) inside the triangle (0,0), (160,0), (0,80) (either order)"""
    return (2 * x + 1) * 1 + (2 * y + 1) * 2 < 320


def plane(depths, x, y):
    """the depth at the centre of (x, y): depths at (0,0), (160,0), (0,80) in the forward order"""
    a, b, c = depths
    return a + (b - a) * (x + 0.5) / 160 + (c - a) * (y + 0.5) / 80


def fwd_depths(r):
    z = [float(t) for t in r[4].split(",")]
    return z if r[2] == FWD else [z[0], z[2], z[1]]


def bits_of(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def zmodel(depths, model):
    """{"drawn": [target pixels drawn, raster], "dwords": {index: (kind, value)}} where kind is
    'eq' (the exact word) or 'near' (a float within TOL)"""
    drawn, dw = [], {}
    for y in range(TH):
        for x in range(TW):
            i = store_dword(x, y)
            if not inside(x, y):
                d, val = False, ("eq", ONE)
            else:
                z = plane(depths, x, y)
                if 0.0 <= z <= 1.0:
                    d, val = True, ("near", z)
                elif model == "H-CLAMP":
                    d, val = True, ("eq", ONE if z > 1 else ZERO)
                elif model == "H-ZCLIP":
                    d, val = False, ("eq", ONE)
                elif model == "H-RAW":
                    d, val = True, ("near", z)
                else:
                    d, val = True, ("near", abs(z))
            dw[i] = val
            if x < W and y < H:
                drawn.append(d)
    return {"drawn": drawn, "dwords": dw}


def ztext(m):
    """the frozen form of a z model: the drawn bitmap, then one line per dword index"""
    out = ["".join("1" if v else "0" for v in m["drawn"][y * W:(y + 1) * W]) for y in range(H)]
    for i in sorted(m["dwords"]):
        k, v = m["dwords"][i]
        out.append("%d %s %s" % (i, k, "0x%08x" % v if k == "eq" else repr(v)))
    return "\n".join(out) + "\n"


def zparse(text):
    ln = text.splitlines()
    drawn = [c == "1" for c in "".join(ln[:H])]
    dw = {}
    for t in ln[H:]:
        i, k, v = t.split()
        dw[int(i)] = (k, int(v, 16) if k == "eq" else float(v))
    return {"drawn": drawn, "dwords": dw}


def zcheck(m, words, drawn):
    """True when the dump's words and the drawn pixels are the model's (None: no data)"""
    if words is None or drawn is None:
        return None
    if drawn != m["drawn"]:
        return False
    for i, (k, v) in m["dwords"].items():
        w = words[i]
        if k == "eq":
            if w != v:
                return False
        else:
            f = struct.unpack("<f", struct.pack("<I", w))[0]
            if not abs(f - v) <= TOL:
                return False
    return True
