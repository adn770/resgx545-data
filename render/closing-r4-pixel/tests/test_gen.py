#!/usr/bin/env python3
"""The generated tables and frozen predictions: stage order and job counts (158), the sets, every row has frozen predictions with a hypothesis
label, the plan's rows (q4-v ladders at 0.80 .. 1.60 x N*, the three stock rows; q4-f's bridge, ld0 and ldo rows; q4-t's 12 + 42 rows; p4-o4's
36; g4-rw's 24), the bridge controls carry their runner-side stop (knob want2) and their loop proof (proofstop), the loop programs of the tables
carry their MARK and relative branch (no `ba` in a --tri row), the stock program is the one R3-geo ran, the Q082 stages read the regtimeline
registers, the jobs stay under pixels x N <= 2.3e7, no forbidden option, the frozen files and FROZEN.commits verify.  Prints ok/FAIL; exit 1."""
import collections
import hashlib
import os
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R4 / "gen"), str(R4 / "score")]
import r4const as C  # noqa: E402
import r4loops as LP  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    rows = []
    for ln in (R4 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5))))
    return rows


def preds(st):
    out = collections.defaultdict(list)
    for ln in (R4 / "predictions" / f"{st}.tsv").read_text().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        out[c].append((q, v, m, s))
    return out


stages = (R4 / "stages.txt").read_text().split()
check("stage order (plan section 5): p4-o4, q4-v, q4-f, q4-t, g4-rw", stages == ["p4-o4", "q4-v", "q4-f", "q4-t", "g4-rw"], str(stages))
T = {st: table(st) for st in stages}
P = {st: preds(st) for st in stages}
counts = {st: len(T[st]) for st in stages}
check("job counts: p4-o4 36, q4-v 28, q4-f 16, q4-t 54, g4-rw 24 = 158", counts == {"p4-o4": 36, "q4-v": 28, "q4-f": 16, "q4-t": 54, "g4-rw": 24} and sum(counts.values()) == 158, str(counts))
sets = {st: dict(collections.Counter(r["set"] for r in T[st])) for st in stages}
check("q4-v sets: 4 bridge controls + 6 FIT points (control), 15 ladder rows + 3 stock rows held out", sets["q4-v"] == {"control": 10, "heldout": 18}, str(sets["q4-v"]))
check("q4-f sets: 5 bridge controls, 11 held out", sets["q4-f"] == {"control": 5, "heldout": 11}, str(sets["q4-f"]))
check("q4-t sets: 12 controls, 42 held out (8 + 5 + 18 + 8 + 4 + the t6 rows counted once)", sets["q4-t"] == {"control": 12, "heldout": 42}, str(sets["q4-t"]))
check("p4-o4 sets: 8 controls, 14 value + 12 predicate held out, 2 replicate", sets["p4-o4"] == {"control": 8, "heldout": 26, "replicate": 2}, str(sets["p4-o4"]))
check("g4-rw sets: 4 controls, 20 table jobs", sets["g4-rw"] == {"control": 4, "heldout": 20}, str(sets["g4-rw"]))
for st in stages:
    pair = lambda n: re.sub(r"-y(-rep)?$", lambda m: "-x" + (m[1] or ""), n) if st == "p4-o4" else n      # a pair's predictions sit on its x job
    miss = [r["name"] for r in T[st] if pair(r["name"]) not in P[st]]
    check(f"{st}: every job has frozen predictions", not miss, str(miss[:3]))
    sets_p = {s for qs in P[st].values() for q, v, m, s in qs}
    check(f"{st}: predictions carry a set label (control, heldout, repeat, replicate)", sets_p <= {"control", "heldout", "repeat", "replicate"}, str(sets_p))
    need = [ln.split(None, 1)[1] for ln in (R4 / "tables" / f"{st}.txt").read_text().splitlines() if ln.startswith("#need ")]
    check(f"{st}: every #need program exists in bins/", all((R4 / "bins" / pathlib.Path(n.replace("$S/", "")).name).exists() for n in need), "")
    used = set(re.findall(r"\$S/([\w.-]+\.bin)", " ".join(r["args"] for r in T[st])))
    check(f"{st}: every program a row names is in #need", used <= {n.replace("$S/", "") for n in need}, str(used - {n.replace("$S/", "") for n in need}))
