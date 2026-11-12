#!/usr/bin/env python3
"""test_gen.py: the frozen tables and predictions against the PLAN, row by row (round 4's slip must be impossible by construction).
  1. the files on disk are what gen/r7plan.py writes now (tables, predictions, TABLES.md, stages.txt, stagesB.txt), and every constant
     r7plan.py writes out (the model per target, the s-b scenes and cells) is what the FROZEN offline rules compute now (gen/r7model.py
     loads them with their FREEZE hashes checked) (about five minutes: the scene search);
  2. the frozen rules are the ones the offline stage printed: g3_span.out's S, A, B per target, g2_replay64.out's verdict (and its
     qf 0x80 cell), q210_targets.out's model cells of the plan;
  3. the ARGV TWIN: every row's command, split as the runner's `eval set --` splits it, against a plan row transcribed BY HAND below from
     exp-dpm-r7.md section 4 (scene, target size, P or the derived cell, knobs), and against the command R6-dpm ran for the same cell
     (kept cases.tsv): the same argv but for the work directory and the dump (dumps on targets up to 2048x2048 only);
  4. the register list is r5's 16 registers, every row; set A's tables name module 41E2F5C7 and set B's 37EC97AB;
  5. the predictions say what section 4 expects (19 discriminating cells, the controls, s-k's bits), and every control declares
     readings its job produces (the generator's refusal is live: a control on a reading it cannot produce raises).
"""
import csv
import pathlib
import re
import shlex
import sys

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "gen"), str(KP / "score")]
import r7plan as P  # noqa: E402
import r7model as M  # noqa: E402
import scorekit as SK  # noqa: E402

DATA = pathlib.Path("/Users/jtorra/src/resgx545-data")
OFF7 = DATA / "cited/closing7/b/offline"
FAIL = []


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


# ---- the plan, by hand (exp-dpm-r7.md section 4 and q210_targets.out): (name, scene, W, H, P (int or ("M", G, k, thr0)), knob words)
T1500, QD = "tri1500", "default"
S22, A22 = {5: 0x132, 6: 0x181, 7: 0x1ca}, {5: 0x178, 6: 0x1c3, 7: 0x20d}
PLAN = {
    "s-a0": [("a0-cal-2048", T1500, 2048, 2048, 0x162, "cal:c2048 prem ctlleft:2"), ("a0-cal-2048f", T1500, 2048, 2048, 0x422, "cal:c2048f prem ctlneed:0x213 ctlcnt:0"),
             ("a0-c4-b5", T1500, 2048, 2048, 0x104, "ctl:R ctlleft:2 prem"), ("a0-c4-b6", T1500, 2048, 2048, 0x105, "ctl:N ctlleft:1 prem"),
             ("a0-t-s3m6", T1500, 2048, 2048, 0x97 + 0x22, "ctlleft:1 prem"), ("a0-qf-0xa2", QD, 4096, 4096, 0xa2, "ctlcnt:2 prem expectdiff")],
    "s-m": [],
    "s-v": [("v-cal-c4", T1500 + "+vtx4", 2048, 2048, 0x422, "cal:v4 vprem"), ("v-cal-c8", T1500 + "+vtx8", 2048, 2048, 0x422, "cal:v8 vprem")],
    "s-k": [("k-b6", T1500, 2048, 2048, 0x105, "fw fwprem"), ("k-b5", T1500, 2048, 2048, 0x104, "fw"), ("k-b3", T1500, 2048, 2048, 0x10a, "fw"),
            ("k-s3", T1500, 2048, 2048, 0x9d + 0x22, "fw"), ("k-s4p1", T1500, 2048, 2048, 0xe9 + 0x22, "fw"),
            ("k-s3m6", T1500, 2048, 2048, 0x97 + 0x22, "fw"), ("k-b5-0x177", T1500, 2048, 2048, 0x177 + 0x22, "fw"),
            ("k-b5-0x178", T1500, 2048, 2048, 0x178 + 0x22, "fw"), ("k-creep", T1500, 2048, 4096, 0x24a + 0x22, "fw"),
            ("k-creep2", T1500, 2048, 4096, 0x24a + 0x22, "fw")],
}
# s-m: q210_targets.out's cells (plan section 4: "3072x3072 band 5 0x32a to 0x32e and band 6 0x3cd, 0x3ce, 3072x2048 0x225 to 0x228,
# 2048x3072 0x22a to 0x22c, 2560x2560 band 6 0x2ae to 0x2b0, 1024x1024 band 5 0x6b, 0x6c"), with B - 1 .. A around them and B3 - 1, B3
HAND = {"c33": ((3072, 3072), None, [(5, range(0x329, 0x330)), (6, range(0x3cc, 0x3d0))]),
        "c32": ((3072, 2048), (3, 0x14c, 0x14d), [(5, range(0x224, 0x22a))]),
        "c23": ((2048, 3072), (3, 0x14e, 0x14f), [(5, range(0x229, 0x22e))]),
        "c25": ((2560, 2560), (3, 0x157, 0x158), [(6, range(0x2ad, 0x2b2))]),
        "c11": ((1024, 1024), (3, 0x40, 0x41), [(5, range(0x6a, 0x6e))])}
