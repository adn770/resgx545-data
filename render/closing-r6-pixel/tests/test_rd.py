#!/usr/bin/env python3
"""Stages p6-rd, p6-l3 and p6-s offline tests (plan closing6/pixel/exp-pixel-r6.md sections 2 and 5).
  - the frozen predictions against the plan's tables (2.1 models over rd-1..rd-7, 2.4 lanes of gated / ignored / never, 2.2 controls,
    2.5 H-Y1 / H-Y2 / H-YN, 2.6 H-OR / H-OWN4);
  - every new program read back from its BYTES through the simulator's decode (`simcheck --list`) and checked against its plan row,
    written out here: rd-j ends `mov.skipinv r10, oJ; mov.skipinv.end o0, r10`, oJ's word with bit 4 and every other with bit 5;
    n-rd-j never writes oJ; x-rd-4/5 write tag 13/14; prd-j-k sets p1 = (g25 == k) after o0 and writes oJ unpredicated (bits 0) then
    under p1 (bit 4); c-ow, c-rd-0, c-prd-0 as 2.2; no task ends on a predicated instruction; and run in sgx-sim at the four lanes:
    rd-j's o0 is oJ's word, prd-j-k's lane k holds bit 4;
  - the scorers on mock worlds (M-P), each world built by running the frozen tables' own commands through the argv-driven fake tool:
    H-STORE, H-FOUR, H-O0, H-MOD4 and a fifth vector are each named; gated, ignored and never each named; a dead c-rd-0 and a c-ow
    where the first write wins void the stage; R4's o2 slip (c-u on the default triangle) fails the bridge; L3's lane worlds give
    H-Y1, H-Y2 and a control failure; S's worlds give H-OR, H-OWN4 and a void set.
Prints ok / FAIL; exit 1 on any FAIL.   PY tests/test_rd.py"""
import collections
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
R6 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R6 / "gen"), str(R6 / "score"), str(R6 / "tests")]
import mockstage as MS  # noqa: E402
import r4lib as L  # noqa: E402
import score_rd as S  # noqa: E402

ok = True
H = R6 / "debug/target/debug/simcheck"


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


P = {st: L.load_preds(stage=st) for st in ("p6-rd", "p6-l3", "p6-s")}
pr = P["p6-rd"]
# ---------------------------------------------------------------- frozen predictions vs the plan
plan_vec = {"H-STORE": "S S S S S S S", "H-FOUR": "S S S !S !S !S !S", "H-O0": "A0 A0 A0 A0 A0 A0 A0", "H-MOD4": "S S S A0 A4 A4 A4"}
got = {m: " ".join({mm: v for v, mm, s in pr[f"rd-{j}-x"]["class"]}[m] for j in range(1, 8)) for m in plan_vec}
check("rd predictions = plan 2.1 (H-MOD4's A4 at j = 4 is o0's word: A0)", got == plan_vec, str(got))
lab = {j: pr[f"rd-{j}-x"]["labels"][0][0] for j in range(1, 8)}
check("rd-j labels: S = tag j+1 with bits 1, A0 = 1:2, A4 = tag j-3 with bits 2 (j >= 5)",
      lab[1] == "S=2:1 A0=1:2" and lab[4] == "S=5:1 A0=1:2" and lab[5] == "S=6:1 A0=1:2 A4=2:2" and lab[7] == "S=8:1 A0=1:2 A4=4:2", str(lab))
check("x-rd-4 / x-rd-5: S is tag 13 / 14 with bits 1", pr["x-rd-4-x"]["labels"][0][0].startswith("S=13:1") and pr["x-rd-5-x"]["labels"][0][0].startswith("S=14:1"))
pl = {(j, k): {m: v for v, m, s in pr[f"prd-{j}-k{k}-x"]["lanes"]} for j in (3, 4) for k in (0, 1, 2, 3, 7)}
check("prd lanes = plan 2.4: gated bit 4 at lane k only (none at k = 7), ignored bit 4 everywhere, never bits 0 everywhere",
      pl[(4, 1)] == {"gated": "5:0,5:1,5:0,5:0", "ignored": "5:1,5:1,5:1,5:1", "never": "5:0,5:0,5:0,5:0"}
      and pl[(3, 7)]["gated"] == "4:0,4:0,4:0,4:0" and pl[(3, 0)]["gated"] == "4:1,4:0,4:0,4:0", str(pl[(4, 1)]))
