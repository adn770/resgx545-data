# SPDX-License-Identifier: MIT
"""Scorers of p6-rd (Q276: is an o4..o7 write stored, does the predicate gate it), p6-l3 (which instance's o3 enters the OR) and p6-s
(the walk in E406's setup).  Written before the run; frozen with the predictions.  Standard library only.
Plan: closing6/pixel/exp-pixel-r6.md sections 2.1 to 2.7.  Readers: R4's grid reader and decode (score_o4.py, pinned), R5's
configuration reader for the tag-5 words (score_o5.read_cfg) and the controls of R5 (G-o4 on c-e709, G-o1 on c-u / r-u, c-all4 5:1).
p6-rd.  TRI = the pixels whose word is their own in both c-rd-0 jobs (the job's marker, tag 1, the x job's high half decoding to
the pixel's x and the y job's to its y); fewer than 300: cannot tell.  At each TRI pixel of each job the own word is labelled: "T:B"
(the job's marker, decoding to the pixel), "D" (the job's marker, another source), "O" (another marker; recorded with tag and bits),
"bg".  A configuration's class (frozen rule): X if fewer than 5 percent of the TRI pixels carry the job's marker in both jobs;
O:T.B if >= 90 percent carry one other marker's word T:B in both jobs; else the label holding >= 90 percent in both jobs, named by
the configuration's labels (S, A0, A4) or W:T.B; else cannot tell (the distribution is printed).
Controls: G-o4 (c-e709), G-o1 (c-u), c-all4 5:1 (else the stage is void), c-ow (bits 1 at >= 95 percent of TRI), c-rd-0 (W_A =
1:2 at >= 95 percent of TRI), c-prd-0 k1 and k7 (lane labels, >= 95 percent of each lane's TRI pixels in both jobs).  The BRIDGE
controls (the driver's gate): c-e709, c-u, c-ow, c-rd-0.  rd vector: the classes of rd-1..rd-7; the models whose frozen vector it
matches (H-MOD4 implies H-FOUR); n-rd-1, n-rd-4 not S; x-rd-4, x-rd-5 S with the new tag (scored only when rd-j reads S); the
replicate of rd-4 reads rd-4's class.  Predicate rows prd-j-k: scored only if rd-j reads S and both c-prd-0 rows pass; a lane reads a
label with >= 95 percent of its TRI pixels in both jobs; survivors among gated / ignored / never; "the predicate gates the o_j write"
iff gated survives alone.
p6-l3.  Each job's tag-5 label (R4's class rule within one job: >= 10 words of one label, no other above 2).  Controls p3-pa-k0 and
-k3 as R5; H-Y1 / H-Y2 / H-YN by the y jobs of k = 1 and 2; the x jobs 5:1.
p6-s.  c-s-all4: tags 2..4 <= 2 a job and tag 5 >= 10 a job (the job's marker), else the set is void; s-0..s-7, s-n4: the
configuration's tag-5 class (R5's reader) against H-OR and H-OWN4; r-u: G-o1 (the restore check)."""
from __future__ import annotations

import collections
import sys

sys.dont_write_bytecode = True

import rd_r4lib as L  # noqa: E402
import rd_rdmodel as RM  # noqa: E402
import rd_score_o4 as R4  # noqa: E402
import rd_score_o5 as S5  # noqa: E402
import scorekit as SK  # noqa: E402

BG = L.BG


def marker_of(preds, cfg):
    mk = preds.get(f"{cfg}-x", {}).get("marker", [])
    return int(mk[0][0], 16) if mk else None


def coord(v, w=64):
    return round(R4.f32_hi(v) * w / 2 + w / 2 - .5)


def grids(k, cfg, xname=None, yname=None):
    nx, ny = xname or f"{cfg}-x", yname or f"{cfg}-y"
    vv = k.void(nx) or k.void(ny)
    if vv:
        return None, vv
    for n in (nx, ny):
        if k.case(n).get("class") not in ("ok", None, ""):
            return None, f"class {k.case(n).get('class')}"
    gx, gy = R4.read_grid(k, nx), R4.read_grid(k, ny)
    if gx is None or gy is None:
        return None, "no 64x64 pixel rows"
    return (gx, gy), None


def own_label(v, x, y, ax, m):
    if v == BG:
        return "bg"
    lo = v & 0xffff
    if lo >> 6 != m:
        return f"O:{lo >> 6:#x}:{lo & 15}.{(lo >> 4) & 3}"
    c = coord(v)
    if c != (x if ax == "x" else y):
        return "D"
    return f"{lo & 15}:{(lo >> 4) & 3}"