DISC = {"c33": [0x32a, 0x32b, 0x32c, 0x32d, 0x32e, 0x3cd, 0x3ce], "c32": [0x225, 0x226, 0x227, 0x228], "c23": [0x22a, 0x22b, 0x22c],
        "c25": [0x2ae, 0x2af, 0x2b0], "c11": [0x6b, 0x6c]}
for g, (wh, b3, bands) in HAND.items():
    PLAN["s-m"].append((f"m-cal-{g}", T1500, *wh, 0x422, f"cal:{g}"))
    if b3:
        PLAN["s-m"] += [(f"m-{g}-0x{t:x}", T1500, *wh, ("M", g, 3, t), "") for t in b3[1:]]
    for k, rg in bands:
        PLAN["s-m"] += [(f"m-{g}-0x{t:x}", T1500, *wh, ("M", g, k, t), "") for t in rg]
PLAN["s-m"] += [(f"m-r{k}-0x{t:x}", T1500, 2048, 2048, t + 0x22, "") for k in (5, 6, 7) for t in (A22[k] - 1, A22[k])]
COUNT = {"s-a0": 6, "s-m": 50, "s-b": 29, "s-v": 2, "s-k": 10}


def argv_of(cmd):
    return shlex.split(cmd.replace('"$W/', '"W/').replace('"$S/', '"S/'))


def scene_of(a):
    if a[0] == "probe":
        ok = a[1:3] == ["--tri", "pixel"] and a[a.index("--vertices") + 1] == "1500" and a[-1] == "S/p1139-green.bin"
        if not ok or "--move" in a or "-n" in a or "--tri-full" in a:
            return "other probe"
        return T1500 + (f"+vtx{a[a.index('--vtx-coords') + 1]}" if "--vtx-coords" in a else "")
    if a[0] == "tri":
        if a[a.index("-n") + 1] != "1" or "--geometry" in a or "--vertices" in a:
            return "other tri"
        return ("moved " + a[a.index("--move") + 1]) if "--move" in a else QD
    return "?"


def wh(a):
    return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])


# 1. the files are the generator's; the written-out constants are the frozen rules' now
T, Pr = P.tables(check=True), P.predictions()
for st in T:
    check((KP / "tables" / f"{st}.txt").read_text() == P.table_text(st, T[st]), f"tables/{st}.txt is what gen/r7plan.py writes")
    want = "case\tquantity\tvalue\tmodel\tset\n" + "".join("\t".join(p) + "\n" for p in Pr[st])
    check((KP / "predictions" / f"{st}.tsv").read_text() == want, f"predictions/{st}.tsv is what gen/r7plan.py writes")
check((KP / "TABLES.md").read_text() == P.tables_md(T, Pr), "TABLES.md is what gen/r7plan.py writes")
check((KP / "stages.txt").read_text().split() == P.STAGES["A"] == ["s-a0", "s-m", "s-b", "s-v"] and
      (KP / "stagesB.txt").read_text().split() == ["s-k"], "stages.txt: s-a0, s-m, s-b, s-v (set A); stagesB.txt: s-k (set B, last)")
