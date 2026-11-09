"""The multisampling region model of opus/msaa.md, written again from its words: a stored 32x16 tile
(tx, ty) is written by the last region walked in it, the regions being (32>>b31) x (16>>b30) pixels
when CR_TE_AA bit 29 is set; the 32x16 sample buffer takes the left half from the region's left
tile mask and the right half from the right one; samples sit at E281's slots. All geometry in
sixteenths of a pixel, integers; ties by the top-left rule on a clockwise (y down) triangle."""
SAMP = [(6, 2), (14, 6), (2, 10), (10, 14)]


def orient(t):
    (ax, ay), (bx, by), (cx, cy) = t
    return t if (bx - ax) * (cy - ay) - (by - ay) * (cx - ax) > 0 else (t[0], t[2], t[1])


def covers(t, px, py):
    t = orient(t)
    for i in range(3):
        (ax, ay), (bx, by) = t[i], t[(i + 1) % 3]
        e = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if e < 0:
            return False
        if e == 0:
            top = by == ay and bx > ax
            left = by < ay
            if not (top or left):
                return False
    return True


def overlaps(t, x0, y0, x1, y1):
    """Does primitive t meet the box [x0,x1) x [y0,y1) (pixels): bounding box, and no edge with all
    four corners strictly outside."""
    xs, ys = [p[0] for p in t], [p[1] for p in t]
    X0, Y0, X1, Y1 = x0 * 16, y0 * 16, x1 * 16, y1 * 16
    if not (max(xs) >= X0 and max(ys) >= Y0 and min(xs) < X1 and min(ys) < Y1):
        return False
    t = orient(t)
    for i in range(3):
        (ax, ay), (bx, by) = t[i], t[(i + 1) % 3]
        if all((bx - ax) * (cy - ay) - (by - ay) * (cx - ax) < 0
               for cx, cy in ((X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1))):
            return False
    return True


def predict(prims, W, H, mode, te, last_region=True, slots=SAMP, bit29_gate=True, origin="buffer", halves=True):
    """{(X, Y): (source pixel x, y)} of every stored pixel the model draws."""
    sx, sy = {0: (1, 1), 1: (2, 1), 2: (2, 2)}[mode]
    b31, b30 = te >> 31 & 1, te >> 30 & 1
    if bit29_gate and not te >> 29 & 1:
        b31 = b30 = 0
    rw, rh = 32 >> b31, 16 >> b30
    out = {}
    for ty in range(-(-H // 16)):
        for tx in range(-(-W // 32)):
            C = 2 * tx + (b31 if last_region else 0) if b31 else tx
            R = 2 * ty + (b30 if last_region else 0) if b30 else ty
            x0, y0 = C * rw, R * rh
            L = [t for t in prims if overlaps(t, x0, y0, x0 + rw // 2, y0 + rh)]
            Rr = [t for t in prims if overlaps(t, x0 + rw // 2, y0, x0 + rw, y0 + rh)]
            ox = 32 * tx + (16 * b31 if sx > 1 and origin == "buffer" else 0)
            oy = 16 * ty + (8 * b30 if sy > 1 and origin == "buffer" else 0)
            for b in range(16):
                for a in range(32):
                    X, Y = 32 * tx + a, 16 * ty + b
                    if X >= W or Y >= H:
                        continue
                    s = slots[0] if mode == 0 else slots[a % 2] if mode == 1 else slots[a % 2 + 2 * (b % 2)]
                    spx, spy = ox + a // sx, oy + b // sy
                    P = (spx * 16 + s[0], spy * 16 + s[1])
                    if any(covers(t, *P) for t in ((L if a < 16 else Rr) if halves else (L + Rr))):
                        out[(X, Y)] = (spx, spy)
    return out


def tri_full(W, H, k=1.25):
    Sx, Sy = int(20 * W * k / 1.25), int(20 * H * k / 1.25)
    return [((0, 0), (Sx, 0), (0, Sy)), ((0, Sy), (Sx, 0), (Sx, Sy))]
