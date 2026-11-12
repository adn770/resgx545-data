#!/usr/bin/env python3
"""m6gen.py: write r6-misc's job tables (tables/STAGE.txt), frozen predictions (predictions/STAGE.tsv) and TABLES.md from
gen/models.py and the published records it reads (gen/data/sources.lst).  Deterministic: a second run writes the same bytes.
  PY gen/m6gen.py            (then run/freeze_m.sh freeze)
Table line: name|set|risk|knobs|tool|args   (tool: t4 = ~/sgxfive-test-rgn4, t6 = ~/scratch/r6m/bin/sgxfive-test)
Prediction line: case<TAB>quantity<TAB>value<TAB>model<TAB>set
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import os  # noqa: E402
import re  # noqa: E402

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import models as M  # noqa: E402

E511_SCRIPT = "/Users/jtorra/src/resgx545-data/ta/mtile-msaa-risky/scripts/mtile-msaa-risky.sh"
E511_SKIPPED = "/Users/jtorra/src/resgx545-data/ta/mtile-msaa-risky/skipped.tsv"
E507_SKIPPED = "/Users/jtorra/src/resgx545-data/ta/mtile-msaa/skipped.tsv"     # the safe script's 1024 x 768 R
E876_X10 = 0x97334F75829DAB25          # E876 / eot_sweep.out: the 64 x 32 fill with x ^ 0x10 (and ^ 0x18)


# ------------------------------------------------------------------------------------------------------------------ q289
def q289():
    rows, preds = [], []
    spec = [("f-ctl-64x32-x10", "control", 64, 32, "x", 0x10),
            ("f-base-128x64", "control", 128, 64, None, None),
            ("f-base-256x32", "control", 256, 32, None, None)]
    spec += [("f-128x64-x%02x" % v, "heldout", 128, 64, "x", v) for v in range(8, 0x48, 8)]
    spec += [("f-128x64-y%04x" % v, "heldout", 128, 64, "y", v) for v in range(0x1000, 0x9000, 0x1000)]
    spec += [("f-256x32-x%02x" % v, "heldout", 256, 32, "x", v) for v in (0x10, 0x18, 0x30, 0x50)]
    for name, sset, w, h, ax, v in spec:
        rows.append("%s|%s|safe|expectdiff needhash|t4|%s" % (name, sset, M.fill_args(w, h, ax, v)))
        preds.append((name, "job", "ok", "all", sset))
        preds.append((name, "outside", "0", "all", sset))
        preds.append((name, "size", "%dx%d" % (w, h), "all", sset))
        f = M.poke_field(ax, v) if ax else 0
        hs = {}
        for op in ("OR", "ADD", "XOR"):
            hh, wrong, unw = M.fill_predict(w, h, ax or "x", f, op)
            hs[op] = hh
            preds.append((name, "hash", "0x%016x" % hh, "M-" + op, sset))
            preds.append((name, "wrong", str(wrong), "M-" + op, sset))
            preds.append((name, "unwritten", ",".join(map(str, unw)) or "-", "M-" + op, sset))
        if name == "f-ctl-64x32-x10":
            assert hs["OR"] == hs["ADD"] == E876_X10, "the control's model hash is not E876's"
            preds.append((name, "hash", "0x%016x" % E876_X10, "E876", sset))
        preds.append((name, "separates", "yes" if hs["OR"] != hs["ADD"] else "no", "OR-vs-ADD", sset))
    head = ["#stage q289", "#limit 1",
            "# Q289 held-out fill row (E876 post hoc, DECISIONS-R6 R6-6 a: Q289 retires if this row picks OR or ADD).  The rgn4 tool's",
            "# fill (64 x 32 default, colour 0xff336699) at 128 x 64 and 256 x 32 with the end-of-tile DOUTU1 (pds:pixev dword 12) XORed:",
            "# x field V / 8, y field V / 0x1000 half-tile units.  Frozen: M-OR and M-ADD (hash, wrong pixels, unwritten tiles), job ok,",
            "# outside 0.  Controls that can fail: the 64 x 32 x ^ 0x10 case (E876's hash 0x97334f75829dab25) and the two baselines.",
            "# expectdiff: a fill with wrong pixels exits 1 (`fill: FAIL, N wrong dwords`, as in the kept sweeps): recorded, not a failure.",
            "# needhash: the row must print `target: WxH hash 0x...`; the second row without one stops the stage (rc 17).  No fault",
            "# is expected (1536 kept fills of this poke ran clean): any fault, hang or failure stops the stage (rc 4)."]
    return head, rows, preds


# ------------------------------------------------------------------------------------------------------------------ q287
def q287():
    rows, preds = [], []
    W = M.ZW
    spec = [("z-dry-34x17-y", "gate", 17, "y", "t6"),
            ("z-ctl-34x18-y-t4", "control", 18, "y", "t4"),
            ("z-ctl-34x18-y-t6", "control", 18, "y", "t6"),
            ("z-ctl-34x18-x-t6", "control", 18, "x", "t6"),
            ("z-fit-34x19-y-r1", "fit", 19, "y", "t6"), ("z-fit-34x19-y-r2", "fit", 19, "y", "t6")]
    for hh in (7, 11, 23, 35):
        spec += [("z-34x%d-y-r1" % hh, "heldout", hh, "y", "t6"), ("z-34x%d-y-r2" % hh, "heldout", hh, "y", "t6")]
    spec += [("z-34x19-x-r1", "heldout", 19, "x", "t6"), ("z-34x23-x-r1", "heldout", 23, "x", "t6"),
             ("z-34x35-x-r1", "heldout", 35, "x", "t6"),
             ("z-34x17-y-r2", "confirm", 17, "y", "t6"),
             ("z-34x21-y-r1", "confirm", 21, "y", "t6"), ("z-34x21-y-r2", "confirm", 21, "y", "t6")]
    for name, sset, h, ramp, tool in spec:
        knobs = "expectdiff" + (" gateodd" if sset == "gate" else "")
        rows.append("%s|%s|safe|%s|%s|%s" % (name, sset, knobs, tool, M.depth_args(W, h, ramp)))
        preds.append((name, "size", "%dx%d" % (W, h), "all", sset))
        preds.append((name, "dead", "0", "all", sset))
        for r in M.G.RULES:
            st = M.band(r, W, h)
            preds.append((name, "stored_count", str(len(st)), r, sset))
            preds.append((name, "stored_set_sha", M.set_sha(st), r, sset))
            preds.append((name, "extent", "%d,%d" % M.G.extent(r, W, h), r, sset))
        a, fl = M.band("A", W, h), M.band("FLOOR", W, h)
        preds.append((name, "separates", "yes" if a != fl else "no", "A-vs-FLOOR", sset))
        if sset == "control":
            preds.append((name, "stored_count", "924", "E831", sset))
    head = ["#stage q287", "#limit 1",
            "# Q287 odd heights (E730, E831; DECISIONS-R6 R6-6 a: Q287 by the odd heights).  E831's g-z row (the full-screen triangle's",
            "# depth ramp, buffer pre-filled 0xdeadbeef, a dword stored iff it is not 1.0f) at W 34 and odd heights, which the rgn4 tool",
            "# refuses: those rows run with t6, the tool built from resgx545 d9b2969 (a6d78db's libsgxfive, odd heights allowed).",
            "# Frozen: rule A (y + 0.5 < 1.25 H) against FLOOR (y < floor(1.25 H)), ROUND, CEIL, RSTRICT, cut at the tile area.",
            "# Separating (A != FLOOR): 19 (fit, the question's own .75 cell), 7, 11, 23, 35 (held out); .25 cells 17, 21 confirm",
            "# (A = FLOOR).  Controls that can fail: 34 x 18 (E831's 924, rule A's set) with t4 and with t6, and t6's x ramp.",
            "# gateodd (the first row, 34 x 17): if the module refuses the odd height (`rejected`, rc 1, no fault) the stage ends",
            "# cleanly (rc 21) and the driver goes on to q086; any fault, hang or other failure stops the stage (rc 4).",
            "# Q291 (the attribute band) is NOT here: deferred (README.md, Deviations)."]
    return head, rows, preds


# ------------------------------------------------------------------------------------------------------------------ q086
def e511_cases():
    """E511's 26 declared risky cases (name, set, W, H, kpokes) from its published script's CASES table."""
    out = []
    for line in open(E511_SCRIPT):
        if not line.startswith("q086-"):
            continue
        name, sset, w, h, args = line.rstrip("\n").split("|")
        kp = {int(i): int(v, 16) for i, v in re.findall(r"1:ta:(\d+)=(0x[0-9a-f]+)", args)}
        out.append((name, sset, int(w), int(h), kp))
    return out


def q086():
    skipped = [ln.split("\t")[0] for ln in open(E511_SKIPPED) if ln.strip()]
    cases = {c[0]: c for c in e511_cases()}
    fam = lambda n: n.rsplit("-", 1)[1]  # noqa: E731
    order = [n for n in skipped if fam(n) in ("U2", "U2Q")] + [n for n in skipped if fam(n) == "FX"] + \
        [n for n in skipped if fam(n) == "HS"]
    assert len(order) == 20 and any(ln.startswith("q086-1024x768-R\t") for ln in open(E507_SKIPPED))
    rows, preds = [], []
    spec = [("q086-1024x768-R", "control", 1024, 768, {}, "-")]
    for n in order:
        _, _, w, h, kp = cases[n]
        g = {"U2": "u", "U2Q": "u", "FX": "fx", "HS": "hs"}[fam(n)]
        spec.append((n, "heldout", w, h, kp, g))
    gmax = {"u": 1, "fx": 1, "hs": 2}
    for name, sset, w, h, kp, g in spec:
        knobs = "expectdiff strict" + ("" if g == "-" else " hypo:%s:%d" % (g, gmax[g]))
        rows.append("%s|%s|risky|%s|t4|%s" % (name, sset, knobs, M.q086_args(w, h, kp)))
        m1, m2, st = M.q086_words(w, h, kp)
        cx, cy = M.coverage(m1, m2)
        tx, ty = M.TILES_4X(w, h)
        preds.append((name, "size", "%dx%d" % (w, h), "all", sset))
        preds.append((name, "words", "0x%08x,0x%08x,0x%x" % (m1, m2, st), "all", sset))
        preds.append((name, "cover", "%d,%d of %d,%d" % (cx, cy, tx, ty), "H-COV", sset))
        preds.append((name, "class", "ok" if M.hcov_completes(w, h, kp) else "fault", "H-COV", sset))
        preds.append((name, "class", "ok", "H-ANY", sset))
        preds.append((name, "wrong_if_ok", "0", "all", sset))
        preds.append((name, "group", g, "all", sset))
    head = ["#stage q086", "#limit 3",
            "# Q086: E511's 20 skipped 4x cases (U2, U2Q, FX, HS words kpoked over the kernel's) and the safe script's 1024 x 768 R,",
            "# on contexts made for 4x targets (--aa4: four region-header arrays on the rgn4 module, E824), every pixel read (--pixels).",
            "# Frozen: H-COV (complete iff the words' macrotile grid covers the 1x tile grid, B3 + B1 tiles per axis; post hoc 6 of 6 on",
            "# E511) against H-ANY (all complete).  H-COV: R and the 6 U2/U2Q complete with 0 wrong, the 7 FX and 7 HS fault (3D side).",
            "# Fault budget 3 (DECISIONS-R6 R6-2 a): hypothesis groups u (at most 1 fault), fx (1), hs (2; last, as the plan orders); a",
            "# group that reaches its count skips its other rows.  Strict health after each fault.  A fault that is not the 3D-side",
            "# class (BIF_INT_STAT bits 15:0 0x0100, BIF_FAULT 0x100000xx) or a -110 stops the stage (rc 18); a fault in R stops it (rc 4)."]
    return head, rows, preds


STAGES = {"q289": q289, "q287": q287, "q086": q086}


def write():
    md = ["# r6-misc job tables (generated by gen/m6gen.py; do not edit)", ""]
    for st, fn in STAGES.items():
        head, rows, preds = fn()
        with open(os.path.join(KP, "tables", st + ".txt"), "w") as f:
            f.write("\n".join(head + rows) + "\n")
        with open(os.path.join(KP, "predictions", st + ".tsv"), "w") as f:
            f.write("case\tquantity\tvalue\tmodel\tset\n")
            for p in preds:
                f.write("\t".join(p) + "\n")
        md += ["## %s (%d jobs)" % (st, len(rows)), ""] + [h[2:] for h in head if h.startswith("# ")] + [""]
        md += ["| job | set | knobs | tool | command |", "|---|---|---|---|---|"]
        for r in rows:
            n, s, _, k, t, a = r.split("|", 5)
            md.append("| %s | %s | %s | %s | `%s` |" % (n, s, k, t, a))
        md.append("")
    with open(os.path.join(KP, "TABLES.md"), "w") as f:
        f.write("\n".join(md))
    with open(os.path.join(KP, "stages.txt"), "w") as f:
        f.write("\n".join(STAGES) + "\n")


if __name__ == "__main__":
    write()
    print("tables:", ", ".join("%s %d" % (s, sum(1 for ln in open(os.path.join(KP, "tables", s + ".txt")) if not ln.startswith("#")))
                               for s in STAGES))