# ---- Q082 stages read the regtimeline registers and the STATUS2 reads
for st in ("q4-v", "q4-f", "q4-t"):
    check(f"{st}: every row runs under regtimeline 0x0008,0x0118,0x012c and reads STATUS2 (s2, stophang)",
          all(r["rt"] == C.RT_REGS and "s2" in r["knobs"].split() and "stophang" in r["knobs"].split() for r in T[st]))
# ---- q4-v
v = {r["name"]: r for r in T["q4-v"]}
check("q4-v: the four bridge controls come first and carry the runner-side stop (want2): ctl0, n1, i880 clear, i1760 set",
      [r["name"] for r in T["q4-v"][:4]] == ["v-ctl0", "v-n1", "v-i880", "v-i1760"] and "want2:0xc0:0x00" in v["v-ctl0"]["knobs"] and "want2:0xc0:0x00" in v["v-i880"]["knobs"]
      and "want2:0x80:0x80" in v["v-i1760"]["knobs"])
for key, kind, nv in (("b12v", "b12v", 3), ("b2v", "b2v", 3), ("v24", "b8v", 24)):
    fit, held = C.v_points(kind, nv)
    names = [r["name"] for r in T["q4-v"] if r["name"].startswith(f"v-{key}-")]
    check(f"q4-v {key}: 2 FIT points then 5 held-out points at 0.80, 0.92, 1.08, 1.20, 1.60 x N* = {C.v_nstar(kind, nv):.0f}",
          names == [f"v-{key}-n{n}" for n in fit + held] and [v[n]["set"] for n in names] == ["control"] * 2 + ["heldout"] * 5
          and all(abs(h / C.v_nstar(kind, nv) - r) < 0.02 for h, r in zip(held, C.V_RATIOS)), str(names))
check("q4-v: the b24 rows carry --vertices 24; the stock rows are 1500 vertices at 2048 (twice) and 4096, last",
      all("--vertices 24" in r["args"] for r in T["q4-v"] if r["name"].startswith("v-v24-")) and
      [r["name"] for r in T["q4-v"][-3:]] == ["v-stock-2048-a", "v-stock-2048-b", "v-stock-4096"] and
      all("--vertices 1500" in r["args"] for r in T["q4-v"][-3:]) and "--width 4096 --height 4096" in T["q4-v"][-1]["args"])
stock_ref = pathlib.Path.home() / "src/scratch/resgx545/closing3/r3-geo/bins/p1139-green.bin"
check("q4-v: the stock program is byte for byte the p1139-green.bin of R3-geo's g-c4", stock_ref.exists() and stock_ref.read_bytes() == (R4 / "bins/p1139-green.bin").read_bytes())
bad = [n for n, r in v.items() if "vloop" in r["args"] and {x for x in [q for q in P["q4-v"][n] if q[0] == "depth_words"][0][1].split(",")} != {f"0x{C.BASE_DEPTH + int(re.search(r'-i(\d+)\.bin', r['args'])[1]):08x}"}]
check("q4-v: the loop proof of every loop row is the depth word 0x3f200000 + N on every vertex", not bad, str(bad[:3]))
check("q4-v: every ladder row predicts the TA rule, the latch window and the layout check", all({"bit7", "t7_after_run_us", "L_model_us"} <= {q[0] for q in P["q4-v"][r["name"]]} for r in T["q4-v"] if re.match(r"v-(b12v|b2v|v24)-", r["name"])))
# ---- q4-f
f = {r["name"]: r for r in T["q4-f"]}
check("q4-f: the bridge rows rel b8 at 16, 53, 56, 136 and ld8 at 70 come first with want2 and proofstop; clear, clear, set, set, clear",
      [r["name"] for r in T["q4-f"][:5]] == ["f-rel-b8-16", "f-rel-b8-53", "f-rel-b8-56", "f-rel-b8-136", "f-ld8-70"] and
      all("want2:" in r["knobs"] and "proofstop:" in r["knobs"] for r in T["q4-f"][:5]) and
      [("0x40:0x40" in r["knobs"]) for r in T["q4-f"][:5]] == [False, False, True, True, False])
