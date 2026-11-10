"""Scorers of the S1 geometry stages.  Written before the run; frozen with the predictions.

Rules common to every scorer: a job whose data is empty, missing, or has an rc that is not a result of the tool is NODATA
(tested first, never a match); a control that fails makes the stage's verdict "cannot tell"; every scorer ends with one
line `SUMMARY: ...` (a verdict, or `cannot tell: why`).
"""
from __future__ import annotations

import re
import struct

from s1lib import Kept, knob_value, load_preds, outcome, peak_status, reg_series, rows_of, runs, table, timeline


def pred1(preds, name, q, model=None):
    for v, m, s in preds.get(name, {}).get(q, []):
        if model is None or m == model:
            return v
    return None


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


# ------------------------------------------------------------------------------------------------ E1
def score_e1(k: Kept, preds):
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
    g = lambda n: res.get(n, dict(void="not run"))
    usable = lambda n: not g(n).get("void")
    valid = lambda n: usable(n) and g(n)["reach"] and g(n)["nparts"] > 1      # the raise is defined only then
    if not usable("c-1500-0x422") or g("c-1500-0x422")["raised"]:
        out.append("SUMMARY: cannot tell: control c-1500-0x422 void or raised (E704 reproduction failed)")
        return "\n".join(out), res
    for n in ("p-1350-0x3e0", "p-1350-0x300", "p-900-0x200"):
        if valid(n) and not g(n)["raised"]:
            out.append(f"SUMMARY: METHOD BROKEN: positive control {n} reaches thr0 and does not raise; nothing is concluded")
            return "\n".join(out), res
    pos_ok = [n for n in ("p-1350-0x3e0", "p-1350-0x300", "p-900-0x200") if valid(n) and g(n)["raised"]]
    d = ["d-1500-0x3e0", "d-1500-0x3e0-r2"]
    if not all(valid(n) for n in d):
        out.append("SUMMARY: cannot tell: a decisive job (d-1500-0x3e0, two runs) is void or its second run does not reach thr0")
        return "\n".join(out), res
    dr = [g(n)["raised"] for n in d]
    if dr[0] != dr[1]:
        out.append("SUMMARY: cannot tell: the two runs of d-1500-0x3e0 disagree (third run; if still split, not a function of the words)")
        return "\n".join(out), res
    ladder = lambda P: sorted((int(re.search(r"l-(\d+)-", n)[1]), g(n)) for n in res if n.startswith("l-") and n.endswith(P) and usable(n))
    if all(dr):
        hi = [n for n in ("d-1500-0x410", "d-1500-0x420")]
        if not all(valid(n) for n in hi):
            out.append("SUMMARY: cannot tell: d-1500-0x3e0 raises but the 0x410/0x420 cells are void or do not reach")
        elif any(g(n)["raised"] for n in hi):
            out.append("SUMMARY: cannot tell: d-1500-0x3e0 raises and a higher P raises too (not HC, not HA/HS)")
        else:
            e = g("d-1500-0x400")
            edge = "edge cell void" if not valid("d-1500-0x400") else ("raises: limit raised <= 0x400" if e["raised"] else "no raise: limit <= 0x3fe")
            out.append(f"SUMMARY: HC (ceiling): 0x3e0 raises 2 of 2, 0x410 and 0x420 do not; {edge}")
        return "\n".join(out), res
    if not pos_ok:
        out.append("SUMMARY: cannot tell: d-1500-0x3e0 does not raise but no positive control raised")
        return "\n".join(out), res
    l422, l3e0 = ladder("0x422"), ladder("0x3e0")
    step = next((V for V, r in l422 if r["dw36"] == 3), None)
    vanish = next((V for V, r in l3e0 if valid_ladder(r) and not r["raised"]), None)
    if vanish is None:
        out.append("SUMMARY: HS (scene-bound otherwise): the raise persists on the whole 0x3e0 ladder and fails only at 1500")
    elif step is None:
        out.append("SUMMARY: cannot tell: the 0x422 ladder shows no dword-36 step")
    elif vanish == step:
        out.append(f"SUMMARY: HA (global list): the raise vanishes at V = {vanish}, where dword 36 steps")
    else:
        out.append(f"SUMMARY: HS (scene-bound otherwise): the steps differ (dword 36 at {step}, raise gone at {vanish})")
    return "\n".join(out), res


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
    param = k.dump(n, f"tri.{K}.param.bin") or k.dump(n, "param.bin")
    wh = walk_head(param)
    return dict(K=K, geo=geo, peak=peak_status(tl) if tl else None, walk=(wh - 1) if wh else None, tl=tl, txt=txt)


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
    c2 = res.get("u-2f-0x38", dict(void="not run"))
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
    rows, bad, void, n_ok = [], [], [], 0
    for n in k.names():
        j = live_job(k, preds, n)
        if j["void"]:
            void.append(n)
            rows.append((n, "NODATA: " + j["void"], "", "", ""))
            continue
        oc = outcome(j["txt"], k.dmesg(n))
        want = pred1(preds, n, "outcome")
        prs, _ = runs(j["tl"])
        hit = None if want is None else (oc == "overflow") == (want == "overflow")
        if hit is False:
            bad.append(n)
        n_ok += bool(hit)
        rows.append((n, oc, want, {True: "yes", False: "NO", None: "-"}[hit], len(prs)))
    out = ["E2b: boundary (E625's overflow rule, held out on K-triangle scenes) and partial-render counts",
           table(rows, ["job", "outcome", "predicted", "match", "parts"])]
    if not k.names():
        s = "cannot tell: no jobs kept"
    elif void:
        s = f"cannot tell: void jobs {void}"
    elif bad:
        s = f"E625's overflow rule REFUTED on K-triangle scenes at {bad}"
    else:
        s = f"E625's overflow rule holds on {n_ok} boundary/count jobs (held out); the (k, s) interval from the counts is printed above"
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


