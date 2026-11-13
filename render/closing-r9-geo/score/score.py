#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r9-geo's scorer (r8-geo's score/score.py, resgx545-data render/closing-r8-geo,
copied and extended). Every verdict rule comes from kit/scorekit.py, the kept files are read
through kit/kitscore.py (byte copies of resgx545 f32dfacc8db8, pinned in FROZEN.commits). The
frozen per-pixel predictions are predictions/STAGE/NAME.MODEL.txt, each checked against its
sha256 in predictions/STAGE.tsv before it is used (a changed file is a STOP, not a verdict).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READ lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another: GATES is empty)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A row is held, FAILED or cannot tell (a void job, no pixel rows, a tri job without `job: ok`, a
gate shut); the controls gate every row of their stage (scorekit.headline). Exploratory rows (set
explore) print READ lines and decide nothing. Replicates (set replicate) decide their own
SUMMARY line only."""
import collections
import fractions
import hashlib
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGES = ("seam1", "seam4", "cube2", "addr2")
REQUIRED = {s: (".txt", "cases.tsv", "void.tsv", "readings.tsv") for s in STAGES}
GATES = {}
TRI, BG = 0xff00ff00, 0xff203040
SIZE = re.compile(r"--width (\d+) --height (\d+)")
HASH = re.compile(r"^target: \d+x\d+ hash (0x[0-9a-f]+)$", re.M)
EDGE_TOL = 1          # gen/cube.py TOL (bytes)
IN_SHARE = 0.9        # the edge premise: this share of the in pixels within EDGE_TOL of the blend


def producible(row):
    """The reading keys a row's job can produce: every row prints its pixels (--pixels); a tri
    job also its `job:` line and its target's hash."""
    a = row["args"].split()
    keys = {"pixels"} if "--pixels" in a else set()
    if a[:1] == ["tri"]:
        keys |= {"jobok", "hash"}
    return keys


def pixels(text, w, h):
    out = {}
    for m in re.finditer(r"row (\d+): ([0-9a-fx ]+)$", text or "", re.M):
        y = int(m.group(1))
        for x, t in enumerate(m.group(2).split()):
            out[(x, y)] = int(t, 16)
    return out if len(out) == w * h else None


def size(row):
    m = SIZE.search(row["args"])
    return (int(m.group(1)), int(m.group(2))) if m else (64, 32)


def frozen(stage, rel, want):
    b = open(os.path.join(KP, "predictions", stage, rel), "rb").read()
    if hashlib.sha256(b).hexdigest() != want:
        raise SystemExit(f"STOP: predictions/{stage}/{rel} is not the frozen file")
    return b.decode()


def observed(d, cases, row):
    """The job's pixels, or None (not run, not ok, a tri job without `job: ok`)."""
    n = row["name"]
    if n not in cases or cases[n]["class"] != "ok":
        return None
    text = K.text(d, n + ".txt")
    if row["args"].startswith("tri") and not re.search(r"^job: ok", text or "", re.M):
        return None
    return pixels(text, *size(row))


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    for n in cases:
        K.text(d, n + ".txt")


def word(v):
    return "held" if v else "FAILED" if v is False else "cannot tell"


def cstate(v):
    return "PASS" if v else "FAILED" if v is False else "cannot tell"


# ---- seam1, seam4 ------------------------------------------------------------------------------
def cells_sha(cells):
    text = "".join(f"{x} {y}\n" for x, y in sorted(cells, key=lambda p: (p[1], p[0])))
    return hashlib.sha256(text.encode()).hexdigest()


SEAM_MODELS = {"seam1": ("H-REGION", "H-UNION"), "seam4": ("H-SAME4", "H-FULL4", "H-UNION")}
SEAM_CTL = {"seam1": "H-REGION", "seam4": "H-SAME4"}


