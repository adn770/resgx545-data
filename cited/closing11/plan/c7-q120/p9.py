from lib import *
import zst2 as Z
from collections import Counter
ref=dw("zst2","z2e-f0")
print(len(ref))
for slot in range(4):
    print("slot",slot)
    for y in (0,1,4,15):
        row=[ref[512*slot+Z.in_tile_index(x,y)] for x in range(32)]
        print(" ",y,[f"{v:08x}" for v in row[:10]],"...",[f"{v:08x}" for v in row[-3:]], Counter(row).most_common(2))
