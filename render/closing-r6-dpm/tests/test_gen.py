#!/usr/bin/env python3
"""test_gen.py: the frozen tables and predictions against the PLAN, row by row (round 4's slip o2 must be impossible by construction).
  1. the files on disk are what gen/r6plan.py writes now (tables, predictions, TABLES.md, stages.txt), and every constant r6plan.py
     writes out (the model's steps and burst ends per target, the r-v models, the r-b scenes and cells) is what the FROZEN offline
     rules compute now (gen/r6model.py loads them with their FREEZE hashes checked);
  2. the frozen rules are the ones the offline stage printed: the model's 2048x2048 steps and B_k = f5_stepmodel.out, the timeline
     rule's E_k = f4_phase.out, F9's counts of the kept t-s5 cells = f9_loss.out, F7's pick = f7_replay.out;
  3. the ARGV TWIN: every row's command, split as the runner's `eval set --` splits it, is checked against a plan row transcribed BY
     HAND below from exp-dpm-r6.md section 4 (scene: 1500-vertex probe of p1139-green, with --vtx-coords N or not, or the default
     triangle with or without a move; target size; P or the derived cell; knobs), and against the command round 3 / round 5 ran for
     the same cell (kept cases.tsv): the same argv but for the work directory and the dump (dumps on targets up to 2048x2048 only);
  4. the register list is r5's 16 registers, every row;
  5. the predictions say what section 4 expects, every case has its label, and the r-b scenes and cells follow their build rules.
"""
import csv
import pathlib
import re
import shlex
import sys

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "gen")]
import r6plan as P  # noqa: E402
import r6model as M  # noqa: E402

DATA = pathlib.Path("/Users/jtorra/src/resgx545-data")
OFF = DATA / "cited/closing6/dpm/offline"
FAIL = []


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


# ---- the plan, by hand (exp-dpm-r6.md section 4); (name, scene, W, H, P, knob words that must be there)
# scene: T1500 the 1500-vertex probe, V4 / V8 with --vtx-coords 4 / 8, QD the default triangle, "moved DX,DY"
# P: an int, ("S", G, k, off), ("M", G, k, off, P), ("E", G, k, off)
T1500, QD, V4, V8 = "tri1500", "default", "tri1500+vtx4", "tri1500+vtx8"
B2048 = {5: 0x176, 6: 0x1c1, 7: 0x20c}                       # f5_stepmodel.out, 2048x2048 B5..B7
NEWT = {"c2x1": (2048, 1024), "c1x2": (1024, 2048), "c15": (1536, 1536)}
PLAN = {
    "r-a0": [("a0-cal-2048", T1500, 2048, 2048, 0x162, "cal:c2048 prem"), ("a0-cal-2048f", T1500, 2048, 2048, 0x422, "cal:c2048f prem"),
             ("a0-c4-b5", T1500, 2048, 2048, 0x104, "ctl:R prem"), ("a0-c4-b6", T1500, 2048, 2048, 0x105, "ctl:N prem"),
             ("a0-t-s3m7", T1500, 2048, 2048, 0x96 + 0x22, "ctlleft:2 prem"), ("a0-t-s3m6", T1500, 2048, 2048, 0x97 + 0x22, "ctlleft:1 prem"),
             ("a0-qf-0xa2", QD, 4096, 4096, 0xa2, "ctlcnt:2 prem expectdiff")],
    "r-m": [(f"m-b{k}-0x{b + o:x}", T1500, 2048, 2048, b + o + 0x22, "") for k, b in B2048.items() for o in (-2, -1, 0, 1, 2)],
    "r-n": [],
    "r-v": [("v-cal-c4", V4, 2048, 2048, 0x422, "cal:v4 vprem"), ("v-c4-e3m1", V4, 2048, 2048, ("E", "v4", "3+", -1), ""),
            ("v-c4-e3", V4, 2048, 2048, ("E", "v4", "3+", 0), ""),
            ("v-cal-c8", V8, 2048, 2048, 0x422, "cal:v8 vprem"), ("v-c8-e3m1", V8, 2048, 2048, ("E", "v8", "3+", -1), ""),
            ("v-c8-e3", V8, 2048, 2048, ("E", "v8", "3+", 0), "")],
    "r-b": [(f"b-qf-0x{p:x}", QD, 4096, 4096, p, "expectdiff") for p in (0x53, 0x54, 0xa2, 0xa3)],
    "r-k": [("k-b5", T1500, 2048, 2048, 0x104, "fw"), ("k-b6", T1500, 2048, 2048, 0x105, "fw"), ("k-b3", T1500, 2048, 2048, 0x10a, "fw"),
            ("k-s3", T1500, 2048, 2048, ("S", "c2048", 3, 0), "fw"), ("k-s4p1", T1500, 2048, 2048, ("S", "c2048", 4, 1), "fw"),
            ("k-s3m6", T1500, 2048, 2048, 0x97 + 0x22, "fw"), ("k-creep", T1500, 2048, 4096, 0x24a + 0x22, "fw"),
            ("k-creep2", T1500, 2048, 4096, 0x24a + 0x22, "fw")],
}
for g, (w, h) in NEWT.items():
    S, B, U = P.MODEL[(w, h)]
    PLAN["r-n"].append((f"n-cal-{g}", T1500, w, h, 0x422, f"cal:{g}"))
    for k in (3, 4):
        PLAN["r-n"] += [(f"n-{g}-b{k}m1", T1500, w, h, ("M", g, k, -1, B[k] - 1 + 0x22), ""),
                        (f"n-{g}-b{k}", T1500, w, h, ("M", g, k, 0, B[k] + 0x22), ""),
                        (f"n-{g}-s{k + 1}m1", T1500, w, h, ("S", g, k + 1, -1), "")]
