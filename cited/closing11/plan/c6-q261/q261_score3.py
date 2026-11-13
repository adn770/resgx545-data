# Scores the frozen candidates of q261_rule3.py (sha256 in q261_rule3.sha256) on the hardware rows.
# round 3 (post hoc): full 4096-pixel decision per candidate
import sys, os, re, gzip, hashlib, fractions, math, multiprocessing
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
G10 = "/Users/jtorra/src/resgx545-data/render/closing-r10-geo"
G9 = "/Users/jtorra/src/resgx545-data/render/closing-r9-x/out/20261113-081821/far"
sys.path.insert(0, G10 + "/gen")
import far as FA          # r10-geo gen/far.py (byte copy of r9-x's): FAR vertices, grid(), E684_CTL
import pivot as PV        # r10-geo gen/pivot.py: TRIS, DLIST, moved()
import q261_rule3 as R
F = fractions.Fraction
BAND = 0.05               # pixel: pixels this near an edge line are re-decided by the candidate
want = open(os.path.join(HERE, "q261_rule3.sha256")).read().split()[0]
assert hashlib.sha256(open(os.path.join(HERE, "q261_rule3.py"), "rb").read()).hexdigest() == want


def img(path):
    t = gzip.open(path, "rt").read()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()]
            for m in re.finditer(r"^row (\d+): ([0-9a-fx ]+)$", t, re.M)}
    px = [v for y in range(64) for v in rows[y]]
    assert len(px) == 4096
    return [v == 0xFF00FF00 for v in px]


def rows():
    out = []
    P = G10 + "/out/20261113-103256/pivot/"
    for tri in PV.TRIS:
        for d in PV.DLIST:
            vp = PV.moved(PV.verts_px(tri), d)
            out.append(("piv-%s-d%d" % (tri[4:], d), tri, d, [(FA.grid(x), FA.grid(y)) for x, y in vp],
                        img(P + PV.row_name(tri, d) + ".txt.gz")))
    n, v = FA.E684_CTL
    out.append(("ctl", "ctl", 0, [(v[0], v[1]), (v[2], v[3]), (v[4], v[5])], img(P + "piv-ctl.txt.gz")))
    for name, verts in FA.FAR:
        out.append(("E979-" + name, "e979", 0, [(FA.grid(x), FA.grid(y)) for x, y in verts],
                    img(G9 + "/%s.txt.gz" % name)))
    out.append(("E979-ctl", "e979", 0, [(v[0], v[1]), (v[2], v[3]), (v[4], v[5])], img(G9 + "/far-ctl.txt.gz")))
    return out


ROWS = None
NEAR = {}


def near_set(ri):
    """pixels within BAND of any edge line of row ri (float estimate) and the exact decision of all"""
    name, tri, d, V, hw = ROWS[ri]
    W = R.prep(V, R.Cand("exact", "exact"))
    if W is None:
        return [], [False] * 4096
    ed = []
    for i in range(3):
        p, q = W[i], W[(i + 1) % 3]
        dx, dy = q[0] - p[0], q[1] - p[1]
        ed.append((p, dx, dy, math.hypot(dx, dy)))
    near, ex = [], []
    for y in range(64):
        for x in range(64):
            px, py = x * 256 + 128, y * 256 + 128
            ins, nr = True, False
            for p, dx, dy, L in ed:
                e = dx * (py - p[1]) - dy * (px - p[0])
                ins &= e > 0 or (e == 0 and R.own(dx, dy))
                if abs(e) / L < BAND * 256:
                    nr = True
            ex.append(ins)
            if nr:
                near.append((x, y))
    return near, ex


def eval_cand(cand):
    res = []
    for ri, (name, tri, d, V, hw) in enumerate(ROWS):
        _n, ex = NEAR[ri]
        near = [(x, y) for y in range(64) for x in range(64)]
        W = R.prep(V, cand)
        if W is None:
            img_ = [False] * 4096
            dec = {}
            for x, y in near:
                dec[(x, y)] = False
        else:
            dec = {(x, y): R.decide(cand, W, x * 256 + 128, y * 256 + 128) for x, y in near}
        nearset = set(near)
        # outside the near set the candidate is taken as exact (verified on the exact image below)
        wrong_out = sum(1 for i in range(4096) if (i % 64, i // 64) not in nearset and ex[i] != hw[i])
        wrong_near = [(x, y) for (x, y) in near if dec[(x, y)] != hw[y * 64 + x]]
        tell = [(x, y) for (x, y) in near if ex[y * 64 + x] != hw[y * 64 + x]]
        tell_ok = sum(1 for p in tell if dec[p] == hw[p[1] * 64 + p[0]])
        res.append((name, len(wrong_near) + wrong_out, len(near), len(tell), tell_ok, len(wrong_near)))
    return cand.id, res


def init():
    global ROWS, NEAR
    ROWS = rows()
    NEAR = {i: near_set(i) for i in range(len(ROWS))}


def main():
    init()
    cands = R.candidates()
    with multiprocessing.Pool(initializer=init) as pool:
        results = pool.map(eval_cand, cands, chunksize=1)
    names = [r[0] for r in ROWS]
    print("rows:", len(ROWS), " [post hoc: E1005 intervals read before the candidates]")
    ex_out = sum(1 for ri in range(len(ROWS)) for i in range(4096)
                 if (i % 64, i // 64) not in set(NEAR[ri][0]) and NEAR[ri][1][i] != ROWS[ri][4][i])
    print("exact image vs hardware outside the 0.05 px near sets, all rows:", ex_out, "pixels")
    print("tell pixels per row (exact != hardware):",
          {ROWS[ri][0]: sum(1 for (x, y) in NEAR[ri][0] if NEAR[ri][1][y * 64 + x] != ROWS[ri][4][y * 64 + x])
           for ri in range(len(ROWS)) if any(NEAR[ri][1][y * 64 + x] != ROWS[ri][4][y * 64 + x]
                                             for (x, y) in NEAR[ri][0])})
    print()
    print("%-28s %6s %6s %9s %9s  %s" % ("candidate", "rowsOK", "/47", "tell ok", "near bad", "rows failing (first 6)"))
    fits = []
    for cid, res in results:
        rok = sum(1 for r in res if r[1] == 0)
        tot_t = sum(r[3] for r in res)
        ok_t = sum(r[4] for r in res)
        bad_near = sum(r[5] for r in res)
        fail = [r[0] for r in res if r[1] != 0][:6]
        print("%-28s %6d %6d %4d/%-4d %9d  %s" % (cid, rok, len(res), ok_t, tot_t, bad_near, " ".join(fail)))
        if rok == len(res):
            fits.append(cid)
    print()
    print("FITS ALL ROWS:", fits)
    # per-triangle rows ok for the pivot triangles (D intervals)
    print()
    print("per-triangle pivot rows exact (x23p, x24p, x25n, of 12 each), candidates with >= 30 of 36:")
    for cid, res in results:
        t = [sum(1 for r in res if r[0].startswith("piv-" + k) and r[1] == 0) for k in ("x23p", "x24p", "x25n")]
        if sum(t) >= 30:
            print("%-28s %s" % (cid, t))


if __name__ == "__main__":
    main()
