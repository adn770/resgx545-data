import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q282_r10_tab import *
A,B,W,H,J=table(FIT)
print(len(A))
dA=h2f(S_:=np.array([S.half_rne(S.s2l(int(a))) for a in A])); dB=h2f(np.array([S.half_rne(S.s2l(int(b))) for b in B]))
w=W/64
ex=dA+w*(dB-dA)
hw=h2f(H)
# ulp of hw
def ulp(x):
    m,e=np.frexp(np.abs(x)); return 2.0**(e-11)  # half ulp for normal
u=ulp(np.where(hw==0,1e-9,hw))
e=(hw-ex)/u
print("err/ulp stats", np.percentile(e,[0,1,10,50,90,99,100]))
print("exact-eq count rne:", (np.array([S.half_rne(float(v)) for v in ex])==H).sum())
# sign vs w
for k in (1,8,16,32,48,63):
    m=W==k; print(k, "mean e",e[m].mean(), "frac below",(e[m]<-0.5).mean())
# monotonic? swapped direction dA>dB
up=dB>dA
print("up:",e[up].mean(),"down:",e[~up].mean())
# using exact linear
lA=s2l_arr(A); lB=s2l_arr(B)
ex2=lA+w*(lB-lA); e2=(hw-ex2)/u
print("exact lin err", np.percentile(e2,[0,1,10,50,90,99,100]))
print("hw== rne(exact lin)", (np.array([S.half_rne(float(v)) for v in ex2])==H).sum())
print("---big")
idx=np.argsort(e)[:12]
for i in idx: print(A[i],B[i],W[i],hex(H[i]),hw[i],ex[i],e[i], dA[i],dB[i])
idx=np.where(np.abs(e)>1.6)[0]; print(len(idx))
import collections
print(collections.Counter((A[idx]==0)|(B[idx]==0)))
# rne mismatches by signed half-ulp diff
rne=np.array([S.half_rne(float(v)) for v in ex]); d=H.astype(int)-rne
print(collections.Counter(d.tolist()).most_common(12))