COUNT = {"r-a0": 7, "r-m": 15, "r-n": 21, "r-v": 6, "r-b": 40, "r-k": 8}


def argv_of(cmd):
    return shlex.split(cmd.replace('"$W/', '"W/').replace('"$S/', '"S/'))


def scene_of(a):
    """The scene a command draws, from its argv alone."""
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
T, Pr = P.tables(), P.predictions()
for st in P.STAGES:
    check((KP / "tables" / f"{st}.txt").read_text() == P.table_text(st, T[st]), f"tables/{st}.txt is what gen/r6plan.py writes")
    want = "case\tquantity\tvalue\tmodel\tset\n" + "".join("\t".join(p) + "\n" for p in Pr[st])
    check((KP / "predictions" / f"{st}.tsv").read_text() == want, f"predictions/{st}.tsv is what gen/r6plan.py writes")
check((KP / "TABLES.md").read_text() == P.tables_md(T, Pr), "TABLES.md is what gen/r6plan.py writes")
check((KP / "stages.txt").read_text().split() == P.STAGES == ["r-a0", "r-m", "r-n", "r-v", "r-b", "r-k"],
      "stages.txt: r-a0, r-m, r-n, r-v, r-b, r-k (r-k last, the plan's order)")
check({st: len(T[st]) for st in P.STAGES} == COUNT and sum(COUNT.values()) == 97, f"job counts {COUNT}: 97 (plan section 4)")
rc = P.recompute()
check(rc["model"] == {wh_: tuple(v) for wh_, v in P.MODEL_FROZEN.items()}, "MODEL_FROZEN = the frozen F5 replay and bands now (5 targets)")
check(rc["vmodel"] == P.VMODEL_FROZEN, "VMODEL_FROZEN = replay_L at L0 = 67 + 15 N for N 4, 8, CAP and PAGE")
check(rc["scenes"] == P.B_SCENES_FROZEN and rc["cells"] == P.B_CELLS_FROZEN, f"r-b scenes {P.B_SCENES_FROZEN} and cells = b_scenes()/b_cells() now")

# 2. the frozen rules are the offline stage's (their printed outputs)
f5 = (OFF / "f5_stepmodel.out").read_text()
S, B, U = P.MODEL[(2048, 2048)]
check("B_k (pages after the burst object): B2 0x97 B3 0xe3 B4 0x12e B5 0x176 B6 0x1c1 B7 0x20c" in f5 and
      B == {2: 0x97, 3: 0xe3, 4: 0x12e, 5: 0x176, 6: 0x1c1, 7: 0x20c} and U == 0x213, "2048x2048 B_k and U = f5_stepmodel.out")
