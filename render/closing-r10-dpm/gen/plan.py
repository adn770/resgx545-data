#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r10-dpm's generator (round 10, session S10-dpm of closing10/seeds/exp-seeds-r10.md
section 10, decision R10-5 (a): safe class only). Writes tables/s6rep.txt and predictions/s6rep.tsv
for the one stage s6rep (17 jobs): Q210's replicates, which decide whether the step replay is
NOISY or BIASED at its sixth global page (S_6).

  gen/r9_tables.json   r9-ldpm's frozen tables (a byte copy of the published
                       render/closing-r9-ldpm/gen/r9_tables.json): E874's step replay S_k per
                       target, U (the need)
  constants below      r9-ldpm's a0 rows, and the kept S_6 reads of E962 and E936 (KEPT)

  python3 gen/plan.py          write the tables and predictions
  python3 gen/plan.py --check  exit 1 when a written file differs from what it would write

The rows: the a0 premise pair of r9-ldpm (a0-cal-2048 at P 0x162 and a0-cal-2048f at P 0x422,
controls, token for token) and, for each of five targets, three calibration replicates (P 0x422:
thr0 = 0x400, above every need, so the job completes and reads S_2 .. S_7 and the need), run
round-robin (replicate 1 of each target, then 2, then 3) so that a replicate never follows its own
target's. Every job is t4 under regtimeline (tool rt, wraps = true) with R5-dpm's 16 registers,
`dbg:render_pb_pages=0x422 expect:rc3-overflow` (a calibration that completes ends rc 0, which is
also an expected end), `#limit 0`: no poke, no held reset, no planned fault, no expectfault.

