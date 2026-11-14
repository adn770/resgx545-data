"""POST HOC (after the run, not frozen): what ty's rows of E1065 read. Every mode 4 to 7 pixel is a
named dword with each byte halved, rounded up (H-HALF, frozen, 9 of 9). Per row: the names n whose
halves give each pixel (the lowest of each pair the halving cannot part), as the name less the
column x mod W (mode 4: whether one c fits the row: the frozen fit predicted 39 W + 52 for types 1
and 3, 40 W + 20 for type 4), the flat names of modes 5 to 7 and the 64 x 64 type 4 rows, and the
references against the layouts the frozen models name. Nothing here was predicted."""
import gzip, os, re
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(KP, "out/20261114-090305/ty")


def px(name):
    t = gzip.open(os.path.join(D, name + ".txt.gz"), "rt").read()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()]
            for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", t, re.M)}
    return [v for y in sorted(rows) for v in rows[y]]


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


HALVES = {}
for n in range(32768):
    HALVES.setdefault(half(0xD0000000 | n), []).append(n)

SIZES = {"08": (8, 8), "64": (64, 64), "6416": (64, 16)}
print("mode 4: names of row 0 as c + (x mod W) (one c a row), the frozen prediction beside it")
for name in ("ty-08-ty1-u4", "ty-64-ty1-u4", "ty-6416-ty1-u4", "ty-08-ty4-u4", "ty-64-ty4-u4"):
    p = px(name)
    w = SIZES[name.split("-")[1]][0]
    ty = int(name.split("-")[2][2:])
    alike = all(p[64 * y:64 * y + 64] == p[:64] for y in range(32))
    cs = None
    for x in range(64):
        c = {n - x % w for n in HALVES.get(p[x], [])}
        cs = c if cs is None else cs & c
    a, b = (39, 52) if ty != 4 else (40, 20)
    print(f"{name}: rows alike {alike}; c in {sorted(cs)} (frozen {a * w + b}); "
          f"names x = 0..8: {[HALVES.get(p[x]) for x in range(0, 9)]}")
    if not cs:
        print("  names of row 0 at x = 0, 8, 16, 24, 32, 40, 48, 56, 63:",
              [HALVES[p[x]][0] for x in (0, 8, 16, 24, 32, 40, 48, 56, 63)])
print("modes 5 to 7: the one value of the row, its names")
for name in ("ty-08-ty1-u5", "ty-64-ty1-u5", "ty-64-ty1-u6", "ty-64-ty1-u7"):
    p = px(name)
    print(f"{name}: {len(set(p))} value(s) {p[0]:08x}: names {HALVES.get(p[0])}")
print("references: the dword read as 0xD0000000 | n, against stride * (y mod H) + (x mod W)")
for name, w, h in (("ty-08-ty1-u0", 8, 8), ("ty-08-ty4-u0", 8, 8), ("ty-64-ty1-u0", 64, 64),
                   ("ty-64-ty4-u0", 64, 64), ("ty-6416-ty1-u0", 64, 16)):
    p = px(name)
    ok = {s: sum(p[64 * y + x] == 0xD0000000 | (s * (y % h) + x % w) for y in range(32)
                 for x in range(64)) for s in (w, 16, 32, 2 * w)}
    print(f"{name}: matches by stride {ok}")
p = px("ty-64-ty4-u0")
print("ty-64-ty4-u0 rows 0, 1, 2, 15, 16, 17, 31 first 4 and x = 63 (n less 0xD0000000):")
for y in (0, 1, 2, 15, 16, 17, 31):
    print(f"  y={y}: {[p[64 * y + x] & 0xFFFFFFF for x in (0, 1, 2, 3, 32, 63)]}")
print("post hoc fit (type 1, labelled; held out by nothing, five sizes): mode 4 name = W H + 7 W + 52 "
      "+ (x mod W) (or 256 less: the halves cannot part them), mode 5 = 7 W + 51, modes 6 and 7 "
      "= mode 4's last column")
for name, w, h in (("ty-08-ty1-u4", 8, 8), ("ty-64-ty1-u4", 64, 64), ("ty-6416-ty1-u4", 64, 16)):
    p = px(name)
    print(f"{name}: {p == [half(0xD0000000 | (w * h + 7 * w + 52 + x % w)) for y in range(32) for x in range(64)]}")
for name, w, n in (("ty-08-ty1-u5", 8, 7 * 8 + 51), ("ty-64-ty1-u5", 64, 7 * 64 + 51),
                   ("ty-64-ty1-u6", 64, 64 * 64 + 7 * 64 + 52 + 63),
                   ("ty-64-ty1-u7", 64, 64 * 64 + 7 * 64 + 52 + 63)):
    print(f"{name}: {set(px(name)) == {half(0xD0000000 | n)}}")
print("E1055's kept 16 x 16 (676 = 420 + 256) and 32 x 32 (1300): W H + 7 W + 52 =",
      16 * 16 + 7 * 16 + 52, 32 * 32 + 7 * 32 + 52, "; mode 5 at 16 x 16: 7 * 16 + 51 =", 7 * 16 + 51)
