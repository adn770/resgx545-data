from lib import *
import zst2 as Z
n="z2y-f0"
ref=dw("zst2",n)
for ty in range(2):
  for tx in range(2):
    slot=ty*2+tx
    print("tile",tx,ty,"slot",slot)
    for y in range(16):
        row=[ref[512*slot+Z.in_tile_index(x,y)] for x in range(32)]
        from collections import Counter
        c=Counter(row)
        print("  ",y,[(f"{k:08x}",v) for k,v in c.most_common(4)])
