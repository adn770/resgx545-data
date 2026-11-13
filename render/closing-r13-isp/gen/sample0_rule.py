"""Frozen rule SAMPLE0 for Q201/C6 (E064 sweep of cmd:16 bits 7:0, 64x64 triangle).

Triangle: sgxfive_tri_default at 64x64 (render.c): vertices (8,8), (56,20), (20,56) pixels, y down,
on the 1/256 grid: x256. Coverage = E606/E660 rule (sgx-pipe isp.rs Tri::covers, ported): exact test,
top-left ties; only the sample point changes: pixel (x, y) is sampled at 256x + 16*sx, 256y + 16*sy
(1/256 units) with (sx, sy) from the byte n = cmd:16 bits 7:0.

Decided BEFORE freezing (E278: "each byte x in bits 3:0 and y in bits 7:4"; E339: 0x26 = (6, 2),
E502 read x + 0.375): x = low nibble, y = high nibble. 0x88 -> (8,8)/16 = pixel centre (E606).

Rules (name -> function n -> (sx16, sy16) in 1/16 pixel, or in 1/32 for the half-offset rival):
  SAMPLE0  : x = n & 15, y = n >> 4, point = (x/16, y/16)         <- the rule under test
  SWAPPED  : x = n >> 4, y = n & 15, point = (x/16, y/16)
  FIXED    : point = (0.5, 0.5) for every n
  HALF     : point = ((x + 0.5)/16, (y + 0.5)/16) with x = n & 15, y = n >> 4

Pass criterion (per rule): for all 256 values, predicted triangle-pixel count == the case's
"N triangle" count AND the partition of the 256 values by predicted image == the partition by the
observed hash (same equivalence classes exactly). Report: values with count held, number of values
whose image-class matches, class counts. The tool's "diff: N of 4096" is its own edge-tolerant check
against its reference, not a diff against the baseline hash, so it is scored only as 'all 0 expected'.
Fit-ish values (E064 tabled): the 31 one-nibble values (other nibble 8); held out: the other 225.
"""
V = [(8 * 256, 8 * 256), (56 * 256, 20 * 256), (20 * 256, 56 * 256)]
W = H = 64


def covers(px, py, v=V):
    (ax, ay), (bx, by), (cx, cy) = v
    area2 = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
    if area2 == 0:
        return False
    vs = [v[0], v[2], v[1]] if area2 < 0 else list(v)
    for i in range(3):
        a, b = vs[i], vs[(i + 1) % 3]
        dx, dy = b[0] - a[0], b[1] - a[1]
        e = dx * (py - a[1]) - dy * (px - a[0])
        if not (e > 0 or (e == 0 and (dy < 0 or (dy == 0 and dx > 0)))):
            return False
    return True


# sample point offsets within the pixel in 1/512 pixel (so the half-offset rival is exact)
def point(rule, n):
    lo, hi = n & 15, n >> 4
    if rule == "SAMPLE0":
        return (32 * lo, 32 * hi)
    if rule == "SWAPPED":
        return (32 * hi, 32 * lo)
    if rule == "FIXED":
        return (256, 256)
    if rule == "HALF":
        return (32 * lo + 16, 32 * hi + 16)
    raise ValueError(rule)


def image(rule, n):
    ox, oy = point(rule, n)  # 1/512 pixel
    v2 = [(2 * x, 2 * y) for x, y in V]  # vertices in 1/512 pixel
    return frozenset((x, y) for y in range(H) for x in range(W)
                     if covers(512 * x + ox, 512 * y + oy, v2))
