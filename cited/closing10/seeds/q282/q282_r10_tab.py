import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import numpy as np
from q282_r10_data import rows, S
def h2f(h): return np.asarray(h, dtype=np.uint16).view(np.float16).astype(np.float64)
def table(names):
    """arrays: A,B bytes, w (k of 64), hw half bits, job idx"""
    A=[];B=[];W=[];H=[];J=[]
    for j,n in enumerate(names):
        stage_b = n[5]=="b"
        for c,t,ix,iy,hw in rows(n):
            A.append(t[0]); B.append(t[2] if stage_b else t[1]); W.append(iy if stage_b else ix); H.append(hw); J.append(j)
    return [np.array(x) for x in (A,B,W,H,J)]
def s2l_arr(b):
    c=b/255.0
    return np.where(c<=0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
FIT=("srgb-a1","srgb-a2","srgb-b1","srgb-b2")
