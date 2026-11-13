#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r8-geo's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 d97c47393531, pinned in FROZEN.commits).
The frozen per-pixel predictions are predictions/STAGE/NAME[.MODEL].txt, each checked against its
sha256 in predictions/STAGE.tsv before it is used (a changed file is a STOP, not a verdict).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and READ lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another: GATES is empty)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A row is held, FAILED or cannot tell (a void job, no pixel rows, a gate shut); the controls gate
every row of their stage (scorekit.headline). Exploratory rows (set explore) print READ lines and
decide nothing."""
import collections
import hashlib
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

REQUIRED = {s: (".txt", "cases.tsv", "void.tsv", "readings.tsv")
            for s in ("cube", "seam", "addr", "vdm")}
GATES = {}
TRI, BG = 0xff00ff00, 0xff203040
SIZE = re.compile(r"--width (\d+) --height (\d+)")


def producible(row):
    """The reading keys a row's job can produce: every row of this session prints its pixels."""
    return {"pixels"} if "--pixels" in row["args"].split() else set()


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


def seam_sha(pix):
    return hashlib.sha256(";".join("%d,%d" % p for p in sorted(pix)).encode()).hexdigest()


def observed(stage, d, cases, row):
    n = row["name"]
    if n not in cases or cases[n]["class"] != "ok":
        return None
    return pixels(K.text(d, n + ".txt"), *size(row))


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    for n in cases:
        K.text(d, n + ".txt")


def word(v):
    return "held" if v else "FAILED" if v is False else "cannot tell"


def cstate(v):
    return "PASS" if v else "FAILED" if v is False else "cannot tell"


# ---- cube ------------------------------------------------------------------------------------
def score_cube(d):
    P = K.predictions(KP, "cube")
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    ctl, rows_a, rows_b, clamp, seam_, out = {}, [], [], [], [], []
    for r in K.table(KP, "cube"):
        n = r["name"]
        px = observed("cube", d, cases, r)
        model = "E726" if r["set"] == "control" else "RULE"
        pred = {}
        for ln in frozen("cube", n + ".txt", P[n]["pixels_sha"][model]).splitlines():
            x, y, st, v = ln.split()
            pred[(int(x), int(y))] = (st, None if v == "-" else int(v, 16))
        ok = [p for p, (st, v) in pred.items() if st == "ok"]
        miss = None if px is None else [p for p in ok if px[p] != pred[p][1]]
        if r["set"] == "control":
            ctl[n] = None if px is None else not miss
            out.append(f"CONTROL {n}: {len(ok) - len(miss) if px else '-'} of {len(ok)} pixels "
                       f"as E726 kept them: {cstate(ctl[n])}")
            continue
        state = None if px is None else not miss
        ties = collections.Counter(st for st, _ in pred.values() if st != "ok")
        head = (f"{n}: {len(ok) - len(miss) if px else '-'} of {len(ok)} predicted pixels as the "
                f"rule, ties not predicted {dict(ties)}")
        if miss:
            head += " first misses " + " ".join("(%d,%d) hw 0x%08x rule 0x%08x" % (
                *p, px[p], pred[p][1]) for p in miss[:4])
        if n.startswith("cube-off-"):
            rows_a.append(state)
            out.append(f"ROW {head}: {word(state)}")
        elif n.startswith("cube-n"):
            rows_b.append(state)
            out.append(f"ROW {head}: {word(state)}")
        elif n.startswith("cube-edge-"):
            out.append(f"READ {head}")
            c, s, line = score_edge(n, P, px)
            clamp.append(c)
            seam_.append(s)
            out.append(line)
        else:
            out.append(f"READ {head}")
            if px is not None:
                out.append(tie_reading(n, r, pred, px))
    out.append("SUMMARY: Q284 cube (s, t) rule on 4 new off-axis 16 x 16 programs: "
               + SK.headline("the frozen q284 rule held out", ctl, rows_a))
    out.append("SUMMARY: Q284 cube rule at 8 x 8 and 32 x 32 faces, N * N dwords apart: "
               + SK.headline("the rule with N = 8, 32 held out", ctl, rows_b))
    out.append("SUMMARY: Q284 bilinear at a face edge: "
               + SK.headline("H-CLAMP (taps clamped inside the face)", ctl, clamp))
    out.append("SUMMARY: Q284 bilinear at a face edge: "
               + SK.headline("H-SEAM (taps from the neighbour face) [infer]", ctl, seam_))
    return out


