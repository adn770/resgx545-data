"""S1 geometry stages: E1 (g-e1), E2 0x422 part (g-e2a), E3 (g-e3), E4 (g-e4), E8 (g-e8), E5 (g-e5).

Each function returns (rows, preds, needs, head).  Predictions are frozen by run/freeze_s1.sh.
The proposals are exp-dpm-geometry.md; deviations from them are listed in PREFLIGHT.md.
"""
from __future__ import annotations

import math
import pathlib
import shlex
import tomllib

from s1common import (BINS, DATA, REPO, RT_DPM, RT_DPM_SHORT, Row, f32, f32v, probe)

TE = REPO / "probes"


def build_green() -> str:
    """The plain green pixel shader of E704 (p1139-green.bin), built here from pix_op.s."""
    BINS.mkdir(exist_ok=True)
    src = (TE / "usse/templates/pix_op.s").read_text()
    out = BINS / "p1139-green.bin"
    p = probe.Probe(name="s1-green", question="", source="pix_op.s", params={}, inputs=["OP"],
                    cases=[["mov.skipinv.end o0, #0xFF00FF00"]], hypotheses={})
    text = probe.render(p, p.cases[0], src)
    probe._assemble(text, out)
    return str(out)


# ------------------------------------------------------------------------------------------ E1
E1_LADDER = (1380, 1410, 1440, 1470, 1491, 1497)     # whole triangles (V % 3 == 0)


def e1():
    cmd = lambda v: (f'probe --tri pixel --width 4096 --height 4096 --vertices {v} '
                     f'--dump-render "$W/dump" "$S/p1139-green.bin"')
    rows, preds = [], []

    def job(name, v, P, st, role, cond=None, knobs="stophang"):
        rows.append(Row(name, st, "safe", P, knobs, RT_DPM, cmd(v), role, cond or name))
        thr0 = (int(P, 16) - 0x22) if int(P, 16) < 0x422 else 0x400
        preds.append((name, "knob0624_first", hex(thr0), "knob", st))

    def raises(name, st, hc, ha, hs, r2):
        for m, v in (("HC", hc), ("HA", ha), ("HS", hs), ("R2", r2)):
            preds.append((name, "raise", v, m, st))

    job("c-1500-0x422", 1500, "0x422", "control", "control: E704's words word for word (no raise)")
    raises("c-1500-0x422", "control", "no", "no", "no", "yes")
    for nm, P in (("d-1500-0x3e0", "0x3e0"), ("d-1500-0x3e0-r2", "0x3e0")):
        job(nm, 1500, P, "heldout" if nm.endswith("0x3e0") else "replicate",
            "decisive: ceiling or scene (HC raises, HA/HS do not)", cond="d-1500-0x3e0")
        raises(nm, "heldout", "yes", "no", "no", "yes")
        thr0 = 0x3e0 - 0x22
        for q, v in (("peak1", hex(thr0)), ("peak2", hex(thr0 + 0x20)), ("dw35", hex(thr0 + 0x1e)),
                     ("dw37", hex(1 << 16 | thr0)), ("dw38", "0x20")):
            preds.append((nm, q, v, "HC", "heldout"))
    for nm, P, hc in (("d-1500-0x400", "0x400", "edge"), ("d-1500-0x410", "0x410", "no"),
                      ("d-1500-0x420", "0x420", "no")):
        job(nm, 1500, P, "heldout", "ceiling edge / above the ceiling (raised = P - 0x22 + 0x20)")
        raises(nm, "heldout", hc, "no", "no", "yes")
    for nm, v, P, role in (("p-1350-0x3e0", 1350, "0x3e0", "positive control if two reaching runs"),
                           ("p-1350-0x300", 1350, "0x300", "positive control, fallback"),
                           ("p-1350-0x420", 1350, "0x420", "expected one run: void for the raise")):
        job(nm, v, P, "heldout", role)
        if nm.endswith("0x420"):
            raises(nm, "heldout", "void", "void", "void", "void")
        else:
            raises(nm, "heldout", "yes", "yes", "yes", "yes")
    for v in E1_LADDER:                                 # the 0x422 ladder first: dword 36 and runs
        nm = f"l-{v}-0x422"
        job(nm, v, "0x422", "heldout", "ladder at 0x422: dword 36 and the run count")
        raises(nm, "heldout", "no", "no", "no", "by-runs")
    for v in E1_LADDER:
        nm = f"l-{v}-0x3e0"
        job(nm, v, "0x3e0", "heldout", "ladder at 0x3e0: raise vs dword-36 step")
        raises(nm, "heldout", "yes", "below-step", "below-step", "yes")
    job("p-900-0x200", 900, "0x200", "heldout",
        "positive control (raised at 0x100 in E630); about 16 partial renders: last and alone")
    raises("p-900-0x200", "heldout", "yes", "yes", "yes", "yes")
    head = """E1 (geometry): Q273/Q210, the raise of the ZLS threshold below P = 0x420: ceiling or scene.
Control first (E704's 0x422 job).  The knob proof is per job: the job's own 0x0624 (first row after the tool's start with 0x0724 non-zero; the first sample is the previous job's) = P - 0x22
(register readback of render_pb_pages shows only the write, the clamp is at use).
Fit/held out: the control reproduces a fit job of R2 (E704); every other job is held out.
Stop rule: a 'job hung' in any job stops the stage (knob stophang)."""
    return rows, preds, ["$S/p1139-green.bin"], head


