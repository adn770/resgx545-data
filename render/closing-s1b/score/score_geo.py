"""Scorers of the geometry stages, S1b.  Written before the run; frozen with the predictions.

S1's scorers with the fixes of the S1 analysis (each tested on S1's own data by tests/test_fixes.py, failing on S1's
code), and the S1b stages (g-e1 ladder, g-e4w, g-e5, g-e3 subset, g-e8b).
Rules common to every scorer: a job whose data is empty, missing, or has an rc that is not a result of the tool is NODATA
(tested first, never a match); controls come from the frozen predictions (set `control`), and a control that fails makes
the verdict of what it controls "cannot tell" (the stage, or in E3 its own group only); every scorer ends with one line
`SUMMARY: ...` (a verdict, or `cannot tell: why`).
"""
from __future__ import annotations

import collections
import gzip
import pathlib
import re
import struct
import sys

from s1lib import (Kept, knob_value, load_preds, outcome, peak_status, reg_series, rows_of, runs, support, table,  # noqa: E402
                   timeline)

FATE = pathlib.Path.home() / "src/resgx545-data/vdm/verification-1141ta/recompute"


def pred1(preds, name, q, model=None):
    for v, m, s in preds.get(name, {}).get(q, []):
        if model is None or m == model:
            return v
    return None


def control_rows(preds, q):
    """{job: value} of the frozen control rows of quantity q, for the jobs whose control rows all give ONE value (a
    job whose models disagree, as S1's c-1500-0x422 'raise' under R2, is not a control of that quantity)."""
    vals = collections.defaultdict(set)
    for n, qs in preds.items():
        for v, m, s in qs.get(q, []):
            if s == "control":
                vals[n].add(v)
    return {n: next(iter(v)) for n, v in vals.items() if len(v) == 1}


def live_job(k: Kept, preds, n, need_timeline=True, dumps=()):
    """A dict for a usable job, or {'void': reason}: void first, then the knob proof (0x0624 of THIS job: its own
    register rows, never the first sample, which is the previous job's)."""
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


# ------------------------------------------------------------------------------------------------ E1
def e1_measure(k: Kept, preds):
    res, lines = {}, []
    for n in k.names():
        j = live_job(k, preds, n)
        ctl = k.buf09(n) if not j["void"] else None
        if not j["void"] and ctl is None:
            j = dict(void="no control block kept")
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
                      ("raise" if res[n]["raised"] else "none") + ("  (second run reaches thr0)" if reach else "  (second run does not reach: void for the raise)")))
    out = ["E1: per job (the 0x0624 of the job itself is the knob proof)",
           table(lines, ["job", "0x0624", "parts", "peaks", "control block", "raise"]), ""]
    return res, out


def e1_controls(res, preds):
    """None if the frozen controls hold, else the SUMMARY text.  Negative controls: control rows `raise no`; positive
    controls: control rows `raise yes` ONLY (S1b fix: S1's scorer named the held-out p-1350-0x3e0 a positive control,
    score_geo.py:69-72; a positive control must be a raise already measured under those exact words)."""
    g = lambda n: res.get(n, dict(void="not run"))
    valid = lambda n: not g(n).get("void") and g(n)["reach"] and g(n)["nparts"] > 1
    for n, v in control_rows(preds, "raise").items():
        if v == "no" and (g(n).get("void") or g(n)["raised"]):
            return f"cannot tell: negative control {n} void or raised"
    for n, v in control_rows(preds, "raise").items():
        if v == "yes":
            if not valid(n):
                return f"cannot tell: positive control {n} void or its second run does not reach thr0"
            if not g(n)["raised"]:
                return f"METHOD BROKEN: positive control {n} reaches thr0 and does not raise; nothing is concluded"
    return None


def score_e1(k: Kept, preds):
    """S1's g-e1 decision (table of S1), with the positive controls taken from the frozen control rows."""
    res, out = e1_measure(k, preds)
    g = lambda n: res.get(n, dict(void="not run"))
    usable = lambda n: not g(n).get("void")
    valid = lambda n: usable(n) and g(n)["reach"] and g(n)["nparts"] > 1
    if not usable("c-1500-0x422") or g("c-1500-0x422")["raised"]:
        out.append("SUMMARY: cannot tell: control c-1500-0x422 void or raised (E704 reproduction failed)")
        return "\n".join(out), res
    bad = e1_controls(res, preds)
    if bad:
        out.append("SUMMARY: " + bad)
        return "\n".join(out), res
    pos_ok = [n for n, v in control_rows(preds, "raise").items() if v == "yes" and valid(n) and g(n)["raised"]]
    d = ["d-1500-0x3e0", "d-1500-0x3e0-r2"]
    if not all(valid(n) for n in d):
        out.append("SUMMARY: cannot tell: a decisive job (d-1500-0x3e0, two runs) is void or its second run does not reach thr0")
        return "\n".join(out), res
    dr = [g(n)["raised"] for n in d]
    if dr[0] != dr[1]:
        out.append("SUMMARY: cannot tell: the two runs of d-1500-0x3e0 disagree (third run; if still split, not a function of the words)")
        return "\n".join(out), res
    if all(dr):
        out.append("SUMMARY: d-1500-0x3e0 raises 2 of 2 (read the ceiling cells above)")
        return "\n".join(out), res
    if not pos_ok:
        out.append("SUMMARY: cannot tell: d-1500-0x3e0 does not raise and no frozen positive control raised")
        return "\n".join(out), res
    out.append("SUMMARY: d-1500-0x3e0 does not raise 2 of 2 with a positive control raising (read the ladders above)")
    return "\n".join(out), res


