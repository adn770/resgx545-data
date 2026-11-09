#!/usr/bin/env python3
"""Goal 1c: the region model against the stored msaa-ident, msaa-te and msaa-tiles images. Prints
per data set the exact images and the pixels off, with in-sample or held-out stated as in
plan.md. Fits nothing: the model is msaa_model.py, written from opus/msaa.md's words."""
import collections, gzip, re, struct, sys
sys.dont_write_bytecode = True
from lib import DATA
import msaa_model as M

ISP = DATA / "isp"
BG = 0xFF203040


def rows(txt, pat):
    img = {}
    for ln in txt.splitlines():
        m = re.search(pat, ln)
        if m:
            for x, v in enumerate(m.group(2).split()):
                try:
                    img[(x, int(m.group(1)))] = int(v, 16)
                except ValueError:
                    pass
    return img


def f32(v):
    return struct.unpack("<f", struct.pack("<I", v))[0]


def ident(k=1.25, slots=M.SAMP, **kw):
    cases = [ln.split("\t") for ln in (ISP / "msaa-ident/cases.tsv").read_text().splitlines()[1:]]
    tot = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for name, st, W, H, mode, te in cases:
        W, H, mode, te = int(W), int(H), int(mode), int(te, 16)
        px = gzip.open(ISP / f"msaa-ident/dumps/{name}-x.txt.gz", "rt", errors="replace").read()
        py = gzip.open(ISP / f"msaa-ident/dumps/{name}-y.txt.gz", "rt", errors="replace").read()
        X, Y = rows(px, r"row (\d+): (.*)$"), rows(py, r"row (\d+): (.*)$")
        obs_bg = {p for p, v in X.items() if v == BG}
        pred = M.predict(M.tri_full(W, H, k), W, H, mode, te, slots=slots, **kw)
        allp = {(x, y) for x in range(W) for y in range(H)}
        pred_bg = allp - set(pred)
        bad = len(obs_bg ^ pred_bg)
        # source positions of the decodable pixels
        sbad = n = 0
        for p, (a, b) in pred.items():
            vx, vy = X.get(p), Y.get(p)
            if vx is None or vx == BG or vy is None or vy == BG:
                continue
            n += 1
            if abs(f32(vx) - (a + 0.375)) > 1e-3 or abs(f32(vy) - (b + 0.125)) > 1e-3:
                sbad += 1
        t = tot[(st, name.split("-")[0])]
        t[0] += 1; t[1] += bad == 0; t[2] += bad; t[3] += len(obs_bg); t[4] += n; t[5] += sbad
    return tot


def listing(tot, title):
    print(title)
    print("  set  group: images, exact coverage, pixels off, observed bg px, decoded px, source mismatches")
    for k, v in sorted(tot.items()):
        print("  %-8s %s: %3d images, %3d exact, %5d px off, %4d bg px, %6d decoded, %4d src off" % (k + tuple(v)))


def te_images():
    names = {0: 0x80000000, 1: 0x40000000, 2: 0x20000000, 3: 0xC0000000, 4: 0xA0000000, 5: 0x60000000, 6: 0xE0000000}
    res = []
    for mode in (0, 1, 2):
        txt = (ISP / f"msaa-te/isp-msaa-te-m{mode}/raw.txt").read_text(errors="replace")
        for i, te in names.items():
            img = rows("\n".join(ln for ln in txt.splitlines() if ln.startswith(f"probe isp-msaa-te-m{mode}__{i}:")),
                       r"row (\d+): (.*)$")
            obs = {p for p, v in img.items() if v == 0xFF00FF00}
            tri = [((8 * 16, 8 * 16), (56 * 16, 20 * 16), (20 * 16, 56 * 16))]
            pred = set(M.predict(tri, 64, 64, mode, te))
            res.append((mode, te, len(obs), len(obs ^ pred)))
    return res


def tiles_images(**kw):
    import tomllib
    res = []
    for probe in ("m1-te0", "m1-te1", "m2-te0", "m2-te1"):
        mode = int(probe[1]); te = 0 if probe.endswith("te0") else 0xE0000000
        txt = (ISP / f"msaa-tiles/isp-msaa-tiles-{probe}/raw.txt").read_text(errors="replace")
        for i in range(27):
            ty, tx, ki = i // 9, i // 3 % 3, i % 3
            x0, y0, k = (4, 20, 36)[tx], (4, 20, 36)[ty], (0, 6, 12)[ki]
            img = rows("\n".join(ln for ln in txt.splitlines() if ln.startswith(f"probe isp-msaa-tiles-{probe}__{i}:")),
                       r"row (\d+): (.*)$")
            obs = {p for p, v in img.items() if v == 0xFF00FF00}
            a, b = x0 * 16 + k, y0 * 16 + k
            tri = [((a, b), (x0 * 16 + 160, b), (a, y0 * 16 + 160))]
            pred = set(M.predict(tri, 64, 64, mode, te, **kw))
            res.append((probe, i, k, len(obs), len(obs ^ pred)))
    return res


if __name__ == "__main__":
    listing(ident(), "== msaa-ident, region model, tri-full seam 1.25 W")
    for kk in (1.2, 1.24, 1.26, 1.3):
        tot = ident(k=kk)
        print("  seam k=%.2f: exact %d of %d images" % (kk, sum(v[1] for v in tot.values()), sum(v[0] for v in tot.values())))
    print("  nulls (the model with one rule changed):")
    for nm, kw in (("first region wins", dict(last_region=False)), ("origin = region origin always", dict(origin="region")),
                   ("union of the two masks", dict(halves=False)), ("all slots (8,8)", dict(slots=[(8, 8)] * 4))):
        tot = ident(**kw); print("  %-40s exact %d of %d" % (nm, sum(v[1] for v in tot.values()), sum(v[0] for v in tot.values())))
    r = te_images()
    print("\n== msaa-te images (mode, te, observed green px, mismatching px)")
    for x in r: print("  m%d te %#010x obs %5d off %4d" % x)
    t = tiles_images()
    by = collections.defaultdict(lambda: [0, 0, 0])
    for probe, i, k, o, off in t:
        b = by[probe]; b[0] += 1; b[1] += off == 0; b[2] += off
    print("\n== msaa-tiles images per probe: images, exact, px off")
    for k, v in by.items(): print("  %s %s" % (k, v))
    print("  images not exact:", [(p, i, k, o, off) for p, i, k, o, off in t if off])
