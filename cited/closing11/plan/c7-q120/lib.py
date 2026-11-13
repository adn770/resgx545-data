import gzip, os, struct, sys
KP="/Users/jtorra/src/resgx545-data/render/closing-r10-zls"
A=KP+"/out/20261113-102039"
FILL=0xDEADBEEF
sys.path.insert(0,KP+"/gen")
def dw(stage,n,base=None):
    p=(base or A)+"/"+stage+"/"+n+".depth.1.bin.gz"
    b=gzip.open(p).read()
    return list(struct.unpack("<%dI"%(len(b)//4),b))
def f(v): return struct.unpack("<f",struct.pack("<I",v))[0]
