# SPDX-License-Identifier: MIT
"""Scorer of p-c3 (Q276, pixel), the frozen rerun of R1's p-c2 (score_q276.py) with GROUP-SCOPED controls.  Written before the run;
frozen with the predictions.  numpy: not needed.

Rules common to every scorer: a job whose data is empty, missing or has an rc that is not a result of the tool is NODATA (tested
first, never a match); a control that fails makes ONLY its group `cannot tell` (decision R3-P6); CONFIRM rows (set `repeat`: read post
hoc in round 2, frozen now) are tallied apart from HELD OUT rows; the last line is one `SUMMARY:` naming the model and the count.

Reading (S1b's c_tags / c_measure, R1's c_decode): the x and y job of a configuration decode, for every landed o1 / o4 word, its
SOURCE pixel (the float in the high half of the word: pa0 / pa1); tag 2 = the p1-true o1 write, 12 = the !p1 write, 5 = the p1-true
o4 write, 13 = the !p1 o4 write.  A rule (x bit b, y bit b, lane k, xeq K = (x mod 32) == K, xany M, xe K = x == K, never) holds iff at
most max(2, 2%) of the >= 300 decoded o1 sources disagree (exact-column rules xeq / xe: at most 1: the 2% budget cannot separate
M from X at x = 52); an alternative that differs from M at no more sources than the budget is `not separable` (void), never consistent.
The o4 class is read from the tag-5 / 5' WORDS of both jobs (at least 10 each, the other tag <= 2), not from the pairs; pairs serve only
the source parity.  Direct reads (o0 alone): the written pixel's own word compared with the model's value at (x, y), at least 90%."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402

from r3lib import BG, Kept, f32v, rows_of, support, table  # noqa: E402

MIN_SOURCES = 300
MAX_DISAGREE = 2
TOL = 0.07
TAGS = (2, 12, 5, 13)
O4_MIN_WORDS = 10
O4_OTHER_MAX = 2
RD_FRAC = 0.9


def f32_hi(v):
    return f32v(v & 0xffff0000)


def source_of(vx, vy, w=64, h=64):
    sx = round(f32_hi(vx) * w / 2 + w / 2 - .5)
    sy = round(f32_hi(vy) * h / 2 + h / 2 - .5)
    return (sx, sy) if 0 <= sx < w and 0 <= sy < h else None


def read_grid(k: Kept, name, w=64, h=64):
    txt = k.out(name)
    g = rows_of(txt or "")
    return g if len(g) == h and all(len(r) == w for r in g) else None


def c_decode(gx, gy, marker=None, w=64, h=64):
    """({tag: {(sx, sy)}}, marker_ok, n_words): the words that pair up between the x and y image (same tag nibble, not background)
    decoded to their source pixel."""
    src = {t: set() for t in TAGS}
    good = bad = 0
    for y in range(h):
        for x in range(w):
            vx, vy = gx[y][x], gy[y][x]
            if BG in (vx, vy) or (vx & 15) != (vy & 15) or (vx & 15) not in TAGS:
                continue
            s = source_of(vx, vy, w, h)
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
    """'x:5' | 'y:4' | 'never' | 'lane:K:A|B' | 'xeq:K' | 'xany:M' | 'xe:K' -> predicate on a source pixel."""
    if rule == "never":
        return lambda sx, sy: False
    p = rule.split(":")
    if p[0] == "x":
        return lambda sx, sy, b=int(p[1]): bool(sx >> b & 1)
    if p[0] == "y":
        return lambda sx, sy, b=int(p[1]): bool(sy >> b & 1)
    if p[0] == "lane":
        return lambda sx, sy, k=int(p[1]), w=p[2]: lane(sx, sy, w) == k
    if p[0] == "xeq":
        return lambda sx, sy, kk=int(p[1]): sx % 32 == kk
    if p[0] == "xany":
        return lambda sx, sy, m=int(p[1]): bool((sx % 32) & m)
    if p[0] == "xe":
        return lambda sx, sy, kk=int(p[1]): sx == kk
    raise ValueError(rule)


def exact(rule):
    return rule.split(":")[0] in ("xeq", "xe")


def disagree(src, rule):
    f = rule_fn(rule)
    return sum(1 for s in src[2] if not f(*s)) + sum(1 for s in src[12] if f(*s))


def n_diff(src, r1, r2):
    f, g = rule_fn(r1), rule_fn(r2)
    return sum(1 for s in src[2] | src[12] if f(*s) != g(*s))


def allowed(src, rule=None):
    """Exceptions a rule may have: 2% of the decoded o1 sources, at least 2 (frozen from S1b's own fit data: c-k0's 6 of 490); an
    exact-column rule: 1."""
    if rule is not None and exact(rule):
        return 1
    return max(MAX_DISAGREE, math.ceil(0.02 * (len(src[2]) + len(src[12]))))


def measure(src):
    n2, n12, n5, n13 = (len(src[t]) for t in (2, 12, 5, 13))
    par = dict(collections.Counter((sx & 1, sy & 1) for sx, sy in src[2]))
    return dict(n2=n2, n12=n12, n5=n5, n13=n13, n=n2 + n12, frac=n2 / (n2 + n12) if n2 + n12 else float("nan"),
                par=par, p5=dict(collections.Counter((sx & 1, sy & 1) for sx, sy in src[5])))


def frac_ok(v, frac):
    if math.isnan(frac):
        return False
    if v.startswith("same"):
        return True
    return abs(frac - float(v)) < TOL


def words(g, tag):
    return sum(1 for r in g for v in r if v != BG and (v & 15) == tag)


def o4_words(gx, gy):
    return dict(x5=words(gx, 5), y5=words(gy, 5), x13=words(gx, 13), y13=words(gy, 13))


def o4_class_words(ow):
    """'5' / "5'" / 'mixed' / None from the tag-5 and tag-5' words of both jobs (at least O4_MIN_WORDS in each job, the other tag
    at most O4_OTHER_MAX)."""
    n5, n13 = min(ow["x5"], ow["y5"]), min(ow["x13"], ow["y13"])
    m5, m13 = max(ow["x5"], ow["y5"]), max(ow["x13"], ow["y13"])
    if n5 >= O4_MIN_WORDS and m13 <= O4_OTHER_MAX:
        return "5"
    if n13 >= O4_MIN_WORDS and m5 <= O4_OTHER_MAX:
        return "5'"
    if n5 >= O4_MIN_WORDS and n13 >= O4_MIN_WORDS:
        return "mixed"
    return None


def class_ok(want, cls):
    if cls is None:
        return None
    return {"5": cls == "5", "5'": cls == "5'", "not5": cls != "5", "not5'": cls != "5'"}[want]


def g_o4_control(ow, meas):
    """The structural G-o4 control (R3-P6): tag-5 words 10..100 in each job (26 runs: 19..50), pairs 5..60 (26 runs: 8..42), every
    pair source (even, even) (571 of 571), tag-5' words <= 2 in the x job.  Returns (ok, why)."""
    why = []
    for k, v in (("x", ow["x5"]), ("y", ow["y5"])):
        if not 10 <= v <= 100:
            why.append(f"tag-5 words in the {k} job {v} (10..100)")
    if not 5 <= meas["n5"] <= 60:
        why.append(f"tag-5 pairs {meas['n5']} (5..60)")
    bad_par = sum(c for key, c in meas["p5"].items() if key != (0, 0))
    if bad_par:
        why.append(f"{bad_par} of {meas['n5']} pair sources are not (even, even)")
    if ow["x13"] > 2:
        why.append(f"tag-5' words in the x job {ow['x13']} (<= 2)")
    return not why, why


