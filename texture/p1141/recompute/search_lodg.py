"""Design search (offline): independent gradient operand sets that tell the five footprint rules apart
on every pair, on 64x64 and 128x32 chains. Seeded; the chosen sets are written into gen/cat1141.py."""
import itertools, random, sys
from lib import P1132
sys.path.insert(0, str(P1132 / "gen"))
from tex2 import *
import catalog as cc
HYP = ["P", "O", "Mp", "Mo", "F", "S"]
random.seed(1141)
def menu():
    m = [("Z", cc.ZERO)]
    for j in (6, 7, 8, 9):
        m.append((f"x{j}", cc.linx(2.0 ** -j)))
        m.append((f"y{j}", cc.liny(2.0 ** -j)))
        m.append((f"c{j}", cc.const(2.0 ** -j)))
    return m
M = menu()
T0 = cc.T0_GRAD
def spec(ops, t1, u, v):
    return dict(t0=T0, t1=t1, u=u, v=v, ins="grad", grad=[o[1] for o in ops], base=0, t3=cc.T3_TW)
def score(ops, sq):
    t1 = cc.W64 if sq else cc.t1tw(128, 32)
    u, v = cc.window(64, 64) if sq else cc.window(128, 32)
    sp = spec(ops, t1, u, v)
    ims = {h: predict(sp, {}, foot=h, two_stage=False) for h in HYP}
    return {(a, b): sum(x != y for x, y in zip(ims[a], ims[b])) for a, b in itertools.combinations(HYP, 2)}
best = []
for it in range(500):
    ops = [random.choice(M) for _ in range(4)]
    if sum(o[0] != "Z" for o in ops) < 3:
        continue
    s = score(ops, True)
    mn = min(v for k, v in s.items() if k != ('Mp', 'Mo'))
    best.append((mn, [o[0] for o in ops], sorted(s.items(), key=lambda kv: kv[1])[:2]))
best.sort(reverse=True)
for b in best[:15]:
    print(b)