for (w, h), line in (((2048, 4096), "B2 0x125 B3 0x1b7 B4 0x248 B5 0x2da B6 0x36e B7 0x402"),):
    check(line in f5 and P.MODEL[(w, h)][1] == {int(k): int(v, 16) for k, v in re.findall(r"B(\d) (0x[0-9a-f]+)", line)},
          f"{w}x{h} B_k = f5_stepmodel.out (r-k's creep cell)")
f4 = (OFF / "f4_phase.out").read_text()
check("E (timeline rule) 2:0x97 3:0xe3 4:0x12e 5:0x178 6:0x1c1 7:0x1cc" in f4 and P.E_TL_2048 == {2: 0x97, 3: 0xe3, 4: 0x12e, 5: 0x178, 6: 0x1c1, 7: 0x1cc},
      "E_TL_2048 = f4_phase.out's timeline-rule burst ends at 2048x2048")
f9 = (OFF / "f9_loss.out").read_text()
e = M.ents(2048, 2048)
for t, line in ((0x12e, "t-s5m4               thr0 0x12e N read 1 12e 12e | replay 1 12e 12e"),
                (0x12d, "t-s5m5               thr0 0x12d N read 2 12d 12d 4d | replay 2 12d 12d 4d")):
    rp = M.f9_count(2048, 2048, t, False)
    check(line in f9 and rp[0] == int(line.split("replay ")[1].split()[0]), f"F9's replay at thr0 0x{t:x} = f9_loss.out ({rp[0]})")
f7 = (OFF / "f7_replay.out").read_text()
check("W* = col (picked on g-qf only)" in f7 and M.h_replay(0, 0, 0x31, "col") == (4, [0x31, 0x51, 0x51, 0x51, 2]),
      "F7: W* = col as f7_replay.out, its qf-0x53 replay 4 31 51 51 51 2")
check(M.LAG == 3 and M.X_US == 75 and "fit 2048x2048: lag 3" in f5 and "X = 75 us" in f4, "lag 3 and X 75 us as the offline outputs")

# 3. the argv twin, row by row
for st in P.STAGES:
    rows = {r["name"]: r for r in T[st]}
    plan = PLAN[st]
    if st == "r-b":
        for sc, mv in P.B_NAME.items():
            plan = plan + [(f"b-cal-{sc}", f"moved 1:{mv[0]},{mv[1]}", 4096, 4096, 0x422, f"ucal:{sc}:{P.B_U[sc]} expectdiff")]
            plan += [(f"b-{sc}-0x{t:x}", f"moved 1:{mv[0]},{mv[1]}", 4096, 4096, t + 0x22, f"uneed:{sc} expectdiff") for t in P.B_CELLS[sc]]
    names = [p[0] for p in plan]
    check(names == [r["name"] for r in T[st]], f"{st}: the rows are the plan's, in the plan's order ({len(names)})")
    for name, scene, w, h, p, kn in plan:
        r = rows.get(name)
        if r is None:
            check(False, f"{st} {name}: no such row")
            continue
        a = argv_of(r["cmd"])
        ok = scene_of(a) == scene and wh(a) == (w, h)
        if isinstance(p, tuple):
            if p[0] == "S":
                ok &= r["P"] == (f"S:{p[1]}:{p[2]}:{p[3]:+d}" if p[3] else f"S:{p[1]}:{p[2]}:0") and P.TARGETS[p[1]] == (w, h)
            elif p[0] == "M":
                ok &= r["P"] == f"M:{p[1]}:{p[2]}:{p[3]}:0x{p[4]:x}" and P.TARGETS[p[1]] == (w, h)
            else:
                ok &= r["P"] == f"E:{p[1]}:{p[2]}:{p[3]}"
        else:
            ok &= int(r["P"], 16) == p
        ok &= all(k in r["knobs"].split() for k in kn.split())
        ok &= ("fw" in r["knobs"].split()) == (st == "r-k")
        ok &= ("--dump-render" in a) == (scene.startswith(T1500) and w * h <= 2048 * 2048)
        ok &= ("model:" in r["knobs"]) == name.startswith("n-cal-")
        check(ok, f"{st} {name}: argv {scene_of(a)} {wh(a)[0]}x{wh(a)[1]} P {r['P']} knobs [{r['knobs'][:40]}] = the plan's row")
    # a calibration with model: carries the frozen model's steps
    for r in T[st]:
        m = re.search(r"model:(\S+)", r["knobs"])
        if m:
            g = r["name"][len("n-cal-"):]
            S, B, U = P.MODEL[NEWT[g]]
            check(m.group(1) == ",".join(f"0x{S[k]:x}" for k in sorted(S)), f"{r['name']}: model: = the frozen steps of {NEWT[g]}")

