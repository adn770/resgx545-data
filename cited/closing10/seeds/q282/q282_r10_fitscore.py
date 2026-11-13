import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
from q282_r10_tab import *
from q282_r10_frozen import *
tot=0
for n in FIT:
    A,B,W,H,J=table((n,))
    o=stage_bits(decode_half(A),decode_half(B),W)
    ok=(o==H)
    px=(ok.reshape(-1,2).all(axis=1)).sum()   # rows alternate channel 0,1 per pixel
    print(n,"halves",int(ok.sum()),"of 4096; pixels",int(px),"of 2048"); tot+=ok.sum()
print("fit total",int(tot),"of 16384")