def score_edge(n, P, px):
    """(H-CLAMP state, H-SEAM state, the READ line). The "in" pixels gate the job: at least half
    of those whose two s or t taps differ by 2 or more in the low byte must read a value that is
    neither tap's (the filter blends); else both rivals cannot tell."""
    cells = {}
    for ln in frozen("cube", n + ".edge.txt", P[n]["edge_sha"]["EDGE"]).splitlines():
        x, y, f, k = ln.split()
        cells[(int(x), int(y))] = (int(f), k)
    if px is None:
        return None, None, f"READ {n} edge: no pixels"
    point = {}
    for ln in frozen("cube", n + ".txt", P[n]["pixels_sha"]["RULE"]).splitlines():
        x, y, st, v = ln.split()
        point[(int(x), int(y))] = None if v == "-" else int(v, 16)
    inn = [p for p, (f, k) in cells.items() if k == "in"]
    blended = sum(1 for p in inn if px[p] != point[p])
    active = 2 * blended >= len(inn) > 0
    outs = [(p, f) for p, (f, k) in cells.items() if k == "out"]
    g_own = sum(1 for p, f in outs if (px[p] >> 8) & 0xff == f and px[p] >> 24 == 0xD0)
    g_other = len(outs) - g_own
    line = (f"READ {n} edge: {blended} of {len(inn)} in pixels differ from the point sample "
            f"(filter {'active' if active else 'NOT shown active'}), out pixels G = own face "
            f"{g_own}, other {g_other} of {len(outs)}")
    if not active or not outs:
        return None, None, line
    return g_other == 0, g_own == 0, line


