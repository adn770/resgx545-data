# Q139 offline macrotile test (round 6 fold, 2026-11-12): the readings of the macrotile words
# that place each 32 x 16 tile's region header, and the loader of the kept tri dumps of
# resgx545-data ta/mtile-fields{,-risky}. Standard library only. Imported by q139_fit.py (the
# safe dataset only) and q139_score.py (the risky dataset, after the freeze).
#
# The rule's words are rules.py's (the datasets' analysis/rules.py: the library's rule, E257,
# E331); a job's poke replaces ta:143 (CR_TE_MTILE1), ta:144 (CR_TE_MTILE2) or ta:146
# (CR_TE_MACROTILE_STRIDE).
#
# Reading R-CELL (the ranking's set test, no parameter): the tiles are cut into cells by the
# rule's boundaries and the job's (x by CR_TE_MTILE1, y by CR_TE_MTILE2); a wrong image is
# consistent iff its wrong tiles are a union of cells.
#
# Readings R-SLOT (a family, one variant fitted on the safe dataset): the TA computes for each
# target region (c, r) its macrotile from the job's words, the boundaries compared in order of
# use (mcol = 0; while mcol < n - 1 and c >= bound[mcol + 1]: mcol += 1; the same for rows),
# n = 4 when CR_TE_MTILE1 bit 31 is set (bounds 0, B1, B2, B3) and 2 otherwise (bounds 0, B2),
# and writes the region's header (its own position) at
#     slot = N * S + ly * P + lx,   lx = c - bound_x[mcol], ly = r - bound_y[mrow],
# S the job's stride word. The render walks the slots the rule's layout has (n_rule^2 * S_rule)
# and draws each header that names a target region; a region whose header was overwritten by a
# later one, dropped, or written past the walk is not drawn (its pixels stay 0xdeadbeef).
# Variant axes:
#   num   'col': N = mcol * n + mrow (headers numbered down then across, E652); 'row': mrow * n + mcol
#   pitch 'rule': P = the rule's mx; 'b': P = the job's first macrotile width (B1 at n = 4, B2 at 2)
#   clip  'none': no clip; 'S': dropped when ly * P + lx >= S; 'P': dropped when lx >= P too
#   order 'raster': regions written row by row over the target; 'mt': by N, then local raster
#   pad   'no': only target regions are written; 'yes': every region of the rule's padded area
#         (n_rule * mx by n_rule * my) is written too, the outside ones overwrite but are not drawn
import gzip
import itertools
import re

TW, TH = 32, 16