def _hits(preds, n, d):
    hit = {}
    for q, lst in preds.get(n, {}).items():
        for v, m, s in lst:
            ok = None
            if q == "object":
                got = {"none": "none", "written-unlisted": "written-unlisted"}.get(d["state"], "present")
                ok = v == got if v != "?" else None
            elif d["state"] != "present":
                ok = None
            elif q == "nvert":
                ok = (d["nvert"] >= 4) if v == ">=4" else (d["nvert"] == int(v))
            elif q == "rhw_word":
                ok = all(w == int(v, 16) for w in d["rhw"])
            elif q == "object_equals_default":
                ok = all(w == 0x3f800000 for w in d["rhw"]) and _xy(d) == DEFAULT_XY
            elif q == "xy_pixels":
                ok = ";".join(f"{x:g},{y:g}" for x, y in _xy(d)) == v
            elif q == "packed_24bit":
                ok = ";".join(f"{x};{y}" for y, x, _ in d["packed"]) == v
            if ok is not None:
                hit[(q, m)] = ok
    return hit


def score_e3(k: Kept, preds):
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
        rows.append((n, d["state"], d.get("nvert", "-"), xy, " ".join(f"{m}:{'Y' if o else 'n'}" for (q, m), o in dec[n][1].items())))
    out = ["E3: object decode per job", table(rows, ["job", "object", "nvert", "x,y (pixels)", "predictions matched"]), ""]
    controls = {"e3w-w1": ("object_equals_default", "E651"), "e3z-flat099": ("object_equals_default", "E651"),
                "e3c-w1": ("object_equals_default", "E651"), "e3o-x1000": ("object", "HO-guard"),
                "e3k-ctl": ("object", "w < clamp removes (E194)"), "e3f-ctl": ("packed_24bit", "HF-trunc")}
    failed = [c for c, (q, m) in controls.items() if c not in dec or not dec[c][1].get((q, m))]
    if failed:
        out.append(f"SUMMARY: cannot tell: controls failed or void: {failed}"
                   + (f" (void jobs: {void})" if void else ""))
        return "\n".join(out), {}
    def tally(names, q, m):
        r = [dec[n][1].get((q, m)) for n in names if n in dec]
        return r if r and None not in r else None
    parts = []
    rz = tally(["e3w-w1e3", "e3w-w1e5"], "rhw_word", "RZ32(1/w) [fit: mte/rhw, 9 vertices]")
    rn = tally(["e3w-w1e3", "e3w-w1e5"], "rhw_word", "RN32(1/w)")
    parts.append("stored 1/w: " + ("RZ32 (held out on w = 1e-3, 1e-5)" if rz and all(rz) else "RN32" if rn and all(rn) else "neither rule fits / void"))
    fl = [dec[n][0]["state"] for n in ("e3z-flat101", "e3z-flatm101") if n in dec]
    parts.append("removed triangle: " + ("HR-none (no object)" if fl == ["none", "none"] else "HR-obj (object written, unlisted)" if fl == ["written-unlisted"] * 2 else f"mixed/void {fl}"))
    cut = [dec[n][0].get("nvert") for n in ("e3z-cut-p", "e3z-cut-m") if n in dec]
    parts.append("cut triangle: " + ("HC-poly (>= 4 vertices)" if cut and all(c and c >= 4 for c in cut) else "HC-orig (3 vertices)" if cut and all(c == 3 for c in cut) else f"unclear {cut}"))
    off = {n: dec[n][0]["state"] for n in ("e3o-x8", "e3o-x64", "e3o-x128", "e3o-x512", "e3o-x1000") if n in dec}
    parts.append(f"off-target objects: {off}")
    f3 = tally(["e3f-r3"], "packed_24bit", "HF-trunc"), tally(["e3f-r3"], "packed_24bit", "HF-round")
    parts.append("fine grid: " + ("HF-trunc" if f3[0] and f3[0][0] else "HF-round" if f3[1] and f3[1][0] else "neither"))
    parts.append("WCLAMP: above -> " + dec.get("e3k-above", ({"state": "void"},))[0]["state"] + ", below -> " + dec.get("e3k-below", ({"state": "void"},))[0]["state"])
    out.append("SUMMARY: controls pass; " + "; ".join(parts) + (f"; void jobs {void}" if void else ""))
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