def score_seam(stage, d):
    """predictions/STAGE.tsv: per job `holes` (tri-full: background pixels) or `stored` (a single
    triangle: triangle-colour pixels), with `..._sha256` of the set, per model; seam4's j1r
    control: its hash and background count (E828)."""
    P = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    models = SEAM_MODELS[stage]
    ctl, rows, out = {}, {m: [] for m in models}, []
    for r in K.table(KP, stage):
        n = r["name"]
        w, h = size(r)
        px = observed(d, cases, r)
        if "hash" in P.get(n, {}):
            text = K.text(d, n + ".txt") if px is not None else ""
            m = HASH.search(text or "")
            got_h = m.group(1) if m else None
            bg = None if px is None else sum(1 for v in px.values() if v != TRI)
            ctl[n] = None if px is None or got_h is None else (
                got_h == P[n]["hash"]["all"] and bg == int(P[n]["background"]["all"]))
            out.append(f"CONTROL {n}: hash {got_h or '-'}, {'-' if bg is None else bg} not "
                       f"triangle; frozen {P[n]['hash']['all']}, 0: {cstate(ctl[n])}")
            continue
        q = "holes" if "--tri-full" in r["args"].split() else "stored"
        got = None if px is None else {p for p, v in px.items() if v == (BG if q == "holes" else TRI)}
        other = 0 if px is None else sum(1 for v in px.values() if v not in (TRI, BG))
        res = {}
        for m in models:
            want = P[n].get(q + "_sha256", {}).get(m)
            res[m] = "-" if want is None else None if got is None else (
                other == 0 and cells_sha(got) == want)
        detail = (f"{n}: {q} {'-' if got is None else len(got)}, {other} other; frozen " +
                  ", ".join(f"{m} {P[n][q][m]}" for m in models if m in P[n][q]))
        if r["set"] == "control":
            ctl[n] = res[SEAM_CTL[stage]]
            agree = {res[m] for m in models if res[m] != "-"}
            out.append(f"CONTROL {detail}: {cstate(ctl[n])}"
                       + ("" if len(agree) <= 1 else " (the rivals disagree on a control)"))
            continue
        for m in models:
            if res[m] != "-":
                rows[m].append(res[m])
        out.append(f"ROW {detail}: " + ", ".join(f"{m} {word(res[m])}" for m in models
                                                if res[m] != "-"))
    for m in models:
        out.append(f"SUMMARY: Q141 {stage} seam holes, {m}: "
                   + SK.headline(f"{m} exact on every held-out set", ctl, rows[m]))
    return out


# ---- cube2 -------------------------------------------------------------------------------------
def pred_pixels(stage, n, model, P):
    pred = {}
    for ln in frozen(stage, f"{n}.{model}.txt", P[n]["pixels_sha"][model]).splitlines():
        x, y, st, v = ln.split()
        pred[(int(x), int(y))] = (st, None if v == "-" else int(v, 16))
    return pred


def match(pred, px):
    """(matched, of predicted, first misses) of the "ok" pixels; None when px is None."""
    ok = [p for p, (st, v) in pred.items() if st == "ok"]
    if px is None:
        return None, len(ok), []
    miss = [p for p in ok if px[p] != pred[p][1]]
    return len(ok) - len(miss), len(ok), miss


def score_cube(d):
    P = K.predictions(KP, "cube2")
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    ctl, out = {}, []
    laws = ("H-E561", "H-MORTON", "H-PAIRSWAP")
    size = {(nn, m): [] for nn in (32, 64) for m in laws}
    n4 = {m: [] for m in ("H-NN", "H-PAD64")}
    ties = {m: [] for m in ("H-HIGHAXIS", "H-LOWAXIS", "H-POS")}
    edges = {m: [] for m in ("H-SEAM-ADJ", "H-SEAM-WRAP")}
    for r in K.table(KP, "cube2"):
        n = r["name"]
        px = observed(d, cases, r)
        if r["set"] == "control":
            got, tot, miss = match(pred_pixels("cube2", n, "E726", P), px)
            ctl[n] = None if got is None else not miss
            out.append(f"CONTROL {n}: {'-' if got is None else got} of {tot} pixels as E726 kept "
                       f"them: {cstate(ctl[n])}")
            continue
        models = sorted(P[n]["pixels_sha"])
        if n.startswith(("cube-n32-", "cube-n64-")) or n.startswith("cube-n4-"):
            res = {}
            for m in models:
                got, tot, miss = match(pred_pixels("cube2", n, m, P), px)
                res[m] = None if got is None else not miss
                out.append(f"READ {n} {m}: {'-' if got is None else got} of {tot} predicted pixels")
            if n.startswith("cube-n4-"):
                for m in n4:
                    n4[m].append(res[m])
            else:
                for m in laws:
                    size[(int(n[6:8]), m)].append(res[m])
            out.append(f"ROW {n}: " + ", ".join(f"{m} {word(res[m])}" for m in models))
            continue
        pred = pred_pixels("cube2", n, "RULE", P)
        got, tot, miss = match(pred, px)
        tc = collections.Counter(st for st, _ in pred.values() if st != "ok")
        head = (f"{n}: {'-' if got is None else got} of {tot} predicted pixels as the rule, ties "
                f"not predicted {dict(sorted(tc.items()))}")
        if miss:
            head += " first misses " + " ".join("(%d,%d) hw 0x%08x rule 0x%08x" % (
                *p, px[p], pred[p][1]) for p in miss[:4])
        out.append(f"READ {head}")
        if n.startswith("cube-ftie-"):
            res, line = score_ties(n, P, px)
            for m in ties:
                ties[m].append(res[m])
            out.append(line)
            out.append(f"ROW {n}: " + ", ".join(f"{m} {word(res[m])}" for m in ties))
        elif n.startswith("cube-ttie-"):
            if px is not None:
                out.append(tie_reading(n, pred, px))
        elif n.startswith("cube-edge-"):
            res, lines = score_edge(n, P, px)
            for m in edges:
                edges[m].append(res[m])
            out += lines
            out.append(f"ROW {n}: " + ", ".join(f"{m} {word(res[m])}" for m in edges))
    for nn in (32, 64):
        for m in laws:
            out.append(f"SUMMARY: Q284 cube faces of {nn} x {nn}, {m}: "
                       + SK.headline(f"{m} at {nn} x {nn} held out", ctl, size[(nn, m)]))
    for m in n4:
        out.append(f"SUMMARY: Q284 cube faces of 4 x 4, {m}: "
                   + SK.headline(f"{m} at 4 x 4 held out", ctl, n4[m]))
    for m in ties:
        out.append(f"SUMMARY: Q284 face ties of x = y and y = z, {m}: "
                   + SK.headline(f"{m} on every tie pixel", ctl, ties[m]))
    for m in edges:
        out.append(f"SUMMARY: Q284 bilinear at a face edge, {m}: "
                   + SK.headline(f"{m} on every out pixel", ctl, edges[m]))
    return out