def score_e1_ladder(k: Kept, preds):
    """S1b g-e1: 1350 and 1500 vertices at P = 0x320 .. 0x3c0.  HP1: one step P for both scenes (raise below a P*,
    none at and above it, the same P* for both); HPS: monotone in P for each scene, the step P* differs; neither: a
    scene not monotone in P.  Cells whose second run does not reach thr0 are void for the raise.  Also the dword-36
    step 1350 -> 1380 at P = 0x3e0 (S1 post hoc, frozen here)."""
    res, out = e1_measure(k, preds)
    bad = e1_controls(res, preds)
    if bad:
        out.append("SUMMARY: " + bad)
        return "\n".join(out), res
    g = lambda n: res.get(n, dict(void="not run"))
    valid = lambda n: not g(n).get("void") and g(n)["reach"] and g(n)["nparts"] > 1
    cells = {}
    for V in (1350, 1500):
        cs = sorted((int(re.search(r"-(0x[0-9a-f]+)$", n)[1], 16), n) for n in k.names() if n.startswith(f"x-{V}-"))
        cells[V] = [(P, g(n)["raised"] if valid(n) else None) for P, n in cs]
        out.append(f"x-{V}: " + " ".join(f"{P:#x}:{'void' if r is None else 'R' if r else '-'}" for P, r in cells[V]))
    dw = {n: g(n).get("dw36") for n in ("s-1350-0x3e0", "s-1380-0x3e0")}
    want = {n: pred1(preds, n, "dw36") for n in dw}
    dws = "dword 36 at 0x3e0 (S1 post hoc): " + ", ".join(f"{n} {dw[n]} (frozen {want[n]})" for n in dw)
    out.append(f"SUMMARY: {ladder_verdict(cells)}; {dws}")
    return "\n".join(out), res


C_LIMIT = (0x2fe, 0x3de)      # S1 post hoc: a raise only if thr0 + 0x20 <= C, 0x2fe <= C < 0x3de


def ladder_verdict(cells):
    """cells {V: [(P, raised: True | False | None = void), ...]} in ladder order.  S1b review: each scene must show
    exactly one flip, raise -> no raise, between two usable cells that are neighbours on the ladder (no void cell
    between them); otherwise cannot tell (the step lies outside the ladder or next to a void cell), except that two
    flips or a no-raise -> raise flip refute both models (not monotone).  The step bounds C, the raised threshold's
    limit (raise iff thr0 + 0x20 = P - 2 <= C): last raising P_r, first silent P_s give P_r - 2 <= C < P_s - 2.
    HP1: the same step in both scenes and that interval inside 0x2fe <= C < 0x3de; HPS: the steps differ."""
    steps = {}
    for V, cs in cells.items():
        use = [(i, P, r) for i, (P, r) in enumerate(cs) if r is not None]
        flips = [(a, b) for a, b in zip(use, use[1:]) if a[2] != b[2]]
        if len(flips) > 1 or (flips and not flips[0][0][2]):
            return f"neither HP1 nor HPS: {V} is not monotone in P ({len(flips)} flips)"
        if not flips:
            return f"cannot tell (step outside the ladder or next to a void cell): {V} has no flip"
        (ia, Pa, _), (ib, Pb, _) = flips[0]
        if ib != ia + 1:
            return f"cannot tell (step outside the ladder or next to a void cell): {V} has a void cell in its step"
        steps[V] = (Pa, Pb)
    if len({s for s in steps.values()}) == 1:
        Pa, Pb = next(iter(steps.values()))
        lo, hi = Pa - 2, Pb - 2
        inside = C_LIMIT[0] <= lo and hi <= C_LIMIT[1]
        # refuted only when the interval and the limit are disjoint, not when the interval is not inside it (post-run fix
        # C8, POSTRUN-FIX.md)
        overlap = lo < C_LIMIT[1] and C_LIMIT[0] < hi
        if not inside and overlap:
            return (f"HP1 consistent (not decided): one step for both scenes, last raise {Pa:#x}, first silent {Pb:#x}: "
                    f"C in [{lo:#x}, {hi:#x}) overlaps [{C_LIMIT[0]:#x}, {C_LIMIT[1]:#x}) without lying inside it")
        return (f"HP1{'' if inside else ' REFUTED by its limit'}: one step for both scenes, last raise {Pa:#x}, first "
                f"silent {Pb:#x}: C in [{lo:#x}, {hi:#x}) {'inside' if inside else 'NOT inside'} "
                f"[{C_LIMIT[0]:#x}, {C_LIMIT[1]:#x})")
    return "HPS: the step differs by scene (" + ", ".join(f"{V}: {a:#x} -> {b:#x}" for V, (a, b) in steps.items()) + ")"