def tri_of(k, preds):
    """(TRI pixel list, why-not)."""
    g, why = grids(k, "c-rd-0")
    if g is None:
        return None, f"c-rd-0 {why}"
    m = marker_of(preds, "c-rd-0")
    tri = [(x, y) for y in range(64) for x in range(64)
           if own_label(g[0][y][x], x, y, "x", m).startswith("1:") and own_label(g[1][y][x], x, y, "y", m + 1).startswith("1:")]
    if len(tri) < RM.TRI_MIN:
        return None, f"TRI has {len(tri)} pixels (< {RM.TRI_MIN})"
    return tri, None


def job_labels(g, tri, m):
    """Counters of own-pixel labels over TRI for the x job and the y job."""
    return [collections.Counter(own_label(gg[y][x], x, y, ax, mm) for x, y in tri) for gg, ax, mm in ((g[0], "x", m), (g[1], "y", m + 1))]


def read_rd(k, preds, cfg, tri, xname=None, yname=None):
    g, why = grids(k, cfg, xname, yname)
    if g is None:
        return dict(void=why)
    m = marker_of(preds, cfg)
    cs = job_labels(g, tri, m)
    n = len(tri)
    names = {}
    for item in preds.get(f"{cfg}-x", {}).get("labels", [("",)])[0][0].split():
        c, v = item.split("=")
        names.setdefault(v, c)
    own = [sum(v for lab, v in c.items() if not lab.startswith("O:") and lab != "bg") / n for c in cs]
    if all(o < RM.X_SHARE for o in own):
        o_top = [c.most_common(1)[0] for c in cs]
        if all(lab.startswith("O:") and v / n >= RM.O_SHARE for lab, v in o_top) and o_top[0][0].split(":", 2)[1] == o_top[1][0].split(":", 2)[1]:
            return dict(void=None, cls="O:" + o_top[0][0].split(":", 2)[2], dist=cs)
        return dict(void=None, cls="X", dist=cs)
    tops = [c.most_common(1)[0] for c in cs]
    if tops[0][0] == tops[1][0] and all(v / n >= RM.CLASS_SHARE for _, v in tops) and tops[0][0] not in ("bg", "D"):
        lab = tops[0][0]
        if lab.startswith("O:"):
            return dict(void=None, cls=None, dist=cs)
        return dict(void=None, cls=names.get(lab, f"W:{lab.replace(':', '.')}"), dist=cs)
    return dict(void=None, cls=None, dist=cs)


def lanes_read(k, preds, cfg, tri):
    """(tuple of 4 lane labels or None per lane, void)."""
    g, why = grids(k, cfg)
    if g is None:
        return None, why
    m = marker_of(preds, cfg)
    out = []
    for lane in range(4):
        px = [(x, y) for x, y in tri if RM.lane_of(x, y) == lane]
        if not px:
            out.append(None)
            continue
        cs = job_labels(g, px, m)
        tops = [c.most_common(1)[0] for c in cs]
        ok = tops[0][0] == tops[1][0] and all(v / len(px) >= RM.LANE_SHARE for _, v in tops) and ":" in tops[0][0] \
            and not tops[0][0].startswith("O:")
        out.append(tops[0][0] if ok else None)
    return tuple(out), None


def share(k, preds, cfg, tri, label):
    g, why = grids(k, cfg)
    if g is None:
        return None, why
    cs = job_labels(g, tri, marker_of(preds, cfg))
    return min(c.get(label, 0) / len(tri) for c in cs), None


def frozen(preds, name, q):
    return {m: v for v, m, st in preds.get(name, {}).get(q, [])}


