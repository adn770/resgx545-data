# SPDX-License-Identifier: MIT
"""st1.py: stage st1 (seeds plan closing10/seeds/exp-seeds-r10.md section 5 "Stage st1", decision
R10-4 (a) and R10-6 (a), Q121; with the ranking plan's R10-4 Q071 stencil rows,
closing10/rank/rank-round10.md R10-D): the stencil test against a stencil the render loaded, and
the byte each pixel reads.

Every row (tool t10, resgx545 a581c06: `tri --isp2`, `--stencil-fill bytes[:S]`):
    tri --keep-going --wait-ms 20000 --tri-full --width W --height H --max-width W --max-height H
        --depth --depth-ctl CTL --depth-fill 0x3f800000 --stencil --stencil-fill F
        --stencil-store [--isp2 V] --depth-dump "$W" --pixels [--depth-pages 16]
CTL = 0x0017300e (E467/E978's: depth and stencil stored, the stencil loaded (bits 1, 13), G 1;
the same at 40 x 20, whose tiles are 64 x 32's). With --isp2 the tool puts V in the state block as
ISP word 2 and sets ISP word 0's word-2-present bit 8: ISP word 0 is 0x01d00300, its reference
(bits 7:0, E284) 0, the depth test always passing (libsgxfive render.c sgxfive_tri_block). E284:
the test passes when (ref & m) compares with (stencil & m), so under EQUAL (bits 27:25 = 2) a pixel
is drawn iff (S & m) == 0. V = mode << 25 | SOP3 5 << 16 | m << 8 | 0xff: a passing pixel's
stencil byte is stored inverted (invert, all bits written), a failing one kept (SOP1 0), so the
stencil store shows the passing bytes too, a second reading of the same byte.

The byte a pixel reads (frozen rivals, x, y its offsets in its 32 x 16 tile, slot = ty 2 + tx):
byte slot * 512 + j of the loaded buffer, with j by
  H-DEPTHORD  j = y0 x0 y1 x1 y2 x2 y3 x3 x4 (E985's offline reading of E978's dumps: lane 0
              replicated, lanes 1 to 3 held out here)
  H-RASTER    j = 32 y + x;  H-F2ORD  j = y0 y1 x0 y2 x1 y3 x2 x3 x4 (E985: 0 of 13 tiles)
  H-NOLOAD    the test reads 0, not the loaded stencil: every EQUAL row draws every pixel
Fills: `bytes[:S]` (byte b of the buffer holds (b + S) & 0xff, so a pixel's byte is (j + S) &
0xff: masks 1 << k, k 0 to 7, read bit k of j for every pixel and lane; S = 1 with mask 0x02 the
carry), 0x03020100 (each byte its lane: masks 0x01 and 0x02 read the lane's two bits).
Per row and model, frozen: the drawn pixels (the image's triangle colour 0xff00ff00, E977's kept
form) and the stencil store's bytes of the target's tiles (H-SOP: the loaded byte, inverted where
the pixel passed; H-NOLOAD: 0xff, the ISP's 0 inverted), over the target's pixels (an edge
tile's pixels past the target are a reading).

Controls (can fail): st1-always (mode 7: all 2048 drawn), st1-never (mode 0: none drawn), st1-noisp
(no --isp2: all drawn, E977/E978's tri, the store a copy of the load, E467).
Q071 (R10-4 (a)): q071-b0 and q071-l1 are st1-b0 and st1-lane1 with the control's inert bits all
flipped at once (bits 15, 21 to 23, 27 to 31 set; 12, 16, 20 cleared: r10-x zbits' mask, E411's
single flips): H-INERT, the image and the stencil store byte for byte their base row's."""
MAIN = "tri --keep-going --wait-ms 20000 --tri-full"
CTL = 0x0017300E
SET_BITS = 0xF8E08000           # 15, 21-23, 27-31 (r10-x gen/z.py)
CLR_BITS = 0x00111000           # 12, 16, 20
FILL_DEPTH = 0x3F800000
EQUAL, ALWAYS, NEVER = 2, 7, 0
SOP3_INVERT = 5
TRI_COLOUR = 0xFF00FF00
EDGE_PAGES = 16
ORDERS = ("H-DEPTHORD", "H-RASTER", "H-F2ORD")
MODELS = ORDERS + ("H-NOLOAD",)


def isp2(mode, m):
    return mode << 25 | SOP3_INVERT << 16 | m << 8 | 0xFF


def args(w, h, fill, v=None, ctl=CTL):
    a = (f"{MAIN} --width {w} --height {h} --max-width {w} --max-height {h} --depth --depth-ctl "
         f"{ctl:#010x} --depth-fill {FILL_DEPTH:#010x} --stencil --stencil-fill {fill} "
         f"--stencil-store" + (f" --isp2 {v:#010x}" if v is not None else "")
         + ' --depth-dump "$W" --pixels')
    return a + (f" --depth-pages {EDGE_PAGES}" if (w, h) != (64, 32) else "")


