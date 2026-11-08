#!/usr/bin/env python3
"""Recompute the 11.26 findings from the KEPT raw outputs, written apart from the run scripts (no
code of them is reused: the run scripts reduce per tile with bounding boxes and digit maps; this
script fits per stored tile, builds the predicates from the words and reads the dumps itself).

usage: recompute_p1126.py KEEPROOT [declared.tsv]
       recompute_p1126.py --selftest

KEEPROOT holds one directory a script (msaa-ident, msaa-te-dumps, mtile-fields,
mtile-fields-risky, mtile-msaa, mtile-msaa-risky, msaa-resolve), each with cases.tsv and
NAME.txt.gz (the whole tool output; NAME-x / NAME-y for the identity jobs) and, for msaa-te-dumps,
NAME.param.txt.gz-style dumps (NAME.param.txt.gz, NAME.tadata.txt.gz hold the raw binary).
Nothing is judged by this script's wording: it prints, per hypothesis, the numbers a reader needs
and counts agreements separately for the declared sets (fit, heldout, prior, control, repeat).

Hypotheses (declared before any run, plan.md section 2):
  H30a  every 32x16 stored tile (tx, ty) holds the samples of its own pixels at 2x in x (modes 1, 2)
        and 1x (mode 1) or 2x (mode 2) in y, and only the stored 16 x 16 corner is written
        (source origin (32 tx, 16 ty)); the rest of the tile is background.
  H30b  as H30a but a tile holds the pixels of another tile (a shift by whole tiles): the fit
        reports the shift, TE bits set are expected to show one.
  PA    a macrotile word set draws exactly iff it splits the tiles into the same macrotile runs as
        the rule's.
  PB    exactly iff B1 <= B2 <= B3, B2 the rule's, bit 31 and the stride the rule's.
  PC    exactly iff B2 is the rule's (the other fields free).
  H86i  at 4x the stored tile signature does not depend on the macrotile words as long as the job
        completes (every family equals R's).
"""
import collections
import csv
import gzip
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gen"))
import rules  # noqa: E402

G, B, SENT = 0xFF00FF00, 0xFF203040, 0xDEADBEEF


def read_gz(path):
    with gzip.open(path, "rb") as fh:
        return fh.read()


def rows_of(path):
    """{(x, y): value} of the 'row Y: v v v' lines of a kept output (tri or probe)."""
    img = {}
    for line in read_gz(path).decode("latin-1").splitlines():
        m = re.search(r"row (\d+): (.*)$", line)
        if m:
            y = int(m.group(1))
            for x, v in enumerate(m.group(2).split()):
                try:
                    img[(x, y)] = int(v, 16)
                except ValueError:      # 11.26: a tool message cut into a row line of a faulted job
                    pass
    return img


def text_of(path):
    return read_gz(path).decode("latin-1")


def cases_of(d):
    p = os.path.join(d, "cases.tsv")
    if not os.path.exists(p):
        return []
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def declared(path):
    out = {}
    if path and os.path.exists(path):
        with open(path, newline="") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                out[(r["script"], r["case"])] = r
    return out


def centre(v):
    f = struct.unpack("<f", struct.pack("<I", v))[0]
    q = round(f - 0.5)
    return (q, abs(f - 0.5 - q)) if f == f and 0 <= q < 8192 else (None, 1.0)