def valid_ladder(r):
    return r["reach"] and r["nparts"] > 1


# ------------------------------------------------------------------------------------------------ E2
def walk_head(param):
    """Free-list head after a render: page table at 0x422000 of the PB dump (an_pool.py), head - 1 = pages taken."""
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


def score_e2a(k: Kept, preds, emit_u=None):
    rows, U, res = [], {}, {}
    for n in k.names():
        j = live_job(k, preds, n)
        if j["void"]:
            res[n] = dict(void=j["void"])
            rows.append((n, "NODATA: " + j["void"], "", "", "", ""))
            continue
        m = e2_measure(k, n)
        geo_ok = m["geo"] == m["K"] - 1
        u = m["peak"]
        agree = m["walk"] is None or m["walk"] == u
        res[n] = dict(void=None, U=u, walk=m["walk"], geo_ok=geo_ok, agree=agree)
        p = pred1(preds, n, "U")
        resid = "-" if p in (None, "") or not u else f"{u - int(p):+d}"
        rows.append((n, f"{m['geo']}/{m['K'] - 1}", u, m["walk"], "agree" if agree else "DISAGREE", resid))
        if re.fullmatch(r"u-\d[as]-0x422", n) and geo_ok and agree and u:
            U[n] = u
    out = ["E2a: page need U (peak status 0x0724, cross-check: free-list head - 1); residual = U - coverage proxy",
           table(rows, ["job", "open kicks", "U peak", "U walk", "peak vs walk", "residual vs proxy (pages)"]), ""]
    ctl = res.get("u-1-0x422", dict(void="not run"))
    ctl_ok = not ctl.get("void") and ctl.get("U") == 19
    if not ctl_ok:
        out.append(f"SUMMARY: cannot tell: control u-1-0x422 must read 0x13 (19): "
                   f"{ctl.get('void') or ctl.get('U')}; U values below are not comparable")
        if emit_u:
            raise SystemExit("refusing --emit-u: the 0x13 control failed or is void")
    else:
        miss = sorted(set(f"u-{k_}{l}-0x422" for k_ in (2, 3, 4) for l in "as") - set(U))
        out.append(f"SUMMARY: U measured for {len(U)} of 6 scenes (void or unusable: {miss or 'none'}); residuals are against an "
                   "empirical coverage proxy, an extrapolation that neither confirms nor refutes HU1; the formula needs "
                   "sgx-pipe's stream bytes")
    if emit_u and ctl_ok:
        import json
        json.dump(U, open(emit_u, "w"), indent=1, sort_keys=True)
        out.append(f"wrote {emit_u}")
    return "\n".join(out), res


def score_e2b(k: Kept, preds):
    """E625's overflow rule on K-triangle scenes.  S1b fix (S1 analysis, score_geo.py:185-192): a job is a test of
    the K-triangle scene only if every kick but the last left the scene open (the open-kick lines, as e2a checks); a
    job in which an earlier kick overflowed alone tested a smaller scene and is listed apart; the partial-render count
    predictions (nparts) are read, and are void where each kick overflowed alone (no K-scene formed)."""
    rows, bad, void, kscene, notk, cnt_void, cnt = [], [], [], [], [], [], {}
    for n in k.names():
        j = live_job(k, preds, n)
        if j["void"]:
            void.append(n)
            rows.append((n, "NODATA: " + j["void"], "", "", "", ""))
            continue
        m = e2_measure(k, n)
        whole = m["geo"] == m["K"] - 1 and not m["early"]
        oc = outcome(j["txt"], k.dmesg(n))
        want = pred1(preds, n, "outcome")
        if oc not in ("ok", "overflow"):
            # a hang or a fault is no outcome: the job is void, never "completed as predicted" (post-run fix C8)
            void.append(n)
            rows.append((n, oc, want, "void", "", f"void ({oc})"))
            continue
        prs, _ = runs(j["tl"])
        np_ = [(v, mm) for v, mm, s in preds.get(n, {}).get("nparts", [])]
        if np_:
            if not whole:
                cnt_void.append(n)
            else:
                cnt[n] = sorted({mm for v, mm in np_ if int(v) == len(prs)})
        hit = None if want is None else (oc == "overflow") == (want == "overflow")
        if want is not None:
            (kscene if whole else notk).append(n)
            if whole and hit is False:
                bad.append(n)
        rows.append((n, oc, want, {True: "yes", False: "NO", None: "-"}[hit], len(prs),
                     "K-scene" if whole else f"kick(s) {m['early']} overflowed alone"))
    out = ["E2b: boundary (E625's overflow rule, held out on K-triangle scenes) and partial-render counts",
           table(rows, ["job", "outcome", "predicted", "match", "parts", "scene"]), ""]
    for n, ms in cnt.items():
        out.append(f"{n}: (k, s) consistent with the count: {ms or 'none'}")
    if not k.names():
        s = "cannot tell: no jobs kept"
    elif void:
        s = f"cannot tell: void jobs {void}"
    elif bad:
        s = f"E625's overflow rule REFUTED on K-triangle scenes at {bad}"
    elif not kscene:
        s = "cannot tell: no job tested a K-triangle scene"
    else:
        s = (f"E625's overflow rule holds on {len(kscene)} K-scene jobs (held out); not K-scene tests (an earlier kick "
             f"overflowed alone): {notk or 'none'}; count predictions void (each kick overflowed alone): {cnt_void or 'none'}")
    out.append("SUMMARY: " + s)
    return "\n".join(out), {}