def tie_reading(n, r, pred, px):
    """Face ties: the faces read at the tie pixels; texel ties: per tied axis, the upper texel
    (the rule's floor at an exact boundary) or the lower one, from the frozen generator's exact
    coordinates (gen/cube.py, frozen with the session)."""
    if "ftie" in n:
        faces = collections.Counter((px[p] & 0xffffff) // 256 for p, (st, _) in pred.items()
                                    if st == "face-tie")
        return f"READ {n} face ties: faces read {dict(sorted(faces.items()))}"
    sys.path.insert(0, os.path.join(KP, "gen"))
    import cube as C
    import texprog as T
    R = C.rule()
    spec = C.TTIE[n.rsplit("-", 1)[1]]
    tally = collections.Counter()
    for p, (st, _) in pred.items():
        if st != "texel-tie":
            continue
        face, vs, vt, ma, order = C.st(R, tuple(T.coord(c, *p) for c in spec), 16)
        fl = [v.numerator // v.denominator for v in (vs, vt)]
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
    return f"READ {n} texel ties at |ma| {n[-4]}.{n[-3:]}: {dict(sorted(tally.items()))}"


# ---- seam ------------------------------------------------------------------------------------
def cells_sha(cells):
    text = "".join(f"{x} {y}\n" for x, y in sorted(cells, key=lambda p: (p[1], p[0])))
    return hashlib.sha256(text.encode()).hexdigest()


def score_seam(d):
    """predictions/seam.tsv is the O8 R8-1 table: per job `holes` (tri-full: background pixels)
    or `stored` (a single triangle: triangle-colour pixels), with `..._sha256` of the set."""
    P = K.predictions(KP, "seam")
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    ctl, rows, out = {}, {"H-REGION": [], "H-UNION": []}, []
    for r in K.table(KP, "seam"):
        n = r["name"]
        w, h = size(r)
        px = observed("seam", d, cases, r)
        q = "holes" if "--tri-full" in r["args"].split() else "stored"
        got = None if px is None else {p for p, v in px.items() if v == (BG if q == "holes" else TRI)}
        other = 0 if px is None else sum(1 for v in px.values() if v not in (TRI, BG))
        res = {m: None if got is None else (other == 0 and cells_sha(got) == P[n][q + "_sha256"][m])
               for m in rows}
        detail = (f"{n}: {q} {'-' if got is None else len(got)}, {other} other; frozen H-REGION "
                  f"{P[n][q]['H-REGION']}, H-UNION {P[n][q]['H-UNION']}")
        if r["set"] == "control":
            ctl[n] = res["H-REGION"]
            out.append(f"CONTROL {detail}: {cstate(ctl[n])}")
            continue
        for m in rows:
            rows[m].append(res[m])
        out.append(f"ROW {detail}: H-REGION {word(res['H-REGION'])}, H-UNION {word(res['H-UNION'])}")
    for m in rows:
        out.append(f"SUMMARY: Q141 seam holes, {m}: "
                   + SK.headline(f"{m} exact on every held-out set", ctl, rows[m]))
    return out


# ---- addr ------------------------------------------------------------------------------------
def score_addr(d):
    P = K.predictions(KP, "addr")
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    models = ("H-MASK-V", "H-NOMASK-PAGE", "H-BORDER")
    ctl, rows, out = {}, {(a, m): [] for a in "uv" for m in models}, []
    for r in K.table(KP, "addr"):
        n = r["name"]
        px = observed("addr", d, cases, r)
        names = ("REPEAT",) if r["set"] == "control" else models
        res = {}
        for m in names:
            img = {}
            for ln in frozen("addr", f"{n}.{m}.txt", P[n]["image_sha"][m]).splitlines():
                x, y, v = ln.split()
                img[(int(x), int(y))] = None if v == "-" else int(v)
            if px is None:
                res[m] = None
                continue
            idx = {p: (v & 0x0fffffff) if v >> 28 == 0xD else -1 for p, v in px.items()}
            inside = all(idx[p] == v for p, v in img.items() if v is not None)
            outside = {idx[p] for p, v in img.items() if v is None}
            res[m] = inside and len(outside) <= 1
        if r["set"] == "control":
            ctl[n] = res["REPEAT"]
            out.append(f"CONTROL {n}: the mode 0 repeat image at page 12: {cstate(ctl[n])}")
            continue
        axis = n.split("-")[1][0]
        for m in models:
            rows[(axis, m)].append(res[m])
        out.append(f"ROW {n}: " + ", ".join(f"{m} {word(res[m])}" for m in models))
        if px is not None:
            out.append(f"READ {n} per position (pair of rows 0, 1): " + " ".join(
                str((px[(p & 63, p >> 6)] & 0x0fffffff) - 12288) for p in range(128)))
    for (a, m), v in rows.items():
        out.append(f"SUMMARY: Q177 modes 4 to 7 on {a}, {m}: "
                   + SK.headline(f"{m} on the {a} axis", ctl, v))
    return out


# ---- vdm -------------------------------------------------------------------------------------
def score_vdm(d):
    P = K.predictions(KP, "vdm")
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    table = K.table(KP, "vdm")
    img = {}
    for r in table:
        px = observed("vdm", d, cases, r)
        img[r["name"]] = None if px is None else hashlib.sha256(
            "".join("%08x" % px[(x, y)] for y in range(64) for x in range(64)).encode()).hexdigest()
    ctl, count, layout, out = {}, [], [], []
    for r in table:
        n = r["name"]
        twin = P.get(n, {}).get("twin", {}).get("all")
        if twin is None:
            out.append(f"READ {n}: reference image {img[n][:16] if img[n] else '-'}")
            continue
        same = None if img[n] is None or img[twin] is None else img[n] == img[twin]
        rel = "-" if same is None else "same" if same else "differs"
        pred = P[n]["vs_twin"]
        line = f"{n}: image {rel} as {twin}; frozen {dict(pred)}"
        if r["set"] == "control":
            ctl[n] = None if same is None else same == (pred["H-FORCE-NEUTRAL"] == "same")
            out.append(f"CONTROL {line}: {cstate(ctl[n])}")
            continue
        hc = None if same is None else same == (pred["H-COUNT"] == "same")
        hl = None if same is None else same == (pred["H-LAYOUT"] == "same")
        if r["set"] == "explore":
            out.append(f"READ {line}")
            continue
        count.append(hc)
        layout.append(hl)
        out.append(f"ROW {line}: H-COUNT {word(hc)}, H-LAYOUT {word(hl)}")
    out.append("SUMMARY: Q271 forced = natural + 1 (the two replicates " + SK.combine(count)
               + " under H-COUNT): " + SK.headline("H-COUNT (rows a count)", ctl, count))
    out.append("SUMMARY: Q271 forced = natural + 1: "
               + SK.headline("H-LAYOUT (rows a stride)", ctl, layout))
    return out


SCORE = {"cube": score_cube, "seam": score_seam, "addr": score_addr, "vdm": score_vdm}


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