FROZEN BEFORE THE RUN (the rivals, per target T with the replay's S_6 = R and the three
replicates' S_6 reads v1 v2 v3, S_6 = max(pp, p - 1) as E962 read it):
  H-NOISE  R lies in [min v, max v] and max v - min v <= 2 (SPAN pages)
  H-BIAS   every v is R + 1 or R + 2 (E962's reading)
  also tallied: H-BIAS-SAME (every v equals the kept read of the same target, KEPT), H-REPLAY6
  (every v = R: E874's replay exact), H-REPLAY (the need = U, nparts 0).
Per target a class: NOISE, BIAS or NEITHER. The decision over the 5 targets (score.py prints it):
  NOISE decided  at least 4 of 5 targets NOISE and no more than 1 BIAS
  BIAS decided   at least 4 of 5 targets BIAS and no more than 1 NOISE
  MIXED          anything else (per-target classes recorded; no verdict for Q210's cause)
and only when both a0 controls pass; a control off makes the session's verdict "cannot tell"."""
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
STAGES = ("s6rep",)
REPS = 3
SPAN = 2                                    # H-NOISE: the replicates span at most 2 pages
BIAS = (1, 2)                               # H-BIAS: every replicate at R + 1 or R + 2
# the five targets (E962's four wide targets and E936's 2048x2304) and the S_6 each was read at
# once (E962: the w calibrations; 2048x2304: the seven kept runs of E936 and r9-ldpm's m6b, all one value)
TARGETS = ((4096, 1024), (4096, 1536), (3584, 1024), (2048, 512), (2048, 2304))
KEPT = {(4096, 1024): 0x17E, (4096, 1536): 0x22B, (3584, 1024): 0x14F, (2048, 512): 0x6F,
        (2048, 2304): 0x1AD}


def hx(v):
    return f"0x{v:x}"


def model(w, h):
    m = T["models"][f"{w}x{h}"]
    conv = lambda d: {int(k): int(v, 16) for k, v in d.items()}  # noqa: E731
    return conv(m["S"]), conv(m["A"]), int(m["U"], 16), [int(x, 16) for x in m["after6"]]


def tag(w, h):
    return f"c{w // 256:02d}{h // 256:02d}"


def rt(cmd):
    return f"0 {LEAD} {RT} -- {TOOL} {cmd}"


def probe(w, h, dump=False):
    c = f"probe --tri pixel --width {w} --height {h} --vertices 1500"
    if dump:
        c += ' --dump-render "$W"'
    return rt(f"{c} {PROG}")


def row(name, sset, thr0, cmd, words=()):
    knobs = [f"dbg:render_pb_pages={hx(thr0 + D_OFF)}", "expect:rc3-overflow"] + list(words)
    return dict(name=name, set=sset, risk="safe", knobs=" ".join(knobs), tool="rt", args=cmd, thr0=thr0)


def reads(*keys):
    return "reads:" + ",".join(keys)


def ctl(**kv):
    return [f"ctl:{k}={v}" for k, v in kv.items()]


def stage_s6rep():
    p = probe(2048, 2048, dump=True)
    rows = [
        row("a0-cal-2048", "control", 0x140, p, [reads("s2", "s3", "s4", "s5", "knob", "gps_left")]
            + ctl(gps_left="0x2")),
        row("a0-cal-2048f", "control", CLAMP, p,
            [reads("s2", "s3", "s4", "s5", "s6", "s7", "knob", "need", "nparts")]
            + ctl(need="0x213", nparts="0")),
    ]
    for k in range(1, REPS + 1):
        for w, h in TARGETS:
            rows.append(row(f"s6r-{tag(w, h)}-{k}", "heldout", CLAMP, probe(w, h)))
    return rows


def tables():
    return {"s6rep": stage_s6rep()}


def target(r):
    a = r["args"].split()
    return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])


def thr0_of(r):
    k = r["knobs"] if isinstance(r["knobs"], list) else r["knobs"].split()
    return int(next(x for x in k if x.startswith("dbg:")).split("=")[1], 16) - D_OFF


def rng(lo, hi):
    return f"{hx(lo)}..{hx(hi)}"


def predictions(st, rows):
    """[(case, quantity, value, model, set, source)]"""
    P = []
    src = {"control": "E935 (r8-ldpm a0), r9-ldpm a0", "heldout": "E874 replay, E962/E936 reads (r9_tables.json)"}
    for r in rows:
        n, s, t = r["name"], r["set"], r["thr0"]
        w, h = target(r)
        add = lambda q, v, m, ss=None: P.append((n, q, v, m, ss or s, src[s]))  # noqa: E731
        add("knob", hx(t), "CTL", "control")
        for k in r["knobs"].split():
            if k.startswith("ctl:"):
                q, v = k[4:].split("=", 1)
                add(q, v, "CTL", "control")
        S, A, U, _ = model(w, h)
        if s == "control":
            if n == "a0-cal-2048":
                for k, v in sorted(S.items()):
                    if v < t:
                        add(f"s{k}", hx(v), "H-STEPMODEL")
            else:
                for k, v in sorted(S.items()):
                    add(f"s{k}", hx(v), "H-STEPMODEL")
            continue
        R = S[6]
        add("nparts", "0", "H-REPLAY")
        add("need", hx(U), "H-REPLAY")
        add("S6", rng(R + BIAS[0], R + BIAS[1]), "H-BIAS")
        add("S6", hx(KEPT[(w, h)]), "H-BIAS-SAME")
        add("S6", hx(R), "H-REPLAY6")
        if n.endswith("-1"):                 # the target-level rivals, on the target's first replicate
            add("S6_range", f"contains={hx(R)};span<={SPAN}", "H-NOISE")
            add("S6_range", f"all={rng(R + BIAS[0], R + BIAS[1])}", "H-BIAS")
    return P


HEAD = ("s6rep (17): the a0 premise pair (r9-ldpm's a0-cal-2048 and a0-cal-2048f, controls: a control "
        "off stops the stage, rc 24) and 3 calibration replicates at each of 4096x1024, 4096x1536, "
        "3584x1024, 2048x512 and 2048x2304 (round-robin): H-NOISE against H-BIAS at S_6")


def table_text(st, rows):
    out = [f"#stage {st}", "#limit 0", f"# {HEAD}"]
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
