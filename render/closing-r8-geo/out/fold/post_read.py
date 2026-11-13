#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""out/fold/post_read.py ATT: the fold's post hoc readings of r8-geo (2026-11-13), not frozen.
Standard library only; reads the kept files of ATT, the session's frozen gen/ and, for addr,
E565's kept jobs (RESGX545_DATA, default /Users/jtorra/src/resgx545-data).

  cube  32 x 32 faces: the frozen rule's index against the same with the fifth bits of s and t
        in the other order (bit 8 and bit 9 swapped); texel ties per axis and |ma|; face ties;
        the edge jobs' G bytes
  seam  each job's `job:` line and the tool's error (the kernel's render check)
  addr  each u job against H-MASK-V plus a constant, and E565's kept u jobs the same way
  vdm   each job's image hash and its tool's o0 histogram"""
import collections
import gzip
import hashlib
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "gen"))
import addr as A  # noqa: E402
import cube as C  # noqa: E402
import texprog as T  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")


def text(path):
    return gzip.open(path, "rt").read() if os.path.exists(path) else ""


def cube(att):
    R = C.rule()
    print("== cube: 32 x 32 faces, the rule's index and the fifth-bit swap")
    for k, spec in C.SIZED.items():
        px = T.pixels(text(f"{att}/cube/cube-n32-{k}.txt.gz"))
        cnt = collections.Counter()
        for p, c in C.coords_of(spec).items():
            st, v = C.predict(R, c, 32)
            if st != "ok":
                continue
            face, vs, vt, ma, order = C.st(R, c, 32)
            s, t = (min(max(q.numerator // q.denominator, 0), 31) for q in (vs, vt))
            low = C.twid(s & 15, t & 15, order, 4)
            hi = (s >> 4, t >> 4) if order == "ty" else (t >> 4, s >> 4)
            swapped = face * 1024 + (low | hi[0] << 8 | hi[1] << 9)
            got = px[p] & 0x0fffffff
            cnt[("rule" if got == v & 0x0fffffff else "") + ("+swap" if got == swapped else "")] += 1
        print(f"cube-n32-{k}: {dict(cnt)} (rule: the frozen index; +swap: bit 8 the first-order"
              f" coordinate's bit 4, bit 9 the other's)")
    print("== cube: face ties (|w| = |u| in column 32) and texel ties")
    for k, spec in C.FTIE.items():
        px = T.pixels(text(f"{att}/cube/cube-ftie-{k}.txt.gz"))
        f = collections.Counter((px[p] & 0xffffff) // 256 for p, c in C.coords_of(spec).items()
                                if C.face_of(c)[0] is None)
        print(f"cube-ftie-{k}: faces read at the 32 tie pixels {dict(f)}")
    for k, spec in C.TTIE.items():
        px = T.pixels(text(f"{att}/cube/cube-ttie-{k}.txt.gz"))
        tab = collections.Counter()
        for p, c in C.coords_of(spec).items():
            face, vs, vt, ma, order = C.st(R, c, 16)
            got = px[p] & 0x0fffffff
            for ax, v in (("s", vs), ("t", vt)):
                if v.denominator != 1:
                    continue
                fl = [q.numerator // q.denominator for q in (vs, vt)]
                lo = list(fl)
                lo[0 if ax == "s" else 1] -= 1
                up = face * 256 + C.twid(*(min(max(z, 0), 15) for z in fl), order, 4)
                dn = face * 256 + C.twid(*(min(max(z, 0), 15) for z in lo), order, 4)
                other = [q for q in (vs, vt) if q is not v][0]
                if other.denominator == 1:
                    tab[(ax, int(v), "both tied")] += 1
                    continue
                tab[(ax, int(v), "up" if got == up else "down" if got == dn else "other")] += 1
        line = " ".join(f"{a}{b}:{c}={n}" for (a, b, c), n in sorted(tab.items()) if c != "both tied")
        print(f"cube-ttie-{k} (|ma| {float(spec[2][1] and T.fbits(spec[2][1]))}): {line}")
    for k, spec in C.EDGE.items():
        px = T.pixels(text(f"{att}/cube/cube-edge-{k}.txt.gz"))
        cells = C.edge_cells(R, spec)
        g = collections.Counter((px[p] >> 8) & 0xff for p, (f, kk) in cells.items() if kk == "out")
        print(f"cube-edge-{k}: out pixels' G bytes {dict(g)}; row 0 every 4th pixel "
              + " ".join("%08x" % px[(x, 0)] for x in range(0, 64, 4)))


def seam(att):
    print("== seam: each job's outcome line and the tool's error")
    for ln in text(f"{att}/seam/cases.tsv.gz").splitlines()[1:] or open(f"{att}/seam/cases.tsv").read().splitlines()[1:]:
        n = ln.split("\t")[0]
        out = text(f"{att}/seam/{n}.txt.gz")
        job = [x for x in out.splitlines() if x.startswith("job:")]
        err = text(f"{att}/seam/{n}.err.gz").strip().replace("\n", " | ")
        te = [w for w in ln.split() if w.startswith("cmd:1=")]
        print(f"{n} {te[0] if te else ''}: {job[0] if job else 'no job line'}; err: {err or '-'}")


def addr(att):
    print("== addr: u jobs against H-MASK-V plus a constant offset (dwords)")
    for m in (4, 5, 6, 7):
        px = T.pixels(text(f"{att}/addr/addr-u{m}.txt.gz"))
        img = A.image("u", m, "H-MASK-V")
        d = collections.Counter((px[p] & 0x0fffffff) - img[p] for p in px)
        ins = collections.Counter((px[p] & 0x0fffffff) - img[p] for p in px
                                  if 0 <= A.texel("u", *p)[0] < 16)
        print(f"addr-u{m}: all pixels {dict(d.most_common(4))}; inside the texture {dict(ins)}")
    print("== addr: E565's kept u jobs (texture/p1132/tx-border), s = x - 24, t = min(y // 2, 15)")
    for lab, m in (("bd-u4", 4), ("bd-u5", 5), ("bd-u6", 6), ("bd-u7", 7), ("bd-hb-u4", 4)):
        px = T.pixels(text(f"{DATA}/texture/p1132/tx-border/{lab}.txt.gz"))
        base = 1024 if "hb" in lab else 0
        how = "repeat" if m in (4, 5) else "clamp"
        ok = sum(1 for (x, y), v in px.items()
                 if (v & 0x0fffffff) - base == 180 + A.morton(A.wrap(x - 24, how), min(y // 2, 15)))
        print(f"{lab}: {ok} of 2048 pixels read H-MASK-V's index + 180")


def vdm(att):
    print("== vdm: image hash (sha256 of the 4096 pixels, first 16) and the o0 line")
    for ln in open(f"{att}/vdm/cases.tsv").read().splitlines()[1:]:
        n = ln.split("\t")[0]
        out = text(f"{att}/vdm/{n}.txt.gz")
        px = T.pixels(out, 64, 64)
        h = hashlib.sha256("".join("%08x" % px[(x, y)] for y in range(64)
                                   for x in range(64)).encode()).hexdigest()[:16] if px else "-"
        o0 = [x.split(": ", 1)[1] for x in out.splitlines() if " o0 " in x]
        print(f"{n}: {h} {o0[0][:110] if o0 else ''}")


if __name__ == "__main__":
    att = sys.argv[1]
    cube(att)
    seam(att)
    addr(att)
    vdm(att)