# ... and against the commands round 3 / 5 ran for the same cells (the dump is the only difference allowed)
kept = {}
for d in ("render/closing-r3-geo/out/g-c4", "render/closing-r3-geo-c/out/g-qf", "render/closing-r3-geo-c/out/g-qh",
          "render/closing-r3-geo/out/g-c5", "render/closing-r5-dpm/out/a2/d-t", "render/closing-r5-dpm/out/a2/d-a0"):
    for c in csv.DictReader(open(DATA / d / "cases.tsv"), delimiter="\t"):
        kept[c["name"]] = c["args"]
norm = lambda cmd: [x for x in argv_of(cmd.replace("/tmp/", "W/")) if not x.startswith("W/") and x != "--dump-render"
                    and not x.startswith("/home/")]
pairs = [("r-a0", "a0-c4-b5", "c4-b5"), ("r-a0", "a0-c4-b6", "c4-b6"), ("r-a0", "a0-cal-2048", "a0-cal-2048"),
         ("r-a0", "a0-t-s3m7", "t-s3m7"), ("r-a0", "a0-qf-0xa2", "qf-0xa0"), ("r-k", "k-b5", "c4-b5"), ("r-k", "k-b3", "c4-b3"),
         ("r-k", "k-creep", "c5b-cal"), ("r-b", "b-qf-0x53", "qf-0x24"), ("r-m", "m-b5-0x174", "c4-b5")]
for st, ours, theirs in pairs:
    r = next(x for x in T[st] if x["name"] == ours)
    a, b = norm(r["cmd"]), norm(kept[theirs])
    a = [x for x in a if x != "S/p1139-green.bin"]
    b = [x for x in b if not x.endswith("p1139-green.bin")]
    check(a == b, f"{ours}'s argv = the kept {theirs} ({' '.join(a)[:70]})")
s275 = norm(kept["qh-s275-0x26"])
for sc, mv in P.B_NAME.items():
    r = next(x for x in T["r-b"] if x["name"] == f"b-cal-{sc}")
    want = [x if x != "1:1024,0" else f"1:{mv[0]},{mv[1]}" for x in s275]
    check(norm(r["cmd"]) == want, f"b-cal-{sc}'s argv = E773's s275 command with the move {mv} (single kick, no --geometry)")
for N in (4, 8):
    r = next(x for x in T["r-v"] if x["name"] == f"v-cal-c{N}")
    a = norm(r["cmd"])
    c = next(x for x in T["r-a0"] if x["name"] == "a0-cal-2048")
    b = norm(c["cmd"])
    check(a == b[:b.index("1500") + 1] + ["--vtx-coords", str(N)] + b[b.index("1500") + 1:],
          f"v-cal-c{N}'s argv = a0-cal-2048's with --vtx-coords {N} added after --vertices 1500 and nothing else")

# 4. registers
regs = "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"
check(all(r["rt"] == regs for st in P.STAGES for r in T[st]), "every row samples r5's 16 registers")

# 5. what the predictions say
pred = {st: list(csv.DictReader(open(KP / "predictions" / f"{st}.tsv"), delimiter="\t")) for st in P.STAGES}
pv = lambda st, c, q, m=None: [x["value"] for x in pred[st] if x["case"] == c and x["quantity"] == q and (m is None or x["model"] == m)]
check(all(x["set"] in ("control", "repeat", "heldout", "explore") for st in P.STAGES for x in pred[st]), "every prediction has its label")
check(pv("r-a0", "a0-cal-2048f", "S6") == ["0x181"] and pv("r-a0", "a0-cal-2048f", "S7") == ["0x1ca"] and
      pv("r-a0", "a0-cal-2048f", "need") == ["0x213"], "r-a0: the complete calibration S6 0x181, S7 0x1ca (E873), need 0x213 (E785)")
