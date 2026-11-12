#!/usr/bin/env python3
"""test_gen.py: the frozen tables and predictions against the PLAN, row by row (round 4's slip o2 must be impossible by construction).
  1. the files on disk are what gen/r5plan.py writes now (tables, predictions, TABLES.md, stages.txt);
  2. the ARGV TWIN: every row's command, split as the runner's `eval set --` splits it, is checked against a plan row transcribed BY HAND
     below from exp-dpm-r5.md section 4 (scene: 1500-vertex probe of p1139-green or the default triangle with or without a move; target
     size; P or the derived step; knobs), and against the command round 3 ran for the same cell (the kept cases.tsv of closing-r3-geo
     g-c4 and closing-r3-geo-c g-qf / g-qh): the same argv but for the work directory and the dump (freeze 2: --dump-render at 2048x2048 only);
  3. the register list is decision 4 (a)'s 16 registers, every row;
  4. the predictions say what section 4 expects (A1 all silent, grow only at S, S4/S5 silent, S2/S3 PEND raise / BLOCK silent, T 2 2 1 1,
     the B counts by H-CNT from HU1's U, A3's H-BITS words) and every case has its label (control / repeat / heldout / explore);
  5. B's scenes and cells follow their build rules (HU1 nearest 120 and 200 along x in steps of 64; 10 cells a scene).
"""
import csv
import pathlib
import re
import shlex
import sys

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "gen")]
import r5plan as P  # noqa: E402
import hu1  # noqa: E402

DATA = pathlib.Path("/Users/jtorra/src/resgx545-data/render")
FAIL = []


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


# ---- the plan, by hand (exp-dpm-r5.md section 4); (name, scene, W, H, P or (k, off), knob words that must be there)
T1500, QD = "tri1500", "default"
PLAN = {
    "d-a0": [("a0-cal-2048", T1500, 2048, 2048, 0x162, "cal:c2048 prem"), ("a0-cal-4096", T1500, 4096, 4096, 0x422, "cal:c4096 prem"),
             ("a0-c4-b5", T1500, 2048, 2048, 0xe2 + 0x22, "ctl:R prem"), ("a0-c4-b6", T1500, 2048, 2048, 0xe3 + 0x22, "ctl:N prem"),
             ("a0-c3-2048-0xe2", T1500, 2048, 2048, 0xe2, "ctl:R prem"), ("a0-c3-2048-0x122", T1500, 2048, 2048, 0x122, "ctl:N prem"),
             ("a0-4096-0x35a", T1500, 4096, 4096, 0x35a + 0x22, "ctl:N prem"), ("a0-4096-0x35c", T1500, 4096, 4096, 0x35c + 0x22, "ctl:N prem")],
    "d-a1": [("a1-rep1", T1500, 2048, 2048, 0x10a, ""), ("a1-s4m1", T1500, 2048, 2048, ("c2048", 4, -1), ""),
             ("a1-rep2", T1500, 2048, 2048, 0x10a, ""), ("a1-s4p1", T1500, 2048, 2048, ("c2048", 4, 1), ""),
             ("a1-rep3", T1500, 2048, 2048, 0x10a, ""), ("a1-b4", T1500, 2048, 2048, 0xe4 + 0x22, ""),
             ("a1-rep4", T1500, 2048, 2048, 0x10a, ""), ("a1-b2", T1500, 2048, 2048, 0xf0 + 0x22, ""), ("a1-rep5", T1500, 2048, 2048, 0x10a, "")],
    "d-a2": [(f"a2-42-{n}", T1500, 2048, 2048, ("c2048", k, o), "") for n, k, o in
             [("s3m1", 3, -1), ("s3a", 3, 0), ("s3b", 3, 0), ("s3p1", 3, 1), ("s2m1", 2, -1), ("s2", 2, 0), ("s2p1", 2, 1), ("s5m1", 5, -1),
              ("s5", 5, 0), ("s5p1", 5, 1)]] +
            [(f"a2-44-{n}", T1500, 4096, 4096, ("c4096", k, o), "") for n, k, o in
             [("s4a", 4, 0), ("s4b", 4, 0), ("s3m1", 3, -1), ("s3a", 3, 0), ("s3b", 3, 0), ("s3p1", 3, 1)]],
    "d-a2b": [("a2b-cal-4x2", T1500, 4096, 2048, 0x422, "cal:c4x2"), ("a2b-4x2-s4", T1500, 4096, 2048, ("c4x2", 4, 0), ""),
              ("a2b-cal-2x4", T1500, 2048, 4096, 0x422, "cal:c2x4"), ("a2b-2x4-s4", T1500, 2048, 4096, ("c2x4", 4, 0), ""),
              ("a2b-cal-33", T1500, 3072, 3072, 0x422, "cal:c33"), ("a2b-33-s4", T1500, 3072, 3072, ("c33", 4, 0), "")],
    "d-t": [(f"t-s{k}m{o}", T1500, 2048, 2048, ("c2048", k, -o), "") for k in (3, 5) for o in (7, 6, 5, 4)],
    "d-b": [(f"b-qf-0x{p:x}", QD, 4096, 4096, p, "expectdiff") for p in (0x24, 0x53, 0x54, 0xa2, 0xa3)],
    "d-a3": [("a3-b5a", T1500, 2048, 2048, 0x104, "fw"), ("a3-b6a", T1500, 2048, 2048, 0x105, "fw"), ("a3-r1", T1500, 2048, 2048, 0x10a, "fw"),
             ("a3-b5b", T1500, 2048, 2048, 0x104, "fw"), ("a3-b6b", T1500, 2048, 2048, 0x105, "fw"), ("a3-r2", T1500, 2048, 2048, 0x10a, "fw"),
             ("a3-r3", T1500, 2048, 2048, 0x10a, "fw"), ("a3-s3", T1500, 2048, 2048, ("c2048", 3, 0), "fw")],
}
COUNT = {"d-a0": 8, "d-a1": 9, "d-a2": 16, "d-a2b": 6, "d-t": 8, "d-b": 27, "d-a3": 8}