check("c-prd-0: k = 1 W_1 on lane 1 (odd x, even y), k = 7 W_0 everywhere", pr["c-prd-0-k1-x"]["lanes"][0][0] == "1:2,1:1,1:2,1:2"
      and pr["c-prd-0-k7-x"]["lanes"][0][0] == "1:2,1:2,1:2,1:2")
ps = P["p6-s"]
check("p6-s: H-OR 3 2 2 3 2 2 2 2 and tag 5 at s-n4; H-OWN4 2 2 2 2 1 2 2 2 and none at s-n4 (plan 2.6)",
      " ".join({m: v for v, m, s in ps[f"s-{j}-x"]["o4_word"]}["H-OR"][2:] for j in range(8)) == "3 2 2 3 2 2 2 2"
      and " ".join({m: v for v, m, s in ps[f"s-{j}-x"]["o4_word"]}["H-OWN4"][2:] for j in range(8)) == "2 2 2 2 1 2 2 2"
      and {m: v for v, m, s in ps["s-n4-x"]["o4_word"]} == {"H-OR": "5:0", "H-OWN4": "none"})
p3 = P["p6-l3"]
check("p6-l3: controls as R5 (k0 x 5:0 y 5:1, k3 5:1 5:1); H-Y1 5:0/5:1, H-Y2 5:1/5:0, H-YN 5:1/5:1 at k = 1/2 (plan 2.5)",
      (p3["p3-pa-k0-x"]["job_x"][0][0], p3["p3-pa-k0-x"]["job_y"][0][0], p3["p3-pa-k3-x"]["job_x"][0][0], p3["p3-pa-k3-x"]["job_y"][0][0]) == ("5:0", "5:1", "5:1", "5:1")
      and {m: v for v, m, s in p3["p3-pa-k1-x"]["job_y"]} == {"H-Y1": "5:0", "H-Y2": "5:1", "H-YN": "5:1"}
      and {m: v for v, m, s in p3["p3-pa-k2-x"]["job_y"]} == {"H-Y1": "5:1", "H-Y2": "5:0", "H-YN": "5:1"})


# ---------------------------------------------------------------- programs from their bytes
def listing(prog):
    o = subprocess.run([str(H), str(R6 / "bins" / f"{prog}.bin"), "0x20", "--list", "--tri-pixel", "0,0"], capture_output=True, text=True).stdout
    return [ln.split(" ", 2)[2] for ln in o.splitlines() if ln.startswith("insn ")]


def sim(prog, lane):
    x, y = lane & 1, lane >> 1
    o = subprocess.run([str(H), str(R6 / "bins" / f"{prog}.bin"), "0x20", "--tri-pixel", f"{x},{y}", "--set", "pa0=0x11110000",
                        "--set", "pa1=0x22220000"], capture_output=True, text=True).stdout
    return o.splitlines()[0], {int(m[1]): int(m[2], 16) for ln in o.splitlines() if (m := re.fullmatch(r"o(\d+) = (0x[0-9a-f]+)", ln))}


WR = re.compile(r"^(?:(!?p1) )?or\.skipinv(\.end)? o(\d), pa([01]), #0x([0-9A-F]+)$")


def writes(ins):
    return [(m[1], int(m[3]), int(m[5], 16) & 0x3f, int(m[5], 16) >> 6, m[4]) for t in ins if (m := WR.match(t))]