check({st: len(T[st]) for st in T} == COUNT and sum(COUNT.values()) == 97, f"job counts {COUNT}: 97 (set A 87, set B 10)")
rc = P.recompute()
check(rc["model"] == P.MODEL_FROZEN, "MODEL_FROZEN = g3_span.model now (S, A, B, U at 7 targets)")
check(rc["scenes"] == P.B_SCENES_FROZEN and rc["cells"] == P.B_CELLS_FROZEN, f"s-b scenes and cells = b_scenes()/b_cells() now: {P.B_SCENES_FROZEN}")

# 2. the frozen rules are the offline stage's printed outputs
g3 = (OFF7 / "g3_span.out").read_text()
for w, h in ((2048, 2048), (3072, 3072), (2048, 4096)):
    S, A, B, U = P.MODEL[(w, h)]
    line = f"== {w}x{h} U {U:#x} S " + " ".join(f"{k}:{v:#x}" for k, v in sorted(S.items())) + " | A " + \
        " ".join(f"{k}:{v:#x}" for k, v in sorted(A.items())) + " | B " + " ".join(f"{k}:{v:#x}" for k, v in sorted(B.items()))
    check(line in g3, f"{w}x{h}: S, A, B and U = g3_span.out")
check("VERDICT H-SPAN: HELD" in g3 and "VERDICT H-REPLAY64: HELD" in (OFF7 / "g2_replay64.out").read_text()
      and "VERDICT H-WALK64: HELD" in (OFF7 / "g1_walk64.out").read_text(), "the offline verdicts the predictions start from: G1, G2, G3 HELD")
check("H-CUM" in (OFF7 / "g5_blocks.out").read_text() and P.VCAL[4][1] == 538 and P.VCAL[8][1] == 691,
      "G5 froze no rule (H-CUM not frozen): s-v is exploration, R6-dpm's kept calibrations repeated (need 538 and 691)")
tg = (KP.parent / "b" / "q210_targets.out").read_text()
for g, (wh_, _, _) in HAND.items():
    S, A, B, U = P.MODEL[wh_]
    for k in sorted(S):
        check(f"S{k} {S[k]:#x} B {B[k]:#x} A {A[k]:#x}" in tg.split(f"{wh_[0]}x{wh_[1]} U")[1].split("\n")[0], f"{g} band {k}: the planner's q210_targets.out")
check(M.replay(4096, 4096, 0, 0, 0x80) == (2, [0x80, 0xa0, 2]) and "thr0  0x80 read 2 [80 a0 2] | replay 2 [80 a0 2] exact" in
      (OFF7 / "g2_replay64.out").read_text(), "g-qf 0xa2 under H-REPLAY64: 2 partial renders, run peaks 0x80 0xa0 0x2 (g2_replay64.out)")

# 3. the argv twin, row by row
for st in T:
    rows = {r["name"]: r for r in T[st]}
    plan = list(PLAN.get(st, []))
    if st == "s-b":
        for n, w, h, dx, dy, U in P.B_SCENES:
            plan.append((f"b-cal-{n}", f"moved 1:{dx},{dy}", w, h, 0x422, f"ucal:{n}:{U} expectdiff" + (" tdump" if n == "s22" else "")))
            plan += [(f"b-{n}-0x{t:x}", f"moved 1:{dx},{dy}", w, h, t + 0x22, f"uneed:{n} expectdiff") for t in P.B_CELLS[n]]
    check([p[0] for p in plan] == [r["name"] for r in T[st]], f"{st}: the rows are the plan's, in the plan's order ({len(plan)})")
    for name, scene, w, h, p, kn in plan:
        r = rows.get(name)
        if r is None:
            check(False, f"{st} {name}: no such row")
            continue
        a = argv_of(r["cmd"])
        ok = scene_of(a) == scene and wh(a) == (w, h)
        if isinstance(p, tuple):
            S = P.MODEL[P.TARGETS[p[1]]][0]
            ok &= r["P"] == f"M:{p[1]}:{p[2]}:{p[3] - S[p[2]]}:0x{p[3] + 0x22:x}" and P.TARGETS[p[1]] == (w, h)
        else:
            ok &= int(r["P"], 16) == p
        ok &= all(k in r["knobs"].split() for k in kn.split())
        ok &= ("fw" in r["knobs"].split()) == (st == "s-k")
        ok &= ("--dump-render" in a) == ((scene.startswith(T1500) and w * h <= 2048 * 2048) or name == "b-cal-s22")
        ok &= ("model:" in r["knobs"]) == (any(k.startswith("cal:") for k in r["knobs"].split()) and not name.startswith("v-"))
        check(ok, f"{st} {name}: argv {scene_of(a)} {wh(a)[0]}x{wh(a)[1]} P {r['P']} knobs [{r['knobs'][:40]}] = the plan's row")
    for r in T[st]:
        m = re.search(r"model:(\S+)", r["knobs"])
        if m:
            S = P.MODEL[target := P.target_of(r["cmd"])][0]
            check(m.group(1) == ",".join(f"0x{S[k]:x}" for k in sorted(S) if S[k] < 0x400), f"{r['name']}: model: = the frozen steps of {target}")
