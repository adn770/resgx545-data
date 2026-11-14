"""POST HOC (after the run, not frozen): what ty's rows read (E1055). Every pixel of every mode 4 to
7 row is a named dword with each byte halved, rounded up (H-HALF, frozen, 10 of 10). Per row: the
names n (all candidates below 32768) whose halves give each pixel, as n less the unwrapped column
U = W + (x mod W) of E567's `map` u in [1, 2), and whether one value fills the row; and the 32 x 32
references against the layouts the sim models."""
import gzip, os, re
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(KP, "out/20261114-073318/ty")


def px(name):
    t = gzip.open(os.path.join(D, name + ".txt.gz"), "rt").read()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()]
            for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", t, re.M)}
    return [v for y in sorted(rows) for v in rows[y]]


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


def names(v):
    return [n for n in range(32768) if half(0xD0000000 | n) == v]


HALVES = {}
for n in range(32768):
    HALVES.setdefault(half(0xD0000000 | n), []).append(n)

for name, w in [("ty-16-ty1-u5", 16), ("ty-16-ty1-u6", 16), ("ty-16-ty1-u7", 16),
                ("ty-16-ty4-u5", 16), ("ty-16-ty4-u6", 16), ("ty-16-ty4-u7", 16),
                ("ty-16-ty1-n16", 16), ("ty-32-ty1-u4", 32), ("ty-32-ty3-u4", 32),
                ("ty-32-ty4-u4", 32)]:
    p = px(name)
    alike = all(p[64 * y:64 * y + 64] == p[:64] for y in range(32))
    vals = sorted(set(p))
    if name.endswith("n16"):
        U = [x - 24 for x in range(64)]
    else:
        U = [w + x % w for x in range(64)]
    cs = None
    for x in range(64):
        c = {n - U[x] for n in HALVES.get(p[x], [])}
        cs = c if cs is None else cs & c
    print(f"{name}: rows alike {alike}; {len(vals)} distinct value(s); names of pixel 0 "
          f"{HALVES.get(p[0])}; c with n = c + U on every pixel: {sorted(cs)}")
    if name.endswith("n16"):
        cw = None
        for x in range(64):
            c = {n - (U[x] % 16) for n in HALVES.get(p[x], [])}
            cw = c if cw is None else cw & c
        print(f"   n = c + (U mod 16) on every pixel: c in {sorted(cw)}")
    if len(vals) == 1:
        print(f"   one value {vals[0]:08x}: names {HALVES.get(vals[0])}")
for ty, stride in ((1, 32), (3, 32), (4, 32)):
    p = px(f"ty-32-ty{ty}-u0")
    ok = p == [0xD0000000 | (stride * y + x % 32) for y in range(32) for x in range(64)]
    print(f"ty-32-ty{ty}-u0: dword {stride} t + s on every pixel: {ok}")