mk = {a: int(b) for a, b in (ln.split("\t") for ln in (R6 / "bins/p6-markers.tsv").read_text().splitlines())}
TAG = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8}
bad = []
for ax in "xy":
    for j in range(1, 8):
        ins, w = listing(f"r6o-rd-{j}-{ax}"), writes(listing(f"r6o-rd-{j}-{ax}"))
        fin = {o: v for _, o, v, _, _ in w}
        if ins[-2:] != [f"mov.skipinv r10, o{j}", "mov.skipinv.end o0, r10"] or fin != {o: TAG[o] | (0x10 if o == j else 0x20) for o in range(8)} \
                or {m for *_, m, _ in w} != {mk[f"rd-{j}-{ax}"]} or {a for *_, a in w} != {"0" if ax == "x" else "1"}:
            bad.append(f"rd-{j}-{ax}")
        st, o = sim(f"r6o-rd-{j}-{ax}", 0)
        if not st.startswith("ended") or o[0] != o[j]:
            bad.append(f"rd-{j}-{ax} sim")
    for j in (1, 4):
        w = writes(listing(f"r6o-n-rd-{j}-{ax}"))
        if any(o == j for _, o, *_ in w) or listing(f"r6o-n-rd-{j}-{ax}")[-2] != f"mov.skipinv r10, o{j}":
            bad.append(f"n-rd-{j}-{ax}")
    for j in (4, 5):
        fin = {o: v for _, o, v, _, _ in writes(listing(f"r6o-x-rd-{j}-{ax}"))}
        if fin[j] != (9 + j) | 0x10:
            bad.append(f"x-rd-{j}-{ax}")
    for j in (3, 4):
        for k in (0, 1, 2, 3, 7):
            ins = listing(f"r6o-prd-{j}-k{k}-{ax}")
            w = writes(ins)
            oj = [(p, v) for p, o, v, _, _ in w if o == j]
            if ins[2] != f"xor.testtaz.chan0 !c0, p1, g25, #{k}" or oj != [(None, TAG[j]), ("p1", TAG[j] | 0x10)] \
                    or ins[-2:] != [f"mov.skipinv r10, o{j}", "mov.skipinv.end o0, r10"]:
                bad.append(f"prd-{j}-k{k}-{ax}")
            for lane in range(4):
                st, o = sim(f"r6o-prd-{j}-k{k}-{ax}", lane)
                if not st.startswith("ended") or ((o[0] >> 4) & 3) != (1 if lane == k else 0) or o[0] != o[j]:
                    bad.append(f"prd-{j}-k{k}-{ax} lane {lane}")
    ins = listing(f"r6o-c-ow-{ax}")
    if [(p, o, v) for p, o, v, _, _ in writes(ins)] != [(None, 0, 0x21), (None, 0, 0x11)] or not ins[-1].startswith("or.skipinv.end o0"):
        bad.append(f"c-ow-{ax}")
    ins = listing(f"r6o-c-rd-0-{ax}")
    if ins[1:] != [ins[1], "mov.skipinv r10, o0", ins[3], "mov.skipinv.end o0, r10"] or [v for _, _, v, _, _ in writes(ins)] != [0x21, 0x31]:
        bad.append(f"c-rd-0-{ax}")
    if sim(f"r6o-c-rd-0-{ax}", 0)[1][0] & 0x3f != 0x21:
        bad.append(f"c-rd-0-{ax} sim")
    for k in (1, 7):
        ins = listing(f"r6o-c-prd-0-k{k}-{ax}")
        if [(p, o, v) for p, o, v, _, _ in writes(ins)] != [(None, 0, 0x21), ("p1", 0, 0x11), (None, 7, 0x08)] or ins[2] != f"xor.testtaz.chan0 !c0, p1, g25, #{k}":
            bad.append(f"c-prd-0-k{k}-{ax}")
        for lane in range(4):
            if (sim(f"r6o-c-prd-0-k{k}-{ax}", lane)[1][0] >> 4) & 3 != (1 if lane == k else 2):
                bad.append(f"c-prd-0-k{k}-{ax} lane {lane}")
check("every new p6-rd program, read from its bytes, is its plan row (2.1 to 2.4) and runs in sgx-sim as the row says at the four lanes",
      not bad, str(bad[:6]))
ends = [p.stem for p in (R6 / "bins").glob("r6o-*.bin") if re.match(r"^!?p\d ", listing(p.stem)[-1])]
check("no program of the session ends on a predicated instruction (c-prd-0 ends with an unpredicated o7 write)", not ends, str(ends))

# ---------------------------------------------------------------- mock worlds (the tables' own commands through the fake tool)


def verdict(stage, env):
    k = L.Kept(MS.build(stage, env))
    fn = {"p6-rd": S.score_rd, "p6-l3": S.score_l3, "p6-s": S.score_s}[stage]
    text, res = fn(k, P[stage])
    return text.splitlines()[-1], res


