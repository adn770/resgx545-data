#!/usr/bin/env python3
"""Q282 offline: the bilinear sample of an sRGB texel (T0 bit 27). Declared candidate family,
fitted on g-bl-st-a ONLY (E723's kept dump); the best is frozen by hash (q282_rule.json +
q282_rule.sha256) before g-bl-st-b is read by q282_score.py.

Per pixel the four corner bytes and the raw fractions come from the landed sampler model
(resgx545-data texture/p1141/recompute/tex2.py, E720's two-stage geometry) instrumented here;
the hardware half per channel from the kept dump. Standard library only beyond that model.

    /Users/jtorra/src/resgx545/.venv/bin/python -B q282_fit.py fit     # fit on a, write the freeze
"""
import gzip, hashlib, itertools, json, math, pathlib, re, struct, sys

DATA = pathlib.Path("/Users/jtorra/src/resgx545-data/texture/p1141")
HERE = pathlib.Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(DATA / "recompute"))
sys.path.insert(0, str(DATA / "gen"))
import tex2  # noqa: E402

CASES = {c["name"]: c for c in json.loads((DATA / "gen/cases.json").read_text())}
DUMPS = DATA / "out-hw/p1141tex-dumps/tex-d-t0b27"
ROW = re.compile(r"row (\d+): (.*)$")


def hw(name):
    txt = gzip.open(DUMPS / f"{name}.txt.gz", "rt").read()
    rows = {}
    for ln in txt.splitlines():
        m = ROW.search(ln)
        if m:
            rows[int(m.group(1))] = [int(v, 16) for v in m.group(2).split() if re.fullmatch(r"(0x)?[0-9a-fA-F]{1,8}", v)]
    px = [v for y in sorted(rows) for v in rows[y]]
    assert len(px) == 2048, len(px)
    return px