def cdiv(a, b):
    return -(-a // b)


def rule(w, h):
    """(tx, ty, n, mx, my, mtile1, mtile2, stride) of the library's rule (rules.py)."""
    tx, ty = cdiv(w, TW), cdiv(h, TH)
    n = 4 if w * h >= 640 * 480 else 2
    mx = cdiv(cdiv(tx, n), 4) * 4
    my = cdiv(cdiv(ty, n), 4) * 4
    b = (1, 2, 3) if n == 4 else (1, 1, 1)
    m1 = ((1 if n == 4 else 0) << 31) | (mx * b[0] << 22) | (mx * b[1] << 12) | (mx * b[2])
    m2 = (my * b[0] << 22) | (my * b[1] << 12) | (my * b[2])
    return tx, ty, n, mx, my, m1, m2, mx * my


def words(w, h, args):
    """The job's (mtile1, mtile2, stride) after its pokes."""
    _, _, _, _, _, m1, m2, s = rule(w, h)
    for idx, val in re.findall(r"ta:(\d+)=(0x[0-9a-fA-F]+)", args):
        v = int(val, 16)
        if idx == "143":
            m1 = v
        elif idx == "144":
            m2 = v
        elif idx == "146":
            s = v
        else:
            raise ValueError(f"unexpected poke ta:{idx}")
    return m1, m2, s


def bounds(m1, m2):
    n = 4 if (m1 >> 31) & 1 else 2
    x = ((m1 >> 22) & 0xff, (m1 >> 12) & 0xff, m1 & 0xff)
    y = ((m2 >> 22) & 0x1ff, (m2 >> 12) & 0x1ff, m2 & 0x1ff)
    if n == 4:
        return n, (0,) + x, (0,) + y
    return n, (0, x[1]), (0, y[1])


def place(v, bs):
    k = 0
    while k < len(bs) - 1 and v >= bs[k + 1]:
        k += 1
    return k, v - bs[k]


def cells(w, h, m1, m2):
    """R-CELL: {tile: cell id} by the rule's and the job's boundaries."""
    tx, ty, _, _, _, r1, r2, _ = rule(w, h)
    _, jx, jy = bounds(m1, m2)
    _, rx, ry = bounds(r1, r2)
    out = {}
    for r in range(ty):
        for c in range(tx):
            out[(c, r)] = (place(c, rx)[0], place(c, jx)[0], place(r, ry)[0], place(r, jy)[0])
    return out


def union_of_cells(bad, cellmap):
    by = {}
    for t, k in cellmap.items():
        by.setdefault(k, set()).add(t)
    return all(ts <= bad or not (ts & bad) for ts in by.values())


VARIANTS = [dict(num=a, pitch=b, clip=c, order=d, pad=e) for a, b, c, d, e in itertools.product(
    ("col", "row"), ("rule", "b"), ("none", "S", "P"), ("raster", "mt"), ("no", "yes"))]


def vname(v):
    return f"num={v['num']},pitch={v['pitch']},clip={v['clip']},order={v['order']},pad={v['pad']}"


def predict(w, h, m1, m2, s, v):
    """R-SLOT variant v: the set of target tiles not drawn."""
    tx, ty, rn, mx, my, _, _, rs = rule(w, h)
    n, bx, by = bounds(m1, m2)
    pitch = mx if v["pitch"] == "rule" else (bx[1] if n == 4 else bx[1])
    if pitch <= 0:
        return None  # no prediction (a zero pitch)
    walk = rn * rn * rs
    regs = []
    cw, ch = (rn * mx, rn * my) if v["pad"] == "yes" else (tx, ty)
    for r in range(ch):
        for c in range(cw):
            mcol, lx = place(c, bx)
            mrow, ly = place(r, by)
            N = mcol * n + mrow if v["num"] == "col" else mrow * n + mcol
            loc = ly * pitch + lx
            drop = (v["clip"] in ("S", "P") and loc >= s) or (v["clip"] == "P" and lx >= pitch)
            regs.append((N, ly, lx, r, c, None if drop else N * s + loc))
    if v["order"] == "mt":
        regs.sort(key=lambda t: (t[0], t[1], t[2]))
    owner = {}
    for _, _, _, r, c, slot in regs:
        if slot is not None:
            owner[slot] = (c, r)
    drawn = {t for sl, t in owner.items() if 0 <= sl < walk and t[0] < tx and t[1] < ty}
    return {(c, r) for r in range(ty) for c in range(tx)} - drawn


def load(path):
    """(W, H, job, wrong tile set or None when the job kept no full image)."""
    W = H = job = None
    img = {}
    cut = False
    for line in gzip.open(path, "rt"):
        if line.startswith("target:"):
            W, H = map(int, line.split()[1].split("x"))
        elif line.startswith("job:"):
            job = line.split()[1]
        elif line.startswith("row "):
            k, val = line.split(":", 1)
            vals = []
            for x in val.split():
                if not re.fullmatch(r"0x[0-9a-f]{8}", x):
                    cut = True
                    break
                vals.append(int(x, 16))
            img[int(k[4:])] = vals
    if job != "ok" or not img or cut:
        return W, H, job, None
    bad = set()
    for y, row in img.items():
        for x, p in enumerate(row):
            if p != 0xff00ff00:
                bad.add((x // TW, y // TH))
    return W, H, job, bad


def cases(dsdir):
    rows = []
    with open(f"{dsdir}/cases.tsv") as f:
        next(f)
        for line in f:
            name, st, w, h, *rest = line.rstrip("\n").split("\t")
            rows.append((name, st, int(w), int(h), rest[0] if rest else ""))
    return rows