for env, want in (({}, ["rd vector S S S S S S S: H-STORE", "o3: the predicate gates the o3 write", "o4: the predicate gates the o4 write"]),
                  ({"FAKE_RD_MODEL": "H-FOUR"}, ["S S S O:9.0 O:9.0 O:9.0 O:9.0: H-FOUR", "o3: the predicate gates", "o4: cannot tell by design"]),
                  ({"FAKE_RD_MODEL": "H-O0"}, ["A0 A0 A0 A0 A0 A0 A0: H-O0", "o3: cannot tell by design", "o4: cannot tell by design"]),
                  ({"FAKE_RD_MODEL": "H-MOD4"}, ["S S S A0 A4 A4 A4: H-MOD4 (and so H-FOUR)", "o3: the predicate gates"]),
                  ({"FAKE_RD_MODEL": "FIFTH"}, ["A0 A0 A0 S S S S: none of the four"]),
                  ({"FAKE_PRED": "ignored"}, ["H-STORE", "o3: survivors ['ignored']", "o4: survivors ['ignored']"]),
                  ({"FAKE_PRED": "never"}, ["H-STORE", "o3: survivors ['never']", "o4: survivors ['never']"]),
                  ({"FAKE_RD_MODEL": "DEAD"}, ["cannot tell: ", "c-rd-0"]),
                  ({"FAKE_OW": "first"}, ["cannot tell: ", "c-ow"])):
    s, res = verdict("p6-rd", env)
    check(f"p6-rd world {env or 'H-STORE, gated'}: " + " | ".join(want), all(w in s for w in want), s[:220])
s, res = verdict("p6-rd", {})
check("  the H-STORE world: bridge gate PASS, replicate agrees, n-rd not S, x-rd S with the new tag, TRI >= 300",
      res["gate"].ok and res["replicate"] is True and all(res["independent"][c + ":state"] for c in ("n-rd-1", "n-rd-4", "x-rd-4", "x-rd-5"))
      and res["tri"] >= 300, f"{res['tri']} {res['independent']}")
s, res = verdict("p6-rd", {"FAKE_RD_MODEL": "DEAD"})
check("  a dead c-rd-0: the bridge gate does not pass (the driver stops, exit 42)", not res["gate"].ok)
s, res = verdict("p6-rd", {"FAKE_OW": "first"})
check("  a c-ow where the first write wins: the bridge gate FAILS", res["gate"].failed)
s, res = verdict("p6-rd", {"FAKE_O4_MODEL": "none"})
check("  a world without tag-5 words: G-o4 on c-e709 fails the bridge gate", res["gate"].failed and "G-o4" in " ".join(res["gate"].problems), s[:120])
# R4's o2 slip: c-u-x on the default triangle (the fake draws nothing readable) -> the bridge fails
rows = MS.rows("p6-rd")
for r in rows:
    if r["name"] == "c-u-x":
        slip = r["args"].replace(" --width 64 --height 64 --vtx-coords 2 --blk 4=0x00030001", "")
tmpt = R6 / "debug/tmp/o2slip"
tmpt.mkdir(parents=True, exist_ok=True)
(tmpt / "p6-rd.txt").write_text("\n".join("|".join([r["name"], r["set"], r["risk"], r["knobs"], r["rt"], slip if r["name"] == "c-u-x" else r["args"]])
                                          for r in rows) + "\n")
orig = MS.rows
MS.rows = lambda st: [dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5))) for ln in (tmpt / "p6-rd.txt").read_text().splitlines()]
MS._cache.clear()
s, res = verdict("p6-rd", {"_O2": "1"})
MS.rows = orig
check("R4's o2 slip by construction: c-u-x on the default triangle fails G-o1 in the argv-driven mock (the bridge gate stops)",
      not res["gate"].ok and any("G-o1" in p for p in res["gate"].problems), s[:120])
for env, want in (({"FAKE_Y_O3_LANE": "1"}, "SUMMARY: H-Y1; x jobs 5:1, 5:1"), ({"FAKE_Y_O3_LANE": "2"}, "SUMMARY: H-Y2; x jobs 5:1, 5:1"),
                  ({}, "SUMMARY: cannot tell: controls")):
    s, res = verdict("p6-l3", env)
    check(f"p6-l3 world {env or 'lane 0 (R5 mock)'}: {want}", s.startswith(want), s)
for env, want in (({}, "SUMMARY: H-OR: 5:3 5:2 5:2 5:3 5:2 5:2 5:2 5:2 5:0; restore check (r-u G-o1) PASS"),
                  ({"FAKE_S_MODEL": "MUX(o4;o4)"}, "SUMMARY: H-OWN4: 5:2 5:2 5:2 5:2 5:1 5:2 5:2 5:2 none"),
                  ({"FAKE_S_MODEL": "plain"}, "SUMMARY: set void: c-s-all4 does not show E406's pattern")):
    s, res = verdict("p6-s", env)
    check(f"p6-s world {env or 'H-OR'}: {want}", s.startswith(want), s)
sys.exit(0 if ok else 1)
