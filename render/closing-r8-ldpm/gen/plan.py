#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r8-ldpm's generator (round 8, session L1 of closing8/leftovers/exp-leftovers-r8.md,
DECISIONS-R8.md R8-8: safe class only). Writes tables/STAGE.txt and predictions/STAGE.tsv for the
seven stages, in run order a0, sp, m6, v, f9, k, u (161 jobs), from:

  gen/ol7_tables.json   OL7 (c)'s frozen tables (closing8/leftovers/ol7_c_tables.py, its
                        sha256 in gen/OL7.sha256 with the FREEZE lines of OL7 (a) to (c)): E874's
                        step model S_k, H-SPAN's A_k, E874's B_k and U per target; F9's counts and
                        run peaks; HU1 and H-BBOX for stage u's shapes; stage k's scenes with
                        H-KICKS and H-UNION (OL7 (b) did not reproduce 4 of 31 kept cells: k's
                        counts are explore, its needs held out on HU1)
  constants below       R7-dpm's kept readings (E915, E917, E918) the controls repeat

  python3 gen/plan.py          write the tables and predictions
  python3 gen/plan.py --check  exit 1 when a written file differs from what it would write

Every job is a plain job of the kit: the tool t4 run under regtimeline (tool rt, wraps = true),
render_pb_pages written by the kit (dbg:render_pb_pages=P, P = thr0 + 0x22, restored to 0x422),
a `probe` DPM cell's rc 3 "scene overflowed" an expected end (expect:rc3-overflow), a `tri` job's
rc 1 with its diff line a reading (expectdiff). No poke, no held reset, no planned fault, no
expectfault row (#limit 0). A control declares its reading keys (reads:) and, where its value is
one number, its frozen value (ctl:KEY=VALUE, run/hooks.sh stops the stage when it is off)."""
from __future__ import annotations

import json
import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
T = json.loads((KP / "gen" / "ol7_tables.json").read_text())

RT = "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"
LEAD = "0.3"
TOOL = '"$HOME/sgxfive-test-rgn4"'
PROG = '"$S/bins/p1139-green.bin"'
D_OFF = 0x22
P_CAL = 0x422
CLAMP = 0x400
STAGES = ("a0", "sp", "m6", "v", "f9", "k", "u")
# R7-dpm's kept readings (render/closing-r7-dpm: E915 s-a0, E917 s-v) that a0 and v repeat
QF_PEAKS = (0x80, 0xA0, 0x2)
VCAL4 = ({2: 0x4F, 3: 0x52, 4: 0x98, 5: 0x9F, 6: 0xE7, 7: 0x12E, 8: 0x133, 9: 0x17D, 10: 0x182,
          11: 0x1C7, 12: 0x1CD, 13: 0x214}, 538)
S22 = ((2048, 2048), (0, 384), 78)          # R7-dpm s-b's s22 scene and its need (E916)
# sp: the frozen step rivals (plan section 2): S6 at 2048x3072 and S3 at 2048x4096
SP_RIVAL = {(2048, 3072): (6, 0x234, "H-R7S6"), (2048, 4096): (3, 0x12C, "H-KEPTS3")}
# m6: the seven held-out targets by class and the two mapped ones (plan section 2's table)
M6_CLASS = {(1536, 1536): "small", (1024, 1024): "small", (4096, 2048): "one", (3072, 2048): "one",
            (2048, 3072): "one", (2560, 3072): "both", (3072, 2560): "both"}
M6_MAPPED = {(3072, 3072): range(0x3CE, 0x3D9), (2560, 2560): range(0x2B0, 0x2B6)}
M6_RIVALS = {"H-SPAN": {"small": 1, "one": 1, "both": 1, "mapped": 1},
             "H-BIG6": {"small": 1, "one": 1, "both": 2, "mapped": 2},
             "H-ANY6": {"small": 1, "one": 2, "both": 2, "mapped": 2},
             "H-6LATE": {"small": 2, "one": 2, "both": 2, "mapped": 2}}
WIN = (-1, 3)                                # m6's window around A_6: A_6 - 1 .. A_6 + 3


def hx(v):
    return f"0x{v:x}"


def model(w, h):
    m = T["models"][f"{w}x{h}"]
    conv = lambda d: {int(k): int(v, 16) for k, v in d.items()}  # noqa: E731
    return conv(m["S"]), conv(m["A"]), conv(m["B"]), int(m["U"], 16)


def span_left(thr0, S, E):
    """g3_span.pred, unchanged: 2 iff S_k < thr0 < E_k, 1 from E_k; None on a step cell."""
    ks = [k for k in sorted(S) if S[k] <= thr0]
    if not ks:
        return 1
    k = ks[-1]
    if thr0 == S[k]:
        return None
    if k not in E:
        return "?"
    return 2 if thr0 < E[k] else 1


def gps_abort(thr0, S):
    return 1 + sum(1 for v in S.values() if v < thr0)


# ---- commands ---------------------------------------------------------------------------------
def rt(cmd):
    return f"0 {LEAD} {RT} -- {TOOL} {cmd}"


def probe(w, h, coords=None, vtx=None, dump=False):
    c = f"probe --tri pixel --width {w} --height {h} --vertices 1500"
    if coords:
        c += f" --vtx-coords {coords}"
    if vtx:
        c += f' --slot "vtxuse=$S/bins/{vtx}.bin"'
    if dump:
        c += ' --dump-render "$W"'
    return rt(f"{c} {PROG}")


def tri(w, h, moves=((0, 0),), dump=False, triv=None):
    K = len(moves)
    c = f"tri --width {w} --height {h} -n {K}"
    c += "".join(f" --geometry {i}" for i in range(1, K))
    c += "".join(f" --move {i + 1}:{dx},{dy}" for i, (dx, dy) in enumerate(moves) if (dx, dy) != (0, 0))
    if triv:
        c += f" --tri-unit 12 --tri-v {triv}"
    # R7-dpm's form: --keep-going with a moved or several-kick scene only (g-qf's command has none)
    c += (" --keep-going" if K > 1 or any(m != (0, 0) for m in moves) or triv else "") + " --keep-overflow --wait-ms 20000"
    if dump:
        c += ' --dump-render "$W"'
    return rt(c + ' --words "$W" --regs 0x0700-0x074c')


def row(name, sset, thr0, cmd, words=()):
    kind = cmd.split(" -- ", 1)[1].split()[1]
    knobs = [f"dbg:render_pb_pages={hx(thr0 + D_OFF)}"]
    knobs.append("expect:rc3-overflow" if kind == "probe" else "expectdiff")
    knobs += list(words)
    return dict(name=name, set=sset, risk="safe", knobs=" ".join(knobs), tool="rt", args=cmd,
                thr0=thr0)


def reads(*keys):
    return "reads:" + ",".join(keys)


def ctl(**kv):
    return [f"ctl:{k}={v}" for k, v in kv.items()]


# ---- the stages ----------------------------------------------------------------------------------
def stage_a0():
    p = probe(2048, 2048, dump=True)
    return [
        row("a0-cal-2048", "control", 0x140, p, [reads("s2", "s3", "s4", "s5", "knob", "gps_left")]
            + ctl(gps_left="0x2")),
        row("a0-cal-2048f", "control", CLAMP, p,
            [reads("s2", "s3", "s4", "s5", "s6", "s7", "knob", "need", "nparts")]
            + ctl(need="0x213", nparts="0")),
        row("a0-c4-b5", "control", 0xE2, p, [reads("gps_left", "knob")] + ctl(gps_left="0x2")),
        row("a0-c4-b6", "control", 0xE3, p, [reads("gps_left", "knob")] + ctl(gps_left="0x1")),
        row("a0-t-s3m6", "control", 0x97, p, [reads("gps_left", "knob")] + ctl(gps_left="0x1")),
        row("a0-qf-0xa2", "control", 0x80, tri(4096, 4096),
            [reads("nparts", "runpeaks", "knob", "gmax")]
            + ctl(nparts="2", runpeaks=",".join(hx(x) for x in QF_PEAKS))),
    ]


def stage_sp():
    p22 = probe(2048, 2048, dump=True)          # R7-dpm's command of the kept cells (E918)
    rows = [row("sp-c-0xe8", "control", 0xE8, p22, [reads("gps_abort", "knob")] + ctl(gps_abort="0x3")),
            row("sp-c-0xe9", "control", 0xE9, p22, [reads("gps_abort", "knob")] + ctl(gps_abort="0x4"))]
    p23 = probe(2048, 3072)
    for i in (1, 2, 3):
        rows.append(row(f"sp-cal-c23-{i}", "heldout", CLAMP, p23))
    for t in range(0x232, 0x237):
        rows.append(row(f"sp-c23-{hx(t)}", "heldout", t, p23))
    p24 = probe(2048, 4096)
    for t in range(0x125, 0x12F):
        rows.append(row(f"sp-c24-{hx(t)}", "heldout", t, p24))
    return rows


def a6_cells(w, h):
    S, A, B, U = model(w, h)
    return [A[6] + d for d in range(WIN[0], WIN[1] + 1)]


def stage_m6():
    p22 = probe(2048, 2048, dump=True)          # R7-dpm's command of the kept cells (E915)
    rows = [row("m6-c-0x1c2", "control", 0x1C2, p22, [reads("gps_left", "knob")] + ctl(gps_left="0x2")),
            row("m6-c-0x1c3", "control", 0x1C3, p22, [reads("gps_left", "knob")] + ctl(gps_left="0x1"))]
    for (w, h), cells in M6_MAPPED.items():
        tag = f"c{w // 256:02d}{h // 256:02d}"
        rows.append(row(f"m6-cal-{tag}", "heldout", CLAMP, probe(w, h)))
        for t in cells:
            rows.append(row(f"m6-map-{tag}-{hx(t)}", "fit", t, probe(w, h, dump=True)))
    for (w, h) in M6_CLASS:
        tag = f"c{w // 256:02d}{h // 256:02d}"
        rows.append(row(f"m6-cal-{tag}", "heldout", CLAMP, probe(w, h)))
        for t in a6_cells(w, h):
            rows.append(row(f"m6-{tag}-{hx(t)}", "heldout", t, probe(w, h)))
    S, A, B, U = model(2560, 2560)
    for t in range(A[7] - 1, A[7] + 3):
        rows.append(row(f"m6-b7-c1010-{hx(t)}", "explore", t, probe(2560, 2560)))
    S, A, B, U = model(3072, 3072)
    for t in (A[4] - 1, A[4]):
        rows.append(row(f"m6-b4-c1212-{hx(t)}", "explore", t, probe(3072, 3072)))
    return rows


def stage_v():
    rows = [row("v-c4", "control", CLAMP, probe(2048, 2048, coords=4, dump=True),
                [reads(*[f"s{k}" for k in sorted(VCAL4[0])], "need", "knob")] + ctl(need=hx(VCAL4[1])))]
    for i in (1, 2, 3):
        rows.append(row(f"v-w8-{i}", "heldout", CLAMP, probe(2048, 2048, 8, "vtx_coord8", dump=True)))
    for i in (1, 2):
        rows.append(row(f"v-w4-{i}", "explore", CLAMP, probe(2048, 2048, 4, "vtx_coord4", dump=True)))
    for i in (1, 2):
        rows.append(row(f"v-p8-{i}", "explore", CLAMP, probe(2048, 2048, 8, dump=True)))
    S = VCAL4[0]
    for t in (S[4] - 1, S[4], S[4] + 1, S[5] - 1, S[5], S[5] + 1):
        rows.append(row(f"v-w4c-{hx(t)}", "explore", t, probe(2048, 2048, 4, "vtx_coord4", dump=True)))
    return rows


def stage_f9():
    rows = []
    done = set()
    for key in T["f9"]:
        wh, t = key.split(":")
        w, h = (int(x) for x in wh.split("x"))
        tag = f"c{w // 256:02d}{h // 256:02d}"
        if wh not in done:
            S, A, B, U = model(w, h)
            ks = [k for k in sorted(S) if S[k] < U]
            rows.append(row(f"f9-cal-{tag}", "control", CLAMP, probe(w, h),
                            [reads(*[f"s{k}" for k in ks], "need", "knob")] + ctl(need=hx(U))))
            done.add(wh)
        rows.append(row(f"f9-{tag}-{t}", "heldout", int(t, 16), probe(w, h)))
    return rows


def k_moves(s):
    return [(i * s["move"][0], i * s["move"][1]) for i in range(s["K"])]


def stage_k():
    rows = []
    for s in T["k"]:
        mv = k_moves(s)
        rows.append(row(f"k-cal-{s['name']}", "heldout", CLAMP,
                        tri(s["w"], s["h"], mv, dump=s["w"] * s["h"] <= 2048 * 2048)))
        for t in s["cells"]:
            rows.append(row(f"k-{s['name']}-{t}", "explore", int(t, 16), tri(s["w"], s["h"], mv)))
    return rows


def stage_u():
    (w, h), mv, U = S22
    rows = [row("u-c-s22", "control", CLAMP, tri(w, h, [mv]), [reads("need", "nparts", "knob")]
                + ctl(need=hx(U), nparts="0"))]
    for s in T["u"]:
        rows.append(row(s["name"], "heldout", CLAMP, tri(s["w"], s["h"], triv=s["triv"])))
    return rows


def tables():
    return {"a0": stage_a0(), "sp": stage_sp(), "m6": stage_m6(), "v": stage_v(), "f9": stage_f9(),
            "k": stage_k(), "u": stage_u()}


def target(r):
    a = r["args"].split()
    return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])


# ---- predictions --------------------------------------------------------------------------------
def predictions(st, rows):
    """[(case, quantity, value, model, set)]"""
    P = []
    for r in rows:
        n, s, t = r["name"], r["set"], r["thr0"]
        w, h = target(r)
        lab = "control" if s == "control" else s
        P.append((n, "knob", hx(t), "CTL", "control"))
        kn = r["knobs"].split()
        for k in kn:
            if k.startswith("ctl:"):
                q, v = k[4:].split("=", 1)
                P.append((n, q, v, "CTL", "control"))
        if st == "a0":
            if n in ("a0-cal-2048", "a0-cal-2048f"):
                S, A, B, U = model(w, h)
                P += [(n, f"s{k}", hx(v), "H-STEPMODEL", "control") for k, v in sorted(S.items()) if v < t]
        elif st == "sp":
            S, A, B, U = model(w, h)
            if n.startswith("sp-c-"):
                pass
            elif "-cal-" in n:
                P += [(n, f"s{k}", hx(v), "H-STEPMODEL", s) for k, v in sorted(S.items()) if v < min(t, U)]
                k, v, mdl = SP_RIVAL[(w, h)]
                P.append((n, f"s{k}", hx(v), mdl, s))
            else:
                k, v, mdl = SP_RIVAL[(w, h)]
                P.append((n, "gps_abort", str(gps_abort(t, S)), "H-STEPMODEL", s))
                P.append((n, "gps_abort", str(gps_abort(t, {**S, k: v})), mdl, s))
        elif st == "m6":
            S, A, B, U = model(w, h)
            if n.startswith("m6-c-"):
                pass
            elif "-cal-" in n:
                P += [(n, f"s{k}", hx(v), "H-STEPMODEL", s) for k, v in sorted(S.items()) if v < min(t, U)]
                if t >= U:
                    P.append((n, "need", hx(U), "H-STEPMODEL", s))
            else:
                left = span_left(t, S, A)
                if left is not None:
                    P.append((n, "gps_left", str(left), "H-SPAN", s))
                if t == A[6] and s == "heldout":
                    cls = M6_CLASS[(w, h)]
                    for mdl, by in M6_RIVALS.items():
                        if mdl != "H-SPAN":
                            P.append((n, "gps_left", str(by[cls]), mdl, s))
                if s == "fit" and t == A[6]:
                    for mdl, by in M6_RIVALS.items():
                        if mdl != "H-SPAN":
                            P.append((n, "gps_left", str(by["mapped"]), mdl, "fit"))
        elif st == "v":
            if n == "v-c4":
                P += [(n, f"s{k}", hx(v), "R7-REPEAT", "control") for k, v in sorted(VCAL4[0].items())]
                P.append((n, "nparts", "0", "R7-REPEAT", "control"))
            elif n.startswith("v-w8-"):
                others = ",".join(f"v-w8-{i}" for i in (1, 2, 3) if f"v-w8-{i}" != n)
                P.append((n, "steps", "=" + others, "H-DET", s))
                P.append((n, "need", "=" + others, "H-DET", s))
                P.append((n, "blocks", "=" + others, "H-DET", s))
                P.append((n, "nparts", "0", "H-DET", s))
        elif st == "f9":
            S, A, B, U = model(w, h)
            if "-cal-" in n:
                P += [(n, f"s{k}", hx(v), "H-STEPMODEL", "control") for k, v in sorted(S.items()) if v < U]
                P.append((n, "nparts", "0", "H-STEPMODEL", "control"))
            else:
                f = T["f9"][f"{w}x{h}:{hx(t)}"]
                if f["F9"] is not None:
                    P.append((n, "nparts", str(f["F9"][0]), "F9", s))
                    P.append((n, "runpeaks", ",".join(f["F9"][1]), "F9", s))
                P.append((n, "nparts", str(f["d=7/4"]), "d=7/4", s))
                P.append((n, "nparts", str(f["d=1"]), "d=1", s))
                P.append((n, "overflow", str(f["E625"]), "E625", s))
        elif st == "k":
            sc = next(x for x in T["k"] if n.startswith(f"k-cal-{x['name']}") or n.startswith(f"k-{x['name']}-"))
            if "-cal-" in n:
                P += [(n, "need", hx(sc["U"]), "HU1", s), (n, "nparts", "0", "HU1", s)]
            else:
                pr = sc["pred"][hx(t)]
                for mdl in ("H-KICKS", "H-UNION"):
                    P.append((n, "nparts", str(pr[mdl][0]), mdl, s))
                    P.append((n, "runpeaks", ",".join(pr[mdl][1]), mdl, s))
        elif st == "u":
            if n != "u-c-s22":
                sh = next(x for x in T["u"] if x["name"] == n)
                P += [(n, "need", hx(sh["U_hu1"]), "HU1", s), (n, "need", hx(sh["U_bbox"]), "H-BBOX", s),
                      (n, "nparts", "0", "HU1", s)]
    return P


def table_text(st, rows):
    head = {"a0": "a0 (gate, 6 controls): R7's s-a0 rows on module 37EC97AB; a control off or without "
                  "a reading stops the session before sp",
            "sp": "sp (20): steps pinned by the abort's global page count; 2 controls, 18 held out",
            "m6": "m6 (69): band 6 margin; 2 controls, 17 fit (mapped, dumped), 44 held out, 6 explore",
            "v": "v (14): larger objects with written outputs; 1 control, 3 held out (H-DET), 10 explore",
            "f9": "f9 (18): many-object partial-render counts; 3 calibrations (controls), 15 held out",
            "k": "k (25): multi-kick scenes; needs held out on HU1, counts explore (OL7 b: no fit)",
            "u": "u (9): the U clause on other shapes; 1 control, 8 held out (HU1 against H-BBOX)"}[st]
    out = [f"#stage {st}", "#limit 0", f"# {head}"]
    out += ["|".join((r["name"], r["set"], r["risk"], r["knobs"], r["tool"], r["args"])) for r in rows]
    return "\n".join(out) + "\n"


def extra_knobs(T_):
    return sorted({k for rows in T_.values() for r in rows for k in r["knobs"].split() if k.startswith("ctl:")})


def knob_values(T_):
    return sorted({k.split("=", 1)[1] for rows in T_.values() for r in rows for k in r["knobs"].split()
                   if k.startswith("dbg:render_pb_pages=")}, key=lambda v: int(v, 16))


def outputs():
    T_ = tables()
    files = {}
    for st in STAGES:
        files[f"tables/{st}.txt"] = table_text(st, T_[st])
        P = predictions(st, T_[st])
        files[f"predictions/{st}.tsv"] = "case\tquantity\tvalue\tmodel\tset\n" + "".join(
            "\t".join(p) + "\n" for p in P)
    return T_, files


def main(argv):
    T_, files = outputs()
    if argv[1:] == ["--check"]:
        bad = [f for f, t in files.items() if not (KP / f).exists() or (KP / f).read_text() != t]
        print("generator current" if not bad else "differs: " + " ".join(bad))
        return 1 if bad else 0
    for f, t in files.items():
        (KP / f).parent.mkdir(exist_ok=True)
        (KP / f).write_text(t)
    print(sum(len(v) for v in T_.values()), "jobs:", {s: len(v) for s, v in T_.items()})
    print("extra_knobs =", json.dumps(extra_knobs(T_)))
    print("render_pb_pages values =", json.dumps(knob_values(T_)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
