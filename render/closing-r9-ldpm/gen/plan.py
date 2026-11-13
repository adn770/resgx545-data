#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r9-ldpm's generator (round 9, session S9-ldpm of closing9/seeds/exp-seeds-r9.md section
7, decision R9-5 (a): safe class only). Writes tables/STAGE.txt and predictions/STAGE.tsv for the
four stages, in run order a0, m6b, w, f9b (59 jobs; stage k2 does not run: OD-3's frozen candidate
gave 7 of 20, offline/od3_score.out), from:

  gen/r9_tables.json   offline/r9_tables.py's frozen tables (a byte copy; FREEZE-tables.sha256):
                       E874's step replay S_k, H-SPAN's A_k, U and after[b_6 + d] per target;
                       m6b's targets with OD-2's frozen end E_6 (H-NEXT1, offline/od2_band6.json);
                       w's targets and cells (OD-1, offline/od1_wide.json); f9b's cells (F9,
                       H-NORAISE, E854's d = 7/4 and d = 1, E625)
  constants below      r8-ldpm's a0 rows and E935/E936's kept readings the controls repeat

  python3 gen/plan.py          write the tables and predictions
  python3 gen/plan.py --check  exit 1 when a written file differs from what it would write

Every job is a plain job of the kit: t4 run under regtimeline (tool rt, wraps = true), the debugfs
knob render_pb_pages written by the kit (dbg:render_pb_pages=P, P = thr0 + 0x22, restored to
0x422), a `probe` DPM cell's rc 3 "scene overflowed" an expected end (expect:rc3-overflow), the one
`tri` job's rc 1 with its diff line a reading (expectdiff). No poke, no held reset, no planned
fault, no expectfault row (#limit 0). No 8-pair (`--vtx-coords 8`) row: OD-1 froze no need for
them (E937: no step rule for blocks larger than 67 dwords), so none runs (E937's rule, a
`vtx_coord8` scene only with a calibration in its stage, is kept by having none)."""
from __future__ import annotations

import json
import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
T = json.loads((KP / "gen" / "r9_tables.json").read_text())

RT = "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"
LEAD = "0.3"
TOOL = '"$HOME/sgxfive-test-rgn4"'
PROG = '"$S/bins/p1139-green.bin"'
D_OFF = 0x22
CLAMP = 0x400
STAGES = ("a0", "m6b", "w", "f9b")
QF_PEAKS = (0x80, 0xA0, 0x2)
WIN = (-1, 3)                                # m6b's window around A_6: A_6 - 1 .. A_6 + 3
M6_RIVALS = {"H-BIG6": {"small": 1, "one": 1, "both": 2},
             "H-ANY6": {"small": 1, "one": 2, "both": 2},
             "H-6LATE": {"small": 2, "one": 2, "both": 2}}


def hx(v):
    return f"0x{v:x}"


def model(w, h):
    m = T["models"][f"{w}x{h}"]
    conv = lambda d: {int(k): int(v, 16) for k, v in d.items()}  # noqa: E731
    return conv(m["S"]), conv(m["A"]), int(m["U"], 16), [int(x, 16) for x in m["after6"]]


def left_by(thr0, S, end6):
    """Band 6's pages left by an end E_6 (H-SPAN: A_6; H-NEXT1: after[b_6 + 1]): 2 iff S_6 < thr0
    < E_6, 1 from E_6 to S_7; None at a step cell or outside band 6."""
    if thr0 in S.values() or not (S[6] < thr0 < S.get(7, 1 << 30)):
        return None
    return 2 if thr0 < end6 else 1


def gps_abort(thr0, S):
    return 1 + sum(1 for v in S.values() if v < thr0)


def tag(w, h):
    return f"c{w // 256:02d}{h // 256:02d}"


# ---- commands ---------------------------------------------------------------------------------
def rt(cmd):
    return f"0 {LEAD} {RT} -- {TOOL} {cmd}"


def probe(w, h, dump=False):
    c = f"probe --tri pixel --width {w} --height {h} --vertices 1500"
    if dump:
        c += ' --dump-render "$W"'
    return rt(f"{c} {PROG}")


def tri_qf():
    return rt('tri --width 4096 --height 4096 -n 1 --keep-overflow --wait-ms 20000 --words "$W" --regs 0x0700-0x074c')


def row(name, sset, thr0, cmd, words=()):
    kind = cmd.split(" -- ", 1)[1].split()[1]
    knobs = [f"dbg:render_pb_pages={hx(thr0 + D_OFF)}"]
    knobs.append("expect:rc3-overflow" if kind == "probe" else "expectdiff")
    knobs += list(words)
    return dict(name=name, set=sset, risk="safe", knobs=" ".join(knobs), tool="rt", args=cmd, thr0=thr0)


def reads(*keys):
    return "reads:" + ",".join(keys)


def ctl(**kv):
    return [f"ctl:{k}={v}" for k, v in kv.items()]


# ---- the stages ----------------------------------------------------------------------------------
def stage_a0():
    """r8-ldpm's a0 rows token for token (E935's six controls), on module B60AB0B4."""
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
        row("a0-qf-0xa2", "control", 0x80, tri_qf(),
            [reads("nparts", "runpeaks", "knob", "gmax")]
            + ctl(nparts="2", runpeaks=",".join(hx(x) for x in QF_PEAKS))),
    ]


def stage_m6b():
    """Six replicates of E936 (controls, no stop: a replicate off gates the stage's verdicts), then
    four new targets: calibration, A_6 - 1 .. A_6 + 3, and A_6 again dumped (explore)."""
    rows = []
    for rp in T["repl"]:
        w, h = rp["w"], rp["h"]
        for t, v in sorted(rp["cells"].items(), key=lambda x: int(x[0], 16)):
            rows.append(row(f"m6b-r-{tag(w, h)}-{t}", "control", int(t, 16), probe(w, h),
                            [reads("gps_next", "knob")]))
    for m in T["m6b"]:
        w, h = m["w"], m["h"]
        A6 = int(m["A6"], 16)
        rows.append(row(f"m6b-cal-{tag(w, h)}", "heldout", CLAMP, probe(w, h)))
        for d in range(WIN[0], WIN[1] + 1):
            rows.append(row(f"m6b-{tag(w, h)}-{hx(A6 + d)}", "heldout", A6 + d, probe(w, h)))
        rows.append(row(f"m6b-{tag(w, h)}-{hx(A6)}-d", "explore", A6, probe(w, h, dump=True)))
    return rows


def stage_w():
    """OD-1's four wide targets: the calibration (a control: its need is OD-1's held-out reading,
    and it gates its own cell; no stop) and one cell each."""
    rows = []
    for x in T["w"]:
        w, h = x["w"], x["h"]
        S, A, U, _ = model(w, h)
        ks = [k for k in sorted(S) if S[k] < U]
        rows.append(row(f"w-cal-{tag(w, h)}", "control", CLAMP, probe(w, h),
                        [reads(*[f"s{k}" for k in ks], "need", "knob", "nparts")]))
        rows.append(row(f"w-{tag(w, h)}-{x['thr0']}", "heldout", int(x["thr0"], 16), probe(w, h)))
    return rows


def stage_f9b():
    """Three targets: the calibration (a control; its need off stops the stage, rc 24), the cells off
    band 4 r9_tables.py found (two, one at 1280x1280) and one band 4 cell (F9 against H-NORAISE)."""
    rows = []
    for x in T["f9b"]:
        w, h = x["w"], x["h"]
        S, A, U, _ = model(w, h)
        ks = [k for k in sorted(S) if S[k] < U]
        rows.append(row(f"f9b-cal-{tag(w, h)}", "control", CLAMP, probe(w, h),
                        [reads(*[f"s{k}" for k in ks], "need", "knob")] + ctl(need=hx(U))))
        for c in x["cells"]:
            rows.append(row(f"f9b-{tag(w, h)}-{c['thr0']}" + ("-b4" if c["kind"] == "band4" else ""),
                            "heldout", int(c["thr0"], 16), probe(w, h)))
    return rows


def tables():
    return {"a0": stage_a0(), "m6b": stage_m6b(), "w": stage_w(), "f9b": stage_f9b()}


def target(r):
    a = r["args"].split()
    return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])


def thr0_of(r):
    k = r["knobs"] if isinstance(r["knobs"], list) else r["knobs"].split()
    return int(next(x for x in k if x.startswith("dbg:")).split("=")[1], 16) - D_OFF


# ---- predictions --------------------------------------------------------------------------------
def predictions(st, rows):
    """[(case, quantity, value, model, set, source)]"""
    P = []
    src = {"a0": "E935 (r8-ldpm a0)", "m6b": "r9_tables.json (E874, E900, OD-2 H-NEXT1)",
           "w": "r9_tables.json (OD-1: E874's U, HU1, F9)", "f9b": "r9_tables.json (F9, E938)"}[st]
    for r in rows:
        n, s, t = r["name"], r["set"], r["thr0"]
        w, h = target(r)
        add = lambda q, v, m, ss=None: P.append((n, q, v, m, ss or s, src))  # noqa: E731
        add("knob", hx(t), "CTL", "control")
        for k in r["knobs"].split():
            if k.startswith("ctl:"):
                q, v = k[4:].split("=", 1)
                add(q, v, "CTL", "control")
        S, A, U, after = model(w, h) if f"{w}x{h}" in T["models"] else ({}, {}, None, [])
        if st == "a0":
            if n in ("a0-cal-2048", "a0-cal-2048f"):
                for k, v in sorted(S.items()):
                    if v < t:
                        add(f"s{k}", hx(v), "H-STEPMODEL", "control")
        elif st == "m6b":
            if s == "control":
                rp = next(x for x in T["repl"] if (x["w"], x["h"]) == (w, h))
                add("gps_next", str(rp["cells"][hx(t)]), "CTL", "control")
            elif "-cal-" in n:
                for k, v in sorted(S.items()):
                    if v < min(t, U):
                        add(f"s{k}", hx(v), "H-STEPMODEL")
                add("need", hx(U), "H-STEPMODEL")
            else:
                m = next(x for x in T["m6b"] if (x["w"], x["h"]) == (w, h))
                for mdl, end in (("H-SPAN", A[6]), ("H-NEXT1", int(m["E6"], 16) if m["E6"] else None),
                                 ("H-NEXT2", after[2])):
                    if end is None:
                        continue
                    v = left_by(t, S, end)
                    if v is not None:
                        add("gps_next", str(v), mdl)
                if t == A[6] and s == "heldout":
                    for mdl, by in M6_RIVALS.items():
                        add("gps_next", str(by[m["class"]]), mdl)
        elif st == "w":
            x = next(y for y in T["w"] if (y["w"], y["h"]) == (w, h))
            if "-cal-" in n:
                for k, v in sorted(S.items()):
                    if v < U:
                        add(f"s{k}", hx(v), "H-STEPMODEL")
                add("nparts", "0", "H-REPLAY")
                add("need", x["U"], "H-REPLAY")
                add("need", x["HU1"], "HU1")
            else:
                add("nparts", str(x["F9"][0]), "F9")
                add("runpeaks", ",".join(x["F9"][1]), "F9")
                add("nparts", str(x["d=7/4"]), "d=7/4")
                add("nparts", str(x["d=1"]), "d=1")
                add("overflow", "1", "E625")
                add("gps_abort", hx(x["gps_abort"]), "H-ABORT")
        elif st == "f9b":
            x = next(y for y in T["f9b"] if (y["w"], y["h"]) == (w, h))
            if "-cal-" in n:
                for k, v in sorted(S.items()):
                    if v < U:
                        add(f"s{k}", hx(v), "H-STEPMODEL", "control")
                add("nparts", "0", "H-STEPMODEL", "control")
            else:
                c = next(y for y in x["cells"] if int(y["thr0"], 16) == t)
                add("nparts", str(c["F9"][0]), "F9")
                add("runpeaks", ",".join(c["F9"][1]), "F9")
                if c["kind"] == "band4":
                    add("nparts", str(c["H-NORAISE"][0]), "H-NORAISE")
                    add("runpeaks", ",".join(c["H-NORAISE"][1]), "H-NORAISE")
                add("nparts", str(c["d=7/4"]), "d=7/4")
                add("nparts", str(c["d=1"]), "d=1")
                add("overflow", str(c["E625"]), "E625")
                add("gps_abort", hx(c["gps_abort"]), "H-ABORT")
    return P


HEAD = {"a0": "a0 (gate, 6 controls): r8-ldpm's a0 rows (E935) on module B60AB0B4; a control off stops a0 "
              "(rc 24) and no later stage opens",
        "m6b": "m6b (34): band 6 at four new targets (OD-2's H-NEXT1 against H-SPAN, H-NEXT2 and E936's "
               "rivals), six E936 replicates as controls (no stop: off gates the verdicts)",
        "w": "w (8): OD-1's four wide targets, calibration (need: H-REPLAY against HU1; gates its "
             "cell) and one F9 cell each",
        "f9b": "f9b (11): F9 at three new targets, one or two cells off band 4 and one band 4 cell (F9 "
               "against H-NORAISE); a calibration's need off stops the stage (rc 24)"}


def table_text(st, rows):
    out = [f"#stage {st}", "#limit 0", f"# {HEAD[st]}"]
    out += ["|".join((r["name"], r["set"], r["risk"], r["knobs"], r["tool"], r["args"])) for r in rows]
    return "\n".join(out) + "\n"


def extra_knobs(T_):
    return sorted({k for rows in T_.values() for r in rows for k in r["knobs"].split() if k.startswith("ctl:")})


def knob_values(T_):
    vals = {k.split("=", 1)[1] for rows in T_.values() for r in rows for k in r["knobs"].split()
            if k.startswith("dbg:render_pb_pages=")}
    return sorted(vals | {"0x422"}, key=lambda v: int(v, 16))


def outputs():
    T_ = tables()
    files = {}
    for st in STAGES:
        files[f"tables/{st}.txt"] = table_text(st, T_[st])
        P = predictions(st, T_[st])
        files[f"predictions/{st}.tsv"] = "case\tquantity\tvalue\tmodel\tset\tsource\n" + "".join(
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
