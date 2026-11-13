from lib import *
import zst2 as Z
for n in ("z2y-f0","z2x-f0","z2e-f0","z2d-f0"):
    ref=dw("zst2",n)
    W,H=Z.PLANES[Z.plane_of(n)][:2]
    tw=-(-W//32)
    print(n)
    for ty in range(-(-H//16)):
      for tx in range(tw):
        slot=ty*tw+tx
        print(" tile",tx,ty,"slot",slot)
        for y in range(16):
            row=[ref[512*slot+Z.in_tile_index(x,y)] for x in range(32)]
            s=sorted(set(row))
            print("  ",y,len(s),f"{s[0]:08x}",f"{s[-1]:08x}", "bg=%d"%sum(v==0 for v in row), "fill=%d"%sum(v==FILL for v in row))
        break
      break