# ------------------------------------------------------------------------------------------------ E5
def score_e5(k: Kept, preds):
    rows, cnt, cls = [], {}, {}
    for n in k.names():
        v = k.void(n)
        if v:
            rows.append((n, "NODATA: " + v, "", ""))
            continue
        txt = k.out(n)
        c = k.case(n).get("class", "ok")
        want = sorted(set(re.findall(r"--vdm (\d)\^=", k.case(n).get("args", ""))))
        got = sorted(set(re.findall(r"\^(\d)", (re.search(r"\(VDM words([^)]*)\)", txt) or [None, ""])[1])))
        if c == "ok" and want != got:
            rows.append((n, f"NODATA: echoed VDM words {got}, table {want}", "", ""))
            continue
        m = re.search(r"o0 mixed (0x[0-9a-f]+) x(\d+)", txt)
        cls[n] = c
        if m and c == "ok":
            cnt[n] = int(m[2])
        rows.append((n, c, "vdm words ok", int(m[2]) if m else "-"))
    out = ["E5: o0 histogram (count of 0xff203040) and outcome per job", table(rows, ["job", "class", "knob", "count"]), ""]
    ctl = {"r-n8-a1": 2288, "r-n2-a9": 2821}
    if any(cnt.get(c) != v for c, v in ctl.items()):
        out.append(f"SUMMARY: cannot tell: controls did not reproduce E702 ({ {c: cnt.get(c) for c in ctl} } wanted {ctl})")
        return "\n".join(out), {}
    res = []
    for cond, base in (("r-n8-a7", 2285), ("r-n8-a12", 2028), ("r-n8-a8", None), ("r-n2-a32", None)):
        names = [f"{cond}-r{i}" for i in (1, 2, 3)]
        if cond == "r-n2-a32":
            hit = [cls.get(n) == "hang" for n in names]
        elif base:
            hit = [cnt.get(n) == base for n in names]
        else:
            hit = [(cnt.get(n) is not None and cnt[n] != 2288) for n in names]
        if any(n not in cls for n in names):
            res.append(f"{cond}: cannot tell (a run is void or was skipped)")
        else:
            h = sum(hit)
            res.append(f"{cond}: " + ("HD (3 of 3)" if h == 3 else "HO (0 of 3)" if h == 0 else f"HI ({h} of 3: not a function of the words)"))
    out.append("SUMMARY: controls reproduce E702; " + "; ".join(res) + ".  (r-n8-a8 counts any change from the base histogram; the lost-vertex fate needs q164_fate.py)")
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
    if win.get("t-opq-near") != "red" or win.get("t-opq-far") != "green":
        out.append(f"SUMMARY: cannot tell: opaque controls failed or void (near {win.get('t-opq-near')}, far {win.get('t-opq-far')})")
        return "\n".join(out), {}
    if void:
        out.append(f"SUMMARY: cannot tell: void jobs {void}")
        return "\n".join(out), {}
    hyps = {}
    for n, w in win.items():
        for v, m, s in preds.get(n, {}).get("overlap_winner", []):
            hyps.setdefault(m, []).append(v == w)
    ok = [m for m, r in hyps.items() if all(r)]
    out.append("SUMMARY: controls pass; hypotheses consistent with all six jobs: " + (", ".join(ok) if ok else "none"))
    return "\n".join(out), {}