# ------------------------------------------------------------------------------------------------ E3, E4
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
    return dict(state="present", words=ws, o=o, nvert=nv, rhw=list(o["PB_OBJ.RHW"]), packed=packed)


DEFAULT_XY = [(8.0, 8.0), (56.0, 20.0), (20.0, 56.0)]


def _xy(d):
    return [(x / 256 - 4096, y / 256 - 4096) for y, x, _ in d["packed"]]


def _pts(v):
    return [tuple(float(c) for c in p.split(",")) for p in v.split(";")]


def _hits(preds, n, d):
    """{(quantity, model): True | False | None} for one decoded job.  S1b fix (score_geo.py:246): the cut and clip
    models are scored by vertex IDENTITY, not count: HC-orig ('3') holds only if the stored vertices are the original
    three (orig_xy, else the default triangle); HC-poly ('>=4') holds if they are not (a clipped polygon may have three
    vertices that are not the original ones, as S1's e3z-cut-m)."""
    hit = {}
    orig = _pts(pred1(preds, n, "orig_xy")) if pred1(preds, n, "orig_xy") else DEFAULT_XY
    for q, lst in preds.get(n, {}).items():
        for v, m, s in lst:
            ok = None
            if q == "object":
                got = {"none": "none", "written-unlisted": "written-unlisted"}.get(d["state"], "present")
                ok = v == got if v != "?" else None
            elif d["state"] != "present":
                ok = False if q in ("rhw_word", "xy_near", "xy_box") and pred1(preds, n, "object") == "present" else None
            elif q == "nvert":
                is_orig = d["nvert"] == 3 and sorted(_xy(d)) == sorted(orig)
                ok = (not is_orig) if v == ">=4" else (is_orig if v == "3" else d["nvert"] == int(v))
            elif q == "rhw_word":
                ok = all(w == int(v, 16) for w in d["rhw"])
            elif q == "object_equals_default":
                ok = all(w == 0x3f800000 for w in d["rhw"]) and _xy(d) == DEFAULT_XY
            elif q == "xy_pixels":
                ok = ";".join(f"{x:g},{y:g}" for x, y in _xy(d)) == v
            elif q == "xy_near":            # the stored vertices are these, each within 1/64 pixel, in any order
                want, got = sorted(_pts(v)), sorted(_xy(d))
                ok = len(want) == len(got) and all(abs(a - c) <= 1 / 64 and abs(b - e) <= 1 / 64
                                                   for (a, b), (c, e) in zip(want, got))
            elif q == "xy_box":             # every stored vertex inside [lo, hi] in x and y
                lo, hi = (float(x) for x in v.split(","))
                ok = all(lo <= x <= hi and lo <= y <= hi for x, y in _xy(d))
            elif q == "packed_24bit":
                ok = ";".join(f"{x};{y}" for y, x, _ in d["packed"]) == v
            if ok is not None:
                hit[(q, m)] = ok
    return hit


