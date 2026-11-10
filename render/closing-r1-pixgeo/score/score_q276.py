"""Scorer of R1's p-c2 (Q276 C2).  Written before the run; frozen with the predictions.  numpy: scratch only.

Rules common to every R1 scorer: a job whose data is empty, missing or has an rc that is not a result of the tool is
NODATA (tested first, never a match); controls come from the frozen predictions (set `control`) and a failing control
makes what it controls `cannot tell`; held-out and replicate rows are tallied apart from `repeat` rows (S1b fits run
again); every scorer ends with one line `SUMMARY: ...` naming the hypothesis and the count.

Reading (S1b's c_tags/c_measure extended): the x and y job of a configuration decode, for every landed o1/o4 word, its
SOURCE pixel (the float in the high half of the word: pa0 / pa1); tag 2 = the p1-true o1 write, 12 = the !p1 write, 5 =
the p1-true o4 write, 13 = the !p1 o4 write.  Per source: the predicate of a model is a RULE on the source pixel
(x bit b, y bit b, g25 lane k under HQ-a / HQ-b, never); a model holds iff at most max(2, 2%) of the decoded sources
disagree with its rule (see allowed(); of at least 300 decoded o1 sources, else the configuration is void).  Direct reads (o0 alone): the written
pixel's own word compared with the model's value at (x, y), at least 90% of the written pixels.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402

from r1lib import Kept, f32v, rows_of, support, table  # noqa: E402

BG = 0xff203040
MIN_SOURCES = 300
MAX_DISAGREE = 2
TOL = 0.07
TAGS = (2, 12, 5, 13)


def f32_hi(v):
    return f32v(v & 0xffff0000)


def source_of(vx, vy, w=64, h=64):
    sx = round(f32_hi(vx) * w / 2 + w / 2 - .5)
    sy = round(f32_hi(vy) * h / 2 + h / 2 - .5)
    return (sx, sy) if 0 <= sx < w and 0 <= sy < h else None


def read_grid(k: Kept, name):
    txt = k.out(name)
    g = rows_of(txt or "")
    return g if len(g) == 64 and all(len(r) == 64 for r in g) else None


def c_decode(gx, gy, marker=None):
    """({tag: {(sx, sy)}}, marker_ok, n_words): the words that pair up between the x and y image (same tag nibble, not
    background) decoded to their source pixel.  marker_ok: the share of decoded x words that carry the job's marker."""
    src = {t: set() for t in TAGS}
    good = bad = 0
    for y in range(64):
        for x in range(64):
            vx, vy = gx[y][x], gy[y][x]
            if BG in (vx, vy) or (vx & 15) != (vy & 15) or (vx & 15) not in TAGS:
                continue
            s = source_of(vx, vy)
            if s is None:
                continue
            src[vx & 15].add(s)
            if marker is not None:
                if ((vx & 0xffff) >> 4) == marker and ((vy & 0xffff) >> 4) == marker + 1:
                    good += 1
                else:
                    bad += 1
    ok = None if marker is None else (good + bad > 0 and good / (good + bad) >= 0.95)
    return src, ok, good + bad


def lane(sx, sy, which):
    return (sx & 1) | (sy & 1) << 1 if which == "A" else (sx & 1) << 1 | (sy & 1)


def rule_fn(rule):
    """'x:5' | 'y:4' | 'never' | 'lane:K:A|B' -> predicate on a source pixel."""
    if rule == "never":
        return lambda sx, sy: False
    p = rule.split(":")
    if p[0] == "x":
        return lambda sx, sy, b=int(p[1]): bool(sx >> b & 1)
    if p[0] == "y":
        return lambda sx, sy, b=int(p[1]): bool(sy >> b & 1)
    if p[0] == "lane":
        return lambda sx, sy, k=int(p[1]), w=p[2]: lane(sx, sy, w) == k
    raise ValueError(rule)


def disagree(src, rule):
    f = rule_fn(rule)
    return sum(1 for s in src[2] if not f(*s)) + sum(1 for s in src[12] if f(*s))


def measure(src):
    n2, n12, n5, n13 = (len(src[t]) for t in (2, 12, 5, 13))
    par = dict(collections.Counter((sx & 1, sy & 1) for sx, sy in src[2]))
    return dict(n2=n2, n12=n12, n5=n5, n13=n13, n=n2 + n12, frac=n2 / (n2 + n12) if n2 + n12 else float("nan"),
                par=par, p5=dict(collections.Counter((sx & 1, sy & 1) for sx, sy in src[5])),
                first=sorted(src[12] & src[2]))


def frac_ok(v, frac):
    if math.isnan(frac):
        return False
    if v == "0|1":
        return frac in (0.0, 1.0)
    if v.startswith("same"):
        return True
    return abs(frac - float(v)) < TOL


def o4_class(m):
    if m["n5"] + m["n13"] < 10:
        return None
    if m["n5"] >= 10 and m["n13"] <= 2:
        return "5"
    if m["n13"] >= 10 and m["n5"] <= 2:
        return "5'"
    return "mixed"


def pq(preds, name, q):
    return preds.get(name, {}).get(q, [])


