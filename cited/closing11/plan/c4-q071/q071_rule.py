# Frozen rule for c4-q071 (round 11 helper). Functions copied from
# resgx545-data/render/closing-r10-st1/gen/st1.py (in_tile_index, fill_byte, pixels_drawn).
"""
Question: does E997's linear layout (bits 12, 16, 20 of CR_ISP_ZLSCTL cleared: depth store = linear
image, dword 32*(G+1)*y + x, G 1 at 64 x 32 -> pitch 64 dwords) explain E989's q071-b0 / q071-l1
(control 0xf8e6a00e, stencil test EQUAL ref 0, mask m, SOP3 invert, loaded stencil buffer filled
bytes[:0] or 0x03020100, 64 x 32 = 2 x 2 tiles of 32 x 16; loaded buffer 73728 bytes)?

Common: pixel (x, y), tile slot = (y // 16) * 2 + x // 32, in-tile x0 = x & 31, y0 = y & 15.
Test: pixel passes (drawn) iff (s & m) == 0, s the byte it reads at offset o; the stencil store
writes byte o = s ^ 0xff if passed else s (SOP3 invert, SOP1 keep). Unwritten bytes of the store
buffer keep the 0xdeadbeef fill (byte o = (0xef, 0xbe, 0xad, 0xde)[o & 3]).

Models (offset o that a pixel reads and stores):
 H-LINLOAD-A   o = 64 * y + x            (E997's H-STRIDE dword index, one byte a pixel)
 H-LINLOAD-B   o = 512 * slot + 32 * y0 + x0   (raster inside each tile, E997's H-LIN)
 H-LINLOAD-C   o = 4 * (64 * y + x)      (the stencil byte as byte 0 of the H-STRIDE dword)
 H-ZEROLOAD    s = 0 for every pixel (all pass), stored 0xff at o = 512 * slot + in_tile_index
               (E989's [infer]; its offsets are the twiddled ones, 2048 bytes)
 H-TWIDLOAD    (control, the base rows' own model, E988's H-DEPTHORD): o = 512 * slot +
               in_tile_index(x0, y0); expected to hold on st1-b0 / st1-lane1 and not on q071-*
Fills: byte o of the loaded buffer: bytes -> o & 0xff; 0x03020100 -> (0x03020100 >> 8 * (o & 3))
& 0xff.
Rows: q071-b0 (fill bytes, m 0x01), q071-l1 (fill 0x03020100, m 0x02), each: image = the set of
pixels with colour 0xff00ff00 in the `row N:` lines of NAME.txt; store = NAME.stencil-store.1.bin
(73728 bytes), loaded = NAME.stencil.1.bin.
Pass criterion per (row, model): drawn set exactly the prediction (extra and missing both 0) AND
all 73728 store bytes exactly the prediction (written bytes as above, others 0xdeadbeef).
Verdict per model: HELD if it passes both rows, FAILED otherwise. Partial counts (pixels right of
2048; store bytes right of 73728) are reported as well.
Refutation of "E997's linear layout explains E989": H-LINLOAD-A, -B and -C all FAILED on both
rows. Support: H-LINLOAD-A (or B, or C) HELD on both rows.
Additionally reported (not part of the verdict): whether loaded buffer == the fill pattern.
"""
FILLS = {"q071-b0": ("bytes", 0x01), "q071-l1": ("0x03020100", 0x02),
         "st1-b0": ("bytes", 0x01), "st1-lane1": ("0x03020100", 0x02)}
W, H, BUF = 64, 32, 73728
MODELS = ("H-LINLOAD-A", "H-LINLOAD-B", "H-LINLOAD-C", "H-ZEROLOAD", "H-TWIDLOAD")
TRI_COLOUR = 0xFF00FF00


def in_tile_index(x, y):
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def fill_byte(fill, o):
    if fill == "bytes":
        return o & 0xFF
    return int(fill, 16) >> (8 * (o & 3)) & 0xFF


def offset(model, x, y):
    slot, x0, y0 = (y // 16) * 2 + x // 32, x & 31, y & 15
    if model == "H-LINLOAD-A":
        return 64 * y + x
    if model == "H-LINLOAD-B":
        return 512 * slot + 32 * y0 + x0
    if model == "H-LINLOAD-C":
        return 4 * (64 * y + x)
    return 512 * slot + in_tile_index(x0, y0)       # H-ZEROLOAD, H-TWIDLOAD


def predict(row, model):
    """(drawn set of (x, y), full store bytearray of BUF bytes)"""
    fill, m = FILLS[row]
    store = bytearray((0xEF, 0xBE, 0xAD, 0xDE)[o & 3] for o in range(BUF))
    drawn = set()
    for y in range(H):
        for x in range(W):
            o = offset(model, x, y)
            s = 0 if model == "H-ZEROLOAD" else fill_byte(fill, o)
            passed = (s & m) == 0
            if passed:
                drawn.add((x, y))
            store[o] = s ^ 0xFF if passed else s
    return drawn, bytes(store)


def pixels_drawn(text, w, h):
    rows = {}
    for ln in (text or "").splitlines():
        if ln.startswith("row "):
            k, _, vals = ln[4:].partition(": ")
            if k.isdigit():
                rows[int(k)] = vals.split()
    if sorted(rows) != list(range(h)) or any(len(v) != w for v in rows.values()):
        return None
    return {(x, y) for y in range(h) for x in range(w) if int(rows[y][x], 16) == TRI_COLOUR}
