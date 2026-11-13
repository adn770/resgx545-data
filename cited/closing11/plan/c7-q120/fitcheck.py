# fit-set check only: z2y-f6 block 0 and z2x-f7-sa5
from lib import *
import c7_rule as R, zst2 as Z
n="z2y-f6"; d=dw("zst2",n); ref=dw("zst2","z2y-f0")
v=[[ref[Z.in_tile_index(0,y)] for y in range(16)]]
ok=0
for q in range(4):
    p=R.f6c_group(v[0][4*q:4*q+4])
    ok+= p==d[12*q:12*q+12]
    print(q,p==d[12*q:12*q+12])
print("fit f6 groups",ok,"of 4")
s=dw("zst2","z2x-f7-sa5")
print("f7 sa5 fit",[R.f7k_block(0xa5)==s[256*k:256*k+12] for k in range(4)])