def score_e3(k: Kept, preds):
    """E3, gated PER GROUP (S1b fix, score_geo.py:280-284: the design's decision is per group, 'a group whose control
    fails' cannot tell; S1's scorer voided the whole stage on one failed control).  Group = the job name's prefix
    before the first '-'; its controls are its jobs with frozen `control` rows; a group counts only if every control
    prediction of every control job holds.  Per group: each model's tally over the group's held-out and replicate
    predictions; consistent = no miss and at least one hit."""
    rows, dec, void = [], {}, []
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
        dec[n] = (d, _hits(preds, n, d))
        xy = ";".join(f"{x:g},{y:g}" for x, y in _xy(d)) if d["state"] == "present" else "-"
        rhw = ",".join(sorted({f"{w:#x}" for w in d["rhw"]})) if d["state"] == "present" else "-"
        rows.append((n, d["state"], d.get("nvert", "-"), xy, rhw,
                     " ".join(f"{m}:{'Y' if o else 'n'}" for (q, m), o in dec[n][1].items())))
    out = ["E3: object decode per job", table(rows, ["job", "object", "nvert", "x,y (pixels)", "1/w words", "predictions matched"]), ""]
    groups = collections.OrderedDict()
    for n in list(k.names()) + [n for n in preds if n not in k.names()]:
        groups.setdefault(n.split("-")[0], []).append(n)
    parts = []
    for gname, names in groups.items():
        ctls = [n for n in names if any(s == "control" for qs in preds.get(n, {}).values() for v, m, s in qs)]
        need = lambda c: [(q, m) for q, lst in preds[c].items() for v, m, s in lst
                          if s == "control" and v != "?" and q != "orig_xy"]
        failed = [c for c in ctls if c not in dec or any(dec[c][1].get(qm) is not True for qm in need(c))]
        if not ctls:
            parts.append(f"{gname}: no control (no verdict)")
            continue
        if failed:
            parts.append(f"{gname}: cannot tell (control {', '.join(failed)} failed or void)")
            continue
        entries = []
        for n in names:
            if n in ctls or n not in dec:
                continue
            jset = {(q, m): s for q, lst in preds.get(n, {}).items() for v, m, s in lst}
            for (q, m), o in dec[n][1].items():
                entries.append((m, jset.get((q, m), "heldout"), o))
        miss = [n for n in names if n not in ctls and n not in dec]
        parts.append(f"{gname}: {support(entries)}" + (f", void {miss}" if miss else ""))
    out.append("SUMMARY: " + "; ".join(parts) + (f"; void jobs {void}" if void else ""))
    return "\n".join(out), {}


def score_e4(k: Kept, preds):
    ctl, rows, info = None, [], {}
    for n in k.names():
        v = k.void(n)
        if v:
            rows.append((n, "NODATA: " + v, "", "", ""))
            info[n] = ("void", None)
            continue
        c = k.case(n)
        oc = c.get("class", "ok")
        d = decode_object(k.dump(n, "param.bin"), k.dump(n, "tadata.bin")) if oc == "ok" else None
        if oc == "ok" and (d is None or d.get("bad") or not d["words"]):
            rows.append((n, "NODATA: no object dump", "", "", ""))
            info[n] = ("void", None)
            continue
        if n == "ix-c":
            ctl = (d["words"], d.get("nvert"))
        info[n] = (oc, d["words"] if d else None)
        rows.append((n, oc, d["state"] if d else "-", d.get("nvert", "-") if d else "-", len(d["words"]) if d else "-"))
    out = ["E4: header bits 25:24 of VDM word 2 (control ix-c: E414's five triangles, 15 vertices, no flip)",
           table(rows, ["job", "class", "object", "vertices", "object dwords"]), ""]
    if "ix-c" not in info or info["ix-c"][0] != "ok" or not ctl or ctl[1] != 15:
        out.append("SUMMARY: cannot tell: control ix-c void, failed, or not five triangles")
        return "\n".join(out), {}
    res = []
    for f in ("ix-24", "ix-25", "ix-2425"):
        runs_ = [info.get(f"{f}-r{i}", ("missing", None)) for i in (1, 2)]
        cls = [r[0] for r in runs_]
        if any(c in ("void",) for c in cls):
            res.append(f"{f}: cannot tell (void run)")
        elif cls == ["ok", "ok"]:
            same = [r[1] == ctl[0] for r in runs_]
            res.append(f"{f}: " + ("HN (unchanged in 2 of 2)" if all(same) else "HW signature (changed in 2 of 2)" if not any(same) else "cannot tell (split: third run)"))
        elif cls == ["hang", "hang"]:
            res.append(f"{f}: HH (hang in 2 of 2)")
        elif cls == ["fault", "fault"]:
            res.append(f"{f}: HW signature (fault in 2 of 2)")
        else:
            res.append(f"{f}: cannot tell ({cls}: split or skipped; third run)")
    out.append("SUMMARY: control ok; " + "; ".join(res))
    return "\n".join(out), {}


def e4_result(k: Kept, n, ctl_words):
    """'same' (the object words equal the control's), 'changed', 'none' (no object), 'hang', 'fault WORD', or void."""
    v = k.void(n)
    if v:
        return "void: " + v
    c = k.case(n).get("class", "ok")
    if c == "hang":
        return "hang"
    if c == "fault":
        fw = re.findall(r"BIF fault (0x[0-9a-f]+)", k.dmesg(n) + (k.out(n) or ""))
        return "fault " + (fw[0] if fw else "?")
    if c != "ok":
        return "void: class " + c
    d = decode_object(k.dump(n, "param.bin"), k.dump(n, "tadata.bin"))
    if d.get("bad"):
        return "void: " + d["bad"]
    if not d["words"]:
        return "none"
    return "same" if d["words"] == ctl_words else "changed"