# ------------------------------------------------------------------------------------------ E2
# The macrotile model of the pages a scene needs.  coverage by sampling, then a 3-parameter fit
# to the ten known (scene, U) points; the proposal's HU1 (stream bytes from sgx-pipe's TA model)
# is NOT computed here, see PREFLIGHT.md.
def layout(w, h):
    tx, ty = -(-w // 32), -(-h // 16)
    n = 4 if w * h >= 640 * 480 else 2
    ru = lambda v: (v + 3) // 4 * 4
    return n, ru(-(-tx // n)) * 32, ru(-(-ty // n)) * 16


def tri(w, h, dx=0, dy=0):
    v = [(8, 8), (56, 20), (20, 56)]
    return [(a * w / 64 + dx, b * h / 64 + dy) for a, b in v]


def inside(p, t):
    (x0, y0), (x1, y1), (x2, y2) = t
    e = lambda ax, ay, bx, by: (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax)
    s = [e(x0, y0, x1, y1), e(x1, y1, x2, y2), e(x2, y2, x0, y0)]
    return all(v >= 0 for v in s) or all(v <= 0 for v in s)


def macrotiles(w, h, ts, g=4):
    n, mw, mh = layout(w, h)
    out = set()
    for i in range(n):
        for j in range(n):
            for a in range(g):
                for b in range(g):
                    p = (i * mw + (a + .5) * mw / g, j * mh + (b + .5) * mh / g)
                    if p[0] < w and p[1] < h and any(inside(p, t) for t in ts):
                        out.add((i, j))
    return out


def tiles(w, h, ts, g=4):
    c = 0
    for i in range(-(-w // 32)):
        for j in range(-(-h // 16)):
            if any(inside((i * 32 + (a + .5) * 32 / g, j * 16 + (b + .5) * 16 / g), t)
                   for a in range(g) for b in range(g) for t in ts
                   if i * 32 + (a + .5) * 32 / g < w and j * 16 + (b + .5) * 16 / g < h):
                c += 1
    return c


KNOWN_U = [(64, 64, 0, 2), (128, 128, 0, 3), (192, 128, 0, 5), (256, 256, 0, 5), (512, 384, 0, 8),
           (1024, 768, 0, 19), (1024, 768, 192, 20), (1024, 768, 384, 17), (1024, 768, 576, 12),
           (4096, 4096, 0, 287)]


def fit_u():
    import numpy as np
    A, y = [], []
    for w, h, dx, u in KNOWN_U:
        ts = [tri(w, h, dx)]
        A.append([1, len(macrotiles(w, h, ts)), tiles(w, h, ts)])
        y.append(u)
    A, y = np.array(A, float), np.array(y, float)
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x, A @ x - y


def predict_u(model, w, h, moves):
    ts = [tri(w, h)] + [tri(w, h, dx, dy) for dx, dy in moves]
    return model[0] + model[1] * len(macrotiles(w, h, ts)) + model[2] * tiles(w, h, ts), \
        len(macrotiles(w, h, ts)), tiles(w, h, ts)


E2_STACKED = [(16, 0), (32, 0), (48, 0)]
E2_APART = [(0, 288), (-64, -240), (-768, -96)]      # greedy max-union moves, see PREFLIGHT.md


def e2_args(k, moves):
    mv = " ".join(f"--move {i + 2}:{dx},{dy}" for i, (dx, dy) in enumerate(moves))
    geo = " ".join(f"--geometry {i}" for i in range(1, k))
    return (f'tri --width 1024 --height 768 -n {k} {geo} {mv} --keep-going --keep-overflow --wait-ms 20000 '
            f'--dump-render "$W/dump" --dump-each --words "$W/words" --regs 0x0700-0x074c').replace("  ", " ")


def e2a():
    model, resid = fit_u()
    rows, preds = [], []

    def job(name, k, moves, P, st, role, cond=None, knobs="stophang expectdiff"):
        rows.append(Row(name, st, "safe", P, knobs, RT_DPM_SHORT, e2_args(k, moves), role, cond or name))
        thr0 = int(P, 16) - 0x22 if int(P, 16) < 0x422 else 0x400
        preds.append((name, "knob0624_first", hex(thr0), "knob", st))
        return thr0

    job("u-1-0x422", 1, [], "0x422", "control", "control: must read 0x13 (E705, E625)")
    preds.append(("u-1-0x422", "U", "19", "E705", "control"))
    job("u-2f-0x38", 2, [(-96, 0)], "0x38", "control", "control: E627's st-two-f, overflows, lists sum 21")
    preds += [("u-2f-0x38", "outcome", "overflow", "E627", "control"),
              ("u-2f-0x38", "lists_sum", "21", "E627", "control")]
    for lay, mv in (("a", E2_APART), ("s", E2_STACKED)):
        for k in (2, 3, 4):
            nm = f"u-{k}{lay}-0x422"
            job(nm, k, mv[:k - 1], "0x422", "heldout", f"U measured: {k} triangles, "
                f"{'least shared macrotiles' if lay == 'a' else 'same macrotiles'}")
            u, m, t = predict_u(model, 1024, 768, mv[:k - 1])
            preds += [(nm, "U", str(round(u)), "coverage-proxy", "heldout"),
                      (nm, "macrotiles", str(m), "geometry", "heldout"),
                      (nm, "tiles", str(t), "geometry", "heldout")]
            if k == 4:
                nm2 = nm + "-r2"
                job(nm2, k, mv[:k - 1], "0x422", "replicate", "replicate of the 4-triangle scene", cond=nm)
                preds += [(nm2, "U", str(round(u)), "coverage-proxy", "replicate")]
    head = f"""E2 first part (geometry): Q211, the page need U of K-triangle scenes at P = 0x422.
-n K with --geometry 1..K-1 submits kicks 1..K-1 TA-only and kick K closes the scene; the tool
prints 'tri 1024x768 #k: geometry only, the scene left open' for each open kick (the option proof).
U = peak of the page status 0x0724 low half; cross-check by the PB free-list walk (head - 1).
Prediction 'coverage-proxy' (NOT the proposal's HU1, which needs sgx-pipe's stream bytes): U =
{model[0]:.4f} + {model[1]:.4f} m + {model[2]:.5f} t (m macrotiles, t tiles covered, 4x4 sampling),
least squares on the 10 known points (FIT; max residual {abs(resid).max():.2f} pages).  The six
scenes are an extrapolation of that proxy to multi-triangle unions: a match neither confirms nor
refutes HU1, a miss refutes only the proxy.  The scorer reports U - proxy, no pass/fail.
HU2 (U = m + c) fails ON THE FIT DATA (the ten known points), not on new data (PREFLIGHT.md).
The boundary and count jobs (g-e2b) are generated after this table by gen/gen_e2_boundary.py."""
    return rows, preds, [], head, model


# ------------------------------------------------------------------------------------------ E4
def e4():
    base = ('probe --tri pixel --vertices 15 --copy-depth --dump-render "$W/dump" --pixels '
            '{flip}"$S/p1139-green.bin"')
    rows, preds = [], []
    for nm, flip, runs in (("ix-c", "", 1), ("ix-24", "--vdm 2^=0x01000000 ", 2),
                           ("ix-25", "--vdm 2^=0x02000000 ", 2), ("ix-2425", "--vdm 2^=0x03000000 ", 2)):
        for r in range(1, runs + 1):
            n = nm if runs == 1 else f"{nm}-r{r}"
            k = f"hypo:{nm}:2" if flip else "stophang"
            rows.append(Row(n, "control" if not flip else ("heldout" if r == 1 else "replicate"), "safe", "-",
                            k, "-", base.format(flip=flip),
                            "E414's five-copy object (15 indices), no flip" if not flip else
                            f"header bits flipped: {flip.split('=')[1].strip()}", cond=nm))
            if not flip:
                preds += [(n, "triangles", "5", "E414", "control"), (n, "outcome", "ok", "E414", "control")]
            else:
                preds += [(n, "object_changed", "no", "HN", "heldout"),
                          (n, "object_changed", "yes-or-fault", "HW", "heldout"),
                          (n, "outcome", "hang", "HH", "heldout")]
    head = """E4 (geometry): Q112, index header (VDM word 2) bits 25:24 and the index width.
Control: unflipped five-copy job (--vertices 15 --copy-depth as E414 ran it; the proposal omitted
--copy-depth).  Two runs per flip.  A hang or fault is a hypothesis (HH, HW): knob hypo:GROUP:2
measures up to two events per flip word (the group's remaining jobs are then skipped); any hang or
fault elsewhere stops the stage.  Nothing here forces a field value the records never touched except the flips."""
    return rows, preds, ["$S/p1139-green.bin"], head


# ------------------------------------------------------------------------------------------ E5
def e5():
    cap = lambda n, f, a: (
        f'probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords {n} '
        + (f'--vdm 6^=0x{(15 ^ f) << 28:08x} ' if f != 15 else '')
        + (f'--vdm 7^=0x{(a << 7) ^ 0x80:08x} ' if a != 1 else '')
        + f'--dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c{n}.bin" '
        f'"$S/p1131-fmt-{n}__0.bin"')
    rows, preds = [], []

    def job(nm, st, n, f, a, runs, knobs, role, pr):
        for r in range(1, runs + 1):
            name = nm if runs == 1 else f"{nm}-r{r}"
            rows.append(Row(name, st if r == 1 else "replicate", "safe" if "hang" not in knobs else "risky",
                            "-", knobs, "-", cap(n, f, a), role, nm))
            for q, v, m in pr:
                preds.append((name, q, v, m, st))

    job("r-n8-a1", "control", 8, 10, 1, 1, "stophang", "control: E702's base, N 8 V 11 a 1",
        [("o0_mixed_x", "2288", "E702")])
    job("r-n2-a9", "control", 2, 15, 9, 1, "stophang", "control: E702's base of the hang row, N 2 a 9",
        [("o0_mixed_x", "2821", "E702")])
    job("r-n8-a7", "heldout", 8, 10, 7, 3, "stophang", "does the a=7 event repeat",
        [("o0_mixed_x", "2285", "HD"), ("o0_mixed_x", "2288", "HO"), ("constant_row_ids", "55 66 77", "HD")])
    job("r-n8-a12", "heldout", 8, 10, 12, 3, "stophang", "does the a=12 event repeat",
        [("o0_mixed_x", "2028", "HD"), ("o0_mixed_x", "2288", "HO"), ("split", "15x7,9,12", "HD")])
    job("r-n8-a8", "heldout", 8, 10, 8, 3, "stophang", "does E546's lost vertex repeat",
        [("vertex_lost", "1", "HD"), ("vertex_lost", "0", "HO")])
    job("r-n2-a32", "heldout", 2, 15, 32, 3, "expecthang", "the hang row: last (a hang each time)",
        [("outcome", "hang", "HD"), ("outcome", "ok", "HO")])
    head = """E5 (geometry): Q272, do the three events repeat (E702's commands, cap(n, f, a)).
The two bases come first and must reproduce E702 (o0 mixed counts) before the cells count.
r-n2-a32 hangs each time if HD holds (about 1 s recovery each): last; stop after a recovery whose
health triangle does not draw.  HD/HO/HI as in the proposal: 3 of 3 or 0 of 3 per condition.
The programs are rebuilt from probes/ta (p1131-progs.toml); their sha256 against the laptop's
~/sgxprobes-stage copies is not checkable offline (PREFLIGHT.md)."""
    needs = ["$S/pix_pa0.bin", "$S/vtx_c8.bin", "$S/vtx_c2.bin", "$S/p1131-fmt-8__0.bin", "$S/p1131-fmt-2__0.bin"]
    return rows, preds, needs, head


def build_e5_programs():
    pt = TE / "ta/p1131-progs.toml"
    src = TE / "ta/templates"
    for p in probe.load(pt):
        if p.name in ("p1131-fmt-8", "p1131-fmt-2"):
            probe.build(p, BINS, src)
            probe.build_helpers([p], BINS, src)


# ------------------------------------------------------------------------------------------ E8
def e8():
    rows, preds = [], []
    base = ('tri --width 128 --height 128 -n {n} {geo}{move}--tri-z 0.2,0.5,0.8 --depth --depth-ctl 0x0017100e '
            '--depth-fill 0x3e800000 --depth-dump "$W/depth" --dump-render "$W/dump" --keep-going '
            '--poke blk:1={isp} --pixels')
    ISP = {"never": "0x00000200", "less": "0x00400200"}
    moves = {"mA": "32,16", "mB": "-16,24"}
    for cmp_ in ("less", "never"):
        for mk, mv in moves.items():
            nm = f"o2-{cmp_}-{mk}"
            rows.append(Row(nm, "heldout", "safe", "-", "stophang expectdiff", "-",
                            base.format(n=2, geo="--geometry 1 ", move=f"--move 2:{mv} ", isp=ISP[cmp_]),
                            f"two objects over a loaded depth (fill 0.25f), compare {cmp_}, move {mv}", nm))
            preds.append((nm, "model", f"{cmp_}/{mv}", "numpy-isp", "heldout"))
    for cmp_ in ("less", "never"):
        nm = f"o1-{cmp_}-ctl"
        # compare never draws nothing, so the tool's triangle check fails by design (rc 1, diff:)
        knobs = "stophang expectdiff" if cmp_ == "never" else "stophang"
        rows.append(Row(nm, "control", "safe", "-", knobs, "-",
                        base.format(n=1, geo="", move="", isp=ISP[cmp_]),
                        f"control: one object over the loaded depth, compare {cmp_} (E664/E665)", nm))
        preds.append((nm, "model", f"{cmp_}/one", "numpy-isp", "control"))
    for cmp_, mk in (("less", "mA"), ("never", "mA")):
        nm = f"o2-{cmp_}-{mk}-r2"
        rows.append(Row(nm, "replicate", "safe", "-", "stophang expectdiff", "-",
                        base.format(n=2, geo="--geometry 1 ", move=f"--move 2:{moves[mk]} ", isp=ISP[cmp_]),
                        "replicate", nm[:-3]))
        preds.append((nm, "model", f"{cmp_}/{moves[mk]}", "numpy-isp", "replicate"))
    head = """E8a (geometry): several objects over a loaded depth, data for the deferred 12.4 (a).
Depth buffer filled with 0.25f and loaded (control 0x0017100e as depth-load); ISP word 0 compare
'less' (0x00400200) or 'never' (0x00000200) (E282); vertex depths 0.2, 0.5, 0.8; object 2 moved.
The single-object controls come first and must equal E664/E665's pattern.  The tool's own
reference check cannot match a two-object scene (rc 1, 'diff:' lines): knob expectdiff.
NOTE: no earlier run combined --depth with --geometry (PREFLIGHT.md).  The compare 'greater'
is not in the proposal.  E8b (translucent order) is in table g-e8b."""
    return rows, preds, [], head
