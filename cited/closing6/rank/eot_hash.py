# Q289: predicted images of the fill (64x32, tiles 32x16) under the half-tile reading, hashed
# with libsgxfive's sgxfive_hash_dwords (FNV-1a 64 over the dwords, row after row).
# Model M-OR: the tile (tx, ty) stores at ((2tx | fx) >> 1, (2ty | fy) >> 1) where fx, fy are
# the XOR constants in field units (bits 11:3, bits 21:12); outside the target nothing is stored.
# Model M-ADD: the same with + in place of |.  Pixels never stored keep 0xdeadbeef.
def h(px):
    v=0xcbf29ce484222325
    for d in px:
        for b in range(4):
            v^=(d>>(8*b))&0xff; v=(v*0x100000001b3)&0xffffffffffffffff
    return v
W,H,TW,TH=64,32,32,16
def img(fx,fy,op):
    st=set()
    for tx in range(2):
        for ty in range(2):
            nx=op(2*tx,fx)>>1; ny=op(2*ty,fy)>>1
            if nx<2 and ny<2: st.add((nx,ny))
    return [0xff336699 if (x//TW,y//TH) in st else 0xdeadbeef for y in range(H) for x in range(W)]
obs={'base':0xb60c6095080bd325,'x10':0x97334f75829dab25,'y2000':0x55d29a878f45ab25,'all':0xfc8ce806207f8325}
for name,op in (('OR',lambda a,b:a|b),('ADD',lambda a,b:a+b),('XOR',lambda a,b:a^b)):
    res=[]
    for lab,fx,fy,want in (('x^0x8',1,0,'base'),('x^0x10',2,0,'x10'),('x^0x18',3,0,'x10'),('x^0x20',4,0,'all'),
                           ('y^0x1000',0,1,'base'),('y^0x2000',0,2,'y2000'),('y^0x3000',0,3,'y2000'),('y^0x4000',0,4,'all')):
        res.append(f"{lab}:{'ok' if h(img(fx,fy,op))==obs[want] else 'MISS'}")
    print(name,' '.join(res))