def argv_of(cmd):
    return shlex.split(cmd.replace('"$W/', '"W/').replace('"$S/', '"S/'))


def scene_of(a):
    """The scene a command draws, from its argv alone."""
    if a[0] == "probe":
        ok = a[1:3] == ["--tri", "pixel"] and a[a.index("--vertices") + 1] == "1500" and a[-1] == "S/p1139-green.bin"
        return T1500 if ok and "--move" not in a and "-n" not in a else "other probe"
    if a[0] == "tri":
        if a[a.index("-n") + 1] != "1" or "--geometry" in a or "--vertices" in a:
            return "other tri"
        return ("moved " + a[a.index("--move") + 1]) if "--move" in a else QD
    return "?"


def wh(a):
    return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])


# 1. the files are the generator's
T, Pr = P.tables(), P.predictions()
for st in P.STAGES:
    check((KP / "tables" / f"{st}.txt").read_text() == P.table_text(st, T[st]), f"tables/{st}.txt is what gen/r5plan.py writes")
    want = "case\tquantity\tvalue\tmodel\tset\n" + "".join("\t".join(p) + "\n" for p in Pr[st])
    check((KP / "predictions" / f"{st}.tsv").read_text() == want, f"predictions/{st}.tsv is what gen/r5plan.py writes")
check((KP / "TABLES.md").read_text() == P.tables_md(T, Pr), "TABLES.md is what gen/r5plan.py writes")
check((KP / "stages.txt").read_text().split() == P.STAGES == ["d-a0", "d-a1", "d-a2", "d-a2b", "d-t", "d-b", "d-a3"],
      "stages.txt: A0, A1, A2, A2b, T, B, A3 (A3 last)")
check({st: len(T[st]) for st in P.STAGES} == COUNT and sum(COUNT.values()) == 82, f"job counts {COUNT}: 82 (decision R5-3 (a))")

# 2. the argv twin, row by row
for st in P.STAGES:
    rows = {r["name"]: r for r in T[st]}
    plan = PLAN[st]
    if st == "d-b":
        for sc, mv in P.B_MOVES.items():
            plan = plan + [(f"b-cal-{sc}", f"moved 1:{mv[0]},{mv[1]}", 4096, 4096, 0x422, f"ucal:{sc}:{P.B_U[sc]} expectdiff")]
            plan += [(r["name"], f"moved 1:{mv[0]},{mv[1]}", 4096, 4096, int(r["P"], 16), f"uneed:{sc} expectdiff")
                     for r in T[st] if r["name"].startswith(f"b-{sc}-")]
    names = [p[0] for p in plan]
    check(sorted(names) == sorted(rows) and (st == "d-b" or names == [r["name"] for r in T[st]]),
          f"{st}: the rows are the plan's, in the plan's order ({len(names)})")
    for name, scene, w, h, p, kn in plan:
        r = rows.get(name)
        if r is None:
            continue
        a = argv_of(r["cmd"])
        ok = scene_of(a) == scene and wh(a) == (w, h)
        if isinstance(p, tuple):
            ok &= r["P"] == (f"S:{p[0]}:{p[1]}:{p[2]:+d}" if p[2] else f"S:{p[0]}:{p[1]}:0") and P.TARGETS[p[0]] == (w, h)
        else:
            ok &= int(r["P"], 16) == p
        ok &= all(k in r["knobs"].split() for k in kn.split())
        ok &= ("fw" in r["knobs"].split()) == (st == "d-a3")
        ok &= ("--dump-render" in a) == (scene == T1500 and (w, h) == (2048, 2048))   # freeze 2: dumps at 2048x2048 only
        check(ok, f"{st} {name}: argv {scene_of(a)} {wh(a)[0]}x{wh(a)[1]} P {r['P']} knobs [{r['knobs']}] = the plan's row")