check(pv("r-a0", "a0-t-s3m7", "gps_left") == ["2"] and pv("r-a0", "a0-t-s3m6", "gps_left") == ["1"] and pv("r-a0", "a0-qf-0xa2", "nparts") == ["2"],
      "r-a0: left 2, 1 (t-s3m7, t-s3m6) and 2 partial renders at qf 0xa2 (plan section 4)")
for k, b in B2048.items():
    got = [pv("r-m", f"m-b{k}-0x{b + o:x}", "gps_left", "H-PHASE")[0] for o in (-2, -1, 0, 1, 2)]
    check(got == ["2", "2", "1", "1", "1"], f"r-m band {k}: H-PHASE 2 2 1 1 1 around B{k} 0x{b:x}")
check([pv("r-m", f"m-b5-0x{0x176 + o:x}", "gps_left", "E-TL")[0] for o in (-2, -1, 0, 1, 2)] == ["2", "2", "2", "2", "1"] and
      [pv("r-m", f"m-b7-0x{0x20c + o:x}", "gps_left", "E-TL")[0] for o in (-2, -1, 0, 1, 2)] == ["1"] * 5,
      "r-m: the timeline rule's rival differs at band 5 (E5 0x178) and band 7 (E7 0x1cc)")
check(all(x["value"] == "N" for x in pred["r-m"] if x["quantity"] == "cls"), "r-m: every predicted class silent (above B3)")
for g in NEWT:
    for k in (3, 4):
        got = [pv("r-n", f"n-{g}-{c}", "gps_left", "H-PHASE")[0] for c in (f"b{k}m1", f"b{k}", f"s{k + 1}m1")]
        check(got == ["2", "1", "1"], f"r-n {g} band {k}: left 2, 1, 1")
    check(pv("r-n", f"n-{g}-b3m1", "cls") == ["R"] and pv("r-n", f"n-{g}-b3", "cls") == ["N"], f"r-n {g}: raise at B3 - 1, silent at B3")
check(pv("r-k", "k-b5", "dec_sa8_380") == ["0x180"] and pv("r-k", "k-b6", "dec_sa8_380") == ["0x0"] and
      pv("r-k", "k-b3", "dec_sa8_380") == ["0x0"] and pv("r-k", "k-s3", "dec_sa8_380") == ["0x180"] and
      pv("r-k", "k-s4p1", "dec_sa8_380") == ["0x0"] and pv("r-k", "k-s3m6", "dec_sa8_380") == ["0x180"] and
      pv("r-k", "k-creep", "dec_sa8_380", "R-5") == ["0x0"] and pv("r-k", "k-creep", "dec_sa8_380", "ISUB-REV") == ["0x180"],
      "r-k: sa8 & 0x380 at the decision 0x180, 0, 0, 0x180, 0, 0x180, 0 (plan section 4); the creep cell 0x180 if the operands swap")
check(pv("r-k", "k-creep", "nparts", "F9") == ["2"] and pv("r-k", "k-creep", "gps_left") == ["1"],
      "r-k: the creep cell has 2 partial renders (F9) and leaves 1 page (H-PHASE): a decision entry with dword 36 = 2")
for sc in P.B_NAME:
    check(len(P.B_CELLS[sc]) == 8 and all(abs(P.B_U[sc] - u) >= 10 for u in P.KEPT_U), f"r-b {sc}: 8 cells, U {P.B_U[sc]} apart from the kept scenes")
    d = sum(1 for t in P.B_CELLS[sc] if pv("r-b", f"b-{sc}-0x{t:x}", "nparts", "H-REPLAY-ROW") != pv("r-b", f"b-{sc}-0x{t:x}", "nparts", "H-REPLAY-COL"))
    check(d >= 3, f"r-b {sc}: row and column order differ at {d} of 8 cells")
for st in P.STAGES:
    for r in T[st]:
        U_ = P.B_U.get(r["name"].split("-")[1]) if st == "r-b" else None
        if U_ and r["name"].startswith("b-s"):
            check(pv(st, r["name"], "nparts", "H-REPLAY-ROW")[0] == str(M.h_replay(*P.B_NAME[r["name"].split("-")[1]], int(r["P"], 16) - 0x22, "row")[0]),
                  f"{r['name']}: H-REPLAY-ROW's count is the frozen F7 replay's")
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
