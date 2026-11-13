import sys; sys.path.insert(0,'/Users/jtorra/src/scratch/resgx545/closing10/seeds/q120')
from ld import *
import numpy as np
SIGN=0x80000000
def in_tile_index(x,y):
    j=0
    for i in range(4):
        j|=((y>>i)&1)<<(2*i)|((x>>i)&1)<<(2*i+1)
    return j|((x>>4)&1)<<8
def ctl_x_depth(c):
    return {x:int(c[in_tile_index(x,0)]) for x in range(32)}
# record start table (chunk-relative), fitted on 64x32 f3 row 0/1 (see report)
R={0:11,1:6,2:1,3:28,4:23,5:18,6:13,7:40,8:35,9:30,10:57,11:52,12:47,13:74,14:69,15:64,
   16:91,17:86,18:81,19:108,20:103,21:98,22:93,23:120,24:115,25:110,26:137,27:132,28:127,
   29:154,30:149,31:144}
def stencil_byte(x,y,slot):
    j=in_tile_index(x,y); k=j>>2; i=slot*128+k; lane=j&3
    return [i&0xff,(i>>8)&0xff,0,0][lane]

def block(tx,ty,tw):
    """stream block of tile (tx,ty): two tile rows form a macro row, x outer, y inner."""
    return 2*tw*(ty>>1)+2*tx+(ty&1)
def tiles(W,H):
    tw=(W+31)//32; th=(H+15)//16
    return tw,th