# ... and against R6-dpm's kept commands of the same cells (the dump is the only difference allowed)
kept = {}
for d in ("render/closing-r6-dpm/out/a2/r-a0", "render/closing-r6-dpm/out/a2/r-k", "render/closing-r6-dpm/out/a2/r-b", "render/closing-r6-dpm/out/a2/r-v"):
    for c in csv.DictReader(open(DATA / d / "cases.tsv"), delimiter="\t"):
        kept[c["name"]] = c["args"]
norm = lambda cmd: [x for x in argv_of(cmd) if not x.startswith("W/") and x != "--dump-render" and not x.endswith("p1139-green.bin")]
for st, ours, theirs in [("s-a0", "a0-cal-2048", "a0-cal-2048"), ("s-a0", "a0-c4-b5", "a0-c4-b5"), ("s-a0", "a0-qf-0xa2", "a0-qf-0xa2"),
                         ("s-k", "k-b5", "k-b5"), ("s-k", "k-creep", "k-creep"), ("s-v", "v-cal-c4", "v-cal-c4"), ("s-v", "v-cal-c8", "v-cal-c8"),
                         ("s-m", "m-r5-0x177", "a0-cal-2048")]:
    r = next(x for x in T[st] if x["name"] == ours)
    check(norm(r["cmd"]) == norm(kept[theirs]), f"{ours}'s argv = R6-dpm's kept {theirs} ({' '.join(norm(r['cmd']))[:70]})")
s262 = norm(kept["b-cal-s262"])
for n, w, h, dx, dy, U in P.B_SCENES:
    r = next(x for x in T["s-b"] if x["name"] == f"b-cal-{n}")
    want = [{"4096": str(w) if i == s262.index("--width") + 1 else str(h)}.get(x, x) if x == "4096" else x for i, x in enumerate(s262)]
    want = [f"1:{dx},{dy}" if x == "1:256,1280" else x for x in want]
    check(norm(r["cmd"]) == want, f"b-cal-{n}'s argv = R6-dpm's b-cal-s262 with {w}x{h} and the move {dx},{dy} (single kick)")

# 4. registers and modules
regs = "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"
check(all(r["rt"] == regs for st in T for r in T[st]), "every row samples r5's 16 registers")
for st in T:
    txt = (KP / "tables" / f"{st}.txt").read_text()
    want = ("B", "37EC97AB0CB37213C42FCCC") if st == "s-k" else ("A", "41E2F5C756F96D20F7109A4")
    check(f"#set {want[0]}\n#module {want[1]}\n" in txt, f"tables/{st}.txt: set {want[0]}, module {want[1][:8]}")
check("#need $S/oomring2.blob" in (KP / "tables/s-k.txt").read_text(), "s-k needs oomring2.blob (staged, hash-checked by the runner)")

# 5. what the predictions say
pred = {st: list(csv.DictReader(open(KP / "predictions" / f"{st}.tsv"), delimiter="\t")) for st in T}
pv = lambda st, c, q, m=None: [x["value"] for x in pred[st] if x["case"] == c and x["quantity"] == q and (m is None or x["model"] == m)]
check(all(x["set"] in ("control", "repeat", "heldout", "explore") for st in T for x in pred[st]), "every prediction has its label")
nd = 0
for g, ts in DISC.items():
    for t in ts:
        a, b = pv("s-m", f"m-{g}-0x{t:x}", "gps_left", "H-SPAN"), pv("s-m", f"m-{g}-0x{t:x}", "gps_left", "E874-B")
        nd += a == ["2"] and b == ["1"]
