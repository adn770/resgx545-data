#!/usr/bin/env python3
"""Generate every R3GC table, prediction file, stages.txt and TABLES.md.  Offline only.

  PYTHONDONTWRITEBYTECODE=1 ~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python gen/r3gen.py

Stages (laptop session L1b): g-z (C1: Q287 + Q122, the ZLS band), g-qf (C2 fit: Q211 count constants at U = 287),
g-qh (C2 held out: the scenes U = 275 and 438).  Writes tables/*.txt, predictions/*.tsv, stages.txt, TABLES.md.
Row order in every table: controls first, then the rest.  No row predicts a hang or a fault: every such line stops its stage.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import shlex  # noqa: E402
import textwrap  # noqa: E402

import r3_geo as G  # noqa: E402
import rcommon as C  # noqa: E402
from rcommon import RT_DPM2, Row, conditions, write_preds, write_table  # noqa: E402

STAGES = ["g-z", "g-qf", "g-qh"]
KNOBS = "stophang expectdiff"
POKE = "--poke blk:1=0x00400200"             # E730's host-side poke of the triangle's state block (word 1)
HEX = lambda v: f"0x{v:x}"                   # noqa: E731


def wrap_cmd(cmd, width=92):
    toks = shlex.split(cmd, posix=False)
    lines, cur = [], ""
    for t in toks:
        if cur and len(cur) + 1 + len(t) > width:
            lines.append(cur + " \\")
            cur = "    " + t
        else:
            cur = (cur + " " + t) if cur else t
    return lines + [cur]


# ----------------------------------------------------------------------------------------------------------------- C1
def z_cmd(w, h, ramp, extra=""):
    z = G.RAMP_X if ramp == "x" else G.RAMP_Y
    return (f'tri --keep-overflow --wait-ms 20000 --width {w} --height {h} --tri-full --tri-z {z}{extra} --depth '
            f'--depth-ctl {HEX(G.depth_ctl(w))} --depth-fill 0xdeadbeef --depth-dump "$W/depth" '
            f'--depth-pages {G.depth_pages(w, h)} {POKE}')


def z_tri_cmd(w, h, v256, z="0.25,0.75,0.25"):
    return (f'tri --keep-overflow --wait-ms 20000 --width {w} --height {h} --tri-v {",".join(str(v) for v in v256)} '
            f'--tri-z {z} --depth --depth-ctl {HEX(G.depth_ctl(w))} --depth-fill 0xdeadbeef --depth-dump "$W/depth" '
            f'--depth-pages {G.depth_pages(w, h)} {POKE}')


# E730's measured counts of the stored (not 1.0f) dwords of its full-screen triangle: its 34 x 18 control and 66 x 34 held-out
E730_COUNT = {(34, 18): 924, (66, 34): 3444}
TRI_IN = (34, 18, [24 * 256, 8 * 256, 40 * 256, 8 * 256, 24 * 256, 20 * 256])       # wholly inside the band (x < 42, y < 22)
TRI_CROSS = (36, 20, [24 * 256, 8 * 256, 80 * 256, 8 * 256, 24 * 256, 56 * 256])    # crosses the band edge (x < 45, y < 25)


def g_z():
    rows, preds = [], []

    def full(name, w, h, ramp, st, role):
        rows.append(Row(name, st, "safe", "-", KNOBS, "-", z_cmd(w, h, ramp), role, name))
        P = lambda q, v, m, s: preds.append((name, q, v, m, s))              # noqa: E731
        sep = G.separating(w, h)
        if st == "control":
            P("stored_count", str(E730_COUNT[(w, h)]), f"E730 (measured: {E730_COUNT[(w, h)]} stored dwords)", "control")
            P("stored_set_sha", G.set_sha(G.band_set("A", w, h)), "E730 (the set equals rule A's, 12 of 12)", "control")
            for r in ("ROUND", "CEIL"):
                P("stored_set_sha", G.set_sha(G.band_set(r, w, h)), G.RULES[r][0], "repeat")
            return
        for r, (label, _) in G.RULES.items():
            xm, ym = G.extent(r, w, h)
            P("extent", f"{xm},{ym}", label, "heldout")
            P("stored_count", str(len(G.band_set(r, w, h))), label, "heldout")
            P("stored_set_sha", G.set_sha(G.band_set(r, w, h)), label, "heldout")
        P("separates", "x:" + "+".join(sep["x"]) + ";y:" + "+".join(sep["y"]), "rules whose extents differ from A's here", "info")

    full("z-ctl-34x18-x", 34, 18, "x", "control", "control (E730, E465): 34 x 18, ramp in x: 924 stored")
    full("z-ctl-34x18-y", 34, 18, "y", "control", "control (E730): 34 x 18, ramp in y: 924 stored")
    full("z-ctl-66x34-x", 66, 34, "x", "control", "control (E730): 66 x 34, ramp in x: 3444 stored, pitch 0x171014")
    for w in (20, 36, 44, 76):
        full(f"z-w{w}", w, 18, "x", "heldout", f"width {w} at H 18: 1.25 W = {1.25 * w:g} (an integer: the band edge on a pixel edge)")
    for h in (20, 28, 36):
        full(f"z-h{h}", 34, h, "y", "heldout", f"height {h} at W 34: 1.25 H = {1.25 * h:g} (an integer)")
    full("z-w32", 32, 18, "x", "heldout", "width 32: the band (x < 40) is past the tile area (x < 32)")
    full("z-w64", 64, 18, "x", "heldout", "width 64: the band (x < 80) is past the tile area (x < 64), pitch 0x17100c")
    full("z-h32", 34, 32, "y", "heldout", "height 32 at W 34: the band (y < 40) is past the tile area (y < 32)")
    for name, (w, h, v), role in (("z-tri-in", TRI_IN, "triangle (24,8) (40,8) (24,20) at 34 x 18, wholly inside the band: the "
                                                      "hypotenuse, not the band, bounds the store"),
                                  ("z-tri-cross", TRI_CROSS, "triangle (24,8) (80,8) (24,56) at 36 x 20: crosses the band edge "
                                                            "(x < 45, y < 25), whose corner it covers")):
        rows.append(Row(name, "heldout", "safe", "-", KNOBS, "-", z_tri_cmd(w, h, v), role, name))
        for r, (label, _) in G.RULES.items():
            if name == "z-tri-in" and r not in ("A",):
                continue
            d, a = G.tri_raster(v, r, w, h)
            preds.append((name, "tri_raster", f"{len(d)}+{len(a)}", label + " with the pixel-centre raster model", "heldout"))
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    head = """C1 (zls, Q287 closes Q122 with it): the ZLS store's band at other alignments.  E730 (post hoc, 12 of 12 jobs; every width 2 mod 4,
every height 2 mod 8) found the stored (not 1.0f) dwords of a full-screen triangle's depth store at x < 1.25 W and y < 1.25 H
of the tile area.  Frozen rule A: the pixel centre test x + 0.5 < 1.25 W, i.e. x < ceil(1.25 W - 0.5), and the same for y
with H, against FLOOR (x < floor(1.25 W)), ROUND (x < floor(1.25 W + 0.5)), CEIL (x < ceil(1.25 W)) and RSTRICT (x + 1 < 1.25 W).
DEVIATION from the proposal: the tool refuses odd sizes (render.c: width % 2, height % 2 -> EINVAL; the Mac mock says `render:
Invalid argument` for 17, 19, 33, 35 and heights 17, 19, 21), so the fractions .25 and .75 of 1.25 W (where A differs from
FLOOR) cannot be run: the nearest accepted shape is the integer fraction (W = 0 mod 4: 20, 36, 44, 76; H = 0 mod 4: 20, 28, 36),
where A = FLOOR = ROUND = CEIL and only RSTRICT differs (RSTRICT agrees with A at E730's .5 and so was not refuted); the new
alignments also put the band's edge at other places of the 32 x 16 tile (W = 76: 95 of the 96 pixels of three tiles).  The
controls (34 x 18 x and y, 66 x 34: E730's .5 sizes) separate A from ROUND and CEIL.  Rows: E730's isp-a-guard rows
(p1141/isp-a-guard.sh) with the sizes changed: the same option string, the depth pitch per width as E730 chose it (0x17100c up to
64, 0x171014 at 66 and 76), the buffer pre-filled with 0xdeadbeef, a depth dump.  Observable: a tile-area dword is stored iff
it is not 1.0f (E465's, as E730's post hoc reader).  Gates, from the kept dump: no dword of the tile area still 0xdeadbeef (the
store writes whole tiles), the tool's own `diff: 0 of W*H pixels`.  A control miss voids the stage.  The pa0 iterated-attribute
clause of Q287 is not run (user decision R3-R5 c).  z-tri-in / z-tri-cross: one triangle by --tri-v; the model is the
pixel-centre raster clipped by the band (edge pixels within 1/16 pixel are ambiguous)."""
    return rows, preds, [], head


# ----------------------------------------------------------------------------------------------------------------- C2
def q_cmd(extra=""):
    return ("tri --width 4096 --height 4096 " + (extra or "-n 1") + ' --keep-overflow --wait-ms 20000 --words "$W/words" '
            "--regs 0x0700-0x074c")


def _count_preds(preds, name, U, P, st):
    preds.append((name, "knob0624_first", HEX(P - 0x22), "knob", st))
    for k, s in G.PAIRS:
        preds.append((name, "nparts", str(G.count(U, k, s, P)), f"E625 count (k={k}, s={s:#x})", st))


def g_qf():
    rows, preds = [], []
    ctl = {0xa0: 2, 0xb0: 1, 0xa3: 1}
    for P, n in ctl.items():
        name = f"qf-{P:#x}"
        rows.append(Row(name, "control", "safe", HEX(P), KNOBS, RT_DPM2, q_cmd(), f"control (E625/E779 measured): P = {P:#x} gives {n}", name))
        preds.append((name, "knob0624_first", HEX(P - 0x22), "knob", "control"))
        preds.append((name, "nparts", str(n), "E625/E779 (measured)", "control"))
    for P in sorted(G.split_cells(), reverse=True):
        name = f"qf-{P:#x}"
        rows.append(Row(name, "fit", "safe", HEX(P), KNOBS, RT_DPM2, q_cmd(), f"fit cell: P = {P:#x} (thr0 {P - 0x22}), counts "
                        f"{sorted({G.count(G.U_DEFAULT, k, s, P) for k, s in G.PAIRS})} among the 20 pairs", name))
        _count_preds(preds, name, G.U_DEFAULT, P, "fit")
    head = """C2 fit stage (Q211): the count of partial renders of the default triangle at 4096x4096 (U = 287) at the 19 cells where the 20
(k, s) pairs that fit E625's 10 and E779's 9 cells together (closing3/rank/q211_fit.out) predict different counts, with E625's
0xa0 (2), 0xb0 (1) and E779's 0xa3 (1) as controls.  The counts are those of E625's family 1 + floor((U + k - thr0) / (thr0
+ s)), thr0 = P - 0x22; the grid holds k in [-8, 0], s in [0x1b, 0x1e].  The 19 cells leave 13 classes of pairs (some pairs predict
the same counts at U = 287 everywhere: e.g. (-8, 27) and (-7, 27)); the held-out stage g-qh separates every one of the 20.  Run
from the highest P down (the fewest partial renders first, up to 10 at 0x24).  Knob proof: the job's own 0x0624 = P - 0x22.  A
count that rises with P, a hang or a failed control stops the reading (the runner stops at a hang)."""
    return rows, preds, [], head


def g_qh():
    rows, preds = [], []
    ho = G.pick_heldout()
    for sc, (U, extra) in G.SCENES.items():
        name = f"qc-{sc}"
        rows.append(Row(name, "control", "safe", "0x422", KNOBS, RT_DPM2, q_cmd(extra),
                        f"scene gate (E773): {sc} at the default P = 0x422 needs U = {U} pages (peak of 0x0724, no overflow)", name))
        preds.append((name, "U", str(U), "E773 (measured: the 0x0724 peak and the free-list walk agree)", "control"))
        preds.append((name, "knob0624_first", HEX(0x422 - 0x22), "knob", "control"))
    for sc, cells in ho.items():
        U, extra = G.SCENES[sc]
        for P in cells:
            name = f"qh-{sc}-{P:#x}"
            vals = sorted({G.count(U, k, s, P) for k, s in G.PAIRS})
            rows.append(Row(name, "heldout", "safe", HEX(P), KNOBS, RT_DPM2, q_cmd(extra),
                            f"held-out cell: scene {sc} (U = {U}), P = {P:#x}, counts {vals} among the 20 pairs", name))
            _count_preds(preds, name, U, P, "heldout")
    rows = [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]
    head = """C2 held-out stage (Q211): the scenes of E773 with U = 275 (-n 1 --move 1:1024,0) and U = 438 (-n 2 --geometry 1 --move
2:0,1024) at 4096x4096.  Two scene-gate jobs at the default P = 0x422 read each scene's U (the peak of 0x0724) as E773 did; a
scene whose U differs voids its cells.  Six cells a scene, chosen offline (gen/r3_geo.py pick_heldout): greedily the cells that
split the 13 classes the fit leaves until every one of the 20 pairs is its own class, then the most divisive, and one cell where
all 20 pairs agree (a plain test of the family at the new U).  The frozen table holds the predicted count of every pair at every
cell; the scorer keeps the pairs the fit stage left (g-qf's kept data) and scores the held-out cells against them.  A job with a
kick lost (`#N: overflowed` for a render before the last) is void (E773's rule).  Run after g-qf."""
    return rows, preds, [], head


def order(rows):
    return [r for r in rows if r.set == "control"] + [r for r in rows if r.set != "control"]


def main():
    out = {"g-z": g_z(), "g-qf": g_qf(), "g-qh": g_qh()}
    md = ["# R3GC job tables (generated by gen/r3gen.py)", "",
          "Each job: name (set, render_pb_pages P, regtimeline), the exact tool command and the frozen predictions.  The tool is `$T`",
          "(~/sgxfive-test-r1), the work directory `$W`.  `set`: control, fit, heldout, repeat, replicate.  `tables/` is the runner's",
          "input; this is a view (the count tables of g-qf and g-qh list the predicted counts per cell, the full 20-pair table is in",
          "`predictions/`).", ""]
    total = 0
    for st in STAGES:
        rows, preds, need, head = out[st]
        rows = order(rows)
        write_table(st, rows, need, head)
        write_preds(st, preds)
        by = collections.defaultdict(list)
        for n, q, v, m, s in preds:
            by[n].append((q, v, m, s))
        total += len(rows)
        md += [f"## {st}: {len(rows)} jobs, {conditions(rows)} conditions", "", "```"]
        md += textwrap.wrap(" ".join(head.split()), 98) + ["```", ""]
        for r in rows:
            tags = f"{r.set}, P={r.P}" + ("" if r.rt == "-" else ", timeline")
            md += textwrap.wrap(f"- `{r.name}`: {r.role}.  [{tags}]", width=96, subsequent_indent="  ") + ["", "  ```"]
            md += ["  " + ln for ln in wrap_cmd(r.args)] + ["  ```"]
            ps = by.get(r.name, [])
            nparts = [(m, v) for q, v, m, s in ps if q == "nparts"]
            if nparts and len(nparts) > 2:
                cnt = collections.defaultdict(list)
                for m, v in nparts:
                    cnt[v].append(m.replace("E625 count ", ""))
                for v, ms in sorted(cnt.items()):
                    md += textwrap.wrap(f"  - frozen: nparts = {v}  [{len(ms)} pairs: " + " ".join(ms) + "]", width=96,
                                        subsequent_indent="      ")
            else:
                for q, v, m, s in ps:
                    if q == "knob0624_first":
                        continue
                    md += textwrap.wrap(f"  - frozen: {q} = {v}  [{m}] ({s})", width=96, subsequent_indent="      ")
            md += [""]
    (C.R1 / "TABLES.md").write_text("\n".join(md) + "\n")
    (C.R1 / "stages.txt").write_text("\n".join(STAGES) + "\n")
    for st in STAGES:
        print(f"{st:6s} jobs {len(out[st][0]):3d} conditions {conditions(out[st][0]):3d} predictions {len(out[st][1]):4d}")
    print("total (session):", total)


if __name__ == "__main__":
    sys.exit(main())