def allowed(src):
    """Exceptions a rule may have: 2% of the decoded o1 sources, at least 2.  Frozen from S1b's own fit data (c-k0: 6 of
    490 lane-0 sources kept the !p1 write, all at x 12..14 or 46; c-g23: 0 of 485); the proposal's '<= 2 of >= 400'
    would refute S1b's fit on its own data.  Wrong rules miss ~25% to 50% of the sources, so 2% separates them."""
    return max(MAX_DISAGREE, math.ceil(0.02 * (len(src[2]) + len(src[12]))))


def model_ok(preds, name, m, src, meas):
    """{model: bool} for one decoded configuration: every frozen quantity of the model must hold."""
    out = {}
    for q in ("frac_tag2_of_o1", "rule", "tag2_parity", "o4_class"):
        for v, mdl, st in pq(preds, name, q):
            if q == "frac_tag2_of_o1":
                ok = frac_ok(v, meas["frac"])
            elif q == "rule":
                ok = disagree(src, v) <= allowed(src)
            elif q == "tag2_parity":
                want = tuple(int(c) for c in v.split(","))
                ok = sum(c for key, c in meas["par"].items() if key != want) <= allowed(src)
            else:
                ok = o4_class(meas) == v
            out[mdl] = out.get(mdl, True) and ok
    return out


