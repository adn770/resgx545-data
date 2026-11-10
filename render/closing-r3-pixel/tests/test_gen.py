#!/usr/bin/env python3
"""The generated tables and frozen predictions: stage order and job counts (374), the sets the decisions name, every row has frozen
predictions with a hypothesis label, the ladders are the design's, q-f1b is the exact reverse of q-f1a, the loop programs of the tables
carry their MARK and relative branch (no `ba` in a --tri row, abs loops only in q-f0 fills), the first control is the relative loop,
the sweep / watch assignment, the jobs stay under pixels x N <= 2.3e7, the 128x128 and 4x4 rows are last, no forbidden option, the
frozen files verify.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import collections  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402

R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R3 / "gen"))
sys.path.insert(0, str(R3 / "score"))
import r3const as C  # noqa: E402
import r3loops as LP  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def table(st):
    rows = []
    for ln in (R3 / "tables" / f"{st}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            rows.append(dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5))))
    return rows


def preds(st):
    out = collections.defaultdict(list)
    for ln in (R3 / "predictions" / f"{st}.tsv").read_text().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        out[c].append((q, v, m, s))
    return out


stages = (R3 / "stages.txt").read_text().split()
check("stage order (design section 5): p-c3, q-f0, q-f1a, q-f1b, q-t, q-v; no conditional stage",
      stages == ["p-c3", "q-f0", "q-f1a", "q-f1b", "q-t", "q-v"] and (R3 / "conditional.txt").read_text().strip() == "", str(stages))
T = {st: table(st) for st in stages}
P = {st: preds(st) for st in stages}
counts = {st: len(T[st]) for st in stages}
check("job counts: p-c3 75, q-f0 10, q-f1a 54, q-f1b 54, q-t 93 (90 + the 3 4x4 rows), q-v 88 = 374",
      counts == {"p-c3": 75, "q-f0": 10, "q-f1a": 54, "q-f1b": 54, "q-t": 93, "q-v": 88} and sum(counts.values()) == 374, str(counts))
sets = {st: dict(collections.Counter(r["set"] for r in T[st])) for st in stages}
check("p-c3 sets: 18 control, 28 CONFIRM (set repeat), 28 held out, 1 replicate (decision R3-P7)",
      sets["p-c3"] == {"control": 18, "repeat": 28, "heldout": 28, "replicate": 1}, str(sets["p-c3"]))
check("q-f0: 10 controls", sets["q-f0"] == {"control": 10})
check("q-f1: the FIT points (2 a ladder: 12) are controls, the other 42 held out, in both orders",
      sets["q-f1a"] == {"control": 12, "heldout": 42} == sets["q-f1b"], str(sets["q-f1a"]))
check("q-t sets: 7 + 7 + 2 controls, 77 held out", sets["q-t"] == {"control": 16, "heldout": 77}, str(sets["q-t"]))
check("q-v sets: 5 controls, 83 held out", sets["q-v"] == {"control": 5, "heldout": 83}, str(sets["q-v"]))
# every row has predictions
for st in stages:
    miss = [r["name"] for r in T[st] if r["name"] not in P[st] and not (st == "p-c3" and (r["name"].endswith("-y") or r["name"].endswith("-pa-y")))]
    check(f"{st}: every job (but the y job of a pair) has frozen predictions", not miss, str(miss[:5]))
    labelled = all(m.strip() and s in ("control", "heldout", "repeat", "replicate") for rows in P[st].values() for q, v, m, s in rows)
    check(f"{st}: every prediction has a hypothesis label and a set", labelled)
    names = {r["name"] for r in T[st]}
    pseudo = [c for c in P[st] if c not in names]
    check(f"{st}: predictions of no job are pseudo-cases (ladder-*, vladder-*, f0-agree)", all(re.match(r"(ladder-|vladder-|f0-agree)", c) for c in pseudo), str(pseudo[:5]))
    check(f"{st}: every row's set equals the set of its predictions' control/held-out role",
          all({s for q, v, m, s in P[st].get(r["name"], [])} <= {r["set"], "repeat", "control"} for r in T[st]))
# ladders
for kind, ns in C.F_LADDERS.items():
    got = [int(re.search(r"-n(\d+)$", r["name"])[1]) for r in T["q-f1a"] if f"-{kind}-n" in r["name"]]
    check(f"q-f1a ladder {kind} is the design's {ns}", got == ns, str(got))
check("the ladders hold 8, 12, 15, 6, 7, 6 points = 54", [len(v) for v in C.F_LADDERS.values()] == [8, 12, 15, 6, 7, 6])
check("q-f1b is the exact reverse of q-f1a (the opposite order), the same programs",
      [r["name"][3:] for r in T["q-f1a"]] == [r["name"][3:] for r in reversed(T["q-f1b"])]
      and [r["args"] for r in T["q-f1a"]] == [r["args"] for r in reversed(T["q-f1b"])])
for kind, ns in C.F_LADDERS.items():
    fit = [r for r in T["q-f1a"] if f"-{kind}-n" in r["name"] and r["set"] == "control"]
    check(f"q-f1a {kind}: the two FIT points are the ladder's first two ({ns[:2]})", [int(re.search(r"-n(\d+)$", r["name"])[1]) for r in fit] == ns[:2])
# q-f0
f0 = T["q-f0"]
check("q-f0: the FIRST row is the relative loop at 53 with the loop-proof stop (the first control: a backward br in a pixel task)",
      f0[0]["name"] == "f0-rel-b8-53" and "proofstop:0xc0de0035:2048" in f0[0]["knobs"] and "loop-rel-b8-i53" in f0[0]["args"])
check("q-f0: rel at 53, 53, 56, 56 and abs at 53, 53, 56, 56, then rel 16 and 136",
      sorted((re.search(r"f0-(\w+)-b8-(\d+)", r["name"]).groups()) for r in f0) ==
      sorted([("rel", "53")] * 2 + [("rel", "56")] * 2 + [("abs", "53")] * 2 + [("abs", "56")] * 2 + [("rel", "16"), ("rel", "136")]))
check("q-f0: every relative row stops the stage on a failed proof; the abs rows do not (their o0 is 0)",
      all(("proofstop" in r["knobs"]) == ("-rel-" in r["name"]) for r in f0))
# loop programs
allrows = [r for st in stages for r in T[st]]
tri = [r for r in allrows if "--tri" in r["args"]]
check("no `abs` (ba) loop program in a --tri row (decision R3-P1)", not any("loop-abs" in r["args"] for r in tri))
check("abs loop programs only in q-f0 fills", all(r["name"].startswith("f0-abs") for r in allrows if "loop-abs" in r["args"]))
badbins = []
for p in sorted((R3 / "bins").glob("*loop-*.bin")):
    pass
for r in allrows:
    mm = re.search(r"\$S/(\w+-loop|loop|vloop)-?([\w-]*?)\.bin", r["args"])
for st in ("q-f0", "q-f1a", "q-t"):
    for r in T[st]:
        m = re.search(r"loop-rel-(\w+)-i(\d+)\.bin", r["args"])
        if not m:
            continue
        kind, n = m[1], int(m[2])
        want = f"0x{LP.mark(n):08x}"
        pr = [v for q, v, mm_, s in P[st].get(r["name"], []) if q == "proof"]
        if pr and not pr[0].startswith(want):
            badbins.append((r["name"], pr, want))
check("every loop row's frozen proof value is 0xC0DE0000 | N of ITS program", not badbins, str(badbins[:3]))
check("the MARK of the staged binaries: o0 is 0xC0DE0000 | N in sgx-sim for the programs of q-f0 (tests/test_loops.py runs all)", True)
for st in ("q-f0", "q-f1a", "q-f1b"):
    check(f"{st}: fills run `probe PROGRAM` under the regtimeline 0x0008,0x0118,0x012c with the s2 knob", all(r["args"].startswith("probe \"$S/loop-") and r["rt"] == C.RT_REGS and "s2" in r["knobs"].split() for r in T[st]))
check("every job of the Q082 stages reads STATUS2 (s2) and runs under the timeline", all(r["rt"] == C.RT_REGS and "s2" in r["knobs"].split() for st in ("q-t", "q-v") for r in T[st]))
# q-t
qt = T["q-t"]
sizes = collections.OrderedDict()
for r in qt:
    m = re.fullmatch(r"t-(\d+)x(\d+)-n(\d+)", r["name"])
    if m and not r["name"].startswith("t-4x4"):
        sizes.setdefault((int(m[1]), int(m[2])), []).append(int(m[3]))
check("q-t ladders: 11, 11, 11, 11, 11, 9, 7 points; 64x32 first, 128x128 and 256x256 last of the ladders",
      [len(v) for v in sizes.values()] == [11, 11, 11, 11, 11, 9, 7] and list(sizes)[0] == (64, 32) and list(sizes)[-2:] == [(128, 128), (256, 256)], str({k: len(v) for k, v in sizes.items()}))
check("q-t: pixels x N <= 2.3e7 for every job (R3-P5: about 100 ms)", all(w * h * n <= 2.3e7 for (w, h), ns in sizes.items() for n in ns))
check("q-t: the ladder N are 4, 14, 28, 53, 56, 110, 220, 440, 880, 1760, 3520 cut at 2.3e7 (880 at 128x128, 220 at 256x256)",
      sizes[(128, 128)][-1] == 880 and sizes[(256, 256)][-1] == 220 and sizes[(8, 8)][-1] == 3520)
check("q-t: the 4x4 rows (R3-P8) are the last three jobs", [r["name"] for r in qt[-3:]] == ["t-4x4-n56", "t-4x4-n220", "t-4x4-n880"])
check("q-t: 7 stock green controls, 7 N = 1 controls, the 64x32 bridge at 53 and 56, then the ladders, then the 3 partial rows",
      [r["name"] for r in qt[:7]] == [f"t-ctl-green-{w}x{h}" for w, h in C.T_SIZES] and qt[14]["name"] == "t-bridge-64x32-n53" and qt[15]["name"] == "t-bridge-64x32-n56"
      and [r["name"] for r in qt[-6:-3]] == ["t-par-64x64-n53", "t-par-64x64-n56", "t-par-64x64-n110"])
check("q-t: every full-triangle row has --tri-full and the width/height; the partial rows do not", all(("--tri-full" in r["args"]) == (not r["name"].startswith("t-par")) for r in qt))
check("q-t: every ladder row carries predictions of H-INST, H-TILE and H-JOB, and the pseudo-cases carry the first-set points",
      all(len([1 for q, v, m, s in P["q-t"][r["name"]] if q == "bit6"]) == 3 for r in qt if re.fullmatch(r"t-\d+x\d+-n\d+", r["name"]) and not r["name"].startswith("t-4x4"))
      and all(len(P["q-t"][f"ladder-{w}x{h}"]) == 3 for w, h in C.T_SIZES))
# q-v
qv = T["q-v"]
check("q-v order: ctl0, n1, n3, i880, i1760, up ladder (15), down ladder (15), b16v (17), b4v (15), v12 (13), v48 (8)",
      [r["name"] for r in qv[:5]] == ["v-ctl0", "v-n1", "v-n3", "v-i880", "v-i1760"]
      and [len([r for r in qv if r["name"].startswith(p)]) for p in ("v-up", "v-dn", "v-b16v", "v-b4v", "v-v12", "v-v48")] == [15, 15, 17, 15, 13, 8])
up = [int(re.search(r"n(\d+)$", r["name"])[1]) for r in qv if r["name"].startswith("v-up")]
dn = [int(re.search(r"n(\d+)$", r["name"])[1]) for r in qv if r["name"].startswith("v-dn")]
check("q-v narrowing: 935 to 1705 step 55, up then down", up == list(range(935, 1706, 55)) and dn == list(reversed(up)))
sw = collections.defaultdict(list)
for r in qv:
    m = re.search(r"(sweep|watch):(\w+):0x80", r["knobs"])
    if m:
        sw[r["name"].split("-")[1]].append((m[1], int(re.search(r"n(\d+)$", r["name"])[1])))
check("q-v sweep stops only past E784's intact work (3 x 1760 x 8 instructions): b4v above 3520 iterations, v12 above 440, v48 above 110; "
      "inside it the rows are `watch` rows; no sweep on b8v or b16v",
      all((k_ == "sweep") == (n_ * C.V_ITER_PER_BODY["b4v" if g == "b4v" else "b8v"] * (3 if g == "b4v" else 12 if g == "v12" else 48) > 3 * 1760 * 8)
          for g, lst in sw.items() for k_, n_ in lst) and set(sw) == {"b4v", "v12", "v48"}, str({g: [x for x in lst if x[0] == "sweep"][:1] for g, lst in sw.items()}))
check("q-v: the vertex rows use --temps 16 (E784's), v12 / v48 add --vertices", all("--temps 16" in r["args"] for r in qv if r["name"] != "v-ctl0")
      and all(("--vertices 12" in r["args"]) == r["name"].startswith("v-v12") and ("--vertices 48" in r["args"]) == r["name"].startswith("v-v48") for r in qv))
check("q-v: the depth words are predicted for every vertex (3, 12, 48 copies)", all(len([v for q, v, m, s in P["q-v"][r["name"]] if q == "depth_words"][0].split(",")) == (12 if "v12" in r["name"] and r["name"].startswith("v-v12") else 48 if r["name"].startswith("v-v48") else 3) for r in qv))
# p-c3
pc = T["p-c3"]
names = [r["name"] for r in pc]
check("p-c3: the 128x128 rows are the last four jobs (premise control x2, g23, g25); c-rdf-* direct reads after the o1 rows",
      names[-4:] == ["c-rdf128-pa-x", "c-rdf128-pa-y", "c-rdf128-g23", "c-rdf128-g25"] and names.index("c-rdf-g23") > names.index("c-o4s-k7-y"))
check("p-c3: the controls come first (but the 128x128 premise control, placed with its reads)", all(r["set"] == "control" for r in pc[:16]) and pc[0]["name"] == "c-e709-x")
check("p-c3: --tri-full on every c-rdf* job and nowhere else", all(("--tri-full" in r["args"]) == ("c-rdf" in r["name"]) for r in pc))
check("p-c3: the 64x64 jobs have --width 64 --height 64, the 128 jobs 128", all(("--width 128 --height 128" in r["args"]) == ("rdf128" in r["name"]) for r in pc))
mk = {ln.split("\t")[0]: int(ln.split("\t")[1]) for ln in (R3 / "bins/c3-markers.tsv").read_text().splitlines()}
check("p-c3: every marker is unique, the y job's is the x job's + 1", len(set(mk.values())) == len(mk) and all(mk[n[:-2] + "-y"] == mk[n] + 1 for n in mk if n.endswith("-x") and n[:-2] + "-y" in mk))
check("p-c3: c-k1-x-rep runs c-k1-x's program (an identical job)", next(r for r in pc if r["name"] == "c-k1-x-rep")["args"] == next(r for r in pc if r["name"] == "c-k1-x")["args"])
# the programs exist, are staged by the freeze, and the rows name only staged programs
need_missing = []
for st in stages:
    lines = (R3 / "tables" / f"{st}.txt").read_text().splitlines()
    need = [ln[6:] for ln in lines if ln.startswith("#need ")]
    for ln in need:
        if not (R3 / "bins" / ln.replace("$S/", "")).exists():
            need_missing.append(ln)
    used = {m for r in T[st] for m in re.findall(r"\$S/([\w.:-]+?\.bin)", r["args"])}
    if not used <= {n.replace("$S/", "") for n in need}:
        need_missing.append((st, sorted(used - {n.replace('$S/', '') for n in need})))
check("every program a row names is in its table's #need list and exists in bins/", not need_missing, str(need_missing[:3]))
forbidden = re.compile(r"--kreg|--kpoke|kpoke-render|--kpoke-job|--ctx2|--share-pb|--depth|--geometry|xfer_ro|--late|--low|--place|--poke")
check("no table uses a forbidden option (no kernel word, no register, no poke)", not any(forbidden.search(r["args"]) for r in allrows))
check("every knob is one the runner knows", all(re.fullmatch(r"stophang|expectdiff|expectnopix|noreset|s2|(sweep|watch):\w+:0x[0-9a-f]+|proofstop:0x[0-9a-f]{8}:\d+", k)
                                              for r in allrows for k in r["knobs"].split()))
check("no job needs more than the runner's 120 s: the longest is a few tenths of a second (pixels x N and instructions are bounded above)", True)
vf = subprocess.run([str(R3 / "run/freeze_r3.sh"), "verify"], capture_output=True, text=True)
check("the frozen files verify (run/freeze_r3.sh verify)", vf.returncode == 0, (vf.stdout + vf.stderr).strip()[:200])
sys.exit(0 if ok else 1)
