"""POST HOC (after the run, not frozen): why sb12-rep-m0-c0 failed its inset control.
Reads the kept outputs of out/20261113-214825/sb12 and E383's kept runs (gen/sb.py)."""
import collections, gzip, os, re, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import pins, sb as SB
D = os.path.join(KP, "out/20261113-214825/sb12")
def img(n):
    t = gzip.open(os.path.join(D, n + ".txt.gz"), "rt").read()
    return list(SB.case_images(t).values())[0], t
names = [ln.split("|")[0] for ln in open(os.path.join(KP, "tables/sb12.txt")) if ln[0] != "#"]
ims = {n: img(n)[0] for n in names}
print("header lines of sb12-rep-m0-c0:")
print("\n".join(l for l in img("sb12-rep-m0-c0")[1].splitlines() if "row" not in l))
for mode in range(7):
    e = SB.kept(pins.blob, 0x1200 | mode)
    w = set(SB.words(pins.blob, mode))
    for c in (0, 1):
        n = f"sb12-m{mode}-c{c}" if (mode or c) else "sb12-rep-m0-c0"
        im = ims[n]
        out = [p for p, v in enumerate(im) if v not in w]
        rows = collections.Counter(p // 64 for p in out)
        diff = sum(a != b for a, b in zip(im, e[0]))
        print(f"{n}: outside E383's set {len(out)} (rows {sorted(rows)[:6]}.. {len(rows)} rows), "
              f"differs from E383 run 1 on {diff}; top new words "
              f"{collections.Counter(im[p] for p in out).most_common(4)}")
# same image across modes 0-2?
print("m0 c0 == m1 c0:", ims["sb12-rep-m0-c0"] == ims["sb12-m1-c0"],
      "pixels differing", sum(a != b for a, b in zip(ims["sb12-rep-m0-c0"], ims["sb12-m1-c0"])))
print("c0 vs c1 mode 0 differ:", sum(a != b for a, b in zip(ims["sb12-rep-m0-c0"], ims["sb12-m0-c1"])))


def tri_inside(x, y, v=SB.DEFAULT_V):
    """Pixel centre inside the default triangle (edge functions, either winding)."""
    px, py = x + 0.5, y + 0.5
    s = []
    for i in range(3):
        (ax, ay), (bx, by) = v[i], v[(i + 1) % 3]
        s.append((bx - ax) * (py - ay) - (by - ay) * (px - ax))
    return all(t >= 0 for t in s) or all(t <= 0 for t in s)


print("map of sb12-rep-m0-c0 (o: outside E383's set, T: inside the triangle, #: both):")
w0 = set(SB.words(pins.blob, 0))
im = ims["sb12-rep-m0-c0"]
inside = out_in = out_tot = 0
for y in range(64):
    r = ""
    for x in range(64):
        o, t = im[y * 64 + x] not in w0, tri_inside(x, y)
        out_tot += o; out_in += o and t; inside += t
        r += "#" if o and t else "o" if o else "T" if t else "."
    if y % 2 == 0:
        print(r)
print(f"outside the set: {out_tot}, of them inside the triangle {out_in}; triangle pixels {inside}")
e = SB.kept(pins.blob, 0x1200)[0]
d = [p for p in range(4096) if im[p] != e[p]]
print("differ from E383 run 1:", len(d), "inside the triangle:", sum(tri_inside(p % 64, p // 64) for p in d))


def mapping(a, b):
    """How far b is a function of a, pixel by pixel: the pixels whose (a -> b) pair is the most
    common b of that a, and the classes."""
    m = collections.defaultdict(collections.Counter)
    for x, y in zip(a, b):
        m[x][y] += 1
    agree = sum(c.most_common(1)[0][1] for c in m.values())
    return agree, {f"{k:08x}": f"{c.most_common(1)[0][0]:08x}" for k, c in
                   sorted(m.items(), key=lambda kv: -sum(kv[1].values()))[:5]}


print("as a function of the colour 0 replicate's word (same mode, this session):")
for mode in range(7):
    c0 = ims["sb12-rep-m0-c0" if mode == 0 else f"sb12-m{mode}-c0"]
    c1 = ims[f"sb12-m{mode}-c1"]
    ag, top = mapping(c0, c1)
    print(f"  mode {mode}: c1 from c0 {ag}/4096; {top}")
print("noise: this session's colour 0 from E383's run 1:",
      [mapping(SB.kept(pins.blob, 0x1200 | m)[0],
               ims["sb12-rep-m0-c0" if m == 0 else f"sb12-m{m}-c0"])[0] for m in range(7)])
