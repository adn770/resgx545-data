# Offline post hoc refit of the partial-render count at U=287 (L1b g-qf, 22 cells),
# held-out check on L1b g-qh s275 (6 cells). Families: count = c + floor((U + a) / (P + b))
# and c + ceil(...). Data copied from closing3/r3-geo-c/out/score-g-q{f,h}.txt.
import math
f287={0x24:9,0x25:9,0x27:8,0x28:8,0x29:8,0x2c:7,0x2d:7,0x31:7,0x32:6,0x39:5,0x3a:5,0x43:5,0x44:4,0x53:4,0x54:3,0x6d:3,0x6e:2,0xa0:2,0xa1:2,0xa2:2,0xa3:1,0xb0:1}
h275={0x26:8,0x27:8,0x2a:7,0x2b:7,0x31:6,0x52:3}
fits=[]
for rnd in ('floor','ceil'):
  op=math.floor if rnd=='floor' else math.ceil
  for a in range(-200,201):
    for b in range(-0x40,0x41):
      for c in range(-2,3):
        ok=True
        for P,n in f287.items():
          d=P+b
          if d<=0 or c+op((287+a)/d)!=n: ok=False;break
        if ok:
          ho=sum(c+op((275+a)/(P+b))==n for P,n in h275.items())
          fits.append((rnd,a,b,c,ho))
print(len(fits),'fits on 22 cells of U=287')
from collections import Counter
print('held-out s275 matches (of 6):',Counter(f[4] for f in fits))
for f in fits[:40]: print(f)

# Family 2: the first abort at P + b1 (a raised first threshold, Q210), later ones every P + b2
# pages, a fixed retained r per partial render is folded into b2: n = 1 + ceil((U + a - (P + b1)) / (P + b2)) for U + a > P + b1.
fits2=[]
for a in range(-60,61):
  for b1 in range(-0x40,0x41):
    for b2 in range(-0x40,0x41):
      ok=True
      for P,n in f287.items():
        A1=P+b1; d=P+b2
        if d<=0: ok=False;break
        m=0 if 287+a<=A1 else 1+math.ceil((287+a-A1)/d)
        if m!=n: ok=False;break
      if ok:
        ho=0
        for P,n in h275.items():
          A1=P+b1; d=P+b2
          m=0 if 275+a<=A1 else 1+math.ceil((275+a-A1)/d)
          ho+=(m==n)
        fits2.append((a,b1,b2,ho))
print(len(fits2),'family-2 fits on U=287')
print('held-out s275:',Counter(f[3] for f in fits2))
for f in fits2[:30]: print(f)