def score_p_c2(k: Kept, preds):
    rows, void, got = [], [], {}
    cfgs = sorted({re.sub(r"-[xy]$", "", n) for n in k.names() if re.search(r"-[xy]$", n) and not n.endswith("-rep")
                   and not n.startswith("c-rd-pa")})
    for cfg in cfgs:
        nx, ny = f"{cfg}-x", f"{cfg}-y"
        vv = k.void(nx) or k.void(ny)
        gx, gy = (None, None) if vv else (read_grid(k, nx), read_grid(k, ny))
        if vv or gx is None or gy is None:
            void.append(cfg)
            rows.append((cfg, "NODATA: " + (vv or "no 64x64 pixel rows"), "", "", "", ""))
            continue
        mk = pq(preds, nx, "marker")
        marker = int(mk[0][0], 16) if mk else None
        src, mok, nw = c_decode(gx, gy, marker)
        meas = measure(src)
        if mok is False:
            void.append(cfg)
            rows.append((cfg, "NODATA: marker proof failed (the program that ran is not the frozen one)", "", "", "", ""))
            continue
        got[cfg] = dict(src=src, meas=meas)
        rows.append((cfg, meas["n2"], meas["n12"], f"{meas['frac']:.3f}", f"{meas['n5']}/{meas['n13']}",
                     meas["par"]))
    out = ["C2: o1 tag per source pixel from the x/y pairs (2 = p1 write, 2' = !p1 write); o4 tags 5 / 5'",
           table(rows, ["config", "tag 2", "tag 2'", "frac 2", "o4 tag 5 / 5'", "tag 2 by (sx&1, sy&1)"]), ""]
    # replicates: another run of NAME-x decoded with NAME-y
    reps = []
    for n in [n for n in k.names() if n.endswith("-x-rep")]:
        base = n[:-len("-x-rep")]
        vv = k.void(n)
        gx, gy = (None, None) if vv else (read_grid(k, n), read_grid(k, f"{base}-y"))
        if vv or gx is None or gy is None or base not in got:
            reps.append((n, None))
            out.append(f"replicate {n}: NODATA ({vv or 'no pixels or no base'})")
            continue
        src, _, _ = c_decode(gx, gy)
        r = measure(src)
        bm = got[base]["meas"]
        same = abs(r["frac"] - bm["frac"]) < TOL and set(r["par"]) == set(bm["par"])
        reps.append((n, same))
        out.append(f"replicate {n}: tag-2 fraction {r['frac']:.3f} vs {bm['frac']:.3f}, parity {r['par']} vs {bm['par']}: "
                   f"{'same' if same else 'DIFFERENT'}")
    # direct reads
    rd = {}
    for cfg in ("c-rd-g23", "c-rd-g25"):
        if cfg not in k.names():
            continue
        vv = k.void(cfg)
        g = None if vv else read_grid(k, cfg)
        if vv or g is None:
            rd[cfg] = dict(void=vv or "no 64x64 pixel rows")
            out.append(f"{cfg}: NODATA ({rd[cfg]['void']})")
            continue
        written = [(x, y, g[y][x]) for y in range(64) for x in range(64) if g[y][x] != BG]
        if len(written) < MIN_SOURCES:
            rd[cfg] = dict(void=f"{len(written)} written pixels")
            out.append(f"{cfg}: NODATA ({len(written)} written pixels < {MIN_SOURCES})")
            continue
        fr = lambda f: sum(1 for x, y, v in written if v == f(x, y)) / len(written)
        rd[cfg] = dict(void=None, g23_xy=fr(lambda x, y: y << 16 | x), g23_x=fr(lambda x, y: x),
                       g25_a=fr(lambda x, y: lane(x, y, "A")), g25_b=fr(lambda x, y: lane(x, y, "B")),
                       vals=collections.Counter(v for _, _, v in written).most_common(4), n=len(written))
        out.append(f"{cfg}: {len(written)} written pixels; o0 == y<<16|x {rd[cfg]['g23_xy']:.3f}, == x {rd[cfg]['g23_x']:.3f}, "
                   f"== g25 lane A {rd[cfg]['g25_a']:.3f}, B {rd[cfg]['g25_b']:.3f}; most common {rd[cfg]['vals']}")
    pa = None
    if "c-rd-pa-x" in k.names() and "c-rd-pa-y" in k.names():
        vv = k.void("c-rd-pa-x") or k.void("c-rd-pa-y")
        gx, gy = (None, None) if vv else (read_grid(k, "c-rd-pa-x"), read_grid(k, "c-rd-pa-y"))
        if vv or gx is None or gy is None:
            out.append(f"c-rd-pa: NODATA ({vv or 'no pixel rows'})")
        else:
            written = [(x, y) for y in range(64) for x in range(64)
                       if gx[y][x] != BG and gy[y][x] != BG and (gx[y][x] & 15) == 15 == (gy[y][x] & 15)]
            ident = sum(1 for x, y in written if source_of(gx[y][x], gy[y][x]) == (x, y)) / len(written) if written else 0
            pa = dict(n=len(written), ident=ident)
            out.append(f"c-rd-pa: {len(written)} pixels, o0 = pa0/pa1 decodes to the pixel's own position in {ident:.3f}")
    # ---------------------------------------------------------------- controls and groups
    e = got.get("c-e709")
    crit = {n[:-2]: float(v) for n, qs in preds.items() if n.endswith("-x") for v, m, s in qs.get("ctl_min_frac", [])}
    us = {c: got[c]["meas"]["frac"] if c in got else "void or not run" for c in crit}
    glob = bool(e and 17 <= e["meas"]["n5"] <= 29 and crit and all(c in got and us[c] >= crit[c] for c in crit))
    if not glob:
        n5 = e["meas"]["n5"] if e else None
        out.append(f"SUMMARY: cannot tell: global controls failed or void (c-e709 tag-5 pairs 17..29: {n5}; order controls "
                   f"(frozen minimum {crit}): {us}); void {void}")
        return "\n".join(out), {}
    entries = collections.defaultdict(list)
    gate_text = []
    held = [c for c in got if any(s in ("heldout", "repeat") for q in ("frac_tag2_of_o1", "rule", "o4_class")
                                  for v, m, s in pq(preds, f"{c}-x", q))]
    grp = lambda c: ("g23" if "g23" in c else "o4" if "-o4-" in c else "k")
    ctl_g23 = got.get("c-g23r4")
    ctl_g23_ok = bool(ctl_g23 and all(model_ok(preds, "c-g23r4-x", None, ctl_g23["src"], ctl_g23["meas"]).values()))
    ctl_o4 = got.get("c-o4-u")
    ctl_o4_ok = bool(ctl_o4 and o4_class(ctl_o4["meas"]) == "5")
    for cfg in sorted(held):
        pn = f"{cfg}-x"
        g = grp(cfg)
        if cfg == "c-g23r4" or cfg == "c-o4-u":
            continue
        if g == "g23" and not cfg == "c-g23" and not ctl_g23_ok:
            gate_text.append(f"{cfg}: cannot tell (the register-form control c-g23r4 failed or void)")
            continue
        if g == "o4" and not ctl_o4_ok:
            gate_text.append(f"{cfg}: cannot tell (the o4 control c-o4-u failed or void)")
            continue
        if g != "o4" and got[cfg]["meas"]["n"] < MIN_SOURCES:
            gate_text.append(f"{cfg}: cannot tell ({got[cfg]['meas']['n']} decoded o1 sources < {MIN_SOURCES})")
            continue
        sets = {m: s for q in ("frac_tag2_of_o1", "rule", "o4_class") for v, m, s in pq(preds, pn, q)}
        for mdl, ok in model_ok(preds, pn, None, got[cfg]["src"], got[cfg]["meas"]).items():
            entries[g].append((mdl, sets.get(mdl, "heldout"), ok))
    # replicates add to their model's group
    for n, same in reps:
        base = n[:-len("-x-rep")]
        entries[grp(base)].append((f"replicate of {base}", "replicate", same))
    # direct reads, gated by c-rd-pa
    if pa is None or pa["ident"] < 0.9 or pa["n"] < MIN_SOURCES:
        for cfg in rd:
            gate_text.append(f"{cfg}: cannot tell (the premise control c-rd-pa failed, void or not run)")
    else:
        for cfg, r in rd.items():
            if r["void"]:
                continue
            for v, mdl, st in pq(preds, cfg, "rd_value"):
                key = {"g23:y<<16|x": "g23_xy", "g25:A": "g25_a", "g25:B": "g25_b"}[v]
                entries["rd"].append((mdl, st, r[key] >= 0.9))
    parts = [f"{g}: {support(es)}" for g, es in entries.items()]
    out.append("SUMMARY: global controls pass (c-e709, c-u x2); " + "; ".join(parts + gate_text)
               + (f"; void configurations {void}" if void else ""))
    return "\n".join(out), {}
