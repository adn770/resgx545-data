#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""FP (round 10, Q260/Q261): floating-point edge set-up and evaluation variants.

Reuses round 9's loaders and HA grid (closing9/offline/oz/ozlib.py, read only). Machine: every
arithmetic result (difference, product, sum, quotient) is rounded to p significant bits (RE
round-to-nearest-even or TZ truncation); the inputs (vertices, pixel centres) enter exact; the
operations themselves run in float64 (a product of operands wider than 26 bits can double-round;
[infer] negligible). Vertices: vq "HA" (1/256, half away from zero, then pixels) or "F" (the
tool's integer / 2^k, unquantised). Winding from the exact integer area. Edge P -> Q, E>0 inside,
E==0 inside iff the edge owns (HA's top-left rule), as in ozlib.

Families (p in 11,16,17,18,19,20,22,24; rm RE,TZ; vq HA,F: 32 each):
  coef   (i)   A=r(y0-y1) B=r(x1-x0) C=r(r(x0 y1)-r(x1 y0)); E=r(r(r(Ax)+r(By))+C)
  rel    (ii)  E=r(r(A r(x-Ox))+r(B r(y-Oy))), O in P,Q,top,near (x4)
  orig   (iii) origin T (target, or the 32x16 tile of S): x'=x-Tx; vertex r(x0-Tx);
               C'=-r(r(A x0')+r(B y0')); E=r(r(r(A x')+r(B y'))+C')  (x2)
  slope  (iv)  m=r(dx/dy), xe=r(Ox+r(r(y-Oy) m)); dy>0 inside iff x<xe, dy<0 iff x>xe, tie
               by own; dy==0 exact; O in P,Q,top,near (x4)
total 32 + 128 + 64 + 128 = 352 variants."""
import sys
import numpy as np

OZ = "/Users/jtorra/src/scratch/resgx545/closing9/offline/oz"
sys.path.insert(0, OZ)
import ozlib as O  # noqa: E402
M = O.M
PS = (11, 16, 17, 18, 19, 20, 22, 24)


def r(x, p, rm):
    x = np.asarray(x, dtype=np.float64)
    m, ex = np.frexp(x)
    y = np.ldexp(m, p)
    y = np.rint(y) if rm == "RE" else np.trunc(y)
    return np.ldexp(y, ex - p)


def variants():
    out = []
    for fam, subs in (("coef", [None]), ("rel", ["P", "Q", "top", "near"]),
                      ("orig", ["target", "tile"]), ("slope", ["P", "Q", "top", "near"])):
        for sub in subs:
            for vq in ("HA", "F"):
                for p in PS:
                    for rm in ("RE", "TZ"):
                        out.append({"fam": fam, "sub": sub, "vq": vq, "p": p, "rm": rm})
    return out


def vname(v):
    if v is None:
        return "HA-exact"
    return "%s%s-%s-p%d-%s" % (v["fam"], "" if v["sub"] is None else "-" + v["sub"], v["vq"], v["p"], v["rm"])


def _base(sub, P, Q, w, h):
    if sub == "P":
        return P
    if sub == "Q":
        return Q
    if sub == "top":
        return P if (P[1], P[0]) <= (Q[1], Q[0]) else Q
    dP = (P[0] - w / 2) ** 2 + (P[1] - h / 2) ** 2
    dQ = (Q[0] - w / 2) ** 2 + (Q[1] - h / 2) ** 2
    return P if dP <= dQ else Q


def coverage(V, k, w, h, var):
    V = np.asarray(V, dtype=np.int64).reshape(3, 2)
    if var["vq"] == "HA":
        g = M.to_grid(V, k, "HA")
        vi, scale = g, 256
    else:
        vi, scale = V, 1 << k
    a, b, c = vi[0], vi[1], vi[2]
    area = int((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    out = np.zeros((h, w), dtype=bool)
    if area == 0:
        return out
    if area < 0:
        b, c = c, b
    f = lambda t: (float(t[0]) / scale, float(t[1]) / scale)
    a, b, c = f(a), f(b), f(c)
    xs = [a[0], b[0], c[0]]
    ys = [a[1], b[1], c[1]]
    x0 = max(int(np.floor(min(xs))) - 1, 0)
    x1 = min(int(np.floor(max(xs))) + 2, w)
    y0 = max(int(np.floor(min(ys))) - 1, 0)
    y1 = min(int(np.floor(max(ys))) + 2, h)
    if x1 <= x0 or y1 <= y0:
        return out
    px = np.arange(x0, x1, dtype=np.int64)
    py = np.arange(y0, y1, dtype=np.int64)
    sx = (px + 0.5)[None, :]
    sy = (py + 0.5)[:, None]
    inside = np.ones((y1 - y0, x1 - x0), dtype=bool)
    p, rm, fam, sub = var["p"], var["rm"], var["fam"], var["sub"]
    R = lambda t: r(t, p, rm)
    for P, Q in ((a, b), (b, c), (c, a)):
        dx, dy = Q[0] - P[0], Q[1] - P[1]
        own = dy < 0 or (dy == 0 and dx > 0)
        A, B = R(P[1] - Q[1]), R(Q[0] - P[0])
        if fam == "coef":
            C = R(R(P[0] * Q[1]) - R(Q[0] * P[1]))
            E = R(R(R(A * sx) + R(B * sy)) + C)
        elif fam == "rel":
            O_ = _base(sub, P, Q, w, h)
            E = R(R(A * R(sx - O_[0])) + R(B * R(sy - O_[1])))
        elif fam == "orig":
            if sub == "target":
                tx, ty = np.float64(0), np.float64(0)
            else:
                tx = ((px // 32) * 32).astype(np.float64)[None, :]
                ty = ((py // 16) * 16).astype(np.float64)[:, None]
            xp, yp = sx - tx, sy - ty
            x0p, y0p = R(P[0] - tx), R(P[1] - ty)
            Cp = -R(R(A * x0p) + R(B * y0p))
            E = R(R(R(A * xp) + R(B * yp)) + Cp)
        else:
            if dy == 0:
                E = dx * (sy - P[1]) + 0 * sx
            else:
                O_ = _base(sub, P, Q, w, h)
                m = R(dx / dy)
                xe = R(O_[0] + R(R(sy - O_[1]) * m))
                s = (xe - sx) * (1.0 if dy > 0 else -1.0)
                E = s
        inside &= (E > 0) | ((E == 0) & own)
    out[y0:y1, x0:x1] = inside
    return out


def far_jobs():
    """E979's 11 far rows (ctl + 10): whole 64 x 64 images; vertices as the tool's integers."""
    import gzip, re
    S = O.DATA + "/render/closing-r9-x"
    sys.path.insert(0, S + "/gen")
    import far as FA
    att = S + "/out/20261113-081821/far"
    jobs, rows = [], [(FA.E684_CTL[0], 8, list(FA.E684_CTL[1]))]
    for name, vp in FA.FAR:
        rows.append((name, 8, [FA.u(c) * 8 for p in vp for c in p]))  # 1/32 to 1/256, exact
    for name, k, v in rows:
        t = gzip.open("%s/%s.txt.gz" % (att, name), "rt").read()
        img = O._pixels(t.replace("0xFF00FF00", "0xff00ff00"), 64, 64)
        if img is None:  # tokens might lack the 0x prefix style; parse by value
            rowsd = {}
            for m in re.finditer(r"^row (\d+): (.*)$", t, re.M):
                rowsd[int(m.group(1))] = np.array([int(x, 16) == FA.TRI_COLOUR for x in m.group(2).split()])
            img = np.stack([rowsd[y] for y in range(64)])
        jobs.append(O.Job("E979", name, "far", 64, 64, k, v, img))
    return jobs, FA
