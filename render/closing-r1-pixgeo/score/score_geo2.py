"""Scorers of R1's geometry stages (g-u1, g-c1, g-c1f, g-t1, g-t2, g-t7, g-u2, g-t5, g-t6).  Written before the run;
frozen with the predictions.  S1b's readers (live_job knob proof, e2 measures, decode_object) with the R1 hypotheses.

Common rules: a job whose data is empty, missing or has an rc that is not a result of the tool is NODATA (tested first,
never a match); the controls come from the frozen `control` rows and a failing control makes the stage's verdict
`cannot tell`; held out and replicate rows are tallied apart from `repeat` rows; every scorer ends with one line
`SUMMARY: ...` naming the hypothesis and the count.  D36 (dword 36 against 0x072c) is a side table, never gating.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402

from r1lib import (Kept, knob_value, outcome, peak_status, reg_series, rows_of, runs, support, table,  # noqa: E402
                   timeline)

sys.path.insert(0, str(pathlib.Path.home() / "src/resgx545/tools/usse-asm"))
C_RANGE = (0x35e, 0x37e)          # E753: C in [0x35e, 0x37e)
XY_TOL = 2 / 256                  # a clip-made vertex's position: 2/256 px
DEFAULT_XY = [(8.0, 8.0), (56.0, 20.0), (20.0, 56.0)]


def pred1(preds, name, q, model=None):
    for v, m, s in preds.get(name, {}).get(q, []):
        if model is None or m == model:
            return v
    return None


def control_rows(preds, q):
    vals = collections.defaultdict(set)
    for n, qs in preds.items():
        for v, m, s in qs.get(q, []):
            if s == "control":
                vals[n].add(v)
    return {n: next(iter(v)) for n, v in vals.items() if len(v) == 1}


def live_job(k: Kept, preds, n, need_timeline=True, dumps=()):
    """A dict for a usable job, or {'void': reason}: void first, then the knob proof (0x0624 of THIS job)."""
    v = k.void(n, dumps)
    if v:
        return dict(void=v)
    txt = k.out(n)
    if not need_timeline:
        return dict(void=None, txt=txt)
    tl = timeline(txt)
    if tl is None:
        return dict(void="no timeline")
    got = knob_value(tl, txt)
    want = pred1(preds, n, "knob0624_first")
    if got is None:
        return dict(void="no status rise: the job's 0x0624 value is unknown")
    if want is not None and got != int(want, 16):
        return dict(void=f"knob did not land: 0x0624 {got:#x}, wanted {want}")
    return dict(void=None, txt=txt, tl=tl, knob=got)


# ------------------------------------------------------------------------------------------------ D36 side table
def d36_of(tl, ctl):
    """(count, predicted, dword 36, raised) of one job with 0x072c sampled, or None.  count = the low half of 0x072c
    in the sample just before the first rising edge of 0x0658 bit 0 (the first abort's partial render)."""
    if not tl or "0x072c" not in tl[0] or not ctl:
        return None
    s58, s2c = reg_series(tl, "0x0658"), reg_series(tl, "0x072c")
    first = next((i for i, v in enumerate(s58) if v & 1), None)
    if first is None:
        return None
    cnt = s2c[max(first - 1, 0)] & 0xffff
    return dict(count=cnt, pred=max(cnt - 2, 0), dw36=ctl[36], raised=ctl[38] == 0x20)


def d36_lines(k: Kept, live):
    """Lines and the (unraised, raised) tallies of D36 over the usable jobs in `live` {name: job dict}."""
    rows, tal = [], {False: [0, 0], True: [0, 0]}
    for n, j in live.items():
        if j.get("void"):
            continue
        d = d36_of(j.get("tl"), k.buf09(n))
        if d is None:
            continue
        ok = d["pred"] == d["dw36"]
        tal[d["raised"]][0] += ok
        tal[d["raised"]][1] += 1
        rows.append((n, d["count"], d["pred"], d["dw36"], "raised" if d["raised"] else "unraised", "ok" if ok else "MISS"))
    if not rows:
        return ["D36: not scored (0x072c was not sampled in any usable job)"], tal
    return ["D36 side table (never gating): dword 36 = max(0x072c count at the first abort - 2, 0)",
            table(rows, ["job", "0x072c count", "predicted", "dword 36", "job", ""]),
            f"D36: unraised jobs {tal[False][0]} of {tal[False][1]}; raised jobs (held out) {tal[True][0]} of {tal[True][1]}"], tal


# ------------------------------------------------------------------------------------------------ U1, U2
def walk_head(param):
    if not param or len(param) < 0x422000 + 4 * 0x424:
        return None
    t = list(struct.unpack("<%dI" % 0x424, param[0x422000:0x422000 + 4 * 0x424]))
    heads = [i for i in range(1, len(t)) if (t[i] >> 16) == 0xffff and t[i] != 0]
    return heads[0] if len(heads) == 1 else None


def e2_measure(k: Kept, n):
    txt = k.out(n)
    tl = timeline(txt)
    args = k.case(n).get("args", "")
    m = re.search(r"-n (\d+)", args)
    K = int(m[1]) if m else 1
    geo = len(re.findall(r"geometry only, the scene left open", txt or ""))
    early = sorted(int(x) for x in re.findall(r"^tri \d+x\d+ #(\d+): overflowed", txt or "", re.M) if int(x) < K)
    param = k.dump(n, f"tri.{K}.param.bin") or k.dump(n, "param.bin")
    wh = walk_head(param)
    return dict(K=K, geo=geo, early=early, peak=peak_status(tl) if tl else None, walk=(wh - 1) if wh else None,
                tl=tl, txt=txt)


def norm_model(m):
    return re.sub(r" with HU1's U = \d+", " (HU1's U)", m)


def score_u1(k: Kept, preds):
    rows, res, live = [], {}, {}
    entries, void, bounds = [], [], []
    for n in k.names():
        j = live_job(k, preds, n)
        live[n] = j
        if j["void"]:
            res[n] = dict(void=j["void"])
            void.append(n)
            rows.append((n, "NODATA: " + j["void"], "", "", "", "", ""))
            continue
        m = e2_measure(k, n)
        oc = outcome(j["txt"], k.dmesg(n))
        whole = m["geo"] == m["K"] - 1 and not m["early"]
        if pred1(preds, n, "outcome") is not None:                         # a boundary job
            want = pred1(preds, n, "outcome")
            # a hang or a fault is no outcome: void, never "completed as predicted" (post-run fix C8, POSTRUN-FIX.md)
            hit = (oc == "overflow") == (want == "overflow") if whole and oc in ("ok", "overflow") else None
            res[n] = dict(void=None, outcome=oc, whole=whole)
            if hit is None:
                void.append(n)
            bounds.append((n, hit))
            for v, mdl, st in preds[n]["outcome"]:
                entries.append((norm_model(mdl), st, hit))
            rows.append((n, oc, "", "", "", "", f"want {want}: {'yes' if hit else 'NO' if hit is False else 'void (kick lines)' if oc in ('ok', 'overflow') else f'void ({oc})'}"))
            continue
        u, wk = m["peak"], m["walk"]
        agree = wk is None or wk == u
        usable = whole and agree and bool(u) and oc == "ok"            # not a hang or a fault either (post-run fix C8)
        res[n] = dict(void=None if usable else "unusable", U=u, walk=wk, agree=agree, whole=whole, oc=oc)
        ms = {mm: v for v, mm, s in preds.get(n, {}).get("U", [])}
        h1 = [v for mm, v in ms.items() if mm.startswith("HU1")]
        h2 = [v for mm, v in ms.items() if mm.startswith("HU2")]
        if not usable:
            void.append(n)
        else:
            for v, mdl, st in preds[n]["U"]:
                entries.append((mdl.split(" (")[0], st, int(v) == u))
        rows.append((n, oc, u, wk, "agree" if agree else "DISAGREE", f"{u - int(h1[0]):+d}" if h1 and u else "-",
                     (f"HU2 {h2[0]}" if h2 else "") + ("" if whole else f" kicks lost {m['early']}")))
    out = ["U1: page need U (peak of 0x0724 low half; cross-check: free-list head - 1) against HU1 (exact) and HU2",
           table(rows, ["job", "outcome", "U peak", "U walk", "peak vs walk", "residual vs HU1", "note"]), ""]
    d36, _ = d36_lines(k, live)
    out += d36
    ctl = control_rows(preds, "U")
    bad = [n for n, v in ctl.items() if res.get(n, {}).get("void") or res.get(n, {}).get("U") != int(v)]
    if bad or not ctl:
        out.append(f"SUMMARY: cannot tell: control(s) {bad} did not read their frozen U (E705/E735: 19 and 29); void {void}")
    else:
        out.append("SUMMARY: controls pass (u-ctl-1 = 19, u-ctl-2a = 29); " + support(entries)
                   + (f"; void or unusable cells {void}" if void else ""))
    return "\n".join(out), res


def score_u2(k: Kept, preds):
    """E625's count formula at U = 287: the (k, s) pairs consistent with every valid cell's count (partial renders =
    the 0x0658 bit 0 stretches).  Controls P = 0xa0 (2) and 0xb0 (1) must hold."""
    rows, counts, live, void = [], {}, {}, []
    for n in k.names():
        j = live_job(k, preds, n)
        live[n] = j
        if j["void"]:
            void.append(n)
            rows.append((n, "NODATA: " + j["void"], ""))
            continue
        prs, _ = runs(j["tl"])
        counts[n] = len(prs)
        rows.append((n, len(prs), hex(j["knob"] + 0x22)))
    out = ["U2: partial renders per cell", table(rows, ["job", "count", "P"]), ""]
    d36, _ = d36_lines(k, live)
    out += d36
    bad = [n for n, v in control_rows(preds, "nparts").items() if counts.get(n) != int(v)]
    if bad:
        out.append(f"SUMMARY: cannot tell: control(s) {bad} did not read their frozen count (E625: 2 at 0xa0, 1 at 0xb0); void {void}")
        return "\n".join(out), {}
    models = collections.defaultdict(list)
    for n in counts:
        for v, mdl, st in preds.get(n, {}).get("nparts", []):
            if st != "control":
                models[mdl].append(int(v) == counts[n])
    fit = sorted(m for m, r in models.items() if r and all(r))
    ctl_names = set(control_rows(preds, "nparts"))
    cells = sorted((int(n.split("-")[1], 16), counts[n]) for n in counts if n not in ctl_names)
    first1 = next((P for P, c in cells if c == 1), None)
    ks = collections.defaultdict(list)
    for m in fit:
        mm = re.match(r"E625 count \(k=(\d+), s=(0x[0-9a-f]+)\)", m)
        ks[mm[2]].append(int(mm[1]))
    desc = "; ".join(f"s={s}: k in [{min(v)}, {max(v)}] ({len(v)} values)" for s, v in sorted(ks.items()))
    if not models:
        out.append("SUMMARY: cannot tell: no valid ladder cell")
    elif not fit:
        out.append(f"SUMMARY: E625's count formula REFUTED at U = 287: none of {len(models)} (k, s) pairs fits the "
                   f"{len(cells)} cells' counts; void {void}")
    else:
        out.append(f"SUMMARY: controls pass; E625 count formula: {len(fit)} of {len(models)} (k, s) pairs fit all "
                   f"{len(cells)} cells ({desc}); first count-1 cell {first1 and hex(first1)}; void {void}")
    return "\n".join(out), {}


# ------------------------------------------------------------------------------------------------ C1
def e1_measure(k: Kept, preds, only=None):
    res = {}
    lines = []
    live = {}
    for n in only or k.names():
        j = live_job(k, preds, n)
        ctl = k.buf09(n) if not j["void"] else None
        if not j["void"] and ctl is None:
            j = dict(void="no control block kept")
        live[n] = j
        if j["void"]:
            res[n] = j
            lines.append((n, "-", "-", "-", "-", "NODATA: " + j["void"]))
            continue
        prs, peaks = runs(j["tl"])
        thr0 = prs[0] if prs else None
        reach = bool(thr0 is not None and len(peaks) > 1 and peaks[1] >= thr0)
        res[n] = dict(void=None, raised=ctl[38] == 0x20, nparts=len(prs), reach=reach, dw36=ctl[36], thr0=thr0)
        lines.append((n, hex(j["knob"]), len(prs), [hex(p) for p in peaks[:3]],
                      f"dw36={ctl[36]} dw37={ctl[37]:#x} dw38={ctl[38]:#x}",
                      ("raise" if res[n]["raised"] else "none") + ("" if reach else "  (second run does not reach thr0: void)")))
    out = ["C1: per job (the 0x0624 of the job itself is the knob proof)",
           table(lines, ["job", "0x0624", "parts", "peaks", "control block", "raise"]), ""]
    return res, out, live


def c1_ladder(cells):
    """cells [(P, raised | None)] of one scene in ladder order -> (kind, info): 'flip' (Pr, Ps), 'multi', 'none',
    'void' (the flip is next to a void cell)."""
    use = [(i, P, r) for i, (P, r) in enumerate(cells) if r is not None]
    flips = [(a, b) for a, b in zip(use, use[1:]) if a[2] != b[2]]
    if len(flips) > 1 or (flips and not flips[0][0][2]):
        return "multi", len(flips)
    if not flips:
        return "none", None
    (ia, Pa, _), (ib, Pb, _) = flips[0]
    return ("flip", (Pa, Pb)) if ib == ia + 1 else ("void", (Pa, Pb))


def c1_verdict(c1500, c1350):
    """H-abs on the 1500 ladder; HP1 on the 1350 cells against the 1500 cells at the same P."""
    kind, info = c1_ladder(c1500)
    if kind == "multi":
        habs = f"H-abs's monotone form REFUTED: {info} flips along the 1500 ladder (not a single raise -> none step)"
    elif kind == "none":
        habs = "cannot tell: no flip on the 1500 ladder"
    elif kind == "void":
        habs = f"cannot tell: a void cell lies inside the flip {info[0]:#x} .. {info[1]:#x}"
    else:
        Pa, Pb = info
        lo, hi = Pa - 2, Pb - 2
        inside = C_RANGE[0] <= lo and hi <= C_RANGE[1]
        # refuted only when the bracket and the range are disjoint, not when the bracket is not inside it (post-run fix C8)
        overlap = lo < C_RANGE[1] and C_RANGE[0] < hi
        if inside or not overlap:
            habs = (f"H-abs {'holds' if inside else 'REFUTED by its range'}: one flip, last raise {Pa:#x}, first silent {Pb:#x}: "
                    f"C in [{lo:#x}, {hi:#x}) ({'inside' if inside else 'NOT inside'} [{C_RANGE[0]:#x}, {C_RANGE[1]:#x}))"
                    + (f"; the step-1 cell {Pa + 1:#x} (g-c1f f-1500-{Pa + 1:#x}) fixes C exactly" if inside else ""))
        else:
            habs = (f"H-abs consistent (not decided): one flip, last raise {Pa:#x}, first silent {Pb:#x}: C in [{lo:#x}, {hi:#x}) "
                    f"overlaps [{C_RANGE[0]:#x}, {C_RANGE[1]:#x}) without lying inside it")
    by1500 = dict(c1500)
    pairs = [(P, r, by1500.get(P)) for P, r in c1350 if r is not None and by1500.get(P) is not None]
    diff = [f"{P:#x}" for P, a, b in pairs if a != b]
    hp1 = (f"HP1: {len(pairs) - len(diff)} of {len(pairs)} 1350 cells equal the 1500 cell at that P"
           + (f" (REFUTED at {diff})" if diff else "") if pairs else "HP1: cannot tell (no usable 1350 cell)")
    return habs, hp1


def score_c1(k: Kept, preds):
    res, out, live = e1_measure(k, preds)
    g = lambda n: res.get(n, dict(void="not run"))
    valid = lambda n: not g(n).get("void") and g(n)["reach"] and g(n)["nparts"] > 1
    ctl = control_rows(preds, "raise")
    bad = [n for n, v in ctl.items() if not valid(n) or g(n)["raised"] != (v == "yes")]
    d36, tal = d36_lines(k, live)
    out += d36
    if bad:
        out.append(f"SUMMARY: cannot tell: control(s) {bad} void, not reaching thr0 or not as E753 measured (0x360 raise, "
                   f"0x380 none)")
        return "\n".join(out), res
    cells = {1500: [], 1350: []}
    for n in k.names():
        mm = re.fullmatch(r"(?:c|f)-(1500|1350)-(0x[0-9a-f]+)", n)
        if mm:
            cells[int(mm[1])].append((int(mm[2], 16), g(n)["raised"] if valid(n) else None))
    for V in cells:
        cells[V].sort()
        out.append(f"{V}: " + " ".join(f"{P:#x}:{'void' if r is None else 'R' if r else '-'}" for P, r in cells[V]))
    habs, hp1 = c1_verdict(cells[1500], cells[1350])
    out.append(f"SUMMARY: {habs}; {hp1}; D36 unraised {tal[False][0]}/{tal[False][1]}, raised {tal[True][0]}/{tal[True][1]}")
    return "\n".join(out), res


def score_c1f(k: Kept, preds):
    res, out, live = e1_measure(k, preds)
    d36, _ = d36_lines(k, live)
    out += d36
    parts = []
    for n, r in res.items():
        mm = re.fullmatch(r"f-1500-(0x[0-9a-f]+)", n)
        P = int(mm[1], 16)
        if r.get("void") or not r["reach"]:
            parts.append(f"{n}: void")
        elif r["raised"]:
            parts.append(f"{n}: raise: C in [{P - 2:#x}, {P - 1:#x})")
        else:
            parts.append(f"{n}: none: C in [{P - 3:#x}, {P - 2:#x})")
    if not parts or any(p.endswith("void") for p in parts):
        out.append("SUMMARY: cannot tell: the step-1 cell is void or not run (" + "; ".join(parts or ["no job"]) + ")")
    else:
        out.append("SUMMARY: step-1 cell: " + "; ".join(parts))
    return "\n".join(out), res


# ------------------------------------------------------------------------------------------------ objects
def decode_object(param, tadata):
    import pbdump
    try:
        ws = pbdump.obj(param) if param else []
        o = pbdump.first_object(param, tadata) if param and tadata else None
    except Exception as e:               # a short or corrupt dump is void, never "no object"
        return dict(state="bad dump", words=[], o=None, bad=str(e)[:60])
    if not ws:
        return dict(state="none", words=[], o=None)
    if o is None:
        return dict(state="written-unlisted", words=ws, o=None)
    big = 0
    for i, w in enumerate(o["packed"]):
        big |= w << (32 * i)
    nv = len(o["vertices"])
    packed = [((big >> (80 * v)) & 0xffffff, (big >> (80 * v + 24)) & 0xffffff, (big >> (80 * v + 48)) & 0xffffffff)
              for v in range(nv)]
    return dict(state="present", words=ws, o=o, nvert=nv, rhw=list(o["PB_OBJ.RHW"]), packed=packed,
                prims=[tuple(p) for p in o["PB_OBJ.PRIM_LIST"]])


def _xy(d):
    return [(x / 256 - 4096, y / 256 - 4096) for y, x, _ in d["packed"]]


def _pts(v):
    return [tuple(float(c) for c in p.split(",")) for p in v.split(";")]


def _near(a, b, tol):
    return len(a) == len(b) and all(abs(p - r) <= tol and abs(q - s) <= tol for (p, q), (r, s) in zip(a, b))


def hits(preds, n, d):
    """{(quantity, model): True | False | None} of one decoded job (None = not decidable, e.g. an unlisted object)."""
    hit = {}
    for q, lst in preds.get(n, {}).items():
        for v, m, s in lst:
            ok = None
            if q == "object":
                if v in ("?", "") or v.startswith("monotone") or v.startswith("same"):
                    ok = None
                elif d["state"] == "written-unlisted":
                    ok = None
                else:
                    ok = v == d["state"]
            elif d["state"] != "present":
                ok = False if q in ("nvert", "xy_set", "xy_ordered", "prims", "depth_words", "xy_near", "rhw_word",
                                    "xy_box", "packed_24bit") and pred1(preds, n, "object") in ("present", None) else None
            elif q == "nvert":
                ok = d["nvert"] == int(v)
            elif q == "xy_set":
                ok = _near(sorted(_xy(d), key=lambda p: (round(p[0] * 16), round(p[1] * 16))),
                           sorted(_pts(v), key=lambda p: (round(p[0] * 16), round(p[1] * 16))), XY_TOL)
            elif q == "xy_ordered":
                ok = _near(_xy(d), _pts(v), XY_TOL)
            elif q == "prims":
                ok = ";".join(",".join(str(e) for e in t) for t in d["prims"]) == v
            elif q == "depth_words":
                ok = ",".join(f"0x{z:08x}" for _, _, z in d["packed"]) == v
            elif q == "object_equals_default_xy":
                ok = _near(_xy(d), DEFAULT_XY, XY_TOL)
            elif q == "rhw_word":
                ok = all(w == int(v, 16) for w in d["rhw"])
            elif q == "xy_near":
                ok = _near(sorted(_xy(d)), sorted(_pts(v)), 1 / 64)
            elif q == "xy_box":
                lo, hi = (float(x) for x in v.split(","))
                ok = all(lo <= x <= hi and lo <= y <= hi for x, y in _xy(d))
            elif q == "packed_24bit":
                ok = ";".join(f"{x};{y}" for y, x, _ in d["packed"]) == v
            if ok is not None:
                hit[(q, m)] = ok
    return hit


def decode_all(k: Kept):
    dec, rows, void = {}, [], []
    for n in k.names():
        v = k.void(n, ("param.bin", "tadata.bin"))
        if v:
            void.append(n)
            rows.append((n, "NODATA: " + v, "", "", ""))
            continue
        d = decode_object(k.dump(n, "param.bin"), k.dump(n, "tadata.bin"))
        if d.get("bad"):
            void.append(n)
            rows.append((n, "NODATA: " + d["bad"], "", "", ""))
            continue
        dec[n] = d
        xy = ";".join(f"{x:g},{y:g}" for x, y in _xy(d)) if d["state"] == "present" else "-"
        rows.append((n, d["state"], d.get("nvert", "-"), xy,
                     ",".join(sorted({f"{w:#x}" for w in d["rhw"]})) if d["state"] == "present" else "-"))
    return dec, rows, void


def score_objects(k: Kept, preds, title, extra_ctl=None):
    """One group per stage: every control job's control predictions must hold (extra_ctl may name the models of a control
    to skip), then each model's tally over the held-out, replicate and repeat predictions."""
    dec, rows, void = decode_all(k)
    hit = {n: hits(preds, n, d) for n, d in dec.items()}
    out = [f"{title}: object decode per job", table(rows, ["job", "object", "nvert", "x,y (pixels)", "1/w words"]), ""]
    skip = extra_ctl or (lambda n, q, m: False)
    ctls = [n for n in preds if any(s == "control" for qs in preds[n].values() for v, m, s in qs)]
    need = lambda c: [(q, m) for q, lst in preds[c].items() for v, m, s in lst
                      if s == "control" and v not in ("?", "") and not skip(c, q, m)]
    failed = [c for c in ctls if c not in dec or any(hit[c].get(qm) is not True for qm in need(c))]
    if not ctls:
        return "\n".join(out + ["SUMMARY: cannot tell: no control row"]), {}
    if failed:
        return "\n".join(out + [f"SUMMARY: cannot tell: control(s) {failed} failed or void; void jobs {void}"]), {}
    entries = []
    for n in preds:
        if n in ctls:
            continue
        for q, lst in preds[n].items():
            for v, m, s in lst:
                if s in ("heldout", "replicate", "repeat"):
                    o = hit[n].get((q, m)) if n in dec else None
                    if v in ("?", "") or (q == "object" and (v.startswith(("monotone", "same")))):
                        continue
                    entries.append((m, s, o))
    miss = [n for n in preds if n not in ctls and n not in dec]
    out.append("SUMMARY: controls pass; " + support(entries) + (f"; void jobs {void}" if void else "")
               + (f"; not run {miss}" if miss and not void else ""))
    return "\n".join(out), {}


def score_t1(k, preds):
    return score_objects(k, preds, "T1")


def score_t2(k, preds):
    return score_objects(k, preds, "T2")


def score_t7(k, preds):
    return score_objects(k, preds, "T7")


def score_t6(k: Kept, preds):
    """Clamp ladder: the control must hold its RZ word (the measured 0x47023555, an object, the shrunk position); each
    held-out cell's stored 1/w is classified RZ / RN / other (the cell where RZ = RN counts as both); the decision is
    all RZ, all RN or mixed over the cells where they differ."""
    dec, rows, void = decode_all(k)
    out = ["T6: object decode per job", table(rows, ["job", "object", "nvert", "x,y (pixels)", "1/w words"]), ""]
    cls, pos = {}, {}
    ctl_bad = []
    for n, d in dec.items():
        rz = pred1_model(preds, n, "rhw_word", "RZ")
        rn = pred1_model(preds, n, "rhw_word", "RN")
        if rz is None:
            continue
        if d["state"] != "present":
            cls[n] = "none-object"
            continue
        ws = {f"{w:#x}" for w in d["rhw"]}
        cls[n] = "RZ" if ws == {rz} and rz != rn else "RN" if ws == {rn} and rz != rn else \
            "both" if ws == {rz} == {rn} else "other"
        pos[n] = _near(sorted(_xy(d)), sorted(_pts(pred1(preds, n, "xy_near"))), 1 / 64)
    ctls = [n for n in preds if any(s == "control" for qs in preds[n].values() for v, m, s in qs)]
    for n in ctls:                       # the control holds its RZ word (the measured one) as an object
        if n not in dec or dec[n]["state"] != "present" or {f"{w:#x}" for w in dec[n]["rhw"]} != {pred1_model(preds, n, "rhw_word", "RZ")}:
            ctl_bad.append(n)
    if not ctls or ctl_bad:
        out.append(f"SUMMARY: cannot tell: control {ctl_bad or 't6-ctl'} failed or void (0x47023555 expected); void {void}")
        return "\n".join(out), {}
    cells = [n for n in cls if not any(s == "control" for qs in preds[n].values() for v, m, s in qs)]
    sep = [n for n in cells if pred1_model(preds, n, "rhw_word", "RZ") != pred1_model(preds, n, "rhw_word", "RN")]
    nz, nn = sum(cls[n] == "RZ" for n in sep), sum(cls[n] == "RN" for n in sep)
    other = [n for n in cells if cls[n] in ("other", "none-object")]
    out += [f"{n}: stored 1/w {cls[n]}" + ("" if n in sep else " (RZ = RN cell)") for n in cells]
    if other:
        v = f"error beyond 1 ulp or no object at {other}"
    elif sep and nz == len(sep):
        v = f"RZ in {nz} of {len(sep)} separating cells: the rounding clause closes as RZ"
    elif sep and nn == len(sep):
        v = f"RN in {nn} of {len(sep)} separating cells: the rounding clause closes as RN"
    else:
        v = f"mixed (RZ {nz}, RN {nn} of {len(sep)}): within 1 ulp, not a rounding rule"
    npos = sum(1 for n in cells if pos.get(n))
    out.append(f"SUMMARY: control t6-ctl holds; {v}; position HREP-xy' (x, y / clamp) {npos} of {len(cells)}"
               + (f"; void jobs {void}" if void else ""))
    return "\n".join(out), {}


def pred1_model(preds, n, q, label):
    for v, m, s in preds.get(n, {}).get(q, []):
        if m.startswith(label):
            return v
    return None


def score_t5(k: Kept, preds):
    dec, rows, void = decode_all(k)
    out = ["T5: object decode per job", table(rows, ["job", "object", "nvert", "x,y (pixels)", "1/w words"]), ""]
    hit = {n: hits(preds, n, d) for n, d in dec.items()}
    ctls = [n for n in preds if any(s == "control" for qs in preds[n].values() for v, m, s in qs)]
    bad = [c for c in ctls if c not in dec or not hit[c] or any(v is not True for v in hit[c].values())]
    if bad or not ctls:
        out.append(f"SUMMARY: cannot tell: control(s) {sorted(set(bad))} failed or void; void {void}")
        return "\n".join(out), {}
    lad = []
    for n in sorted(preds):
        if re.fullmatch(r"s-e\d+", n):
            ext, area = float(pred1(preds, n, "extent")), float(pred1(preds, n, "area"))
            st = dec[n]["state"] if n in dec else None
            lad.append((ext, area, st if st in ("present", "none") else None, n))
    seq = [s for _, _, s, _ in lad if s]
    mono = all(not (a == "present" and b == "none") for a, b in zip(seq, seq[1:]))
    out.append("ladder (extent, area, object): " + "; ".join(f"{e:.3f}/{a:.3f}/{s}" for e, a, s, _ in lad))
    el = dec.get("s-elong")
    if not mono:
        out.append("SUMMARY: HS-ext and HS-area both REFUTED: the ladder is not monotone in the extent (none -> present only); "
                   f"void {void}")
        return "\n".join(out), {}
    if el is None or el["state"] not in ("present", "none") or any(s is None for _, _, s, _ in lad):
        out.append(f"SUMMARY: cannot tell: the elongated cell or a ladder cell is void or unlisted; void {void}")
        return "\n".join(out), {}
    top = lad[-1][2]
    a_el = float(pred1(preds, "s-elong", "area"))
    none_a = [a for _, a, s, _ in lad if s == "none"]
    pres_a = [a for _, a, s, _ in lad if s == "present"]
    ext_ok = (el["state"] == top)
    area_ok = (el["state"] == "present" and (not none_a or a_el > max(none_a))) or \
              (el["state"] == "none" and (not pres_a or a_el < min(pres_a)))
    flip = next((f"{lad[i][0]:.2f}" for i in range(1, len(lad)) if lad[i - 1][2] == "none" and lad[i][2] == "present"), "none")
    out.append(f"SUMMARY: controls pass; ladder monotone (flip at extent {flip}); elongated {el['state']}: HS-ext "
               f"{'consistent' if ext_ok else 'REFUTED'} (the 0.98 cell is {top}), HS-area "
               f"{'consistent' if area_ok else 'REFUTED'} (area {a_el:.3f}; absent up to {max(none_a, default=0):.3f}, "
               f"present from {min(pres_a, default=0):.3f})" + ("; the elongated cell does not separate them" if ext_ok and area_ok else "")
               + (f"; void jobs {void}" if void else ""))
    return "\n".join(out), {}
