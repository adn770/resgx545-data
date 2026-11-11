#!/usr/bin/env python3
"""Q211 offline: the page need U of a scene from sgx-pipe's TA model (ta.rs: tiling, tile_lists, walk, 128 bytes a
stream, a page per macrotile list at least), against every measured U.

HU1: U = sum over macrotiles of ceil(streams_m * 128 / 4096) + G, G the global list's pages (1 for these scenes).
Measured U (whole-buffer pages a completing job takes, E626/E705/E625/E735/E627):
  default triangle at 64x64 2, 128x128 3, 192x128 5, 256x256 5, 512x384 8, 1024x768 19, 4096x4096 287
  1024x768 moved (192,0) 20, (384,0) 17, (576,0) 12
  K-triangle open scenes at 1024x768 (E735): apart 2: 29, 3: 35, 4: 37; stacked 2: 19, 3: 22, 4: 22
  E627 two triangles (--geometry 1 --move 2:-96,0): overflow at 0x38 (thr0 22), completes at 0x3c (26): U in 23..26
This is a FIT on all of them (nothing held out): every number was measured before this script was written.
"""
import math, sys
sys.dont_write_bytecode = True


def tiling(w, h):
    tx, ty = -(-w // 32), -(-h // 16)
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = ((-(-tx // n)) + 3) & ~3, ((-(-ty // n)) + 3) & ~3
    return tx, ty, n, mx, my


def tile_lists(t, x0, y0):
    x1, y1 = x0 + 16.0, y0 + 16.0
    xs = [p[0] for p in t]; ys = [p[1] for p in t]
    if max(xs) < x0 or max(ys) < y0 or min(xs) >= x1 or min(ys) >= y1:
        return False
    for i in range(3):
        a, b, c = t[i], t[(i + 1) % 3], t[(i + 2) % 3]
        nx, ny = b[1] - a[1], a[0] - b[0]
        side = nx * (c[0] - a[0]) + ny * (c[1] - a[1])
        if all((nx * (x - a[0]) + ny * (y - a[1])) * side < 0 for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))):
            return False
    return True


def default_tri(w, h, dx=0, dy=0):
    return [(8 * w / 64 + dx, 8 * h / 64 + dy), (56 * w / 64 + dx, 20 * h / 64 + dy), (20 * w / 64 + dx, 56 * h / 64 + dy)]


def streams(w, h, tris):
    """streams per macrotile (index m = column * n + row as ta.rs), counting a region once however many tris."""
    tx, ty, n, mx, my = tiling(w, h)
    per = {}
    for m in range(n * n):
        k = 0
        for i in range(mx * my):
            c, r = (m // n) * mx + i % mx, (m % n) * my + i // mx
            if 32 * c >= w or 16 * r >= h:
                continue
            x0, y0 = 32.0 * c, 16.0 * r
            if any(tile_lists(t, x0, y0) or tile_lists(t, x0 + 16, y0) for t in tris):
                k += 1
        if k:
            per[m] = k
    return per


def pages(per, bytes_per_stream=128, page=4096):
    return {m: math.ceil(k * bytes_per_stream / page) for m, k in per.items()}


def model(w, h, tris, G=1, bps=128):
    per = streams(w, h, tris)
    pg = pages(per, bps)
    return sum(pg.values()) + G, per, pg


def main():
    rows = []
    for (w, h), U in (((64, 64), 2), ((128, 128), 3), ((192, 128), 5), ((256, 256), 5), ((512, 384), 8), ((1024, 768), 19),
                      ((4096, 4096), 287)):
        rows.append((f"default {w}x{h}", w, h, [default_tri(w, h)], U))
    for dx, U in ((192, 20), (384, 17), (576, 12)):
        rows.append((f"1024x768 moved ({dx},0)", 1024, 768, [default_tri(1024, 768, dx, 0)], U))
    base = default_tri(1024, 768)
    apart = [(0, 288), (-64, -240), (-768, -96)]
    stacked = [(16, 0), (32, 0), (48, 0)]
    for K in (2, 3, 4):
        rows.append((f"apart K={K}", 1024, 768, [base] + [default_tri(1024, 768, *apart[i]) for i in range(K - 1)], {2: 29, 3: 35, 4: 37}[K]))
    for K in (2, 3, 4):
        rows.append((f"stacked K={K}", 1024, 768, [base] + [default_tri(1024, 768, *stacked[i]) for i in range(K - 1)], {2: 19, 3: 22, 4: 22}[K]))
    rows.append(("E627 two (-96,0)", 1024, 768, [base, default_tri(1024, 768, -96, 0)], "23..26"))
    print(f"{'scene':26} {'tiling(tx,ty,n,mx,my)':24} {'mtiles':>6} {'streams':>7} {'sum pages':>9} {'model U':>7} {'meas U':>6} resid   per-macrotile (streams:pages)")
    for name, w, h, tris, U in rows:
        mU, per, pg = model(w, h, tris)
        resid = (mU - U) if isinstance(U, int) else "-"
        tl = tiling(w, h)
        detail = " ".join(f"{m}:{per[m]}:{pg[m]}" for m in sorted(per))
        print(f"{name:26} {str(tl):24} {len(per):6d} {sum(per.values()):7d} {sum(pg.values()):9d} {mU:7d} {str(U):>6} {str(resid):>6}  {detail}")
    # E310/E627 abort-state check: default triangle 1024x768 at 0x30: lists 0,1,2,4,5(3),6,8,9(3),13 sum 13 (partial)
    print("\nE310's full-page macrotiles at 1024x768 (3 pages at 5 and 9) and the model's pages:", pages(streams(1024, 768, [base]))[5], pages(streams(1024, 768, [base]))[9])
    # alternative bytes per stream (64, 96, 256) and G
    print("\nresiduals per (bytes per stream, G):")
    for bps in (64, 96, 128, 160, 192, 256):
        for G in (0, 1, 2):
            res = []
            for name, w, h, tris, U in rows:
                if isinstance(U, int):
                    res.append(model(w, h, tris, G, bps)[0] - U)
            print(f"  bps {bps:3d} G {G}: {res}  |sum abs| {sum(abs(r) for r in res)}")


if __name__ == "__main__":
    main()