# ... and against the commands round 3 ran (the same argv but for the work directory)
kept = {}
for d in ("closing-r3-geo/out/g-c4", "closing-r3-geo-c/out/g-qf", "closing-r3-geo-c/out/g-qh", "closing-r3-geo/out/g-c5"):
    for c in csv.DictReader(open(DATA / d / "cases.tsv"), delimiter="\t"):
        kept[c["name"]] = c["args"]
# the dump is the only difference allowed (freeze 2 drops it off 2048x2048; it is checked row by row above)
norm = lambda cmd: [x for x in argv_of(cmd.replace("/tmp/", "W/")) if not x.startswith("W/") and x != "--dump-render"]
pairs = [("d-a0", "a0-c4-b5", "c4-b5"), ("d-a0", "a0-c4-b6", "c4-b6"), ("d-a0", "a0-c3-2048-0xe2", "c3-2048-0xe2"),
         ("d-a0", "a0-c3-2048-0x122", "c3-2048-0x122"), ("d-a0", "a0-4096-0x35a", "c3-4096-0x372"), ("d-a1", "a1-rep1", "c4-b3"),
         ("d-a3", "a3-b5a", "c4-b5"), ("d-b", "b-qf-0x24", "qf-0x24"), ("d-b", "b-qf-0xa3", "qf-0xa3"), ("d-a2b", "a2b-cal-4x2", "c5a-cal"),
         ("d-a2b", "a2b-cal-2x4", "c5b-cal"), ("d-a2b", "a2b-cal-33", "c5c-cal")]
for st, ours, theirs in pairs:
    r = next(x for x in T[st] if x["name"] == ours)
    check(norm(r["cmd"]) == norm(kept[theirs]), f"{ours}'s argv = round 3's {theirs} ({' '.join(norm(r['cmd']))[:70]})")
s275 = norm(kept["qh-s275-0x26"])
for sc, mv in P.B_MOVES.items():
    r = next(x for x in T["d-b"] if x["name"] == f"b-cal-{sc}")
    want = [x if x != "1:1024,0" else f"1:{mv[0]},{mv[1]}" for x in s275]
    check(norm(r["cmd"]) == want, f"b-cal-{sc}'s argv = E773's s275 command with the move {mv} (single kick, no --geometry)")

# 3. registers
regs = "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"
n = sum(1 for part in regs.split(",") for _ in range(int(part.split("-")[0], 16), int(part.split("-")[-1], 16) + 4, 4))
check(n == 16 and all(r["rt"] == regs for st in P.STAGES for r in T[st]), f"every row samples the 16 registers of decision 4 (a) ({n})")
old = set(range(0x624, 0x62c, 4)) | set(range(0x654, 0x664, 4)) | set(range(0x700, 0x714, 4)) | set(range(0x720, 0x730, 4)) | {0x748}
new = {int(x, 16) for part in regs.split(",") for x in [part] if "-" not in part} | \
      {v for part in regs.split(",") if "-" in part for v in range(int(part.split("-")[0], 16), int(part.split("-")[1], 16) + 4, 4)}
check(old - new == {0x654, 0x65c, 0x704, 0x708} and new - old == {0x12c, 0x730, 0x734, 0xa74},
      "g-c4's list less 0x0654, 0x065c, 0x0704, 0x0708, plus 0x012c, 0x0730, 0x0734, 0x0a74")

