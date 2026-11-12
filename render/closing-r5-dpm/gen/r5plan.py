#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r5plan.py: the frozen content of R5-dpm, generated from the approved plan closing5/dpm/exp-dpm-r5.md (decisions R5-3 (a) and
R5-5 (a): all seven stages, 82 jobs, the 16-register list with 0x0734, 0x0730, 0x012c and 0x0a74 swapped in, stage A3 with the own
task oomring, last).  Writes tables/STAGE.txt, predictions/STAGE.tsv, TABLES.md and stages.txt.  Pure python, no I/O but those files.

    .../pixel-faults/.venv/bin/python gen/r5plan.py

Every number below is the plan's (section 1's step table, section 3's count rule, section 4's stage list); the constants that the
plan leaves to the build (the two B scenes, the B cells, the A3 rung reading) are chosen here by the rules written next to them and
listed in PREFLIGHT.md section 7.
"""
from __future__ import annotations

import pathlib
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KP / "gen"))
import hu1  # noqa: E402

# ------------------------------------------------------------------------------------------------ the measurement
RT = "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"   # decision 4 (a): 16 registers
RT_G_C4 = "0x0624-0x0628,0x0654-0x0660,0x0700-0x0710,0x0720-0x072c,0x0748"                     # g-c4's, for the record
PROG = "p1139-green.bin"
D_OFF = 0x22                                   # P = thr0 + 0x22 (the knob proof: the job's own 0x0624 = P - 0x22)


def probe(w, h):
    """The 1500-vertex probe (g-c4's command).  Freeze 2 (after attempt 1's d-a0): --dump-render only at 2048x2048, where round 3 and
    attempt 1 dumped cleanly; no reading uses the dumps, and the larger targets' TA data dump is where attempt 1's capture failed."""
    dump = ' --dump-render "$W/dump"' if (w, h) == (2048, 2048) else ""
    return f'probe --tri pixel --width {w} --height {h} --vertices 1500{dump} "$S/{PROG}"'


def qtri(move=None):
    """g-qf's command (E832), and E773's s275 form for a moved triangle (-n 1 --move 1:DX,DY --keep-going)."""
    mv = f" --move 1:{move[0]},{move[1]} --keep-going" if move else ""
    return f'tri --width 4096 --height 4096 -n 1{mv} --keep-overflow --wait-ms 20000 --words "$W/words" --regs 0x0700-0x074c'


# ------------------------------------------------------------------------------------------------ plan section 1 (kept data)
TARGETS = {"c2048": (2048, 2048), "c4096": (4096, 4096), "c4x2": (4096, 2048), "c2x4": (2048, 4096), "c33": (3072, 3072)}
STEPS = {   # S_k: the page count read just before global page k appears (plan section 1's table)
    (2048, 2048): {2: 0x51, 3: 0x9d, 4: 0xe8, 5: 0x132},
    (4096, 4096): {2: 0x125, 3: 0x240, 4: 0x35b},
    (4096, 2048): {2: 0x97, 3: 0x126, 4: 0x1b9},
    (2048, 4096): {2: 0x9a, 3: 0x12c, 4: 0x1be, 5: 0x255},
    (3072, 3072): {2: 0xa9, 3: 0x14d, 4: 0x1ef, 5: 0x293},
}
LAST_RAISE = {(2048, 2048): 0xe2, (4096, 4096): 0x351, (4096, 2048): 0x1b2, (2048, 4096): 0x1b6, (3072, 3072): 0x1e8}
M_TAIL = {wh: STEPS[wh][4] - LAST_RAISE[wh] for wh in STEPS}          # m: 6, 10, 7, 8, 7

# ------------------------------------------------------------------------------------------------ hypotheses (plan section 2)


def band(wh, thr0):
    """The global page the first run ends in: 1 + the steps S_k (k >= 2) below thr0 (S_k itself counts as the step's
    page: the page count reads S_k when page k is asked for)."""
    return 1 + sum(1 for k, s in STEPS[wh].items() if s < thr0)


def is_step(wh, thr0, steps=None):
    return thr0 in (steps or STEPS[wh]).values()


def guard_class(wh, thr0, hyp="PEND"):
    """R-5's guard on the ladder of section 1 (item 5) for a cell OFF a step: below S3 the floor (raise); from S3 to S4 - m two of
    three left (raise); the last m - 1 pages before S4 one left (silent); above S4 silent.  On a step S_k (a grow cell): H-PEND
    takes the count one lower at the resume, so the cell behaves as the band below it (S2, S3: raise; S4, S5: silent); H-BLOCK:
    silent always."""
    s = STEPS[wh]
    if thr0 in s.values():
        k = next(k for k, v in s.items() if v == thr0)
        if hyp == "BLOCK":
            return "N"
        return "R" if k <= 3 else "N"
    if thr0 < s[3]:
        return "R"
    if thr0 <= LAST_RAISE[wh]:
        return "R"
    return "N"


def tail_left(wh, thr0):
    """H-TAIL (exploratory): global pages left by the first partial render: 2 normally in bands 2 and 4 of the T cells, one fewer
    in the last m - 1 pages before the next step (m fitted on band 3)."""
    nxt = min((v for v in STEPS[wh].values() if v > thr0), default=None)
    m = M_TAIL[wh]
    return 1 if (nxt is not None and nxt - thr0 <= m - 1) else 2


# H-CNT (plan section 3): n = min{n >= 1 : thr0 + n (thr0 + 0x20 - d) >= U + k}, d = 7/4, k = 0; the alternatives qf_cells.py lists
def cnt(t, U, d=F(7, 4), k=0):
    n = 1
    while t + n * (t + 0x20 - d) < U + k:
        n += 1
    return n


def e625(t, U, k, s):
    return max(1, 1 + (U + k - t) // (t + s))


ALTS = {"d=1": lambda t, U: cnt(t, U, F(1)), "d=5/4": lambda t, U: cnt(t, U, F(5, 4)), "d=9/4": lambda t, U: cnt(t, U, F(9, 4)),
        "d=3": lambda t, U: cnt(t, U, F(3)), "E625(0,0x1e)": lambda t, U: e625(t, U, 0, 0x1e),
        "E625(-1,0x1e)": lambda t, U: e625(t, U, -1, 0x1e), "E625(2,0x1f)": lambda t, U: e625(t, U, 2, 0x1f)}

# B's scenes (plan: "one triangle moved (--move) to HU1 needs near 120 and 200 at 4096x4096, single kick").  Build rule: moves along
# x in steps of 64 pixels (E773's s275 is (1024, 0)); the move whose HU1 is nearest 120 and 200, ties to the smaller move.
B_MOVES = {"s119": (2560, 0), "s198": (1984, 0)}
B_U = {k: hu1.hu1(4096, 4096, hu1.moved(4096, 4096, *mv))[0] for k, mv in B_MOVES.items()}


def b_scene_pick(target):
    best = None
    for dx in range(0, 4096, 64):
        u = hu1.hu1(4096, 4096, hu1.moved(4096, 4096, dx, 0))[0]
        key = (abs(u - target), dx)
        if best is None or key < best[0]:
            best = (key, dx, u)
    return best[1], best[2]


def b_cells(U, want=10):
    """Plan section 4: the pairs around the rule's steps n 1/2, 2/3, 3/4, 5/6 and thr0 2 and 3.  Build rule for a scene whose
    count never reaches 5 (U = 119: no 5/6 step): fill to `want` with the cell one above each step, the highest count's step first.
    Returns ascending thr0."""
    step = {}
    for t in range(1, U):
        for k in range(1, 12):
            if cnt(t, U) <= k and k not in step:
                step[k] = t
    cells = []
    for hi_n in (1, 2, 3, 5):       # the step from hi_n + 1 to hi_n
        t = step.get(hi_n)
        if t is not None and t > 1 and cnt(t - 1, U) == hi_n + 1:
            cells += [t - 1, t]
    cells += [2, 3]
    for hi_n in (5, 3, 2, 1):
        t = step.get(hi_n)
        if len(set(cells)) >= want:
            break
        if t is not None and t > 1 and cnt(t - 1, U) == hi_n + 1:
            cells.append(t + 1)
    return sorted(set(cells))[:want]


# ------------------------------------------------------------------------------------------------ A3: the rungs (gen_oomring.py)
OOM = (1 << 20) | (1 << 21)
EOR = 1 << 4

# ------------------------------------------------------------------------------------------------ the stages
STAGES = ["d-a0", "d-a1", "d-a2", "d-a2b", "d-t", "d-b", "d-a3"]
HDR = {
    "d-a0": "A0 premise (8): the two calibrations (steps of section 1) and the kept flips on rgn4 with the new register list.  Every row is "
            "a premise (prem): a control off, a calibration whose steps are not monotone, or a job whose own 0x0624 is not P - 0x22 STOPS "
            "the session before A1 (rc 10, state/CTLFAIL).",
    "d-a1": "A1 repeat (9): c4-b3 (P 0x10a) five times, interleaved with S4 - 1, S4 + 1 (S4 read from a0-cal-2048 by the runner), c4-b4 "
            "(0xe4) and c4-b2 (0xf0).  H-GREQ: grow in 5 of 5 and none of the 4 others; all 9 silent.",
    "d-a2": "A2 held out (16): cells on and around the steps read from the calibrations (2048: S3 - 1, S3 twice, S3 + 1, S2 - 1, S2, S2 + 1, "
            "S5 - 1, S5, S5 + 1; 4096: S4 twice, S3 - 1, S3 twice, S3 + 1).  Grow at S only; S2 and S3 cells raise under H-PEND, are silent "
            "under H-BLOCK.",
    "d-a2b": "A2b other targets (6): a calibration and the S4 cell at 4096x2048, 2048x4096 and 3072x3072.  Grow and silent.",
    "d-t": "T tail (8, exploratory): 2048 thr0 S3 - 7 .. S3 - 4 and S5 - 7 .. S5 - 4: global pages left 2, 2, 1, 1 in each band.",
    "d-b": "B count (27): five g-qf controls of the default triangle at 4096x4096 (9, 4, 3, 2, 1 partial renders), two moved-triangle "
           "scenes (HU1 U = 119 and 198): a calibration each (ucal: the measured page need must equal HU1, else the scene's cells are "
           "skipped as void) and 10 held-out cells each, counts by H-CNT.",
    "d-a3": "A3 sa8 (8, LAST): the own task oomring armed before each job (fw: reset, arm, ring cleared, job, results page kept): c4-b5 "
            "twice, c4-b6 twice, P 0x10a three times, the 2048 S3 cell once.  An EDM stall is reset once; a second one ends A3.",
}


def row(name, sset, P, knobs, cmd, rt=RT, risk="safe"):
    return dict(name=name, set=sset, risk=risk, P=P, knobs=knobs, rt=rt, cmd=cmd)


def hx(v):
    return f"0x{v:x}"


def s_ref(g, k, off):
    return f"S:{g}:{k}:{off:+d}" if off else f"S:{g}:{k}:0"


def tables():
    p42, p44 = probe(2048, 2048), probe(4096, 4096)
    T = {}
    T["d-a0"] = [
        row("a0-cal-2048", "control", "0x162", "stophang prem cal:c2048", p42),
        row("a0-cal-4096", "control", "0x422", "stophang prem cal:c4096", p44),
        row("a0-c4-b5", "control", "0x104", "stophang prem ctl:R", p42),
        row("a0-c4-b6", "control", "0x105", "stophang prem ctl:N", p42),
        row("a0-c3-2048-0xe2", "control", "0xe2", "stophang prem ctl:R", p42),
        row("a0-c3-2048-0x122", "control", "0x122", "stophang prem ctl:N", p42),
        row("a0-4096-0x35a", "control", "0x37c", "stophang prem ctl:N", p44),
        row("a0-4096-0x35c", "control", "0x37e", "stophang prem ctl:N", p44),
    ]
    rep = lambda i: row(f"a1-rep{i}", "repeat", "0x10a", "stophang", p42)
    T["d-a1"] = [rep(1), row("a1-s4m1", "heldout", s_ref("c2048", 4, -1), "stophang", p42), rep(2),
                 row("a1-s4p1", "heldout", s_ref("c2048", 4, 1), "stophang", p42), rep(3),
                 row("a1-b4", "repeat", "0x106", "stophang", p42), rep(4), row("a1-b2", "repeat", "0x112", "stophang", p42), rep(5)]
    a2 = []
    for nm, k, off in [("s3m1", 3, -1), ("s3a", 3, 0), ("s3b", 3, 0), ("s3p1", 3, 1), ("s2m1", 2, -1), ("s2", 2, 0), ("s2p1", 2, 1),
                       ("s5m1", 5, -1), ("s5", 5, 0), ("s5p1", 5, 1)]:
        a2.append(row(f"a2-42-{nm}", "heldout", s_ref("c2048", k, off), "stophang", p42))
    for nm, k, off in [("s4a", 4, 0), ("s4b", 4, 0), ("s3m1", 3, -1), ("s3a", 3, 0), ("s3b", 3, 0), ("s3p1", 3, 1)]:
        a2.append(row(f"a2-44-{nm}", "heldout", s_ref("c4096", k, off), "stophang", p44))
    T["d-a2"] = a2
    T["d-a2b"] = []
    for g, tag in (("c4x2", "4x2"), ("c2x4", "2x4"), ("c33", "33")):
        w, h = TARGETS[g]
        T["d-a2b"] += [row(f"a2b-cal-{tag}", "control", "0x422", f"stophang cal:{g}", probe(w, h)),
                       row(f"a2b-{tag}-s4", "heldout", s_ref(g, 4, 0), "stophang", probe(w, h))]
    T["d-t"] = [row(f"t-s{k}m{-o}", "explore", s_ref("c2048", k, o), "stophang", p42) for k in (3, 5) for o in (-7, -6, -5, -4)]
    b = [row(f"b-qf-{hx(P)}", "control", hx(P), "stophang expectdiff", qtri()) for P in (0x24, 0x53, 0x54, 0xa2, 0xa3)]
    for sc, mv in B_MOVES.items():
        U = B_U[sc]
        b.append(row(f"b-cal-{sc}", "control", "0x422", f"stophang expectdiff ucal:{sc}:{U}", qtri(mv)))
        for t in b_cells(U):
            b.append(row(f"b-{sc}-{hx(t)}", "heldout", hx(t + D_OFF), f"stophang expectdiff uneed:{sc}", qtri(mv)))
    T["d-b"] = b
    T["d-a3"] = [row("a3-b5a", "control", "0x104", "stophang fw", p42), row("a3-b6a", "control", "0x105", "stophang fw", p42),
                 row("a3-r1", "repeat", "0x10a", "stophang fw", p42), row("a3-b5b", "control", "0x104", "stophang fw", p42),
                 row("a3-b6b", "control", "0x105", "stophang fw", p42), row("a3-r2", "repeat", "0x10a", "stophang fw", p42),
                 row("a3-r3", "repeat", "0x10a", "stophang fw", p42),
                 row("a3-s3", "heldout", s_ref("c2048", 3, 0), "stophang fw", p42)]
    return T


def target_of(cmd):
    import re
    m = re.search(r"--width (\d+) --height (\d+)", cmd)
    return (int(m.group(1)), int(m.group(2))) if m else None


def thr0_of(r):
    """The thr0 a row runs at, by the section 1 table for a derived row (the runner reads it from the calibration)."""
    P = r["P"]
    if P.startswith("S:"):
        _, g, k, off = P.split(":")
        return STEPS[TARGETS[g]][int(k)] + int(off)
    return int(P, 16) - D_OFF


def role(r):
    """('step'|'off', k, off) of a derived row; None for a fixed row."""
    if not r["P"].startswith("S:"):
        return None
    _, g, k, off = r["P"].split(":")
    return (int(k), int(off))


def predictions():
    """{stage: [(case, quantity, value, model, set)]}: the frozen predictions."""
    T = tables()
    out = {}
    for st, rows in T.items():
        P = []
        for r in rows:
            n, s, wh = r["name"], r["set"], target_of(r["cmd"])
            kn = r["knobs"].split()
            if st == "d-b":
                if n.startswith("b-qf-"):
                    t = int(r["P"], 16) - D_OFF
                    P.append((n, "nparts", str(cnt(t, 287)), "CTL", "control"))
                    P.append((n, "gmax", "1", "SCENE", "control"))
                elif n.startswith("b-cal-"):
                    sc = n[len("b-cal-"):]
                    P += [(n, "need", str(B_U[sc]), "HU1", "control"), (n, "nparts", "0", "HU1", "control"),
                          (n, "gmax", "1", "SCENE", "control")]
                else:
                    sc = n.split("-")[1]
                    t, U = int(r["P"], 16) - D_OFF, B_U[sc]
                    P.append((n, "nparts", str(cnt(t, U)), "H-CNT", "heldout"))
                    for a, f in ALTS.items():
                        P.append((n, "nparts", str(f(t, U)), a, "heldout"))
                    P.append((n, "gmax", "1", "SCENE", "heldout"))
                continue
            t = thr0_of(r)
            if any(k.startswith("cal:") for k in kn):
                for k, v in STEPS[wh].items():
                    if v < t:
                        P.append((n, f"S{k}", hx(v), "TABLE", "control"))
                P.append((n, "grow", "0", "H-GREQ", "control"))
                P.append((n, "knob", hx(t), "CTL", "control"))
                continue
            P.append((n, "knob", hx(t), "CTL", "control" if s == "control" else s))
            on = is_step(wh, t)
            P.append((n, "grow", "1" if on else "0", "H-GREQ", s))
            if st == "d-a1" and n.startswith("a1-rep"):
                P.append((n, "x734_clear", "1", "H-GREQ", s))
            if st == "d-t":
                P.append((n, "gps_left", str(tail_left(wh, t)), "H-TAIL", s))
                P.append((n, "cls", guard_class(wh, t), "R-5", s))
                continue
            cp, cb = guard_class(wh, t, "PEND"), guard_class(wh, t, "BLOCK")
            if any(k.startswith("ctl:") for k in kn):
                P.append((n, "cls", next(k for k in kn if k.startswith("ctl:"))[4:], "CTL", "control"))
            elif cp == cb:
                P.append((n, "cls", cp, "H-PEND", s))
                P.append((n, "cls", cb, "H-BLOCK", s))
            else:
                P.append((n, "cls", cp, "H-PEND", s))
                P.append((n, "cls", cb, "H-BLOCK", s))
            if st == "d-a3":
                if n.startswith("a3-b5"):
                    P += [(n, "dec_sa8_380", "0x180", "H-BITS", "heldout"), (n, "next_sa8_380", "0x380", "H-BITS", "heldout"),
                          (n, "cls", "R", "CTL-A3", "control")]
                elif n.startswith("a3-b6"):
                    P += [(n, "dec_sa8_380", "0x0", "H-BITS", "heldout"), (n, "cls", "N", "CTL-A3", "control")]
                else:
                    P += [(n, "dec_sa8_380", "0x0" if cp == "N" else "0x180", "H-PEND", s),
                          (n, "dec_sa8_380", "0x0", "H-BLOCK", s)]
                    if cp == "N":     # c4-b3's cell: the resume's skip bit tells the two apart
                        P += [(n, "eor_sa9_b8", "0", "H-PEND", s), (n, "eor_sa9_b8", "1", "H-BLOCK", s)]
        if st == "d-a1":
            P += [("@d-a1", "grows_of_5", "5", "H-GREQ", "repeat"), ("@d-a1", "grows_of_5", "<=1", "H-NOISE", "repeat")]
        if st == "d-a0":
            P += [("@d-a0", "grows", "0", "H-GREQ", "control")]
        out[st] = P
    return out


def table_text(st, rows):
    lines = [f"#stage {st}"]
    if st != "d-b":
        lines.append(f"#need $S/{PROG}")
    for chunk in [HDR[st][i:i + 128] for i in range(0, len(HDR[st]), 128)]:
        lines.append("# " + chunk)
    for r in rows:
        lines.append("|".join((r["name"], r["set"], r["risk"], r["P"], r["knobs"], r["rt"], r["cmd"])))
    return "\n".join(lines) + "\n"


def tables_md(T, Pr):
    out = ["# R5-dpm: the frozen tables and predictions (generated by gen/r5plan.py; do not edit)", "",
           f"Register list (all rows): `{RT}` (g-c4's was `{RT_G_C4}`).", "",
           "Derived P `S:G:k:off`: thr0 = S_k of calibration G + off, P = thr0 + 0x22 (the runner reads S_k from the calibration job's "
           "own timeline with run/r5read.py; the thr0 column below is the section 1 table's value).", ""]
    tot = 0
    for st in STAGES:
        out += [f"## {st} ({len(T[st])} jobs)", "", HDR[st], "", "| job | set | P | thr0 (table) | knobs | target / scene | predictions |",
                "|---|---|---|---|---|---|---|"]
        tot += len(T[st])
        for r in T[st]:
            pr = "; ".join(f"{q} = {v} [{m}]" for c, q, v, m, s in Pr[st] if c == r["name"])
            sc = "tri 1500" if r["cmd"].startswith("probe") else ("tri -n 1 " + (r["cmd"].split("--move ")[1].split()[0] if "--move" in r["cmd"] else "default"))
            wh = target_of(r["cmd"])
            out.append(f"| {r['name']} | {r['set']} | {r['P']} | {hx(thr0_of(r))} | {r['knobs']} | {wh[0]}x{wh[1]} {sc} | {pr} |")
        for c, q, v, m, s in Pr[st]:
            if c.startswith("@"):
                out.append(f"| {c} | {s} | | | | | {q} = {v} [{m}] |")
        out.append("")
    out.insert(4, f"**{tot} jobs** in {len(STAGES)} stages: " + ", ".join(f"{st} {len(T[st])}" for st in STAGES) + ".")
    out.insert(5, "")
    return "\n".join(out) + "\n"


def main():
    T, Pr = tables(), predictions()
    (KP / "tables").mkdir(exist_ok=True)
    (KP / "predictions").mkdir(exist_ok=True)
    for st in STAGES:
        (KP / "tables" / f"{st}.txt").write_text(table_text(st, T[st]))
        (KP / "predictions" / f"{st}.tsv").write_text("case\tquantity\tvalue\tmodel\tset\n" +
                                                      "".join("\t".join(p) + "\n" for p in Pr[st]))
    (KP / "stages.txt").write_text("\n".join(STAGES) + "\n")
    (KP / "TABLES.md").write_text(tables_md(T, Pr))
    print(sum(len(v) for v in T.values()), "jobs;", {st: len(T[st]) for st in STAGES}, "B U:", B_U)


if __name__ == "__main__":
    main()