def pq(preds, name, q):
    return preds.get(name, {}).get(q, [])


def model_entries(preds, name, src, meas, ow):
    """[(model, set, ok)] for one decoded configuration: every frozen quantity of a model must hold.  ok is True, False, or None
    (void: an o4 class with too few words, or an alternative that cannot be told from M at this row)."""
    res, sets = collections.defaultdict(list), {}
    mrule = next((v for v, m, s in pq(preds, name, "rule") if m.startswith("M")), None)
    for q in ("frac_tag2_of_o1", "rule", "tag2_parity", "o4_class"):
        for v, mdl, st in pq(preds, name, q):
            sets[mdl] = st
            if q == "frac_tag2_of_o1":
                ok = frac_ok(v, meas["frac"])
            elif q == "rule":
                ok = disagree(src, v) <= allowed(src, v)
                if (not mdl.startswith("M") and mrule is not None and "reported apart" not in mdl
                        and n_diff(src, v, mrule) <= allowed(src, v)):
                    ok = None                                    # the alternative cannot be told from M at this row
            elif q == "tag2_parity":
                want = tuple(int(c) for c in v.split(","))
                ok = sum(c for key, c in meas["par"].items() if key != want) <= allowed(src)
            else:
                ok = class_ok(v, o4_class_words(ow))
            res[mdl].append(ok)
    out = []
    for m, oks in res.items():
        ok = False if False in oks else (None if None in oks else True)
        out.append((m, sets[m], ok))
    return out