def score_e4w(k: Kept, preds):
    """S1b g-e4w: --index-width 32 (32-bit index list, VDM word 2 bit 25 set by the option).  Controls: ix-c (16-bit,
    E414's 15-vertex object) and ix-25 (16-bit list with bit 25: the S1 fault 0xd0008, last).  The option's echo
    '32-bit indices' is the knob proof of the 32-bit jobs.  Frozen per condition (two runs): HW32 (bit 25 selects
    32-bit indices): ix32-25 'same' 2 of 2, ix32-n (bit 25 cleared over the 32-bit list) not 'same' 2 of 2;
    HX (bit 25 is not the width): ix32-25 faults as S1's 16-bit job did."""
    rows, res = [], {}
    ctl = None
    if not k.void("ix-c") and k.case("ix-c").get("class") == "ok":
        d = decode_object(k.dump("ix-c", "param.bin"), k.dump("ix-c", "tadata.bin"))
        if d.get("state") == "present" and d.get("nvert") == 15:
            ctl = d["words"]
    for n in k.names():
        r = e4_result(k, n, ctl) if ctl is not None else "void: no control"
        if n.startswith("ix32") and not r.startswith("void") and "32-bit indices" not in (k.out(n) or ""):
            r = "void: no '32-bit indices' echo (knob not proven)"
        res[n] = r
        rows.append((n, k.case(n).get("class", "-"), r))
    out = ["E4w: 32-bit indices (control ix-c: E414's five triangles over the 16-bit list)",
           table(rows, ["job", "class", "result vs ix-c"]), ""]
    if ctl is None:
        out.append("SUMMARY: cannot tell: control ix-c void, failed, or not 15 vertices")
        return "\n".join(out), res
    c25 = pred1(preds, "ix-25", "result")
    if c25 and not res.get("ix-25", "").startswith(c25):
        out.append(f"SUMMARY: cannot tell: control ix-25 must reproduce S1's `{c25}`: {res.get('ix-25', 'not run')}")
        return "\n".join(out), res
    cond = collections.defaultdict(list)
    for n, r in res.items():
        if n.startswith("ix32"):
            cond[re.sub(r"-r\d$", "", n)].append(r)
    entries = []
    for c, rs in cond.items():
        for i, r in enumerate(rs, 1):
            if r.startswith("void: skipped"):
                continue                    # a replicate the hypothesis limit skipped: the condition rests on one run
            for v, m, s in preds.get(f"{c}-r{i}", {}).get("result", []):
                if r.startswith("void"):
                    entries.append((m, s, None))
                else:
                    entries.append((m, s, any(r.startswith(x) for x in v.split("|")) if not v.startswith("not ") else
                                    not r.startswith(v[4:])))
    per = "; ".join(f"{c}: {rs}" for c, rs in cond.items())
    if not entries:
        out.append(f"SUMMARY: control ok; cannot tell: no usable run ({per})")
        return "\n".join(out), res
    out.append(f"SUMMARY: controls ok; {per}; {support(entries)}")
    return "\n".join(out), res


# ------------------------------------------------------------------------------------------------ E5
def fate(k: Kept, n):
    """(lost vertex ids, object sizes) of one job's dump with q164_fate's functions; None without a dump."""
    p, t = k.dump(n, "param.bin"), k.dump(n, "tadata.bin")
    if not p or not t:
        return None
    if str(FATE) not in sys.path:
        sys.path.insert(0, str(FATE))
    import q164_fate as Q
    try:
        per, ws, O = Q.objects(p, t)
    except Exception:
        return None
    seen, sizes = collections.Counter(), []
    for a, (nv, e) in sorted(O.items()):
        sizes.append(nv)
        for vv in Q.verts(ws, per, a, nv, e):
            if vv is not None:
                seen[vv] += 1
    return [i for i in range(126) if seen[i] == 0], sizes


