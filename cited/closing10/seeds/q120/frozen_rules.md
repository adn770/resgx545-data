Frozen before the 96 x 48 scoring (round 10 seed q120). Fit data: the 64 x 32 dumps only.

Rivals for the stencil in-tile byte order j (byte j of the tile's 512 stencil bytes, dword j >> 2, lane j & 3),
x, y the pixel's offsets in its 32 x 16 tile, bit names lowest first:
  H-DEPTHORD : j = y0 x0 y1 x1 y2 x2 y3 x3 x4
  H-RASTER   : j = 32 y + x
  H-F2ORD    : lane = y0 y1 (the 4 rows of a column in the 4 bytes: E466's format 2 puts y0 in the half
               of a dword, extended by y1 for the bytes), then x0 y2 x1 y3 x2 x3 x4 up the dword index:
               j = y0 y1 x0 y2 x1 y3 x2 x3 x4
The loaded stencil dword i = slot * 128 + (j >> 2) holds bytes i & 255, i >> 8, 0, 0 (index fill); slot =
ty * tiles_across + tx.

Rules (fit on 64 x 32, to be checked on 96 x 48 with G = 2):
  TILES  : packed formats store tile (tx, ty) in block 2 * tw * (ty >> 1) + 2 * tx + (ty & 1) of 640 (formats 3,
           5), 512 (6) or 256 (4, 7) dwords; tw = G + 1.
  F3/F5  : a tile is 16 chunks of 160 bytes, chunk r = row y = r; pixel P = x is the record (4 bytes of the
           float depth with the sign bit set, little endian, then the stencil byte); record P byte q goes to
           chunk address a = T + q with g = P div 3, T = 1 + 17 g + 5 (2 - P mod 3), minus 32 when a >= 16 (g + 1).
  F4     : a tile is 8 groups of 80 bytes, group n = rows 2n and 2n + 1; the 16 records m = 8 (y & 1) + x div 4
           (5 bytes: 0xf0, then the stencil bytes of x = 4 qd + 3, +2, +1, +0) use the same address rule with
           P = m (T, the -32 for a >= 16 (g + 1) with g = m div 3).
  F6     : a tile is 512 dwords, dword 32 r + x = float depth of (x, y = r) with the sign bit set.
  F7     : not decoded.