def r5_controls(k, preds, out, restore=None):
    """G-o4 on c-e709, G-o1 on c-u (or the restore rows), c-all4 5:1, the code of R5's score_o5."""
    ctl = {}
    if restore is None:
        r = S5.read_cfg(k, preds, "c-e709")
        if r["void"]:
            ctl["G-o4 c-e709"] = None
        else:
            p5 = r["src"][5]
            cx5 = collections.Counter({("A" if lab.startswith("5:") else lab): n for lab, n in r["cx"].items()})
            cy5 = collections.Counter({("A" if lab.startswith("5:") else lab): n for lab, n in r["cy"].items()})
            okc, why = R4.g_o4_control(cx5, cy5, len(p5), sum(1 for s in p5 if s[0] & 1 or s[1] & 1), r["x13"])
            ctl["G-o4 c-e709"] = okc
            if not okc:
                out.append(f"G-o4 control c-e709: FAIL {why}")
    cu = restore or "c-u"
    ru = S5.read_cfg(k, preds, cu)
    crit = float(preds.get(f"{cu}-x", {}).get("ctl_min_frac", [("0.98",)])[0][0])
    if ru["void"]:
        ctl[f"G-o1 {cu}"] = None
        out.append(f"G-o1 control {cu}: NODATA ({ru['void']})")
    else:
        n2, n12 = len(ru["src"][2]), len(ru["src"][12])
        frac = n2 / (n2 + n12) if n2 + n12 else 0.0
        ctl[f"G-o1 {cu}"] = n2 + n12 >= R4.MIN_SOURCES and frac >= crit
        out.append(f"G-o1 control {cu}: tag-2 fraction {frac:.3f} of {n2 + n12} sources (frozen >= {crit})")
    return ctl


