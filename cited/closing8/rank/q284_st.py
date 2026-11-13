#!/usr/bin/env python3
"""Q284 offline: fit a cube-face (s, t) rule on E726's eight jobs, freeze it, then score E844's two
off-axis jobs (never used for an (s, t) fit) as held out.

Usage: q284_st.py fit   -> writes q284_rule.json and q284_rule.sha256 (the freeze)
       q284_st.py score -> checks the freeze hash, scores the held-out jobs
Standard library only. Inputs: public resgx545-data paths (E726: texture/p1141 tex-h-cube dumps;
E844: render/closing-r4-render4x out/20261111-211315/c). A pixel's value is 0xD0000000 | index;
face = index // 256, local = index % 256 (a 16 x 16 twiddled face).
"""
import gzip, hashlib, itertools, json, re, struct, sys, os

DATA = "/Users/jtorra/src/resgx545-data"
FIT_DIR = DATA + "/texture/p1141/out-hw/p1141tex-dumps/tex-h-cube"
HELD_DIR = DATA + "/render/closing-r4-render4x/out/20261111-211315/c"
HERE = os.path.dirname(os.path.abspath(__file__))
W, H, N = 64, 32, 16


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def lin(ax, k, c):
    return ("lin", ax, k, c)


ONE, MONE = ("c", 1.0), ("c", -1.0)
FIT = {  # label: (u, v, w), from texture/p1141/probes/p1141-cube.toml
    "cu-zp": (lin("x", 1.5, -2.25), lin("y", 1.5, -2.25), ONE),
    "cu-xp": (ONE, lin("x", 1.5, -2.25), lin("y", 1.5, -2.25)),
    "cu-yp": (lin("x", 1.5, -2.25), ONE, lin("y", 1.5, -2.25)),
    "cu-zn": (lin("x", 1.5, -2.25), lin("y", 1.5, -2.25), MONE),
    "cu-xn": (MONE, lin("x", 1.5, -2.25), lin("y", 1.5, -2.25)),
    "cu-yn": (lin("x", 1.5, -2.25), MONE, lin("y", 1.5, -2.25)),
    "cu-w02": (("m16",), ("c", 0.53125), lin("y", 2.0, -2.0)),
    "cu-w11": (("m16",), ("c", 0.53125), lin("y", 2.0, -3.0)),
}
HELD = {  # E844's method line
    "c-cube-a": (lin("x", 1.5, -2.5), ("c", -0.5), lin("y", 1.5, -2.25)),
    "c-cube-b": (("c", 0.5), lin("x", 1.5, -2.25), lin("y", 1.5, -2.5)),
}


def coord(spec, x, y):
    if spec[0] == "c":
        return spec[1]
    if spec[0] == "m16":
        return f32(1.0 + (2 * (x & 15) + 1) / 32)
    _, ax, k, c = spec
    r = 1.0 + (x / 64 if ax == "x" else y / 32)
    return f32(r * k + c)


def pixels(path):
    rows = {}
    with gzip.open(path, "rt") as fh:
        for line in fh:
            m = re.search(r"row (\d+): (.*)$", line)
            if m:
                rows[int(m.group(1))] = [int(v, 16) for v in m.group(2).split()]
    assert sorted(rows) == list(range(H)) and all(len(r) == W for r in rows.values()), path
    return rows


def twid(s, t, order):
    """Morton index; order 'ty': t in bit 0 (y low), 'sx': s in bit 0."""
    i = 0
    for b in range(4):
        lo, hi = ((t, s) if order == "ty" else (s, t))
        i |= ((lo >> b) & 1) << (2 * b) | ((hi >> b) & 1) << (2 * b + 1)
    return i


def texel(q, mode):
    v = (q + 1.0) / 2 * N
    if mode == "floor":
        k = int(v // 1)
    elif mode == "floor_m":   # ceil(v) - 1: an exact texel boundary goes to the lower texel
        k = -int((-v) // 1) - 1
    else:
        raise ValueError(mode)
    return min(max(k, 0), N - 1)


def predict(rule, u, v, w):
    c = (u, v, w)
    a = [abs(t) for t in c]
    ax = max(range(3), key=lambda i: a[i])
    face = 2 * ax + (c[ax] < 0)
    r = rule[str(face)]
    mi = [i for i in range(3) if i != ax]
    sa, ta = mi[r["s_minor"]], mi[1 - r["s_minor"]]
    qs = r["s_sign"] * c[sa] / a[ax]
    qt = r["t_sign"] * c[ta] / a[ax]
    s, t = texel(qs, r["mode"]), texel(qt, r["mode"])
    return face * 256 + twid(s, t, r["order"])


def jobs(table, d):
    for lab, spec in table.items():
        px = pixels(f"{d}/{lab}.txt.gz")
        yield lab, [(x, y, coord(spec[0], x, y), coord(spec[1], x, y), coord(spec[2], x, y),
                     px[y][x] & 0x0FFFFFFF) for y in range(H) for x in range(W)]


def fit():
    data = dict(jobs(FIT, FIT_DIR))
    rule, log = {}, []
    for face in range(6):
        best = None
        for sm, ss, ts, order, mode in itertools.product((0, 1), (1, -1), (1, -1), ("ty", "sx"),
                                                         ("floor", "floor_m")):
            cand = {str(f): dict(s_minor=sm, s_sign=ss, t_sign=ts, order=order, mode=mode)
                    for f in range(6)}
            hit = tot = 0
            for lab, rows in data.items():
                for x, y, u, v, w, idx in rows:
                    if idx // 256 != face:
                        continue
                    tot += 1
                    hit += predict(cand, u, v, w) == idx
            key = (hit, sm, ss, ts, order, mode)
            log.append(f"face {face} sm={sm} ss={ss:+d} ts={ts:+d} {order} {mode}: {hit}/{tot}")
            if best is None or hit > best[0]:
                best = (hit, tot, cand[str(face)])
        rule[str(face)] = best[2]
        log.append(f"BEST face {face}: {best[0]}/{best[1]} {best[2]}")
    per = {}
    for lab, rows in data.items():
        per[lab] = (sum(predict(rule, u, v, w) == idx for x, y, u, v, w, idx in rows), len(rows))
        log.append(f"fit {lab}: {per[lab][0]}/{per[lab][1]}")
    blob = json.dumps(rule, sort_keys=True, indent=1).encode()
    open(f"{HERE}/q284_rule.json", "wb").write(blob)
    open(f"{HERE}/q284_rule.sha256", "w").write(hashlib.sha256(blob).hexdigest() + "  q284_rule.json\n")
    print("\n".join(log))
    print("frozen", hashlib.sha256(blob).hexdigest())


def score():
    blob = open(f"{HERE}/q284_rule.json", "rb").read()
    want = open(f"{HERE}/q284_rule.sha256").read().split()[0]
    assert hashlib.sha256(blob).hexdigest() == want, "freeze changed"
    rule = json.loads(blob)
    # control that can fail: the fit jobs must reproduce exactly under the frozen rule
    for tag, table, d in (("fit", FIT, FIT_DIR), ("held", HELD, HELD_DIR)):
        for lab, rows in jobs(table, d):
            miss = [(x, y, idx, predict(rule, u, v, w)) for x, y, u, v, w, idx in rows
                    if predict(rule, u, v, w) != idx]
            faces = sorted({idx // 256 for *_, idx in rows})
            print(f"{tag} {lab}: {len(rows) - len(miss)}/{len(rows)} faces {faces}")
            for m in miss[:12]:
                print("   miss x=%d y=%d hw=%#x model=%#x" % m)


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