check("q4-f: ld0 at K = 28, 53, 70, 110 and ldo at (28,4) (28,16) (40,8) (70,1) (70,4) (110,2) (220,1), in that order",
      [r["name"] for r in T["q4-f"][5:]] == [f"f-ld0-k{k}" for k in C.F_LD0] + [f"f-ldo-k{k}-m{m}" for k, m in C.F_LDO])
hyps = {h: [q for q in P["q4-f"]["f-ld0-k70"] if q[0] == "bit6" and q[2].startswith(h)] for h in C.F_HYP}
check("q4-f: every held-out row carries a frozen bit-6 row for H-YIELD, H-LOADOFF and H-SUM", all(len(v_) == 1 for v_ in hyps.values()))
tabrows = {h: [q[1] for r in T["q4-f"][5:] for q in P["q4-f"][r["name"]] if q[0] == "bit6" and q[2].startswith(h)] for h in C.F_HYP}
check("q4-f: the frozen table is the plan's (H-YIELD c either S S | c c c | S S S S; H-LOADOFF all clear; H-SUM c either S S | S S S | S S S S)",
      tabrows["H-YIELD"] == "clear either set set clear clear clear set set set set".split() and tabrows["H-LOADOFF"] == ["clear"] * 11 and
      tabrows["H-SUM"] == "clear either set set set set set set set set set".split(), str(tabrows))
for n in ("f-rel-b8-53", "f-rel-b8-56"):
    mod = [q for q in P["q4-f"][n] if q[0] == "bit6"][0][2]
    check(f"q4-f {n}: the prediction says sgx-pipe's rule refuses the edge and the value is E804's measured bracket", "refuses" in mod and "E804" in mod)
check("q4-f: the pipe_rule rows are clear at 16, edge at 53 and 56, set at 136 (sgx-pipe status2_bit6 on the modelled tile time)",
      [[q for q in P["q4-f"][n] if q[0] == "pipe_rule"][0][1] for n in ("f-rel-b8-16", "f-rel-b8-53", "f-rel-b8-56", "f-rel-b8-136")] == ["clear", "edge", "edge", "set"])
# ---- q4-t
t = {r["name"]: r for r in T["q4-t"]}
names = [r["name"] for r in T["q4-t"]]
check("q4-t: the 12 controls come first (green and N = 1 at 4x4, 8x8, 16x16, 32x16, 64x32, then the fill at 53 and 56)",
      names[:12] == [f"t4-ctl-green-{w}x{h}" for w, h in C.T_CTL_SIZES] + [f"t4-ctl-n1-{w}x{h}" for w, h in C.T_CTL_SIZES] + ["t4-fill-n53", "t4-fill-n56"])
check("q4-t: 8x8 at 60..104 (7), 4x4 at 80..200 (5), 16x16, 32x16, 64x32 at 46, 56, 56 again, 60, 66, 72 (18), 64x32 and 8x8 at 150..330 (8), 64x64 default (4)",
      sum(n.startswith("t4-8x8-") for n in names) == 7 + 4 and sum(n.startswith("t4-4x4-n") for n in names) == 5 and
      sum(bool(re.match(r"t4-(16x16|32x16|64x32)-n(46|56|56b|60|66|72)$", n)) for n in names) == 18 and
      sum(bool(re.match(r"t4-(64x32|8x8)-n(150|180|250|330)$", n)) for n in names) == 8 and sum(n.startswith("t4-par-64x64-") for n in names) == 4)