def score_rd(k, preds):
    out = []
    ctl = r5_controls(k, preds, out)
    r = S5.read_cfg(k, preds, "c-all4")
    all4 = None if r["void"] or r["cls"] is None else r["cls"] == "5:1"
    out.append(f"c-all4: {'NODATA ' + r['void'] if r['void'] else 'reads ' + str(r['cls'])} (frozen 5:1; else the stage is void)")
    tri, why = tri_of(k, preds)
    out.append(f"TRI: {len(tri)} pixels" if tri else f"TRI: cannot tell ({why})")
    if tri:
        s_ow, w1 = share(k, preds, "c-ow", tri, "1:1")
        ctl["c-ow (last o0 write)"] = None if s_ow is None else s_ow >= RM.CTL_SHARE
        out.append(f"c-ow: bits 1 at {s_ow if s_ow is None else round(s_ow, 3)} of TRI (frozen >= {RM.CTL_SHARE}){' ' + w1 if w1 else ''}")
        s_rd, w2 = share(k, preds, "c-rd-0", tri, "1:2")
        ctl["c-rd-0 (readback)"] = None if s_rd is None else s_rd >= RM.CTL_SHARE
        out.append(f"c-rd-0: W_A at {s_rd if s_rd is None else round(s_rd, 3)} of TRI (frozen >= {RM.CTL_SHARE}){' ' + w2 if w2 else ''}")
    else:
        ctl["c-ow (last o0 write)"] = ctl["c-rd-0 (readback)"] = None
    bridge = dict(ctl)
    gate = SK.gate(bridge)
    cprd = {}
    for kk in RM.CPRD_K:
        cfg = f"c-prd-0-k{kk}"
        if not tri:
            cprd[cfg] = None
            continue
        lr, why = lanes_read(k, preds, cfg, tri)
        want = tuple(preds.get(f"{cfg}-x", {}).get("lanes", [("",)])[0][0].split(","))
        cprd[cfg] = None if lr is None or None in lr else lr == want
        out.append(f"{cfg}: lanes {lr if lr else 'NODATA ' + why} (frozen {','.join(want)})")
    pgate = SK.gate({**ctl, **cprd})
    out.append("bridge controls: " + ("PASS" if gate.ok else "; ".join(gate.problems)))
    stage_ok = gate.ok and all4 is True
    if all4 is not True:
        out.append("c-all4 does not read 5:1: the stage is void (" + ("cannot tell" if all4 is None else "FAILED") + ")")
    # ---- the rd vector
    cls = {}
    for j in RM.RD_J:
        cfg = f"rd-{j}"
        rr = read_rd(k, preds, cfg, tri) if tri else dict(void="no TRI")
        cls[cfg] = None if rr["void"] else rr["cls"]
        out.append(f"{cfg}: " + (f"NODATA ({rr['void']})" if rr["void"] else f"class {rr['cls']}  x {dict(rr['dist'][0].most_common(3))}  "
                                  f"y {dict(rr['dist'][1].most_common(3))}"))
    vec = tuple(cls[f"rd-{j}"] for j in RM.RD_J)
    out.append("rd vector (j = 1..7): " + " ".join(str(v) for v in vec))
    mvec = {}
    for item in preds.get("@p6-rd", {}).get("models", [("",)])[0][0].split():
        mn, v = item.split("=")
        mvec[mn] = tuple(v.split(","))
    fits = [mn for mn, fv in mvec.items() if None not in vec and all(RM.matches(f, r) for f, r in zip(fv, vec))]
    ind = {}
    for cfg in ("n-rd-1", "n-rd-4", "x-rd-4", "x-rd-5"):
        rr = read_rd(k, preds, cfg, tri) if tri else dict(void="no TRI")
        ind[cfg] = None if rr["void"] else rr["cls"]
        want = preds.get(f"{cfg}-x", {}).get("class", [("",)])[0][0]
        if cfg.startswith("x-") and cls.get(f"rd-{cfg[-1]}") != "S":
            out.append(f"{cfg}: {ind[cfg]} (rd-{cfg[-1]} does not read S: cannot tell by design)")
            continue
        st = None if ind[cfg] is None else RM.matches(want, ind[cfg])
        out.append(f"{cfg}: read {ind[cfg]}, frozen {want}: {SK._state(st)}")
        ind[cfg + ":state"] = st
    rr = read_rd(k, preds, "rd-4", tri, "rd-4-x-rep", "rd-4-y-rep") if tri and "rd-4-x-rep" in k.names() else dict(void="not run")
    rep = None if rr["void"] or rr["cls"] is None or cls["rd-4"] is None else rr["cls"] == cls["rd-4"]
    out.append(f"replicate rd-4: {rr.get('cls') if not rr['void'] else 'NODATA ' + rr['void']} vs {cls['rd-4']}: {SK._state(rep)}")
    indep = [ind.get(c + ":state") for c in ("n-rd-1", "n-rd-4", "x-rd-4", "x-rd-5") if c + ":state" in ind]
    # ---- predicate rows
    pver = {}
    for j in RM.PRD_J:
        if cls.get(f"rd-{j}") != "S":
            pver[j] = f"cannot tell by design (rd-{j} reads {cls.get(f'rd-{j}')}, not S)"
            continue
        if not pgate.ok:
            pver[j] = "cannot tell (c-prd-0: " + "; ".join(pgate.problems) + ")"
            continue
        obs, surv = {}, set(RM.PMODELS)
        for kk in RM.PRD_K:
            cfg = f"prd-{j}-k{kk}"
            lr, why = lanes_read(k, preds, cfg, tri)
            obs[kk] = lr
            fz = frozen(preds, f"{cfg}-x", "lanes")
            if lr is None or None in lr:
                surv = None
                break
            surv &= {pm for pm, v in fz.items() if tuple(v.split(",")) == lr}
        if surv is None:
            pver[j] = f"cannot tell (a predicate row not decided: {obs})"
        else:
            pver[j] = ("the predicate gates the o%d write" % j if surv == {"gated"} else f"survivors {sorted(surv) or 'none'}") + f" (lanes {obs})"
        out.append(f"prd-{j}: {pver[j]}")
    # ---- verdict
    if not stage_ok:
        verdict = "cannot tell: " + ("; ".join(gate.problems) if not gate.ok else "c-all4 does not read 5:1")
    elif None in vec:
        verdict = "cannot tell: rd entries " + ", ".join(f"rd-{j}" for j, v in zip(RM.RD_J, vec) if v is None) + " not decided"
    else:
        name = "H-MOD4 (and so H-FOUR)" if "H-MOD4" in fits else (fits[0] if len(fits) == 1 else (" / ".join(fits) if fits else "none of the four"))
        verdict = f"rd vector {' '.join(vec)}: {name}"
        if rep is not True:
            verdict += f"; the replicate of rd-4 {'differs' if rep is False else 'is not decided'}"
        if False in indep:
            verdict += "; an independent row differs"
        verdict += "; " + "; ".join(f"o{j}: {v.split(' (lanes')[0]}" for j, v in pver.items())
    out.append("SUMMARY: " + verdict)
    return "\n".join(out), {"gate": gate, "controls": ctl, "vector": vec, "fits": fits, "pred": pver, "replicate": rep,
                            "independent": ind, "stage_ok": stage_ok, "tri": len(tri) if tri else 0}


def job_label(c):
    """R4's class rule within one job: the label with >= 10 words, no other above 2; 'none' if none above 2; else None."""
    big = [lab for lab, n in c.items() if n >= R4.MIN_WORDS]
    amb = [lab for lab, n in c.items() if R4.OTHER_MAX < n < R4.MIN_WORDS]
    if amb or len(big) > 1:
        return None
    return big[0] if big else "none"