def score_e5(k: Kept, preds):
    """E5.  S1b fix (score_geo.py:374-386): every model's value is the FROZEN one (HO is the base histogram, not 'any
    count but HD's'): a condition is a model's in r of r runs, 'neither' when no frozen value matches (the count then
    printed with how often it repeats), split otherwise.  Lost vertices from q164_fate (vertex_lost 1/0, lost_ids)."""
    rows, cnt, cls, lost = [], {}, {}, {}
    for n in k.names():
        v = k.void(n)
        if v:
            rows.append((n, "NODATA: " + v, "", "", ""))
            continue
        txt = k.out(n)
        c = k.case(n).get("class", "ok")
        want = sorted(set(re.findall(r"--vdm (\d)\^=", k.case(n).get("args", ""))))
        got = sorted(set(re.findall(r"\^(\d)", (re.search(r"\(VDM words([^)]*)\)", txt) or [None, ""])[1])))
        if c == "ok" and want != got:
            rows.append((n, f"NODATA: echoed VDM words {got}, table {want}", "", "", ""))
            continue
        m = re.search(r"o0 mixed (0x[0-9a-f]+) x(\d+)", txt)
        cls[n] = c
        if m and c == "ok":
            cnt[n] = int(m[2])
        f = fate(k, n) if c == "ok" else None
        if f is not None:
            lost[n] = f
        rows.append((n, c, int(m[2]) if m else "-", " ".join(map(str, f[0])) if f else "-",
                     ",".join(map(str, f[1])) if f else "-"))
    out = ["E5: o0 histogram (count of 0xff203040), outcome and lost vertices per job",
           table(rows, ["job", "class", "count", "lost vertices", "object sizes"]), ""]
    ctl = {n: int(v) for n, v in control_rows(preds, "o0_mixed_x").items()}
    if not ctl or any(cnt.get(c) != v for c, v in ctl.items()):
        out.append(f"SUMMARY: cannot tell: controls did not reproduce E702 ({ {c: cnt.get(c) for c in ctl} } wanted {ctl})")
        return "\n".join(out), {}
    conds = collections.OrderedDict()
    for n in preds:
        if n in ctl:
            continue
        conds.setdefault(re.sub(r"-r\d$", "", n), []).append(n)
    res = []
    for cond, names in conds.items():
        if any(n not in cls for n in names):
            res.append(f"{cond}: cannot tell (a run is void or was skipped)")
            continue
        # per model and run: the model holds on the run if every one of its predictions for the run holds; a run
        # without a dump leaves a fate prediction unknown (None)
        per = collections.defaultdict(dict)
        for n in names:
            for q, lst in preds[n].items():
                for v, m, s in lst:
                    if q == "o0_mixed_x":
                        r = cnt.get(n) == int(v)
                    elif q == "outcome":
                        r = cls.get(n) == v
                    elif q == "vertex_lost":
                        r = (bool(lost[n][0]) == (v == "1")) if n in lost else None
                    elif q == "lost_ids":
                        r = (" ".join(map(str, lost[n][0])) == v) if n in lost else None
                    else:
                        continue
                    prev = per[m].get(n, True)
                    per[m][n] = None if prev is None or r is None else prev and r
        vals = [(cnt.get(n, cls.get(n)), " ".join(map(str, lost[n][0])) if n in lost else "?") for n in names]
        tally = {m: [d.get(n) for n in names] for m, d in per.items()}
        full = [m for m, r in tally.items() if all(x is True for x in r)]
        if full:
            res.append(f"{cond}: {'/'.join(full)} ({len(names)} of {len(names)})")
        elif any(None in r for r in tally.values()) and not any(sum(x is True for x in r) for r in tally.values()):
            res.append(f"{cond}: cannot tell (no fate: dump missing) {vals}")
        elif all(not any(x is True for x in r) for r in tally.values()):
            c_ = collections.Counter(vals).most_common(1)[0]
            res.append(f"{cond}: neither frozen model ({', '.join(tally)}): {c_[0][0]} in {c_[1]} of {len(vals)}")
        else:
            best = max(tally.items(), key=lambda kv: sum(x is True for x in kv[1]))
            res.append(f"{cond}: HI ({best[0]} in {sum(x is True for x in best[1])} of {len(names)}: not a function "
                       f"of the words) {vals}")
    # HC (state carry, S1b): the a = 8 runs with and without a reset before them
    if "r-n8-a8" in conds and "r-n8-a8-nr" in conds:
        pat = lambda c: sorted(" ".join(map(str, lost[n][0])) if n in lost else "?" for n in conds[c])
        a, b = pat("r-n8-a8"), pat("r-n8-a8-nr")
        res.append(f"HC (state carry): reset {a} vs no reset {b}: " + ("cannot tell (a fate missing)" if "?" in a + b
                   else "the same lost-vertex pattern (no carry shown)" if a == b else "DIFFERENT patterns"))
    # S1b review: conditions whose runs are all `repeat` (S1's post-hoc fits run again) are printed apart
    rep_c = {c for c, ns in conds.items() if all(s == "repeat" for n in ns for qs in preds[n].values() for v, m, s in qs)}
    held = [x for x in res if x.split(":", 1)[0] not in rep_c]
    rept = [x for x in res if x.split(":", 1)[0] in rep_c]
    out.append("SUMMARY: controls reproduce E702; held out: " + ("; ".join(held) or "none")
               + "; repeat only: " + ("; ".join(rept) or "none"))
    return "\n".join(out), {}