# ---- Q030 / Q089: the identity maps ------------------------------------------------------------
def fit_axis(pairs, org, s):
    """pairs [(stored, source)], stored origin org, s stored pixels a source pixel: the source
    origin q = source - (stored - org) // s that most pairs share, and how many do."""
    c = collections.Counter(src - (st - org) // s for st, src in pairs)
    return c.most_common(1)[0] if c else (None, 0)


def ident_case(dd, name, w, h, mode):
    X = rows_of(os.path.join(dd, name + "-x.txt.gz"))
    Y = rows_of(os.path.join(dd, name + "-y.txt.gz"))
    tx, ty = -(-w // 32), -(-h // 16)
    n = len(X)
    dec = {}
    off = 0
    for k, vx in X.items():
        vy = Y.get(k)
        if vy is None:
            continue
        (px, ex), (py, ey) = centre(vx), centre(vy)
        if px is None or py is None:
            continue
        if ex > 0.05 or ey > 0.05:
            off += 1
            continue
        dec[k] = (px, py)
    src = set(dec.values())
    print("  stored %d, decodable %d, off-centre %d, other %d; distinct source pixels %d of %d" % (
        n, len(dec), off, n - len(dec) - off, len(src), w * h))
    sx_pred, sy_pred = (2, 1 if mode == 1 else 2) if mode else (1, 1)
    good = pix_ok = pix_all = 0
    shifts = collections.Counter()
    for j in range(ty):
        for i in range(tx):
            pts = [(k, v) for k, v in dec.items() if k[0] // 32 == i and k[1] // 16 == j]
            if not pts:
                continue
            best = None
            for sx in (1, 2):
                qx, cx = fit_axis([(k[0], v[0]) for k, v in pts], 32 * i, sx)
                for sy in (1, 2):
                    qy, cy = fit_axis([(k[1], v[1]) for k, v in pts], 16 * j, sy)
                    sc = sum(1 for k, v in pts if v[0] - (k[0] - 32 * i) // sx == qx and
                             v[1] - (k[1] - 16 * j) // sy == qy)
                    if best is None or sc > best[0]:
                        best = (sc, sx, sy, qx, qy)
            sc, sx, sy, qx, qy = best
            corner = sum(1 for k, v in pts if k[0] - 32 * i < 16 and k[1] - 16 * j < 16)
            shifts[((qx - 32 * i) / 32.0, (qy - 16 * j) / 16.0)] += 1
            ok = (sx, sy, qx, qy) == (sx_pred, sy_pred, 32 * i, 16 * j) and corner == len(pts)
            good += ok
            pix_ok += sc if (sx, sy) == (sx_pred, sy_pred) else 0
            pix_all += len(pts)
            print("  tile (%d,%d): %4d decodable, fit sx %d sy %d source origin (%s, %s) %d of them, "
                  "in the 16x16 corner %d, H30a %s" % (i, j, len(pts), sx, sy, qx, qy, sc, corner,
                                                        "yes" if ok else "no"))
    print("  H30a tiles %d of %d; tile shifts (in tiles) %s" % (
        good, sum(shifts.values()), dict(shifts.most_common(4))))


def do_ident(root, dec):
    d = os.path.join(root, "msaa-ident")
    for c in cases_of(d):
        print("== msaa-ident %s set=%s (declared %s) %sx%s mode %s te %s" % (
            c["name"], c["set"], dec.get(("msaa-ident", c["name"]), {}).get("set", "NOT DECLARED"),
            c["W"], c["H"], c["mode"], c["te"]))
        if not os.path.exists(os.path.join(d, c["name"] + "-x.txt.gz")):
            print("  no dump")
            continue
        ident_case(d, c["name"], int(c["W"]), int(c["H"]), int(c["mode"]))


# ---- Q030: the TE bits in the TA's output ------------------------------------------------------
def do_te(root, dec):
    d = os.path.join(root, "msaa-te-dumps")
    cs = cases_of(d)
    by = {c["name"]: c for c in cs}
    for c in cs:
        print("== msaa-te-dumps %s set=%s te %s" % (c["name"], c["set"], c["te"]))
        t = text_of(os.path.join(d, c["name"] + ".txt.gz")) if os.path.exists(
            os.path.join(d, c["name"] + ".txt.gz")) else ""
        print("  " + " ".join(re.findall(r"^reg 0x020[4-9a-f] 0x[0-9a-f]+", t, re.M)[:6]))
        ctl = "te-m%s-20-%sx%s" % (c["mode"], c["W"], c["H"])
        for f in ("param", "tadata"):
            a, b = (os.path.join(d, "%s.%s.txt.gz" % (n, f)) for n in (c["name"], ctl))
            if c["te"] == "0x20000000" or not (os.path.exists(a) and os.path.exists(b)):
                continue
            x, y = read_gz(a), read_gz(b)
            m = min(len(x), len(y)) // 4
            wx, wy = struct.unpack("<%dI" % m, x[:4 * m]), struct.unpack("<%dI" % m, y[:4 * m])
            print("  %s against %s: %d dwords, %d differ" % (f, ctl, m, sum(1 for i in range(m) if wx[i] != wy[i])))


# ---- Q100 / Q086 ---------------------------------------------------------------------------------
def tile_counts(img, w, h):
    tx, ty = -(-w // 32), -(-h // 16)
    c = [[0] * tx for _ in range(ty)]
    for (x, y), v in img.items():
        if v == G:
            c[y // 16][x // 32] += 1
    return c


def kwords(args):
    out = {}
    for m in re.finditer(r"ta:(143|144|146)=(0x[0-9a-fA-F]+)", args):
        out[int(m.group(1))] = int(m.group(2), 16)
    return out


def predicates(w, h, args):
    r = rules.words(w, h)
    k = kwords(args)
    m1, m2, st = k.get(143, r[0]), k.get(144, r[1]), k.get(146, r[2])
    f, a1, a2, a3 = rules.fields1(m1)
    c1, c2, c3 = rules.fields2(m2)
    rf, ra1, ra2, ra3 = rules.fields1(r[0])
    rc1, rc2, rc3 = rules.fields2(r[1])

    def runs(t, n):
        key = [sum(1 for b in t if b <= x) for x in range(n)]
        return [i for i in range(n) if i == 0 or key[i] != key[i - 1]]
    tx, ty = -(-w // 32), -(-h // 16)
    pa = runs((a1, a2, a3), tx) == runs((ra1, ra2, ra3), tx) and runs((c1, c2, c3), ty) == runs((rc1, rc2, rc3), ty)
    mono = a1 <= a2 <= a3 and c1 <= c2 <= c3
    pb = mono and a2 == ra2 and c2 == rc2 and f == rf and st == r[2]
    pc = a2 == ra2 and c2 == rc2 and f == rf and st == r[2]
    return {"PA": pa, "PB": pb, "PC": pc}


PRIOR = [  # E407, 256x256, (word, bit, observed) read: exact / wrong / fault
    (143, 24, "exact"), (144, 0, "exact"), (143, 12, "wrong"), (143, 15, "wrong"), (143, 16, "wrong"),
    (143, 13, "fault"), (143, 31, "fault"), (144, 12, "wrong"), (144, 15, "fault"), (144, 16, "fault")]


def do_prior():
    r = rules.words(256, 256)
    print("== prior rows (E407, 256x256; they formed PA/PB/PC, so they are FIT, not held out)")
    for word, bit, obs in PRIOR:
        v = (r[0] if word == 143 else r[1]) ^ (1 << bit)
        args = "--kpoke-render 1:ta:%d=0x%08x" % (word, v)
        p = predicates(256, 256, args)
        print("  ta:%d bit %2d observed %-5s predicted exact: PA %-5s PB %-5s PC %-5s" % (
            word, bit, obs, p["PA"], p["PB"], p["PC"]))


def do_mtile(root, dec, script, q):
    d = os.path.join(root, script)
    agree = collections.defaultdict(lambda: collections.Counter())
    base = {}
    if q == "Q086":     # R's signatures come from the safe script's dumps, for both scripts
        for c in cases_of(os.path.join(root, "mtile-msaa")):
            p = os.path.join(root, "mtile-msaa", c["name"] + ".txt.gz")
            if c["name"].endswith("-R") and os.path.exists(p):
                im = rows_of(p)
                base[(int(c["W"]), int(c["H"]))] = tuple(tuple(r) for r in tile_counts(im, int(c["W"]), int(c["H"]))) if im else None
    for c in cases_of(d):
        p = os.path.join(d, c["name"] + ".txt.gz")
        w, h = int(c["W"]), int(c["H"])
        if not os.path.exists(p):
            print("== %s %s: no dump" % (script, c["name"]))
            continue
        t = text_of(p)
        img = rows_of(p)
        failed = (not img) or bool(re.search(r"job: (failed|rejected)|faulted|hung", t))
        cnt = tile_counts(img, w, h) if img else None
        green = sum(sum(r) for r in cnt) if cnt else 0
        exact = bool(img) and green == w * h
        obs = "fault" if failed else "exact" if exact else "wrong"
        line = "== %s %s set=%s: observed %s, green %d of %d" % (script, c["name"], c["set"], obs, green, w * h)
        if q == "Q100":
            p3 = predicates(w, h, c.get("args", ""))
            line += "; predicted exact PA %s PB %s PC %s" % (p3["PA"], p3["PB"], p3["PC"])
            for k, v in p3.items():
                agree[c["set"]][(k, v == (obs == "exact"))] += 1
        else:
            key = (w, h)
            sig = tuple(tuple(r) for r in cnt) if cnt else None
            fam = c["name"].rsplit("-", 1)[1]
            if fam == "R":
                base[key] = sig
            line += "; signature %s R's" % ("equals" if sig is not None and sig == base.get(key) else "differs from")
            if not failed:
                agree[c["set"]][("H86i", sig == base.get(key))] += 1
        print(line)
    for st, cnts in sorted(agree.items()):
        print("-- %s %s agreement by set: %s" % (script, q, st))
        for k in sorted({k for k, _ in cnts}):
            print("     %-5s agrees %d, disagrees %d" % (k, cnts[(k, True)], cnts[(k, False)]))


def do_resolve(root, dec):
    d = os.path.join(root, "msaa-resolve")
    for c in cases_of(d):
        p = os.path.join(d, c["name"] + ".txt.gz")
        if not os.path.exists(p):
            continue
        img = rows_of(p)
        col = collections.Counter(img.values())
        other = sum(v for k, v in col.items() if k not in (G, B))
        print("== msaa-resolve %s sideband %s: %d pixels, other colours %d (%d colours)%s" % (
            c["name"], c["sideband"], len(img), other, len(col), "  <- BLEND?" if other else ""))


def main(argv):
    if argv and argv[0] == "--selftest":
        return selftest()
    root = argv[0]
    dec = declared(argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "declared.tsv"))
    do_prior()
    do_ident(root, dec)
    do_te(root, dec)
    for s in ("mtile-fields", "mtile-fields-risky"):
        do_mtile(root, dec, s, "Q100")
    for s in ("mtile-msaa", "mtile-msaa-risky"):
        do_mtile(root, dec, s, "Q086")
    do_resolve(root, dec)
    return 0


def selftest():
    """A model image of H30a is built, written as kept dumps and recomputed: the fit must report
    every tile as H30a; the prior rows must give PB fitting all ten."""
    import tempfile
    rules.selftest()
    w, h, mode = 64, 64, 2
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "msaa-ident"))
    X, Y = {}, {}
    for yy in range(h):
        for xx in range(w):
            i, j = xx // 32, yy // 16
            lx, ly = xx - 32 * i, yy - 16 * j
            if lx < 16 and ly < 16:
                X[(xx, yy)] = struct.unpack("<I", struct.pack("<f", 32 * i + lx // 2 + 0.5))[0]
                Y[(xx, yy)] = struct.unpack("<I", struct.pack("<f", 16 * j + ly // 2 + 0.5))[0]
            else:
                X[(xx, yy)] = Y[(xx, yy)] = B
    for ax, img in (("x", X), ("y", Y)):
        txt = "".join("probe p: row %d: %s\n" % (yy, " ".join("%08x" % img[(xx, yy)] for xx in range(w))) for yy in range(h))
        with gzip.open(os.path.join(d, "msaa-ident", "t-%s.txt.gz" % ax), "wb") as fh:
            fh.write(txt.encode())
    import io
    buf, old = io.StringIO(), sys.stdout
    sys.stdout = buf
    ident_case(os.path.join(d, "msaa-ident"), "t", w, h, mode)
    sys.stdout = old
    out = buf.getvalue()
    assert "H30a tiles 8 of 8" in out, out
    ok = all(predicates(256, 256, "--kpoke-render 1:ta:%d=0x%08x" % (
        wd, (rules.words(256, 256)[0] if wd == 143 else rules.words(256, 256)[1]) ^ (1 << b)))["PB"] == (o == "exact")
        for wd, b, o in PRIOR)
    assert ok, "PB does not fit the prior rows"
    print("selftest ok: H30a model recovered in 8 of 8 tiles; PB fits the 10 prior rows")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
