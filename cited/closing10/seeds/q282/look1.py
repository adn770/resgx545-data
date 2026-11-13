import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sys; sys.dont_write_bytecode=True
import numpy as np
from q282_r10_data import *
def h2f(h): return float(np.array([h],dtype=np.uint16).view(np.float16)[0])
for n in ("srgb-a1","srgb-a2","srgb-b1","srgb-b2"):
    R=rows(n); b=n[5]=="b"
    tot=bad=0; ex=0
    for c,t,ix,iy,hw in R:
        w = iy if b else ix
        if w==0:
            A=t[0]; d=S.half_rne(S.s2l(A)); tot+=1
            if d!=hw:
                bad+=1
                # other-axis neighbour
                N=t[2] if not b else t[1]
                ex+= (S.half_rne(S.s2l(N))>>10 &31) > (d>>10&31)
    print(n,"w=0 pixels",tot,"mismatch decode",bad,"of which neighbour exp bigger",ex)