def corners(name):
    """per pixel: (b00, b10, b01, b11) per channel (2 channels), raw fx, fy (floats in [0, 1))."""
    rec = []
    orig = tex2.Tex2.level_read

    def lr(self, u, v, l, bilinear):
        lw, lh, _ = self.level_geom(l)
        x, y = u * lw - 0.5, v * lh - 0.5
        x0, y0 = math.floor(x), math.floor(y)
        t = [self.fetch(x0 + dx, y0 + dy, l) for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
        rec.append(([[t[k] >> 8 * c & 255 for k in range(4)] for c in (0, 1)], x - x0, y - y0))
        return orig(self, u, v, l, bilinear)

    tex2.Tex2.level_read = lr
    try:
        tex2.predict(CASES[name]["spec"], {}, srgb=True, srgb_pre=True)
    finally:
        tex2.Tex2.level_read = orig
    assert len(rec) == 2048, len(rec)
    return rec


def s2l(b):
    c = b / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def h2f(h):
    return struct.unpack("<e", struct.pack("<H", h))[0]


def half_rne(f):
    return struct.unpack("<H", struct.pack("<e", f))[0]


def half_rz(f):
    h = half_rne(f)
    return h - 1 if h2f(h) > f and h & 0x7fff else h


def half_ru(f):
    h = half_rne(f)
    return h + 1 if h2f(h) < f else h


ROUND = {"rne": half_rne, "rz": half_rz, "ru": half_ru}


def frac(f, P, mode):
    return int(f * P) if mode == "trunc" else min(int(f * P + 0.5), P)


def model(bytes4, fx, fy, m):
    """one channel. m: decode (exact|half|f32), arith (float|f32|half2|fix16|fix12), order (xy|yx|joint),
    P (64|128|256), fr (trunc|round), out (rne|rz|ru)."""
    P = m["P"]
    ix, iy = frac(fx, P, m["fr"]), frac(fy, P, m["fr"])
    if m["decode"] == "exact":
        d = [s2l(b) for b in bytes4]
    elif m["decode"] == "half":
        d = [h2f(half_rne(s2l(b))) for b in bytes4]
    else:
        d = [f32(s2l(b)) for b in bytes4]
    a = m["arith"]
    if a.startswith("fix"):
        n = int(a[3:])
        S = 1 << n
        q = [int(v * S + 0.5) for v in d]
        sh = P.bit_length() - 1
        rnd = P // 2 if m.get("lr", "half") == "half" else 0
        L = lambda p, r, w: (p * (P - w) + r * w + rnd) >> sh
        if m["order"] == "xy":
            r = L(L(q[0], q[1], ix), L(q[2], q[3], ix), iy)
        elif m["order"] == "yx":
            r = L(L(q[0], q[2], iy), L(q[1], q[3], iy), ix)
        else:
            r = (q[0] * (P - ix) * (P - iy) + q[1] * ix * (P - iy) + q[2] * (P - ix) * iy + q[3] * ix * iy + (P * P // 2 if rnd else 0)) >> (2 * sh)
        return ROUND[m["out"]](r / S)
    wx, wy = ix / P, iy / P
    if a == "half2":
        H = lambda v: h2f(half_rne(v))
        Lh = lambda p, r, w: H(p * (1 - w) + r * w)
        if m["order"] == "yx":
            return ROUND[m["out"]](Lh(Lh(d[0], d[2], wy), Lh(d[1], d[3], wy), wx))
        return ROUND[m["out"]](Lh(Lh(d[0], d[1], wx), Lh(d[2], d[3], wx), wy))
    R = f32 if a == "f32" else (lambda v: v)
    if m["order"] == "joint":
        v = R(d[0] * (1 - wx) * (1 - wy) + d[1] * wx * (1 - wy) + d[2] * (1 - wx) * wy + d[3] * wx * wy)
    elif m["order"] == "yx":
        v = R(R(R(d[0] * (1 - wy) + d[2] * wy) * (1 - wx)) + R(R(d[1] * (1 - wy) + d[3] * wy) * wx))
    else:
        v = R(R(R(d[0] * (1 - wx) + d[1] * wx) * (1 - wy)) + R(R(d[2] * (1 - wx) + d[3] * wx) * wy))
    return ROUND[m["out"]](v)


FAMILY = [dict(decode=d, arith=a, order=o, P=P, fr=fr, out=out)
          for d in ("exact", "half", "f32")
          for a in ("float", "f32", "half2", "fix8", "fix10", "fix12", "fix14", "fix16", "fix20")
          for o in ("xy", "yx", "joint")
          for P in (64, 128, 256)
          for fr in ("trunc", "round")
          for out in ("rne", "rz", "ru")
          if not (a == "half2" and o == "joint")]


def score(name, m, rec=None, pix=None):
    rec = rec or corners(name)
    pix = pix or hw(name)
    ok_px = ok_ch = 0
    for (ch, fx, fy), w in zip(rec, pix):
        good = [model(ch[c], fx, fy, m) == (w >> 16 * c & 0xffff) for c in (0, 1)]
        ok_ch += sum(good)
        ok_px += all(good)
    return ok_px, ok_ch


def key(m):
    return json.dumps(m, sort_keys=True)


if __name__ == "__main__":
    assert sys.argv[1:] == ["fit"]
    rec, pix = corners("g-bl-st-a"), hw("g-bl-st-a")
    res = sorted(((score("g-bl-st-a", m, rec, pix), key(m)) for m in FAMILY), reverse=True)
    print(f"family {len(FAMILY)} candidates, fit job g-bl-st-a (2048 pixels, 4096 channels)")
    for (px, ch), k in res[:25]:
        print(f"  px {px:4d} ch {ch:4d}  {k}")
    print("  the frozen E723 order (exact, float, xy, 64, trunc, rne):",
          score("g-bl-st-a", dict(decode="exact", arith="float", order="xy", P=64, fr="trunc", out="rne"), rec, pix))
    best = res[0]
    ties = [k for s, k in res if s == best[0]]
    rule = {"question": "Q282", "fit_job": "g-bl-st-a", "fit_score": list(best[0]), "rule": json.loads(best[1]),
            "tied_at_best": [json.loads(k) for k in ties], "heldout_job": "g-bl-st-b",
            "prediction": "every tied rule scores the same on g-bl-st-b as the rule; the rule exact on >= 2040 of 2048 pixels"}
    blob = json.dumps(rule, sort_keys=True, indent=1)
    (HERE / "q282_rule.json").write_text(blob + "\n")
    (HERE / "q282_rule.sha256").write_text(hashlib.sha256((blob + "\n").encode()).hexdigest() + "  q282_rule.json\n")
    print(f"frozen: {len(ties)} tied at best; sha256 {hashlib.sha256((blob + chr(10)).encode()).hexdigest()}")