# name: (W, H, fill, mode or None (no --isp2), mask, base row (Q071) or None, control word)
ROWS = {
    "st1-always": (64, 32, "bytes", ALWAYS, 0xFF, None, CTL),
    "st1-never": (64, 32, "bytes", NEVER, 0xFF, None, CTL),
    "st1-noisp": (64, 32, "bytes", None, 0, None, CTL),
}
for _k in range(8):
    ROWS[f"st1-b{_k}"] = (64, 32, "bytes", EQUAL, 1 << _k, None, CTL)
ROWS["st1-s1b1"] = (64, 32, "bytes:1", EQUAL, 0x02, None, CTL)
ROWS["st1-lane0"] = (64, 32, "0x03020100", EQUAL, 0x01, None, CTL)
ROWS["st1-lane1"] = (64, 32, "0x03020100", EQUAL, 0x02, None, CTL)
ROWS["st1-e-b0"] = (40, 20, "bytes", EQUAL, 0x01, None, CTL)
ROWS["st1-e-b4"] = (40, 20, "bytes", EQUAL, 0x10, None, CTL)
ROWS["q071-b0"] = (64, 32, "bytes", EQUAL, 0x01, "st1-b0", (CTL & ~CLR_BITS) | SET_BITS)
ROWS["q071-l1"] = (64, 32, "0x03020100", EQUAL, 0x02, "st1-lane1", (CTL & ~CLR_BITS) | SET_BITS)
CONTROL_DRAWN = {"st1-always": 2048, "st1-never": 0, "st1-noisp": 2048}


def jobs():
    """[(name, set, knobs, args, {quantity: {model: value}})]"""
    out = []
    for n, (w, h, fill, mode, m, base, ctl) in ROWS.items():
        a = args(w, h, fill, None if mode is None else isp2(mode, m), ctl)
        if n in CONTROL_DRAWN:
            out.append((n, "control", "expectdiff reads:drawn", a,
                        {"drawn": {"H-E284": str(CONTROL_DRAWN[n])}}))
        elif base:
            out.append((n, "heldout", "expectdiff", a,
                        {"image": {"H-INERT": f"same:{base}"}, "sst": {"H-INERT": f"same:{base}"}}))
        else:
            out.append((n, "heldout", "expectdiff", a,
                        {"image": {md: "rule" for md in MODELS}, "sst": {md: "rule" for md in MODELS}}))
    return out


# ---- the rivals ---------------------------------------------------------------------------------
def in_tile_index(x, y):
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def j_order(order, x, y):
    x, y = x & 31, y & 15
    if order == "H-DEPTHORD":
        return in_tile_index(x, y)
    if order == "H-RASTER":
        return 32 * y + x
    if order == "H-F2ORD":
        bits = [y & 1, y >> 1 & 1, x & 1, y >> 2 & 1, x >> 1 & 1, y >> 3 & 1, x >> 2 & 1,
                x >> 3 & 1, x >> 4 & 1]
        return sum(b << i for i, b in enumerate(bits))
    raise ValueError(order)


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def fill_byte(fill, b):
    """byte b of a buffer filled with F (t10's fills: bytes[:S] or a value)"""
    if fill.startswith("bytes"):
        s = int(fill.split(":")[1]) if ":" in fill else 0
        return (b + s) & 0xFF
    return int(fill, 16) >> (8 * (b & 3)) & 0xFF


def predict(name, model):
    """(drawn: set of (x, y) in the target, {byte offset: value} of the stencil store's tiles)"""
    return predict_from(*ROWS[name][:5], model)


def predict_from(w, h, fill, mode, m, model):
    """predict() from a row's size, fill, compare mode (None: no --isp2, all drawn, the store a
    copy) and mask"""
    tw, th = tiles(w, h)
    drawn, sst = set(), {}
    for ty in range(th):
        for tx in range(tw):
            slot = ty * tw + tx
            for y in range(16):
                for x in range(32):
                    if model == "H-NOLOAD":     # the ISP's stencil 0: passes, stored 0 ^ 0xff
                        b = slot * 512 + in_tile_index(x, y)
                        s, passed = 0, True
                    else:
                        b = slot * 512 + j_order(model, x, y)
                        s = fill_byte(fill, b)
                        passed = {EQUAL: (s & m) == 0, ALWAYS: True, NEVER: False,
                                  None: True}[mode]
                    px, py = 32 * tx + x, 16 * ty + y
                    if px >= w or py >= h:      # past an edge target: a reading
                        continue
                    if passed:
                        drawn.add((px, py))
                    sst[b] = s ^ 0xFF if passed and mode is not None else s
    return drawn, sst


def pixels_drawn(text, w, h):
    """the set of (x, y) of the triangle colour in the output's `row N:` lines, or None"""
    rows = {}
    for ln in (text or "").splitlines():
        if ln.startswith("row "):
            k, _, vals = ln[4:].partition(": ")
            if k.isdigit():
                rows[int(k)] = vals.split()
    if sorted(rows) != list(range(h)) or any(len(v) != w for v in rows.values()):
        return None
    return {(x, y) for y in range(h) for x in range(w) if int(rows[y][x], 16) == TRI_COLOUR}
