#!/usr/bin/env python3
"""p1141/ta o4_parity.py: source-pixel parity of o4..o6 (tags 5, 6, 7) in output-room-tiles.

Own reading of the -x/-y job pairs: dest pixel (x,y) value v: low nibble = tag k, bits 15:4 =
job marker (inferred here as the modal value over tag-2 pixels, not read from the markers file),
high half = float16-ish coordinate decoded as f32(v & 0xffff0000) * W/2 + W/2 - .5 (as E570).
A pair needs both jobs to carry the same tag and marker.  Counts (sx&1, sy&1) per tag.
Tables: o23-order (the fit, where the rule was found), o23-size and o23-tiles (read after the
rule was stated: held out of the rule, but the same probe family and shader).
Usage: python3 o4_parity.py
"""
import collections, gzip, os, re, struct
R = os.path.expanduser('~/src/resgx545-data/usse/output-room-tiles/dumps')
BG = 0xff203040
def f32(w): return struct.unpack('<f', struct.pack('<I', w & 0xffffffff))[0]
def rows(p):
    r = {}
    for l in gzip.open(p, 'rt'):
        m = re.search(r'row (\d+): (.*)$', l)
        if m: r[int(m[1])] = [int(v, 16) for v in m[2].split()]
    return [r[i] for i in sorted(r)]
def marker(g):
    c = collections.Counter((v & 0xffff) >> 4 for row in g for v in row if v != BG and (v & 15) == 2)
    return c.most_common(1)[0][0] if c else None
def main():
    for tab in ('o23-order', 'o23-size', 'o23-tiles'):
        d = f'{R}/{tab}'; tot = collections.defaultdict(collections.Counter); ncfg = 0
        for f in sorted(os.listdir(d)):
            if not f.endswith('-x.txt.gz'): continue
            cfg = f[:-9]
            if not os.path.exists(f'{d}/{cfg}-y.txt.gz'): continue
            gx, gy = rows(f'{d}/{f}'), rows(f'{d}/{cfg}-y.txt.gz')
            if not gx or not gy: continue
            mx, my = marker(gx), marker(gy)
            if mx is None or my is None: continue
            ncfg += 1; H, W = len(gx), len(gx[0])
            for y in range(H):
                for x in range(W):
                    vx, vy = gx[y][x], gy[y][x]
                    if vx == BG or vy == BG: continue
                    k = vx & 15
                    if k != (vy & 15) or k < 2: continue
                    if (vx & 0xffff) >> 4 != mx or (vy & 0xffff) >> 4 != my: continue
                    sx = round(f32(vx & 0xffff0000) * W / 2 + W / 2 - .5)
                    sy = round(f32(vy & 0xffff0000) * H / 2 + H / 2 - .5)
                    if 0 <= sx < W and 0 <= sy < H: tot[k][(sx & 1, sy & 1)] += 1
        print(tab, 'configs', ncfg)
        for k in sorted(tot):
            n = sum(tot[k].values()); ee = tot[k][(0, 0)]
            print(f'  tag {k}: pairs {n:6d} even-even {ee:6d} ({100*ee/n:.1f}%)')
if __name__ == '__main__': main()
