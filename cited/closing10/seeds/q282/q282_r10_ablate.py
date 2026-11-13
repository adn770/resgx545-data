import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
from q282_r10_tab import *
from q282_r10_rules import half_bits, expo, rnd
from q282_r10_frozen import decode_half
names=("srgb-a1","srgb-a2","srgb-b1","srgb-b2","srgb-c1","srgb-c2")  # ablation only compares fit-set single stages
def run(M=11,qin="floor",out="rhu",byp=True,names=FIT):
    A,B,W,H,J=table(names); a,b=decode_half(A),decode_half(B)
    g=2.0**(np.maximum(expo(a),expo(b))-M)
    qa,qb=rnd(a/g,qin)*g,rnd(b/g,qin)*g
    r=half_bits(qa+(W/64)*(qb-qa),out)
    if byp: r=np.where(W==0,half_bits(a,"rne"),r)
    return int((r==H).sum())
print("frozen",run())
print("no k0 bypass",run(byp=False)); print("RNE out",run(out="rne")); print("RZ out",run(out="rz"))
for M in (9,10,11,12,13): print("M",M,run(M=M))
print("input rne",run(qin="rne"))
