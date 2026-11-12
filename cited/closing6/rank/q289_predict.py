# Q289 draft predictions for a held-out fill row (not frozen: the builder freezes them).
# Target W x H in 32x16 tiles; poke x^(8*fx) (DOUTU1 bits 11:3) or y^(0x1000*fy) (bits 21:12).
# M-OR: tile t stores at (2t | f) >> 1; M-ADD: (2t + f) >> 1; outside the target: no store.
# Printed: tile columns (x pokes) or rows (y pokes) left unwritten (0xdeadbeef) under each model.
import sys
def unwritten(n,f,op):
    hit={op(2*t,f)>>1 for t in range(n)}
    return [t for t in range(n) if t not in hit]
for W,H in ((128,64),(256,32),(64,128)):
    nx,ny=W//32,H//16
    print(f'fill {W}x{H}: {nx} tile columns, {ny} tile rows')
    for ax,n,unit in (('x',nx,8),('y',ny,0x1000)):
        for f in range(1,2*n+1):
            o=unwritten(n,f,lambda a,b:a|b); a=unwritten(n,f,lambda a,b:a+b)
            sep='SEPARATES' if o!=a else ''
            print(f'  {ax}^{f*unit:#x}: OR {o} ADD {a} {sep}')