GROUP = [("o4s", lambda c: c.startswith("c-o4s-")), ("o4", lambda c: c.startswith("c-o4-")),
         ("g23", lambda c: c.startswith("c-g23")), ("g25", lambda c: c.startswith("c-g25")), ("k", lambda c: re.fullmatch(r"c-k\d", c))]


def group_of(cfg):
    for g, f in GROUP:
        if f(cfg):
            return g
    return "other"


def score_p_c3(k: Kept, preds):
    out, void, got, ow = [], [], {}, {}
    names = k.names()
    cfgs = sorted({re.sub(r"-[xy]$", "", n) for n in names if re.search(r"-[xy]$", n) and not n.endswith("-rep")
                   and "-rd" not in n and not n.startswith("c-rd")})
    for cfg in cfgs:
        nx, ny = f"{cfg}-x", f"{cfg}-y"
        vv = k.void(nx) or k.void(ny)
        gx, gy = (None, None) if vv else (read_grid(k, nx), read_grid(k, ny))
        if vv or gx is None or gy is None:
            void.append(cfg)
            out.append(f"{cfg}: NODATA ({vv or 'no 64x64 pixel rows'})")
            continue
        mk = pq(preds, nx, "marker")
        marker = int(mk[0][0], 16) if mk else None
        src, mok, nw = c_decode(gx, gy, marker)
        if mok is False:
            void.append(cfg)
            out.append(f"{cfg}: NODATA (marker proof failed: the program that ran is not the frozen one)")
            continue
        meas = measure(src)
        ow[cfg] = o4_words(gx, gy)
        got[cfg] = dict(src=src, meas=meas, ow=ow[cfg])
    rows = [(c, g["meas"]["n2"], g["meas"]["n12"], f"{g['meas']['frac']:.3f}", f"{g['ow']['x5']}/{g['ow']['y5']}",
             f"{g['ow']['x13']}/{g['ow']['y13']}", g["meas"]["n5"], g["meas"]["par"]) for c, g in got.items()]
    out = ["Q276 (p-c3): o1 tag per source pixel from the x/y pairs (2 = p1 write, 2' = !p1 write); o4 words tag 5 / 5' (x job / y job)",
           table(rows, ["config", "tag 2", "tag 2'", "frac 2", "o4 5 words x/y", "o4 5' words x/y", "5 pairs", "tag 2 by (sx&1, sy&1)"]), ""] + out
    # replicates
    reps = []
    for n in [n for n in names if n.endswith("-x-rep")]:
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
        out.append(f"replicate {n}: tag-2 fraction {r['frac']:.3f} vs {bm['frac']:.3f}, parity {r['par']} vs {bm['par']}: {'same' if same else 'DIFFERENT'}")
    # direct reads, each premise control for its shape
    prem = {}
    for shape, name, (w, h) in (("rd", "c-rd-pa", (64, 64)), ("rdf", "c-rdf-pa", (64, 64)), ("rdf128", "c-rdf128-pa", (128, 128))):
        if f"{name}-x" not in names:
            prem[shape] = None
            continue
        vv = k.void(f"{name}-x") or k.void(f"{name}-y")
        gx, gy = (None, None) if vv else (read_grid(k, f"{name}-x", w, h), read_grid(k, f"{name}-y", w, h))
        if vv or gx is None or gy is None:
            out.append(f"{name}: NODATA ({vv or 'no pixel rows'})")
            prem[shape] = dict(ok=False, why="NODATA")
            continue
        mk = pq(preds, f"{name}-x", "marker")
        written = [(x, y) for y in range(h) for x in range(w) if gx[y][x] != BG and gy[y][x] != BG
                   and (gx[y][x] & 15) == 15 == (gy[y][x] & 15)]
        ident = sum(1 for x, y in written if source_of(gx[y][x], gy[y][x], w, h) == (x, y)) / len(written) if written else 0
        need = float(pq(preds, f"{name}-x", "rd_identity")[0][0])
        prem[shape] = dict(ok=ident >= need and len(written) >= MIN_SOURCES, ident=ident, n=len(written))
        out.append(f"{name}: {len(written)} pixels, o0 = pa0/pa1 decodes to the pixel's own position in {ident:.3f} (frozen >= {need})")
    rd = {}
    for n in names:
        m = re.fullmatch(r"c-(rd|rdf|rdf128)-(g23|g24|g25)", n)
        if not m:
            continue
        w = 128 if m[1] == "rdf128" else 64
        vv = k.void(n)
        g = None if vv else read_grid(k, n, w, w)
        if vv or g is None:
            rd[n] = dict(void=vv or f"no {w}x{w} pixel rows", shape=m[1])
            out.append(f"{n}: NODATA ({rd[n]['void']})")
            continue
        written = [(x, y, g[y][x]) for y in range(w) for x in range(w) if g[y][x] != BG]
        if len(written) < MIN_SOURCES:
            rd[n] = dict(void=f"{len(written)} written pixels", shape=m[1])
            out.append(f"{n}: NODATA ({len(written)} written pixels < {MIN_SOURCES})")
            continue
        fr = lambda f: sum(1 for x, y, v in written if v == f(x, y)) / len(written)
        rd[n] = dict(void=None, shape=m[1], n=len(written), vals={
            "g23:xmod32": fr(lambda x, y: x % 32), "g23:x": fr(lambda x, y: x), "g23:y<<16|x": fr(lambda x, y: y << 16 | x),
            "g23:xmod64": fr(lambda x, y: x % 64), "g24:ymod16": fr(lambda x, y: y % 16), "g24:y": fr(lambda x, y: y),
            "g25:A": fr(lambda x, y: lane(x, y, "A")), "g25:B": fr(lambda x, y: lane(x, y, "B"))},
            common=collections.Counter(v for _, _, v in written).most_common(3))
        out.append(f"{n}: {len(written)} written pixels; " + ", ".join(f"{q} {v:.3f}" for q, v in rd[n]["vals"].items() if q.split(":")[0] == m[2])
                   + f"; most common {rd[n]['common']}")
    # ------------------------------------------------------------------------- group controls (R3-P6: each scopes its group)
    ctl = {}
    for c in ("c-e709", "c-o4-u"):
        if c in got:
            ok_, why = g_o4_control(got[c]["ow"], got[c]["meas"])
            ctl[c] = (ok_, why)
    g_o4 = all(c in ctl and ctl[c][0] for c in ("c-e709", "c-o4-u")) and o4_class_words(got["c-o4-u"]["ow"]) == "5"
    crit = {n[:-2]: float(v) for n, qs in preds.items() if n.endswith("-x") for v, m, s in qs.get("ctl_min_frac", [])}
    g_o1 = bool(crit) and all(c in got and got[c]["meas"]["frac"] >= crit[c] for c in crit)
    g23_reg = False
    if "c-g23r4" in got:
        g23_reg = all(ok for m, s, ok in model_entries(preds, "c-g23r4-x", got["c-g23r4"]["src"], got["c-g23r4"]["meas"], got["c-g23r4"]["ow"]))
    o4s_ctl = "c-o4s-u" in got and o4_class_words(got["c-o4s-u"]["ow"]) == "5'" and ctl.get("c-e709", (False,))[0] is True  # post-run fix C11
    for c, (ok_, why) in ctl.items():
        out.append(f"G-o4 control {c}: {'PASS' if ok_ else 'FAIL ' + str(why)}")
    out.append(f"G-o1 control (c-u, c-u-r2 tag-2 fraction >= {max(crit.values()) if crit else '?'}): "
               + ("PASS " + str({c: round(got[c]['meas']['frac'], 3) for c in crit}) if g_o1 else "FAIL or void " + str({c: (round(got[c]['meas']['frac'], 3) if c in got else None) for c in crit})))
    out.append(f"register-form control c-g23r4: {'PASS' if g23_reg else 'FAIL or void'}; swapped-order control c-o4s-u: {'PASS' if o4s_ctl else 'FAIL or void'}; "
               f"G-o4 overall: {'PASS' if g_o4 else 'FAIL or void'}")
    entries, gate_text, groups_ok = collections.defaultdict(list), [], {}
    need = {"k": g_o1, "g25": g_o1, "g23": g_o1 and g23_reg, "o4": g_o4, "o4s": g_o4 and o4s_ctl}
    why_ = {"k": "G-o1", "g25": "G-o1", "g23": "G-o1 and the register-form control c-g23r4", "o4": "G-o4", "o4s": "G-o4 and the swapped-order control c-o4s-u"}
    for cfg in sorted(got):
        if cfg in ("c-e709", "c-o4-u", "c-u", "c-u-r2", "c-g23r4", "c-o4s-u"):
            continue
        g = group_of(cfg)
        pn = f"{cfg}-x"
        if g not in need:
            continue
        if not need[g]:
            gate_text.append(f"{cfg}: cannot tell (control {why_[g]} failed or void)")
            continue
        if g not in ("o4", "o4s") and got[cfg]["meas"]["n"] < MIN_SOURCES:
            gate_text.append(f"{cfg}: cannot tell ({got[cfg]['meas']['n']} decoded o1 sources < {MIN_SOURCES})")
            continue
        for mdl, st, ok in model_entries(preds, pn, got[cfg]["src"], got[cfg]["meas"], got[cfg]["ow"]):
            entries[g].append((mdl, st, ok))
    for n, same in reps:
        entries["k"].append((f"replicate of {n[:-len('-x-rep')]}", "replicate", same))
    # direct reads
    for n, r in rd.items():
        if r.get("void"):
            continue
        sh = r["shape"]
        key = {"rd": "rd", "rdf": "rdf", "rdf128": "rdf128"}[sh]
        p = prem.get(sh)
        if p is None or not p["ok"]:
            gate_text.append(f"{n}: cannot tell (the premise control {'c-' + sh + '-pa'} failed, void or not run)")
            continue
        for v, mdl, st in pq(preds, n, "rd_value"):
            entries[key].append((mdl, st, r["vals"][v] >= RD_FRAC))
    parts = [f"{g}: {support(es)}" for g, es in entries.items()]
    # the verdict (decision R3-P6/P7): every group control passes, M holds in every CONFIRM and HELD OUT row, each alternative fails
    allm = [(m, s, ok) for es in entries.values() for m, s, ok in es]
    m_rows = [ok for m, s, ok in allm if m.startswith("M")]
    alt_rows = [(m, ok) for m, s, ok in allm if not m.startswith(("M", "replicate")) and "reported apart" not in m]
    expected_m = len({(c, m) for c, qs in preds.items() for q in ("frac_tag2_of_o1", "rule", "tag2_parity", "o4_class", "rd_value")
                      for v, m, st in qs.get(q, []) if m.startswith("M") and st in ("heldout", "repeat")})
    ctl_pass = g_o4 and g_o1 and g23_reg and o4s_ctl and all(p and p["ok"] for p in prem.values())
    ctl_missing = [n for n in ("c-e709", "c-o4-u", "c-u", "c-u-r2", "c-g23r4", "c-o4s-u") if n not in got]
    answered = bool(m_rows) and all(m_rows) and not gate_text and not void and ctl_pass and all(ok is False for m, ok in alt_rows) \
        and all(s for n, s in reps if s is not None) and len(m_rows) == expected_m
    verdict = ("Q276 ANSWERED: not gated on o4; the instance whose lane equals k writes o1 (M holds in every row, every alternative fails where it differs)"
               if answered else
               f"Q276 NOT ANSWERED: M rows {sum(1 for x in m_rows if x)} of {len(m_rows)} hold"
               + (f"; alternatives still consistent or void: {[m for m, ok in alt_rows if ok is not False][:4]}" if any(ok is not False for m, ok in alt_rows) else "")
               + (f"; cannot tell: {len(gate_text)} rows" if gate_text else "") + (f"; void configurations {void}" if void else ""))
    out += gate_text
    out.append("SUMMARY: " + verdict + "; groups: " + "; ".join(parts))
    return "\n".join(out), {"answered": answered, "gate_text": gate_text, "g_o4": g_o4, "g_o1": g_o1, "entries": {g: es for g, es in entries.items()}}