# ------------------------------------------------------------------------------------------------ E8
def _model(nobj, cmp_, mv):
    import numpy as np
    zs = [float(np.float32(z)) for z in (0.2, 0.5, 0.8)]
    base = [(16, 16), (112, 40), (40, 112)]
    depth = np.full((128, 128), 0.25)
    cover = np.zeros((128, 128), dtype=int)
    ne = np.zeros((128, 128), dtype=bool)
    ys, xs = np.mgrid[0:128, 0:128]
    px, py = xs + 0.5, ys + 0.5
    for oi in range(nobj):
        dx, dy = mv if oi == 1 else (0, 0)
        (x0, y0), (x1, y1), (x2, y2) = [(a + dx, b + dy) for a, b in base]
        det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        l1 = ((px - x0) * (y2 - y0) - (x2 - x0) * (py - y0)) / det
        l2 = ((x1 - x0) * (py - y0) - (px - x0) * (y1 - y0)) / det
        l0 = 1 - l1 - l2
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        z = l0 * zs[0] + l1 * zs[1] + l2 * zs[2]
        ne |= (inside & (np.minimum(np.minimum(l0, l1), l2) < 2e-4)) | (inside & (np.abs(z - depth) < 1e-4))
        if cmp_ == "less":
            draw = inside & (z < depth)
            depth = np.where(draw, z, depth)
            cover = np.where(draw, oi + 1, cover)
    return cover, ~ne


def score_e8(k: Kept, preds):
    import numpy as np
    GREEN, RED = 0xff00ff00, 0xffff0000
    rows, miss, void = [], {}, []
    for n in k.names():
        v = k.void(n)
        m = re.match(r"o(\d)-(less|never)-?(m[AB]|ctl)?", n)
        img = np.array(rows_of(k.out(n) or ""), dtype=np.int64)
        if v or not m or img.shape != (128, 128):
            void.append(n)
            rows.append((n, "NODATA: " + (v or "no 128x128 image")))
            continue
        mv = {"mA": (32, 16), "mB": (-16, 24), "ctl": (0, 0), None: (0, 0)}[m[3]]
        cover, valid = _model(int(m[1]), m[2], mv)
        obs = np.where(img == GREEN, 1, np.where(img == RED, 2, 0))
        d = int(((obs != cover) & valid).sum())
        miss[n] = d
        rows.append((n, f"{int(valid.sum())} scored", f"{d} differ", f"green {(obs == 1).sum()} red {(obs == 2).sum()}"))
    out = ["E8a: two objects over a loaded depth (numpy ISP model; edge and depth-tie pixels excluded)", table(rows, ["job", "pixels", "model", "image"]), ""]
    ctls = ["o1-less-ctl", "o1-never-ctl"]
    if any(c not in miss or miss[c] != 0 for c in ctls):
        out.append(f"SUMMARY: cannot tell: one-object controls void or not equal to the model ({ {c: miss.get(c) for c in ctls} })")
    elif void:
        out.append(f"SUMMARY: cannot tell: void jobs {void}")
    else:
        bad = [n for n in miss if miss[n]]
        out.append("SUMMARY: controls pass; two-object jobs " + ("all equal the list-order ISP model" if not bad else f"differ from the model: {bad}"))
    return "\n".join(out), {}


def score_e8b(k: Kept, preds):
    """Overlap winner (the colour with more pixels).  Controls: the frozen control rows (every model predicts the same
    winner there); hypotheses: those consistent with every held-out and replicate job."""
    GREEN, RED = 0xff00ff00, 0xffff0000
    rows, win, void = [], {}, []
    for n in k.names():
        v = k.void(n)
        flat = [x for r in rows_of(k.out(n) or "") for x in r]
        g, r_ = flat.count(GREEN), flat.count(RED)
        if v or g + r_ == 0:
            void.append(n)
            rows.append((n, "NODATA: " + (v or "no green or red pixel")))
            continue
        win[n] = "red" if r_ > g else "green"
        rows.append((n, g, r_, win[n]))
    out = ["E8b: overlap winner (colour with more pixels)", table(rows, ["job", "green px", "red px", "winner"]), ""]
    ctl = control_rows(preds, "overlap_winner")
    bad = {c: win.get(c) for c, v in ctl.items() if win.get(c) != v}
    if not ctl or bad:
        out.append(f"SUMMARY: cannot tell: controls failed or void ({bad} wanted {ctl})")
        return "\n".join(out), {}
    if void:
        out.append(f"SUMMARY: cannot tell: void jobs {void}")
        return "\n".join(out), {}
    entries = []
    for n, w in win.items():
        if n in ctl:
            continue
        for v, m, s in preds.get(n, {}).get("overlap_winner", []):
            entries.append((m, s, v == w))
    out.append(f"SUMMARY: controls pass; {support(entries)}")
    return "\n".join(out), {}