def score_l3(k, preds):
    out, ctl, obs = [], {}, {}
    for kk in (0, 1, 2, 3):
        cfg = f"p3-pa-k{kk}"
        r = S5.read_cfg(k, preds, cfg)
        if r["void"]:
            obs[kk] = (None, None)
            out.append(f"{cfg}: NODATA ({r['void']})")
            continue
        obs[kk] = (job_label(r["cx"]), job_label(r["cy"]))
        out.append(f"{cfg}: x {obs[kk][0]} {dict(r['cx'])}  y {obs[kk][1]} {dict(r['cy'])}")
    for kk in (0, 3):
        cfg = f"p3-pa-k{kk}-x"
        want = (preds[cfg]["job_x"][0][0], preds[cfg]["job_y"][0][0])
        ctl[f"p3-pa-k{kk} reads as R5 {want[0]}/{want[1]}"] = None if None in obs[kk] else obs[kk] == want
    g = SK.gate(ctl)
    out.append("controls (determinism, as R5): " + ("PASS" if g.ok else "; ".join(g.problems)))
    xs = [obs[kk][0] for kk in (1, 2)]
    ys = (obs[1][1], obs[2][1])
    hy = {}
    for m in ("H-Y1", "H-Y2", "H-YN"):
        hy[m] = tuple(frozen(preds, f"p3-pa-k{kk}-x", "job_y")[m] for kk in (1, 2))
    if not g.ok:
        verdict = "cannot tell: controls " + "; ".join(g.problems)
    elif None in ys or None in xs:
        verdict = "cannot tell: a new row not decided"
    else:
        hit = [m for m, v in hy.items() if v == ys]
        verdict = (f"{hit[0]}" if hit else f"none of H-Y1, H-Y2, H-YN (y reads {ys[0]} at k = 1, {ys[1]} at k = 2)") + \
            f"; x jobs {xs[0]}, {xs[1]} (frozen 5:1)"
    out.append("SUMMARY: " + verdict)
    return "\n".join(out), {"gate": SK.gate({"(L3 does not stop the session)": True}), "controls": ctl, "obs": obs, "verdict": verdict}


def tag_counts(g, m):
    c = collections.Counter()
    for row in g:
        for v in row:
            if v != BG and ((v & 0xffff) >> 6) == m:
                c[v & 15] += 1
    return c


def score_s(k, preds):
    out = []
    g, why = grids(k, "c-s-all4")
    patt = None
    if g is not None:
        m = marker_of(preds, "c-s-all4")
        cs = [tag_counts(g[0], m), tag_counts(g[1], m + 1)]
        patt = all(sum(c[t] for t in (2, 3, 4)) <= 2 and c[5] >= 10 for c in cs)
        out.append(f"c-s-all4: tags by job {[dict(c) for c in cs]}: E406's pattern {SK._state(patt)}")
    else:
        out.append(f"c-s-all4: NODATA ({why})")
    ctl = r5_controls(k, preds, out, restore="r-u")
    obs = {}
    for c in [f"s-{j}" for j in range(8)] + ["s-n4"]:
        r = S5.read_cfg(k, preds, c)
        obs[c] = None if r["void"] else r["cls"]
        out.append(f"{c}: {'NODATA ' + r['void'] if r['void'] else 'reads ' + str(r['cls'])}  "
                   f"{'' if r['void'] else 'x ' + str(dict(r['cx'])) + ' y ' + str(dict(r['cy']))}")
    hs = {}
    for h in ("H-OR", "H-OWN4"):
        hs[h] = all(frozen(preds, f"{c}-x", "o4_word")[h] == obs[c] for c in obs) if None not in obs.values() else None
    gate = SK.gate(ctl)
    if patt is not True:
        verdict = "set void: c-s-all4 does not show E406's pattern" + ("" if patt is False else " (cannot tell)")
    elif None in obs.values():
        verdict = "cannot tell: " + ", ".join(c for c, v in obs.items() if v is None) + " not decided"
    else:
        hit = [h for h, v in hs.items() if v]
        verdict = (hit[0] if len(hit) == 1 else "neither H-OR nor H-OWN4") + ": " + " ".join(str(obs[c]) for c in obs)
    verdict += "; restore check (r-u G-o1) " + ("PASS" if gate.ok else "; ".join(gate.problems))
    out.append("SUMMARY: " + verdict)
    return "\n".join(out), {"gate": gate, "pattern": patt, "obs": obs, "models": hs, "verdict": verdict}