check("q4-t: the fill bridge rows (53 clear, 56 set) and the green and N = 1 rows carry want2; the partial 64x64 rows are the only ones without --tri-full",
      all("want2:" in t[n]["knobs"] for n in ["t4-fill-n53", "t4-fill-n56"] + [x for x in names[:10]]) and
      all(("--tri-full" in r["args"]) == (not r["name"].startswith("t4-par-") and not r["name"].startswith("t4-fill-")) for r in T["q4-t"]))
check("q4-t: H-SEG, H-N and E806-DISC rows (the plan's refutation conditions: 16x16 or 64x32 clear at 72, 8x8 set at 60 or clear at 104, 4x4 set at 110)",
      C.t_pred("H-SEG", (16, 16), 72) == "set" and C.t_pred("H-SEG", (64, 32), 72) == "set" and C.t_pred("H-SEG", (8, 8), 60) == "clear" and C.t_pred("H-SEG", (8, 8), 104) == "set"
      and C.t_pred("H-SEG", (4, 4), 110) == "clear" and C.t_pred("H-N", (4, 4), 80) == "set" and C.t_pred("H-SEG", (16, 16), 46) == "clear")
check("q4-t: the t6 rows predict 250 + 0.43 N to N = 290 and 250 beyond (+- 15)", [round(C.t6_pred(n), 1) for n in C.T_T6_N] == [314.5, 327.4, 357.5, 250.0])
check("q4-t: no job passes pixels x N = 2.3e7 (E357's longest completed fill)",
      all(int(re.search(r"--width (\d+) --height (\d+)", r["args"])[1]) * int(re.search(r"--width (\d+) --height (\d+)", r["args"])[2]) * int(re.search(r"-i(\d+)\.bin", r["args"])[1]) <= 2.3e7
          for r in T["q4-t"] if "--width" in r["args"] and "-i" in r["args"]))
# ---- loop programs: MARK proof, relative branch, no ba in a --tri row
bad = []
for st in stages:
    for r in T[st]:
        for m in re.finditer(r"proofstop:(0x[0-9a-f]+):(\d+)", r["knobs"]):
            prog = re.search(r"\$S/([\w.-]+)\.bin", r["args"])[1]
            mm = re.fullmatch(r"loop-rel-(?:b8|ld8)-i(\d+)", prog)
            exp = LP.mark(int(mm[1])) if mm else (LP.load_mark(int(re.search(r"k(\d+)", prog)[1]), int(x[1]) if (x := re.search(r"-m(\d+)", prog)) else None))
            if int(m[1], 16) != exp or int(m[2]) != 2048:
                bad.append((r["name"], m[1]))
check("every proofstop knob is the MARK of the row's own program on 2048 of 2048", not bad, str(bad[:3]))
check("no `ba` loop program in any table row (abs loops are not staged in R4)", not any("loop-abs" in r["args"] for st in stages for r in T[st]))
check("no forbidden tool option in any table (kreg, kpoke, ctx2, share-pb, depth, geometry, xfer_ro, late, low, place)",
      not any(re.search(r"--kreg|--kpoke|kpoke-render|--ctx2|--share-pb|--depth|--geometry|xfer_ro|--late|--low|--place", r["args"]) for st in stages for r in T[st]))
# ---- the freeze
r = subprocess.run([str(R4 / "run/freeze_r4.sh"), "verify"], capture_output=True, text=True)
check("the frozen files verify (run/freeze_r4.sh verify)", r.returncode == 0, (r.stdout + r.stderr)[-200:])
fc = R4 / "FROZEN.commits"
check("FROZEN.commits exists and names the pinned resgx545 commit 5a13042 for every resgx545 pin", fc.exists() and all(
    ln.split()[1] in ("untracked", subprocess.run(["git", "-C", str(pathlib.Path.home() / "src/resgx545"), "rev-parse", "5a13042"], capture_output=True, text=True).stdout.strip())
    for ln in fc.read_text().splitlines() if ln and not ln.startswith("#")))
sys.exit(0 if ok else 1)
