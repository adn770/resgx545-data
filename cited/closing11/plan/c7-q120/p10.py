from lib import *
import c7_rule as R
for n,S in (("sa5",0xa5),):
    s=dw("zst2","z2x-f7-"+n)
    for k in range(4):
        print(k," ".join(f"{v:08x}" for v in s[256*k:256*k+12])); print("  ", " ".join(f"{v:08x}" for v in R.f7k_block(S)))
