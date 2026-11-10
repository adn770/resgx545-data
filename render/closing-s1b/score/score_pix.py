"""Scorers of the S1 pixel stages.  Written before the run; frozen with the predictions.  numpy: scratch only.

Same rules as score_geo.py: void first (empty/missing data, rc that is not a result), controls enforced, one `SUMMARY:` line.
"""
from __future__ import annotations

import collections
import math
import pathlib
import re
import sys

import numpy as np

from s1lib import S1, Kept, f32v, outcome, pixel_sha, rows_of, support, table

sys.path.insert(0, str(S1 / "gen"))
BG = 0xDEADBEEF


# ------------------------------------------------------------------------------------------------ depth
def mort(x, y):
    r = 0
    for k, (v, b) in enumerate([(y, 0), (x, 0), (y, 1), (x, 1), (y, 2), (x, 2), (y, 3), (x, 3)]):
        r |= ((v >> b) & 1) << k
    return r | (((x >> 4) & 1) << 8)


def depth_image(raw, w, h):
    tw = (w + 31) // 32
    idx = np.array([[512 * ((y // 16) * tw + x // 32) + mort(x % 32, y % 16) for x in range(w)] for y in range(h)])
    return np.frombuffer(raw, dtype="<u4")[idx]


def ulp32(a):
    return 2.0 ** (np.floor(np.log2(np.abs(a))) - 23)


def grad_bounds(w, u, s):
    """The gradient range such that some T0 satisfies w_i <= T0 + g s_i < w_i + u_i (depth_drift.py grad_bounds)."""
    ds = s[None, :] - s[:, None]
    num = (w[None, :] + u[None, :]) - w[:, None]
    pos, neg = ds > 0, ds < 0
    hi = np.min(num[pos] / ds[pos]) if pos.any() else np.inf
    lo = np.max(num[neg] / ds[neg]) if neg.any() else -np.inf
    return lo, hi


CLEAR = 0x3F800000        # the clear depth 1.0 the ZLS stores where the triangle is not


def row_ranges(z, axis="x", minpix=48):
    # S1b fix (S1 analysis, score_pix.py:49): the cleared 1.0 is not a covered pixel
    cov = (z != BG) & (z != 0) & (z != CLEAR)
    zf = z.view(np.float32).astype(np.float64)
    out = []
    for k in range(z.shape[0] if axis == "x" else z.shape[1]):
        m = cov[k] if axis == "x" else cov[:, k]
        if m.sum() < minpix:
            continue
        w = zf[k][m] if axis == "x" else zf[:, k][m]
        s = np.arange(z.shape[1] if axis == "x" else z.shape[0])[m] + 0.5
        lo, hi = grad_bounds(w, ulp32(w), s)
        out.append((k, lo, hi))
    return out


def row_range(z, axis="x", minpix=48):
    """(lo, hi, rows used, rows total, first row that empties the joint range) or None (no row with minpix pixels).
    E731's rows 99 to 127 differ by one ulp from row 0 (ties of a finer internal value): a prefix may be feasible when the
    joint over all rows is empty.  used == 0 means even the first row is infeasible (EMPTY)."""
    rr = row_ranges(z, axis, minpix)
    if not rr:
        return None
    lo, hi, used, bad = -np.inf, np.inf, 0, None
    for k, l, h in rr:
        if l >= h:                       # a single row already infeasible
            bad = k
            break
        if max(lo, l) >= min(hi, h):
            bad = k
            break
        lo, hi, used = max(lo, l), min(hi, h), used + 1
    return lo, hi, used, len(rr), bad


def echoed_ok(k, n):
    """The tool echoes 'tri: vertices256 X0 Y0 X1 Y1 X2 Y2, depth a b c': the knob proof of --tri-v / --tri-z."""
    t = k.out(n) or ""
    m = re.search(r"tri: vertices256 (\S+ \S+ \S+ \S+ \S+ \S+)", t)
    v = re.search(r"--tri-v (\S+)", k.case(n).get("args", ""))
    return bool(m and v and [int(x.rstrip(",")) for x in m[1].split()] == [int(x) for x in v[1].split(",")])


def depth_void(k, n, render=1):
    v = k.void(n)
    if v:
        return v
    if k.depth(n, render) is None:
        return "no depth dump"
    if not echoed_ok(k, n):
        return "the tool's echoed vertices differ from the table"
    return None


# ------------------------------------------------------------------------------------------------ B1
def score_b1(k: Kept, preds, size=(1024, 32)):
    rows, res, rules_in = [], {}, collections.defaultdict(dict)
    for n in k.names():
        v = depth_void(k, n)
        if v:
            res[n] = dict(status="NODATA: " + v)
            rows.append((n, "NODATA: " + v, "", "", ""))
            continue
        rr = row_range(depth_image(k.depth(n), *size))
        if rr is None:
            res[n] = dict(status="NODATA: no row with 48 covered pixels")
            rows.append((n, res[n]["status"], "", "", ""))
            continue
        lo, hi, used, nall, bad = rr
        A = float(next(x for x, m, s in preds[n]["A_exact"]))
        u = 2.0 ** (math.floor(math.log2(A)) - 23)
        if used == 0:
            st = "EMPTY"
        elif bad is not None:
            st = "PREFIX-ONLY"                       # a later row empties the joint range: cannot tell for this job
        elif (hi - lo) / u > 4:
            st = "WIDE"
        else:
            st = "ok"
        inside = {m for x, m, s in preds[n]["rule_word"] if st != "EMPTY" and lo <= f32v(int(x, 16)) < hi}
        for x, m, s in preds[n]["rule_word"]:
            rules_in[m][n] = m in inside
        res[n] = dict(status=st, inside=inside)
        rows.append((n, f"{used}/{nall}" + (f" (row {bad} empties)" if bad is not None else ""),
                     f"[{lo:.10e}, {hi:.10e}]" if used else "-", f"{(hi - lo) / u:.2f}" if used else "-", f"{st}: " + " ".join(sorted(inside))))
    out = ["B1: joint gradient range over the rows; width in float32 ulps of A; rules whose word lies inside",
           table(rows, ["job", "rows used", "range of g", "width (ulps)", "status: rules inside"]), ""]
    ok = lambda n: res.get(n, {}).get("status") == "ok"
    ramps = [f"g-r{i}" for i in (2, 4, 6, 7, 9, 11, 12, 13)]
    ctl = res.get("g-ctl", {})
    ctl_good = ok("g-ctl") and "T16" in ctl["inside"] and "f32" not in ctl["inside"]
    dy_good = ok("g-dyadic") and "f32" in res["g-dyadic"]["inside"]
    if not ctl_good or not dy_good:
        out.append(f"SUMMARY: cannot tell: controls failed or unusable (g-ctl: {ctl.get('status')}, T16 inside and f32 outside "
                   f"required; g-dyadic: {res.get('g-dyadic', {}).get('status')}, f32 inside required)")
        return "\n".join(out), res
    miss = [n for n in ramps if not ok(n)]
    if miss:
        out.append(f"SUMMARY: cannot tell: ramps not usable (void, EMPTY, prefix-only or wide): {miss}")
        return "\n".join(out), res
    if "g-r2-rep" in res and k.depth("g-r2") != k.depth("g-r2-rep"):
        out.append("SUMMARY: cannot tell: g-r2-rep differs from g-r2 (not deterministic)")
        return "\n".join(out), res
    allin = sorted(m for m in rules_in if all(rules_in[m].get(n) for n in ramps))
    if len(allin) == 1:
        out.append(f"SUMMARY: the gradient rule is {allin[0]}: inside on 8 of 8 ramps, every other rule outside on at least one")
    elif len(allin) > 1:
        out.append(f"SUMMARY: the ramps did not split the rules {allin} (all inside on 8 of 8): add ramps")
    else:
        out.append("SUMMARY: no rule is inside on all 8 ramps: the gradient is not a function of A alone (read the x-dependence)")
    return "\n".join(out), res


# ------------------------------------------------------------------------------------------------ B2
def parse_depth_job(n, cases):
    c = next(c for c in cases if c["name"] == n)["args"]
    w, h = int(re.search(r"--width (\d+)", c)[1]), int(re.search(r"--height (\d+)", c)[1])
    v = [int(x) for x in re.search(r"--tri-v (\S+)", c)[1].split(",")]
    z = [float(x) for x in re.search(r"--tri-z (\S+)", c)[1].split(",")]
    return w, h, [(v[0], v[1]), (v[2], v[3]), (v[4], v[5])], z


def score_b2(k: Kept, preds):
    from b2model import deviation
    sets = {nm: np.unpackbits(np.frombuffer((S1 / "predictions" / f"p-b2-set-{nm}.bits").read_bytes(), dtype=np.uint8))
            [:128 * 256].reshape(128, 256).astype(bool) for nm in ("ctl", "ht_shift", "hv_shift")}
    rows, devs, void = [], {}, []
    for n in k.names():
        v = depth_void(k, n)
        if v:
            void.append(n)
            rows.append((n, "NODATA: " + v, "", ""))
            continue
        w, h, V, Z = parse_depth_job(n, k.cases)
        d, cov = deviation(k.depth(n), w, h, V, Z)
        if not cov.any():
            void.append(n)
            rows.append((n, "NODATA: no covered pixel", "", ""))
            continue
        dev = (d != 0) & cov
        devs[n] = dev
        vals, cnt = np.unique(d[cov], return_counts=True)
        per = [int(dev[16 * t:16 * t + 16].sum()) for t in range(h // 16)]
        ys = [y for y in range(h) if dev[y].any()]
        line = "-"
        if len(ys) > 2:
            c1, c0 = np.polyfit(ys, [int(np.nonzero(dev[y])[0].min()) for y in ys], 1)
            line = f"xmin = {c0:.2f} {c1:+.3f} y"
        rows.append((n, {int(a): int(b) for a, b in zip(vals, cnt) if a}, per[:12], line))
    out = ["B2: stored - trunc32(exact) in float32 ulps; per tile row counts; boundary line",
           table(rows, ["job", "deviations (ulps: pixels)", "per tile row", "boundary line"]), ""]
    if "d-ctl" not in devs or not np.array_equal(devs["d-ctl"], sets["ctl"]):
        out.append("SUMMARY: cannot tell: control d-ctl void or does not reproduce dp-ax-b2 (7680 at -1, 1536 at -2, same set)")
        return "\n".join(out), {}
    if "d-shift" not in devs:
        out.append("SUMMARY: cannot tell: d-shift void or missing")
        return "\n".join(out), {}
    o = devs["d-shift"]
    j = {lab: (o & sets[lab]).sum() / max(1, (o | sets[lab]).sum()) for lab in ("ht_shift", "hv_shift")}
    out.append(f"d-shift observed vs HT set: Jaccard {j['ht_shift']:.3f}; vs HV set: {j['hv_shift']:.3f}")
    if j["ht_shift"] > 0.9 and j["hv_shift"] < 0.5:
        s = "HT: the region is fixed in target coordinates (does not move with the triangle)"
    elif j["hv_shift"] > 0.9 and j["ht_shift"] < 0.5:
        s = "HV: the region moves with the triangle by (64, 32)"
    else:
        s = "cannot tell: d-shift matches neither set (Jaccard above)"
    out.append(f"SUMMARY: control reproduces dp-ax-b2; {s}" + (f"; void jobs {void}" if void else ""))
    return "\n".join(out), {}


# ------------------------------------------------------------------------------------------------ C
def f32_hi(v):
    return f32v(v & 0xffff0000)


def read_pairs(kx: Kept, nx, ny):
    gx, gy = rows_of(kx.out(nx) or ""), rows_of(kx.out(ny) or "")
    if not gx or not gy:
        return None
    return np.array(gx, dtype=np.int64), np.array(gy, dtype=np.int64)


def _frac_ok(v, frac):
    if math.isnan(frac):
        return False
    if v == "0|1":
        return frac in (0.0, 1.0)
    if v.startswith("same"):
        return True
    return abs(frac - float(v)) < 0.07


def c_tags(gx, gy):
    """{(tag, sx, sy)} of one x/y pair: tag 2 (p1 write), 12 (the !p1 write, 2'), 5 (o4), by source pixel."""
    H, W = gx.shape
    tags = {}
    for y in range(H):
        for x in range(W):
            vx, vy = int(gx[y, x]), int(gy[y, x])
            if 0xff203040 in (vx, vy) or (vx & 15) != (vy & 15) or (vx & 15) not in (2, 12, 5):
                continue
            sx, sy = round(f32_hi(vx) * W / 2 + W / 2 - .5), round(f32_hi(vy) * H / 2 + H / 2 - .5)
            if 0 <= sx < W and 0 <= sy < H:
                tags[(vx & 15, sx, sy)] = 1
    return tags


def c_measure(tags):
    n2 = sum(1 for t in tags if t[0] == 2)
    n12 = sum(1 for t in tags if t[0] == 12)
    n5 = sum(1 for t in tags if t[0] == 5)
    frac = n2 / (n2 + n12) if n2 + n12 else float("nan")
    par = dict(collections.Counter((sx & 1, sy & 1) for t, sx, sy in tags if t == 2))
    first = sorted((sx, sy) for t, sx, sy in tags if t == 12)
    return dict(frac=frac, n5=n5, n=n2 + n12, n2=n2, n12=n12, par=par, first=first)


def score_c(k: Kept, preds):
    """C.  S1b fixes (S1 analysis): the replicate (NAME-x-rep: another run of NAME-x) is decoded with NAME-y and
    compared, never dropped (score_pix.py:241); the order controls (c-u, every run) pass by the FROZEN criterion
    `ctl_min_frac` (S1b: >= 0.98, S1 had exact 1.0, score_pix.py:271); a model with `tag2_parity` must also put every
    tag-2 source at that (sx & 1, sy & 1)."""
    rows, got, void, reps = [], {}, [], []
    cfgs = sorted({re.sub(r"-[xy]$", "", n) for n in k.names() if not n.endswith("-rep")})
    for cfg in cfgs:
        nx, ny = f"{cfg}-x", f"{cfg}-y"
        vv = k.void(nx) or k.void(ny)
        pr = None if vv else read_pairs(k, nx, ny)
        if vv or pr is None or pr[0].shape != (64, 64):
            void.append(cfg)
            rows.append((cfg, "NODATA: " + (vv or "no 64x64 pixel rows")))
            continue
        got[cfg] = c_measure(c_tags(*pr))
        g = got[cfg]
        rows.append((cfg, g["n2"], g["n12"], f"{g['frac']:.3f}", g["n5"], g["par"]))
    out = ["C: o1 tag per source pixel from the x/y pairs: tag 2 = p1 true write, 2' = the !p1 write",
           table(rows, ["config", "tag 2", "tag 2'", "frac 2", "tag 5 pairs", "tag 2 by (sx&1, sy&1)"]), ""]
    for n in [n for n in k.names() if n.endswith("-x-rep")]:
        base = n[:-len("-x-rep")]
        vv = k.void(n) or k.void(f"{base}-x") or k.void(f"{base}-y")
        pr = None if vv else read_pairs(k, n, f"{base}-y")
        if vv or pr is None or pr[0].shape != (64, 64) or base not in got:
            reps.append((n, None))
            out.append(f"replicate {n}: NODATA ({vv or 'no pixels or no base'})")
            continue
        r = c_measure(c_tags(*pr))
        bx = np.array(rows_of(k.out(f"{base}-x")), dtype=np.int64)
        ndiff = int((bx != pr[0]).sum())
        same = abs(r["frac"] - got[base]["frac"]) < 0.07 if not (math.isnan(r["frac"]) or math.isnan(got[base]["frac"])) \
            else math.isnan(r["frac"]) and math.isnan(got[base]["frac"])
        reps.append((n, same))
        out.append(f"replicate {n}: {ndiff} dwords differ from {base}-x; tag-2 fraction {r['frac']:.3f} vs "
                   f"{got[base]['frac']:.3f} ({'same' if same else 'DIFFERENT'} within 0.07)")
    for cfg in got:
        for v, m, s in preds.get(f"{cfg}-x", {}).get("first_write_sources", []):
            want = sorted(tuple(int(c) for c in p.strip("()").split(",")) for p in v.split(";"))
            out.append(f"{cfg}: sources keeping the first write {got[cfg]['first']}: "
                       f"{'the' if got[cfg]['first'] == want else 'NOT the'} cluster of {m}")
    e = got.get("c-e709")
    # S1b review: the criterion covers EVERY config with a frozen ctl_min_frac, run or not (a missing one is void)
    crit = {n[:-2]: float(v) for n, qs in preds.items() if n.endswith("-x")
            for v, m, s in qs.get("ctl_min_frac", [])}
    if not crit and "c-u" in got:
        crit["c-u"] = 1.0                       # S1's tables carry no criterion: S1's exact 1.0
    us = {c: got[c]["frac"] if c in got else "void or not run" for c in crit}
    if not e or not (17 <= e["n5"] <= 29) or not crit or any(c not in got or not (us[c] >= crit[c]) for c in crit):
        out.append(f"SUMMARY: cannot tell: controls failed or void (c-e709 tag-5 pairs 17..29: {e and e['n5']}; "
                   f"order controls (frozen minimum {crit}): {us}); void {void}")
        return "\n".join(out), {}
    entries, voidc = [], []
    held = sorted({n[:-2] for n, qs in preds.items() if n.endswith("-x") and "frac_tag2_of_o1" in qs
                   and any(s in ("heldout", "repeat") for v, m, s in qs["frac_tag2_of_o1"])})
    for cfg in held:
        if cfg not in got or got[cfg]["n"] == 0:
            voidc.append(cfg)
            continue
        par = {m: v for v, m, s in preds.get(f"{cfg}-x", {}).get("tag2_parity", [])}
        for v, m, s in preds.get(f"{cfg}-x", {}).get("frac_tag2_of_o1", []):
            ok = _frac_ok(v, got[cfg]["frac"])
            if m in par:
                want = par[m]
                keys = set(got[cfg]["par"])
                ok = ok and (keys == set() if want == "none" else keys == {tuple(int(c) for c in want.split(","))})
            entries.append((m, s, ok))
    # a model is consistent if it holds on every guard job it predicts (it need not predict all: HQ has no g23
    # value); support from `repeat` jobs (S1's post-hoc fits run again) is printed apart from held-out support
    rep = "" if not reps else "; replicates " + ", ".join(f"{n} {'same' if s else 'void' if s is None else 'DIFFERENT'}" for n, s in reps)
    if voidc:
        out.append(f"SUMMARY: cannot tell: configurations void or without o1 landings: {voidc}{rep}")
    else:
        out.append(f"SUMMARY: controls pass; {support(entries)}{rep}")
    return "\n".join(out), {}


# ------------------------------------------------------------------------------------------------ G
def score_g(k: Kept, preds):
    rows, trans, firsts, void = [], {}, {}, []
    for n in k.names():
        v = k.void(n)
        img = rows_of(k.out(n) or "") if not v else []
        if v or not img:
            void.append(n)
            rows.append((n, "NODATA: " + (v or "no pixels")))
            continue
        r0 = img[0]
        trans[n] = [c for c in range(1, len(r0)) if r0[c] != r0[c - 1]]
        pe = next((int(x) for x, m, s in preds.get(n, {}).get("exact_crossing_col", [])), None)
        ctl = [x for x, m, s in preds.get(n, {}).get("pix_sha256", [])]
        firsts[n] = (trans[n][0] - pe) if trans[n] and pe is not None else None
        rows.append((n, trans[n][:8], pe, firsts[n] if firsts[n] is not None else "-",
                     ("sha " + ("MATCH" if ctl[0] == pixel_sha(img) else "DIFF")) if ctl else ""))
    out = ["G: row-0 transitions along the ladder (u, v constant): first change vs exact crossing (1 column = 1/2048 step)",
           table(rows, ["job", "transition columns", "exact crossing", "first - exact", "control"]), ""]
    ctl = k.names() and "g-ctl-lf-r8" in trans and pixel_sha(rows_of(k.out("g-ctl-lf-r8"))) == [x for x, m, s in preds["g-ctl-lf-r8"]["pix_sha256"]][0]
    if not ctl:
        out.append("SUMMARY: cannot tell: control g-ctl-lf-r8 void or its image sha256 differs from E721's")
        return "\n".join(out), {}
    lad = [n for n in k.names() if n.startswith("g-s")]
    bad = [n for n in lad if n not in firsts or firsts[n] is None]
    if bad:
        out.append(f"SUMMARY: cannot tell: ladders void or without a transition (measured nothing): {bad}")
        return "\n".join(out), {}
    rep = [n for n in lad if n.endswith("-r2")]
    if any(trans[n] != trans[n[:-3]] for n in rep if n[:-3] in trans):
        out.append("SUMMARY: cannot tell: a replicate differs (not deterministic)")
        return "\n".join(out), {}
    worst = max(abs(v) for v in firsts.values())
    out.append(f"SUMMARY: control reproduces E721; largest |first - exact| = {worst} columns = {worst / 2048:.4f} of a 1/64 step: "
               + ("H13 holds (within +-40 columns)" if worst <= 40 else "H13 refuted (a larger offset)"))
    return "\n".join(out), {}


# ------------------------------------------------------------------------------------------------ D
def score_d(k: Kept, preds):
    rows, res, void = [], {}, []
    for n in k.names():
        v = k.void(n)
        if v:
            void.append(n)
            rows.append((n, "NODATA: " + v))
            continue
        txt = k.out(n)
        m = re.search(r"scratch at 0x[0-9a-f]+ \((\d+) KiB\)", txt)
        want = [x for x, mm, s in preds.get(n, {}).get("scratch_line", [])]
        if not m or not want or f"({m[1]} KiB)" != want[0]:
            void.append(n)
            rows.append((n, f"NODATA: scratch line {m and m[1]} KiB, wanted {want}"))
            continue
        oc = k.case(n).get("class", "ok")
        sha = pixel_sha(rows_of(txt)) if oc == "ok" else None
        a4 = [x for x, mm, s in preds.get(n, {}).get("pix_sha256_if_complete", [])]
        if oc == "ok" and not rows_of(txt):
            void.append(n)
            rows.append((n, "NODATA: completed without pixels"))
            continue
        res[n] = (oc, sha == a4[0] if sha and a4 else None)
        fw = re.search(r"0x9[0-9a-f]{4}", k.dmesg(n))
        rows.append((n, m[1], oc, "A4 exact" if res[n][1] else ("DIFF" if sha else "-"), fw[0] if fw else "-"))
    out = ["D: scratch pages (the probe's own 'scratch at ... (N KiB)' line is the knob proof)",
           table(rows, ["job", "KiB", "class", "pixels vs A4", "fault word"]), ""]
    if res.get("d-ok-64") != ("ok", True) or res.get("d-L2e2-16", ("",))[0] != "fault":
        out.append(f"SUMMARY: cannot tell: controls failed or void (d-ok-64 must complete A4 exact: {res.get('d-ok-64')}; "
                   f"d-L2e2-16 must fault as in E722: {res.get('d-L2e2-16')})")
        return "\n".join(out), {}
    big = ["d-L2e2-64", "d-L3e3-64", "d-st-L3e2-64"]
    if any(n not in res for n in big + ["d-L2e2-20", "d-L2e2-21"]):
        out.append(f"SUMMARY: cannot tell: jobs void or skipped (a group stopped after its fault limit): {void}")
        return "\n".join(out), {}
    if all(res[n] == ("ok", True) for n in big):
        b = res["d-L2e2-20"][0] == "fault"
        out.append("SUMMARY: HB: the three extents complete and fit A4 at 64 pages; 80 KiB " + ("faults" if b else "does NOT fault (the limit is not the buffer's end)")
                   + f"; 84 KiB {res['d-L2e2-21'][0]}")
    elif all(res[n][0] == "fault" for n in big):
        out.append("SUMMARY: HX: the extents fault again at 64 pages (another limit; the fault word is the new fact)")
    else:
        out.append(f"SUMMARY: cannot tell: mixed outcomes {({n: res[n] for n in big})}")
    return "\n".join(out), {}


def load_a4(path=None):
    p = pathlib.Path(path) if path else S1 / "predictions" / "p-d-A4.tsv"
    out = {}
    for ln in p.read_text().splitlines()[1:]:
        n, lab, pg, px = ln.split("\t")
        out[n] = (int(pg), [int(v, 16) for v in px.split(",")])
    return out


def score_d_s1b(k: Kept, preds, a4=None):
    """S1b D: per job the knob proof (the probe's own scratch line), the outcome, and the pixels against A4 rendered at
    the job's OWN pages (predictions/p-d-A4.tsv): exact on every pixel, on the in-scratch pixels (the model's non-OOB
    ones), and how many of the rest carry the fill's 0xD tag.  Controls from the frozen control rows (outcome and, if
    frozen, the A4 hash).  Hypotheses: those whose outcome (and, for HB-A4, A4 exact) holds on every held-out job."""
    a4 = a4 if a4 is not None else load_a4()
    rows, res, void = [], {}, []
    for n in k.names():
        v = k.void(n)
        txt = k.out(n) or ""
        m = re.search(r"scratch at 0x[0-9a-f]+ \((\d+) KiB\)", txt)
        want = [x for x, mm, s in preds.get(n, {}).get("scratch_line", [])]
        if not v and (not m or not want or f"({m[1]} KiB)" != want[0]):
            v = f"scratch line {m and m[1]} KiB, wanted {want}"
        if v:
            void.append(n)
            rows.append((n, "NODATA: " + v))
            continue
        oc = k.case(n).get("class", "ok")
        fw = re.search(r"BIF fault (0x[0-9a-f]+)", k.dmesg(n) + txt)
        if oc == "fault":
            res[n] = dict(outcome="fault " + (fw[1] if fw else "?"))
            rows.append((n, m[1], res[n]["outcome"], "-", "-", "-"))
            continue
        if oc != "ok":
            res[n] = dict(outcome=oc)
            rows.append((n, m[1], oc, "-", "-", "-"))
            continue
        px = [x for r in rows_of(txt) for x in r]
        if n not in a4 or len(px) != len(a4[n][1]):
            void.append(n)
            rows.append((n, f"NODATA: {len(px)} pixels, model {len(a4.get(n, (0, []))[1])}"))
            continue
        model = a4[n][1]
        ins = [i for i, x in enumerate(model) if x != OOB_MODEL]
        exact_all = px == model
        exact_in = all(px[i] == model[i] for i in ins)
        tagged = sum(1 for i, x in enumerate(model) if x == OOB_MODEL and px[i] >> 28 == 0xD)
        res[n] = dict(outcome="complete", exact=exact_all, exact_in=exact_in, nin=len(ins), tagged=tagged,
                      sha=pixel_sha([px]))
        rows.append((n, m[1], "complete", "A4 exact" if exact_all else ("in-scratch exact" if exact_in else "DIFF"),
                     f"{len(ins)} in scratch", f"{tagged} of {len(model) - len(ins)} past it 0xD-tagged"))
    out = ["D: scratch pages (the probe's 'scratch at ... (N KiB)' line is the knob proof); pixels vs A4 at the job's pages",
           table(rows, ["job", "KiB", "outcome", "pixels vs A4", "model pixels", "past the scratch"]), ""]
    bad = []
    for n, qs in preds.items():
        for v, mm, s in qs.get("outcome", []):
            if s != "control":
                continue
            r = res.get(n)
            ok = r is not None and r["outcome"].startswith(v)
            h = [x for x, m2, s2 in qs.get("pix_sha256_if_complete", [])]
            if ok and h and v == "complete":
                ok = r.get("exact", False)
            if not ok:
                bad.append(n)
    if bad:
        out.append(f"SUMMARY: cannot tell: controls failed or void {bad}: { {n: res.get(n) and res[n]['outcome'] for n in bad} }")
        return "\n".join(out), res
    entries = []
    for n, qs in preds.items():
        for v, mm, s in qs.get("outcome", []):
            if s == "control":
                continue
            r = res.get(n)
            if r is None:
                entries.append((mm, s, None))
                continue
            ok = r["outcome"].startswith(v)
            if ok and v == "complete" and mm.startswith("HB-A4"):
                ok = r.get("exact", False)
            entries.append((mm, s, ok))
    rep = res.get("d-L2e2-20", {})
    out.append(f"SUMMARY: controls pass; {support(entries)}"
               + (f"; d-L2e2-20 (past the scratch) image sha {rep['sha'][:16]}" if rep.get("sha") else ""))
    return "\n".join(out), res


OOB_MODEL = 0xDEADBEEF


def score_b2_s1b(k: Kept, preds):
    """S1b B2: deviation maps (stored - trunc32(exact), the clear 1.0 excluded), compared inside the 256 x 128 window
    with the frozen sets (HT, HV), and HCLIP read from each job's own PB dump: the job deviates iff its stored object
    is not the original triangle (a clipped polygon); and jobs whose stored polygons are equal deviate alike."""
    from b2model import deviation
    sets = {nm: np.unpackbits(np.frombuffer((S1 / "predictions" / f"p-b2-set-{nm}.bits").read_bytes(), dtype=np.uint8))
            [:128 * 256].reshape(128, 256).astype(bool) for nm in ("ctl", "ht_shift", "hv_shift")}
    import score_geo as G
    rows, devs, polys, covs, void = [], {}, {}, {}, []
    for n in k.names():
        v = depth_void(k, n)
        if not v and (k.dump(n, "param.bin") is None or k.dump(n, "tadata.bin") is None):
            v = "no PB dump"
        if v:
            void.append(n)
            rows.append((n, "NODATA: " + v, "", "", ""))
            continue
        w, h, V, Z = parse_depth_job(n, k.cases)
        d, cov = deviation(k.depth(n), w, h, V, Z)
        o = G.decode_object(k.dump(n, "param.bin"), k.dump(n, "tadata.bin"))
        if not cov.any() or o.get("state") != "present":
            void.append(n)
            rows.append((n, "NODATA: " + ("no covered pixel" if not cov.any() else f"object {o.get('state')}"), "", "", ""))
            continue
        dev = (d != 0) & cov
        devs[n], covs[n] = dev, cov
        orig = sorted((x / 256, y / 256) for x, y in V)
        stored = sorted((round(x, 4), round(y, 4)) for x, y in G._xy(o))
        polys[n] = (tuple(stored), stored != orig)
        vals, cnt = np.unique(d[cov], return_counts=True)
        rows.append((n, {int(a): int(b) for a, b in zip(vals, cnt) if a}, int(dev.sum()),
                     f"{len(stored)} vertices{' (clipped)' if polys[n][1] else ' (original)'}", stored[:5]))
    out = ["B2: stored - trunc32(exact) in float32 ulps (clear 1.0 excluded); the stored polygon from the PB dump",
           table(rows, ["job", "deviations (ulps: pixels)", "deviating", "stored object", "vertices (pixels)"]), ""]
    ctl = [n for n, qs in preds.items() if any(s == "control" for vv in qs.values() for x, m, s in vv)]
    bad = [n for n in ctl if n not in devs or not np.array_equal(devs[n][:128, :256], sets["ctl"])]
    if bad:
        out.append(f"SUMMARY: cannot tell: control(s) {bad} void or not dp-ax-b2's region (7680 at -1, 1536 at -2)")
        return "\n".join(out), {}
    entries = []
    jobset = {n: next((s for vv in qs.values() for x, m, s in vv), "heldout") for n, qs in preds.items()}
    for n, qs in preds.items():
        if n in ctl:
            continue
        if n not in devs:
            for vv in qs.values():
                for x, m, s in vv:
                    entries.append((m, s, None))
            continue
        win = devs[n][:128, :256] & covs[n][:128, :256]
        for x, m, s in qs.get("dev_set_window", []):
            want = sets[x] & covs[n][:128, :256]
            entries.append((m, s, bool(np.array_equal(win, want))))
        for x, m, s in qs.get("dev_iff_clipped", []):
            entries.append((m, s, bool(devs[n].any()) == polys[n][1]))
        for x, m, s in qs.get("dev_pixels", []):
            entries.append((m, s, int(devs[n].sum()) == int(x)))
    # HCLIP's second clause: equal stored polygons, equal maps on the shared window (held out unless both are repeats)
    same = collections.defaultdict(list)
    for n in devs:
        same[polys[n][0]].append(n)
    hclip = sorted({m for m, s, o in entries if m.startswith("HCLIP")})
    for poly, ns in same.items():
        for a, b in zip(ns, ns[1:]):
            ok = bool(np.array_equal(devs[a][:128, :256], devs[b][:128, :256]))
            out.append(f"same stored polygon: {a} and {b}: maps {'equal' if ok else 'DIFFER'} in the 256 x 128 window")
            st = "repeat" if {jobset.get(a), jobset.get(b)} <= {"repeat", "control"} else "heldout"
            entries += [(m, st, ok) for m in hclip]
    out.append(f"SUMMARY: control reproduces dp-ax-b2; {support(entries)}" + (f"; void jobs {void}" if void else ""))
    return "\n".join(out), {}


# ------------------------------------------------------------------------------------------------ F
def renders_exact(txt, args):
    """Every render of a tri job exact: `tri: N renders ok`, or under --keep-overflow `tri: K of N renders ok, M
    overflowed` with K + M = N (S1b fix, S1 analysis score_pix.py:394: S1 accepted only the first form, so two exact
    partial-render runs became 'split'); and every `diff:` line 0, one per render."""
    n = int(m[1]) if (m := re.search(r"-n (\d+)", args)) else 1
    ok = re.search(r"^tri: (\d+) renders ok", txt, re.M)
    part = re.search(r"^tri: (\d+) of (\d+) renders ok, (\d+) overflowed", txt, re.M)
    diffs = re.findall(r"^diff: (\d+) of", txt, re.M)
    whole = bool(ok and int(ok[1]) == n) or bool(part and "--keep-overflow" in args and int(part[2]) == n
                                                  and int(part[1]) + int(part[3]) == n)
    return whole and len(diffs) == n and all(d == "0" for d in diffs)


def score_f(k: Kept, preds):
    """F.  S1b fixes: exact under partial renders (renders_exact); two faults read as HJ (a pair needed together) only
    when the mask leaves buffer 0 in (S1 analysis, score_pix.py:413-414: mask 0x1f faulted with buffer 0's own fault);
    controls from the frozen control rows (outcome), every run of a control condition."""
    rows, by, void, masks = [], collections.defaultdict(list), [], {}
    klog = (k.d / "kernel.log").read_text(errors="replace") if (k.d / "kernel.log").exists() else ""
    rb = dict(re.findall(r"resgx545 s1b? readback (\S+) alias_skip=(\S+)", klog))
    for n in k.names():
        v = k.void(n)
        mask = re.search(r"alias_skip=(\S+)", k.case(n).get("knobs", ""))
        if not v and mask and not (rb.get(n) and int(rb[n], 16) == int(mask[1], 16)):
            v = "no alias_skip read-back marker (knob not proven)"
        if v:
            void.append(n)
            rows.append((n, "NODATA: " + v, ""))
            continue
        txt = k.out(n)
        oc = k.case(n).get("class", "ok")
        fw = re.findall(r"0x[89d][0-9a-f]{4}", k.dmesg(n))
        if oc == "fault":
            res = "fault " + fw[0] if fw else "fault"
        elif oc == "ok" and renders_exact(txt, k.case(n).get("args", "")):
            res = "exact"
        else:
            res = oc
        c = re.sub(r"-r\d$", "", n)
        by[c].append(res)
        masks[c] = int(mask[1], 16) if mask else 0
        rows.append((n, oc, res))
    out = ["F: alias_skip masks (HI: a buffer is needed only if leaving it out alone faults; HJ: a pair is needed together)",
           table(rows, ["job", "class", "result"]), ""]
    ctl = collections.defaultdict(set)
    for n, qs in preds.items():
        for v, m, s in qs.get("outcome", []):
            if s == "control":
                ctl[re.sub(r"-r\d$", "", n)].add(v)
    bad = {c: by.get(c) for c, v in ctl.items() if len(v) != 1 or not by.get(c) or any(r != next(iter(v)) for r in by[c])}
    if not ctl or bad:
        out.append(f"SUMMARY: cannot tell: controls failed or void ({bad}, wanted { {c: sorted(v) for c, v in ctl.items()} }); void {void}")
        return "\n".join(out), {}
    res, rep = [], []
    cset = {}
    for n, qs in preds.items():
        for v_, m, s in qs.get("outcome", []):
            cset.setdefault(re.sub(r"-r\d$", "", n), set()).add(s)
    skipped = {re.sub(r"-r\d$", "", n) for n in k.names() if k.case(n).get("class") == "skipped"}
    for c, v in by.items():
        if c in ctl:
            continue
        dst = rep if cset.get(c) and cset[c] <= {"repeat"} else res    # S1's post-hoc fits run again: apart
        if len(v) < 2 and not (v and v[0].startswith("fault") and c in skipped):
            dst.append(f"{c}: cannot tell (a run void or skipped)")
        elif len(v) == 1:
            dst.append(f"{c}: {v[0]} 1 of 1, the replicate skipped by the hypothesis limit"
                       + (" (mask includes buffer 0: not a pair test)" if masks.get(c, 0) & 1 else " (HJ, one run)"))
        elif all(r == "exact" for r in v):
            dst.append(f"{c}: exact {len(v)} of {len(v)}")
        elif all(r.startswith("fault") for r in v) and len(set(v)) == 1:
            dst.append(f"{c}: {v[0]} {len(v)} of {len(v)} " + ("(mask includes buffer 0: buffer 0's own fault, not a pair test)"
                                                              if masks.get(c, 0) & 1 else "(needed: HJ)"))
        else:
            dst.append(f"{c}: split {v} (third run)")
    out.append("SUMMARY: controls reproduce (" + ", ".join(sorted(ctl)) + "); held out: " + ("; ".join(res) or "none")
               + "; repeat only: " + ("; ".join(rep) or "none") + (f"; void {void}" if void else ""))
    return "\n".join(out), {}