def score_ties(n, P, px):
    """Each rival held when every tie pixel reads its face (a 16 x 16 face: the index // 256)."""
    names = ("H-HIGHAXIS", "H-LOWAXIS", "H-POS")
    body = frozen("cube2", n + ".ties.txt", P[n]["ties_sha"][names[0]])
    cells = {}
    for ln in body.splitlines():
        x, y, *f = ln.split()
        cells[(int(x), int(y))] = dict(zip(names, map(int, f)))
    if px is None or not cells:
        return {m: None for m in names}, f"READ {n} face ties: no pixels"
    read = {p: (px[p] & 0x0fffffff) // 256 if px[p] >> 28 == 0xD else None for p in cells}
    res = {m: all(read[p] == c[m] for p, c in cells.items()) for m in names}
    by_row = collections.Counter(("third<0" if p[1] < 16 else "third=0" if p[1] == 16
                                  else "third>0", read[p]) for p in cells)
    return res, (f"READ {n} face ties: faces read {dict(sorted(collections.Counter(read.values()).items(), key=str))}"
                 f" by the third coordinate's sign {dict(sorted(by_row.items(), key=str))}")


def tie_reading(n, pred, px):
    """Texel ties: per tied axis, the upper texel (the rule's floor at an exact boundary) or the
    lower one, per boundary (s texel, t texel), from the frozen generator's exact coordinates."""
    sys.path.insert(0, os.path.join(KP, "gen"))
    import cube as C
    import texprog as T
    R = C.rule()
    spec = C.TTIE[n.rsplit("-", 1)[1]]
    tally, bound = collections.Counter(), collections.Counter()
    for p, (st, _) in pred.items():
        if st != "texel-tie":
            continue
        face, vs, vt, ma, order = C.st(R, tuple(T.coord(c, *p) for c in spec), 16)
        fl = [C.flo(v) for v in (vs, vt)]
        tied = [v.denominator == 1 for v in (vs, vt)]
        got = px[p] & 0x0fffffff
        hit = None
        for ds in ((0, -1) if tied[0] else (0,)):
            for dt in ((0, -1) if tied[1] else (0,)):
                s, t = min(max(fl[0] + ds, 0), 15), min(max(fl[1] + dt, 0), 15)
                if got == face * 256 + C.twid(s, t, order, 4):
                    hit = ("s" + ("down" if ds else "up") if tied[0] else "") + \
                          ("t" + ("down" if dt else "up") if tied[1] else "")
        tally[hit or "other"] += 1
        for ax, nm in ((0, "s"), (1, "t")):
            if tied[ax] and hit and nm in hit:
                bound[(nm, fl[ax], "down" if nm + "down" in hit else "up")] += 1
    return (f"READ {n} texel ties at |ma| {n[-4]}.{n[-3:]}: {dict(sorted(tally.items()))}; per "
            f"boundary {dict(sorted(bound.items()))}")


def score_edge(n, P, px):
    """({rival: state}, READ lines). The in pixels gate the job: at least IN_SHARE of them read
    their exact in-face blend within EDGE_TOL in every byte, else both rivals cannot tell. A rival
    holds when every out pixel's bytes lie within EDGE_TOL of its blend."""
    F = fractions.Fraction
    names = ("H-SEAM-ADJ", "H-SEAM-WRAP")
    ins, outs = {}, collections.defaultdict(dict)
    for ln in frozen("cube2", n + ".edge.txt", P[n]["edge_sha"]["EDGE"]).splitlines():
        f = ln.split()
        p = (int(f[0]), int(f[1]))
        if f[2] == "in":
            ins[p] = [F(b) for b in f[3:]]
        else:
            outs[p][f[3]] = None if f[4] == "-" else [F(b) for b in f[4:]]
    if px is None:
        return {m: None for m in names}, [f"READ {n} edge: no pixels"]

    def near(v, b):
        return all(abs(((v >> (8 * i)) & 255) - b[i]) <= EDGE_TOL for i in range(4))

    ok_in = sum(1 for p, b in ins.items() if near(px[p], b))
    active = ins and ok_in >= IN_SHARE * len(ins)
    cnt = {m: sum(1 for p, d in outs.items() if d[m] is not None and near(px[p], d[m]))
           for m in names}
    vals = collections.Counter("%08x" % px[p] for p in outs)
    lines = [f"READ {n} edge: {ok_in} of {len(ins)} in pixels within {EDGE_TOL} of the exact blend "
             f"(premise {'met' if active else 'NOT met'}); out pixels within {EDGE_TOL}: "
             + ", ".join(f"{m} {cnt[m]} of {len(outs)}" for m in names),
             f"READ {n} edge out values: {dict(sorted(vals.items()))}"]
    if not active or not outs:
        return {m: None for m in names}, lines
    return {m: cnt[m] == len(outs) for m in names}, lines


# ---- addr2 -------------------------------------------------------------------------------------
def score_addr(d):
    P = K.predictions(KP, "addr2")
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    ctl, out = {}, []
    groups = collections.OrderedDict()
    for r in K.table(KP, "addr2"):
        n = r["name"]
        px = observed(d, cases, r)
        idx = None if px is None else {p: (v & 0x0fffffff) - 12288 if v >> 28 == 0xD else None
                                       for p, v in px.items()}
        res = {}
        imgs = {}
        for m in P[n]["image_sha"]:
            img = {}
            for ln in frozen("addr2", f"{n}.{m}.txt", P[n]["image_sha"][m]).splitlines():
                x, y, v = ln.split()
                img[(int(x), int(y))] = int(v)
            imgs[m] = img
            res[m] = None if idx is None else all(idx[p] == v for p, v in img.items())
        if r["set"] == "control":
            ctl[n] = res["REPEAT"]
            out.append(f"CONTROL {n}: the mode 0 repeat image at page 12: {cstate(ctl[n])}")
            continue
        g = group(n, r["set"])
        for m, v in res.items():
            groups.setdefault((g, m), []).append(v)
        out.append(f"ROW {n}: " + ", ".join(f"{m} {word(v)}" for m, v in res.items()))
        if idx is not None:
            ref = [(m, k) for m, k in (("H-MASK-V", 0), ("H-OFF180", 180), ("H-T3-INERT", 180))
                   if m in imgs]
            if ref:
                base, sub = imgs[ref[0][0]], ref[0][1]
                off = collections.Counter(None if idx[p] is None else idx[p] - (v - sub)
                                          for p, v in base.items())
                out.append(f"READ {n} index less H-MASK-V's: {dict(sorted(off.items(), key=str))}")
            out.append(f"READ {n} per position (pair of rows 0, 1): " + " ".join(
                "-" if idx[(p & 63, p >> 6)] is None else str(idx[(p & 63, p >> 6)])
                for p in range(128)))
    for (g, m), v in groups.items():
        out.append(f"SUMMARY: Q177 {g}, {m}: " + SK.headline(f"{m} ({g})", ctl, v))
    return out


def group(n, sset):
    if sset == "replicate":
        return "replicate " + n
    if "-t3-" in n:
        return "u mode 4 at 16 x 16 under T3"
    if n == "addr-uv4":
        return "u and v mode 4"
    return "u modes 4 and 6 at 8 x 8 and 32 x 32"


SCORE = {"seam1": lambda d: score_seam("seam1", d), "seam4": lambda d: score_seam("seam4", d),
         "cube2": score_cube, "addr2": score_addr}


def main(argv):
    sys.path.insert(0, os.path.join(KP, "score"))
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in SCORE:
        print("\n".join(SCORE[argv[1]](argv[2])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