# 4. predictions say what section 4 expects
pr = {st: list(csv.DictReader(open(KP / "predictions" / f"{st}.tsv"), delimiter="\t")) for st in P.STAGES}
get = lambda st, c, q, m=None: [x["value"] for x in pr[st] if x["case"] == c and x["quantity"] == q and (m is None or x["model"] == m)]
check(all(get("d-a1", r["name"], "cls", "H-PEND") == ["N"] == get("d-a1", r["name"], "cls", "H-BLOCK") for r in T["d-a1"]), "A1: all 9 silent")
check(all(get("d-a1", f"a1-rep{i}", "grow") == ["1"] for i in range(1, 6)) and get("d-a1", "a1-b4", "grow") == ["0"], "A1: grow at P 0x10a only")
check(get("d-a1", "@d-a1", "grows_of_5", "H-GREQ") == ["5"] and get("d-a1", "@d-a1", "grows_of_5", "H-NOISE") == ["<=1"], "A1: H-GREQ 5 of 5, H-NOISE at most 1")
a2 = {r["name"]: (get("d-a2", r["name"], "grow")[0], get("d-a2", r["name"], "cls", "H-PEND")[0], get("d-a2", r["name"], "cls", "H-BLOCK")[0]) for r in T["d-a2"]}
check(all(v[0] == ("1" if re.search(r"-s\d[ab]?$", n) else "0") for n, v in a2.items()), "A2: grow at S cells only")
check(all(a2[n][1:] == ("N", "N") for n in ("a2-42-s5", "a2-44-s4a", "a2-44-s4b", "a2-42-s5m1", "a2-42-s5p1")), "A2: S4/S5 cells and the S5 neighbours silent")
check(all(a2[n][1:] == ("R", "N") for n in ("a2-42-s3a", "a2-42-s3b", "a2-42-s2", "a2-44-s3a", "a2-44-s3b")), "A2: S2/S3 cells raise under H-PEND, silent under H-BLOCK")
check(all(a2[n][1:] == ("R", "R") for n in ("a2-42-s3m1", "a2-42-s3p1", "a2-42-s2m1", "a2-42-s2p1", "a2-44-s3m1", "a2-44-s3p1")), "A2: the S2/S3 neighbours raise")
check(all(get("d-a2b", f"a2b-{t}-s4", "grow") == ["1"] and get("d-a2b", f"a2b-{t}-s4", "cls", "H-PEND") == ["N"] for t in ("4x2", "2x4", "33")), "A2b: grow, silent")
check([get("d-t", f"t-s{k}m{o}", "gps_left")[0] for k in (3, 5) for o in (7, 6, 5, 4)] == ["2", "2", "1", "1"] * 2, "T: pages left 2, 2, 1, 1 in each band")
check([get("d-t", f"t-s{k}m7", "cls")[0] for k in (3, 5)] == ["R", "N"], "T: band 2 raises, band 4 silent")
check([get("d-b", f"b-qf-0x{p:x}", "nparts")[0] for p in (0x24, 0x53, 0x54, 0xa2, 0xa3)] == ["9", "4", "3", "2", "1"], "B controls 9, 4, 3, 2, 1")
check(get("d-a3", "a3-b5a", "dec_sa8_380") == ["0x180"] and get("d-a3", "a3-b6a", "dec_sa8_380") == ["0x0"] and get("d-a3", "a3-b5b", "next_sa8_380") == ["0x380"],
      "A3: H-BITS 0x180 raised, 0 silent, 0x380 after the raise")
check(get("d-a3", "a3-r1", "eor_sa9_b8", "H-PEND") == ["0"] and get("d-a3", "a3-r1", "eor_sa9_b8", "H-BLOCK") == ["1"]
      and get("d-a3", "a3-s3", "dec_sa8_380", "H-PEND") == ["0x180"], "A3: c4-b3's sa9 bit 8 separates PEND and BLOCK; the S3 cell 0x180 under PEND")
labels = {x["set"] for st in P.STAGES for x in pr[st]}
check(labels <= {"control", "repeat", "heldout", "explore"} and all(r["set"] in labels for st in P.STAGES for r in T[st]), f"labels {sorted(labels)}")

# 5. B's build rules
check([P.b_scene_pick(120), P.b_scene_pick(200)] == [(2560, 119), (1984, 198)] and P.B_MOVES == {"s119": (2560, 0), "s198": (1984, 0)},
      "B scenes: HU1 nearest 120 and 200 along x in steps of 64: (2560, 0) U 119, (1984, 0) U 198")
check(hu1.hu1(4096, 4096, hu1.moved(4096, 4096, 1024, 0))[0] == 275 and hu1.hu1(4096, 4096, [hu1.default_tri(4096, 4096)])[0] == 287,
      "HU1 reproduces E773's s275 and the default 287")
check([hex(t) for t in P.b_cells(198)] == ["0x2", "0x3", "0x7", "0x8", "0x1a", "0x1b", "0x2d", "0x2e", "0x53", "0x54"], "B s198 cells: the step pairs 1/2, 2/3, 3/4, 5/6 and thr0 2, 3")
check(len(P.b_cells(119)) == 10 and {2, 3, 7, 8, 0x13, 0x14, 0x2c, 0x2d} <= set(P.b_cells(119)), f"B s119 cells: {[hex(t) for t in P.b_cells(119)]}")
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