check(nd == 19, f"s-m: the 19 discriminating cells of the plan (H-SPAN 2, E874-B 1): {nd}")
check(all(pv("s-m", f"m-{g}-0x{A - 0:x}", "gps_left", "H-SPAN") == ["1"] for g, (wh_, _, bands) in HAND.items()
          for k, rg in bands for A in [P.MODEL[wh_][1][k]]), "s-m: 1 page left from A_k at every parting band")
check([pv("s-m", f"m-r{k}-0x{t:x}", "gps_left", "H-SPAN")[0] for k in (5, 6, 7) for t in (A22[k] - 1, A22[k])] == ["2", "1"] * 3,
      "s-m replicates: 2 at A - 1, 1 at A at bands 5 to 7 (E900)")
for g in ("c32", "c23", "c25", "c11"):
    b3 = P.MODEL[P.TARGETS[g]][2][3]
    check(pv("s-m", f"m-{g}-0x{b3 - 1:x}", "cls") == ["R"] and pv("s-m", f"m-{g}-0x{b3:x}", "cls") == ["N"], f"s-m {g}: R-5 raises at B3 - 1, silent at B3")
check(pv("s-a0", "a0-cal-2048f", "S7") == ["0x1ca"] and pv("s-a0", "a0-cal-2048f", "need") == ["0x213"] and
      not pv("s-a0", "a0-cal-2048f", "grow") and not pv("s-a0", "a0-cal-2048f", "gps_left"),
      "s-a0: the complete calibration's controls are its steps and need only (no grow, no pages left: r6-dpm's slip)")
check(pv("s-k", "k-b5", "dec_sa8_380") == ["0x180"] and pv("s-k", "k-b6", "dec_sa8_380") == ["0x0"] and pv("s-k", "k-b3", "dec_sa8_380") == ["0x0"]
      and pv("s-k", "k-s3", "dec_sa8_380") == ["0x180"] and pv("s-k", "k-b5-0x177", "dec_sa8_380", "R-5") == ["0x180"]
      and pv("s-k", "k-b5-0x177", "dec_sa8_380", "R-5|E874-B") == ["0x0"] and pv("s-k", "k-creep", "dec_sa8_380", "R-5") == ["0x0"]
      and pv("s-k", "k-creep", "dec_sa8_380", "ISUB-REV") == ["0x180"], "s-k: R-5's bits (k-b5 0x180, k-b6 0, c4-b3 0, S3 0x180, 0x177 0x180 where E874-B says 0, creep 0)")
check(pv("s-k", "k-creep", "abort_gp") == ["4"] and pv("s-k", "k-creep", "dec_gp") == ["1"] and pv("s-k", "k-s3", "dec_gp") == ["1"]
      and pv("s-k", "k-s3", "abort_gp") == ["2"], "s-k H-PASS: the creep cell 4 global pages at the abort, 1 at the decision; the S3 grow cell 2 and 1 (H-PENDREQ)")
for n, w, h, dx, dy, U in P.B_SCENES:
    cells = P.B_CELLS[n]
    d = sum(1 for t in cells if pv("s-b", f"b-{n}-0x{t:x}", "runpeaks", "H-REPLAY64") != pv("s-b", f"b-{n}-0x{t:x}", "runpeaks", "ROW"))
    check(d == len(cells) and (w != 4096 or all(abs(U - u) >= 10 for u in P.KEPT_U[(4096, 4096)])),
          f"s-b {n}: walk64 and row order differ at {d} of {len(cells)} cells; U {U}")
# the refusal is live: the same tables with a0-cal-2048f reading `grow` (r6-dpm's control) are refused
bad = {r["name"]: (("grow", "need"), r) for r in T["s-a0"] if r["name"] == "a0-cal-2048f"}
try:
    SK.refuse_unreadable(bad, P.producible)
    check(False, "a0-cal-2048f reading grow was NOT refused")
except SK.ControlReadError as e:
    check("a0-cal-2048f reads grow" in str(e), f"the generator refuses r6-dpm's control (a0-cal-2048f reads grow): {e}")
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
