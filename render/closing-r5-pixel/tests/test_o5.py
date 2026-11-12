#!/usr/bin/env python3
"""Stage p5-o4 offline tests: the table (58 jobs: 8 controls, 16 walk, 8 independent, 24 predicate, 2 replicates), the frozen
predictions against the plan's tables, every staged program run in sgx-sim (the premise: each program's eight output words are the
table's, marker and tags included; the predicate programs at lane 0 and at the lane k), the reused programs byte for byte, and the
scorer on mock worlds built from a real R3 image: each of the nine models x {gated, ignored} is named with its predicate gating, a
tenth model reads "family refuted", c-all4 reading 5:0 voids the stage (the bridge gate still passes), a void job, a replicate that
differs, a failing bridge control (c-v-a4).  Prints ok / FAIL; exit 1 on any FAIL.   PY tests/test_o5.py"""
import collections
import gzip
import pathlib
import re
import sys
import tempfile

sys.dont_write_bytecode = True
R5 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R5 / "gen"), str(R5 / "score"), str(R5 / "tests")]
(R5 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R5 / "debug/tmp")
import fake_o4 as F  # noqa: E402
import o4world as WD  # noqa: E402
import o5model as M  # noqa: E402
import r4lib as L  # noqa: E402
import r5_o4  # noqa: E402
import score_o5 as S  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


rows = [dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5)))
        for ln in (R5 / "tables/p5-o4.txt").read_text().splitlines() if ln and not ln.startswith("#")]
preds = L.load_preds(stage="p5-o4")
names = [r["name"] for r in rows]
check("58 jobs", len(rows) == 58, str(len(rows)))
check("sets: 8 control, 48 heldout, 2 replicate", dict(collections.Counter(r["set"] for r in rows)) == {"control": 8, "heldout": 48, "replicate": 2})
order = [n.rsplit("-", 1)[0] for n in names[:-2:2]]
check("order: controls, walk w-0..w-7, z-o3 l-o4 l-o6 n-o4, P4 then P3 (pa k0 k3 k7, ps k0 k3 k7), the replicate of w-3",
      order == ["c-e709", "c-u", "c-all4", "c-v-a4"] + [f"w-{j}" for j in range(8)] + ["z-o3", "l-o4", "l-o6", "n-o4"]
      + [f"{p}-{o}-k{k}" for p in ("p4", "p3") for o in ("pa", "ps") for k in (0, 3, 7)] and names[-2:] == ["w-3-x-rep", "w-3-y-rep"], str(order))
check("every row: knobs `stophang s2`, no regtimeline", all(r["knobs"] == "stophang s2" and r["rt"] == "-" for r in rows))
mk = {n: int(v[0][0], 16) for n, q in preds.items() for v in [q.get("marker")] if v}
new = [m for n, m in mk.items() if not n.startswith(("c-u", "c-v-a4", "w-3-x-rep"))]
check("markers: R4's for c-u (0x105) and c-v-a4 (0x109), new ones 0x141.. unique and two apart, below 0x200",
      mk["c-u-x"] == 0x105 and mk["c-v-a4-x"] == 0x109 and len(set(new)) == len(new) == 25
      and all(b - a >= 2 for a, b in zip(sorted(new), sorted(new)[1:])) and max(new) < 0x200 and min(new) > 0x140, f"{len(new)}")
# ---------------------------------------------------------------- the frozen predictions against the plan's tables (2.1, 2.2)
plan_walk = {"OR(o0,o3)": "3 2 2 3 2 2 2 2", "AND(o4,o6)": "2 2 2 2 0 2 0 2", "XOR(o0,o2,o6)": "1 2 1 2 2 2 1 2",
             "XOR(o3,o5,o6)": "2 2 2 1 2 1 1 2"}
for i, j in ((0, 0), (2, 2), (3, 3), (5, 5), (6, 6)):
    plan_walk[f"MUX(o4;o{i})"] = " ".join("1" if x == j else "2" for x in range(8))
got = {m: " ".join(preds[f"w-{j}-x"]["o4_word"][M.MODELS.index(m)][0].split(":")[1] for j in range(8)) for m in M.MODELS}
check("walk predictions = the plan's table 2.1 (bits 5:4 at the tag-5 words, nine different vectors)", got == plan_walk and len(set(got.values())) == 9, str(got))
plan_ind = {"z-o3": ["d1", "5:0", "5:0", "d1"] + ["5:0"] * 5, "l-o4": ["5:0", "4:0", "5:0", "5:0"] + ["4:0"] * 5,
            "l-o6": ["5:0", "d1", "d1", "d1"] + ["5:0"] * 5, "n-o4": ["5:0", "nofrozen", "5:0", "5:0"] + ["nofrozen"] * 5}
check("independent rows = the plan's table 2.2", all([v for v, m, s in preds[f"{c}-x"]["o4_word"]] == plan_ind[c] for c in plan_ind))
check("c-all4: every model reads 5:1", {v for v, m, s in preds["c-all4-x"]["o4_word"]} == {"5:1"})
p4g = {c: preds[f"p4-{c}-x"]["o4_word"] for c in ("pa-k0", "pa-k3", "ps-k3")}
check("P4 for AND(o4,o6): gated k0 5:0, k3 4:0; ignored pa 4:0 (the !p1 write last), ps 5:0",
      dict((m, v) for v, m, s in p4g["pa-k0"])["AND(o4,o6)+gated"] == "5:0" and dict((m, v) for v, m, s in p4g["pa-k3"])["AND(o4,o6)+gated"] == "4:0"
      and dict((m, v) for v, m, s in p4g["pa-k0"])["AND(o4,o6)+ignored"] == "4:0" and dict((m, v) for v, m, s in p4g["ps-k3"])["AND(o4,o6)+ignored"] == "5:0")
p3 = dict((m, v) for v, m, s in preds["p3-pa-k3-x"]["o4_word"])
check("P3 for OR(o0,o3): gated k3 5:1 (o3 = tag 4 with bit 4), ignored pa 5:1; P3 cannot separate gating for AND(o4,o6) (5:0 both)",
      p3["OR(o0,o3)+gated"] == "5:1" and p3["OR(o0,o3)+ignored"] == "5:1" and p3["AND(o4,o6)+gated"] == p3["AND(o4,o6)+ignored"] == "5:0")
# ---------------------------------------------------------------- every staged program in sgx-sim (the premise of the table)
W6 = {}
for ln in (R5 / "bins/p5o4-words.tsv").read_text().splitlines():
    n, ws, pr = ln.split("\t")
    W6[n] = ([None if x == "-" else int(x, 16) for x in ws.split(",")], pr)
bad = []
for r in rows:
    n = r["name"]
    binf = R5 / "bins" / (re.search(r'"\$S/([\w-]+\.bin)"$', r["args"])[1])
    if n.endswith("-rep") or n.startswith(("c-e709", "c-u", "c-v-a4")):
        continue
    m = mk[n] if n.endswith("-x") else mk[n[:-2] + "-x"] + 1
    for lane, xy in ((0, (0, 0)), (3, (1, 1))):
        st, ax, w = F.sim_words(binf, xy)
        ws, pr = W6[n]
        exp = {j: (None if ws[j] is None else (m << 6) | ws[j]) for j in range(8)}
        if pr != "-":
            cfg = n.rsplit("-", 1)[0]
            ps, od, kk = cfg.split("-")
            j, wp1, wnp1 = M.PSETS[ps]
            exp[j] = (m << 6) | (wp1 if lane == int(kk[1:]) else wnp1)
        if not st.startswith("ended") or ax != n[-1] or w != exp:
            bad.append((n, lane, st, ax, {j: hex(v) if v is not None else None for j, v in w.items()}))
check("every new program (48) ends in sgx-sim with its eight output words = marker << 6 | the table's word, the right axis; "
      "predicate programs: the p1 word at the lane k, the !p1 word elsewhere (lanes 0 and 3)", not bad, str(bad[:2]))
R4B = r5_o4.R4PIX / "bins"
check("the reused programs are R4's published bytes (c-u, c-v-a4, E709's)",
      all((R5 / "bins" / f).read_bytes() == (R4B / f).read_bytes() for f in ("r4o-u-x.bin", "r4o-u-y.bin", "r4o-v-a4-x.bin", "r4o-v-a4-y.bin",
                                                                           "r4o-e709-x.bin", "r4o-e709-y.bin")))
st, ax, w = F.sim_words(R5 / "bins/r4o-e709-x.bin")
check("E709's program at the lane-0 instance writes no o4 (p1 = lane == 3): noted for the lead (the o4-reading models predict no "
      "tag-5 word there unless the predicate is ignored or o4 keeps a value)", w[4] is None and w[0] == 0x0cf1)
# ---------------------------------------------------------------- mock worlds
HEAD = "name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tnote"
SIMW = {}


def words16(n, gating):
    """The output words of job n's landing instance in a world with this gating (sim for every program but the predicate ones, which
    the sim can only run gated)."""
    binf = R5 / "bins" / (re.search(r'"\$S/([\w-]+\.bin)"$', next(r for r in rows if r["name"] == n)["args"])[1])
    if binf not in SIMW:
        SIMW[binf] = F.instance_words(binf)[2]
    w = dict(SIMW[binf])
    cfg = n.rsplit("-", 1)[0]
    if cfg.startswith(("p4-", "p3-")):
        ps, od, kk = cfg.split("-")
        m = w[0] >> 6
        w = {j: (m << 6) | v for j, v in M.pred_words(ps, od, int(kk[1:]), gating).items()}
    return w


def mk_world(model, gating="gated", void=(), override=None, rep_model=None):
    d = pathlib.Path(tempfile.mkdtemp(prefix="o5w-"))
    cases = [HEAD]
    for n in names:
        if n in void:
            cases.append("\t".join([n, "p5-o4", "x", "safe", "x", "x", "x", "124", "fail", "-"]))
            continue
        base = n[:-4] if n.endswith("-rep") else n
        mdl = rep_model if (rep_model and n.endswith("-rep")) else model
        w = words16(base, gating)
        if override and base.rsplit("-", 1)[0] in override:
            w = override[base.rsplit("-", 1)[0]](w)
        g = WD.image(base[-1], w, mdl)
        cases.append("\t".join([n, "p5-o4", "x", "safe", "x", "x", "x", "0", "ok", "-"]))
        with gzip.open(d / f"{n}.txt.gz", "wb") as f:
            f.write(WD.text(n, g).encode())
    (d / "cases.tsv").write_text("\n".join(cases) + "\n")
    return L.Kept(d)


fails = []
for m in M.MODELS:
    for g in ("gated", "ignored"):
        t, r = S.score(mk_world(m, g), preds)
        want_p = {}
        if m in M.READS_O4:
            want_p["p4"] = [g]
        if m in M.READS_O3:
            want_p["p3"] = [x for x in ("gated", "ignored") if all(
                M.predict(m, M.pred_words("p3", o, k, x)) == M.predict(m, M.pred_words("p3", o, k, g)) for o in M.ORDERS for k in M.PRED_K)]
        if not r["answered"] or r["model"] != m or r["pred"] != want_p or not r["gate"].ok:
            fails.append((m, g, r["model"], r["pred"], want_p, t.splitlines()[-1][:100]))
check("mock worlds: each of the nine models x {gated, ignored} (18): the tag-5 word is named, the predicate set it reads names the "
      "world's gating, the other set is cannot tell by design", not fails, str(fails[:2]))
t, r = S.score(mk_world("XOR(o1,o2,o3)"), preds)
check("a tenth model XOR(o1,o2,o3) (passes every control; walk 1 1 2 2 2 2 2 2... none of the nine): family refuted, vector recorded", "family refuted, vector recorded" in t.splitlines()[-1]
      and not r["answered"], t.splitlines()[-1][:120])
t, r = S.score(mk_world("none"), preds)
check("a world with no tag-5 word: not answered (c-all4 and the walk read none)", not r["answered"] and "cannot tell" in t.splitlines()[-1], t.splitlines()[-1][:120])
t, r = S.score(mk_world("OR(o0,o3)", override={"c-all4": lambda w: {j: (None if v is None else v & ~0x30) for j, v in w.items()}}), preds)
check("c-all4 reading 5:0 voids the stage (cannot tell) while the bridge gate (c-e709, c-u, c-v-a4) still passes",
      not r["answered"] and "c-all4" in t.splitlines()[-1] and r["gate"].ok, t.splitlines()[-1][:120])
t, r = S.score(mk_world("OR(o0,o3)", override={"c-v-a4": lambda w: {**w, 3: w[3] | 0x10}}), preds)
check("c-v-a4 reading 5:1 (E838 not reproduced) fails the bridge gate: the driver stops the session", not r["gate"].ok and r["gate"].failed, str(r["gate"]))
t, r = S.score(mk_world("OR(o0,o3)", void=("w-5-y",)), preds)
check("a void walk job: cannot tell (never a pass)", not r["answered"] and "w-5" in t.splitlines()[-1], t.splitlines()[-1][:120])
t, r = S.score(mk_world("OR(o0,o3)", rep_model="XOR(o3,o5,o6)"), preds)
check("a replicate of w-3 that reads another class: cannot tell", not r["answered"] and "replicate" in t.splitlines()[-1], t.splitlines()[-1][:120])
t, r = S.score(mk_world("OR(o0,o3)", override={"w-0": lambda w: {**w, 0: w[0] & ~0x10}}), preds)
check("the walk's positive control (w-0's own tag-1 words without bit 4) shuts the walk", not r["answered"] and "positive" in t.splitlines()[-1], t.splitlines()[-1][:120])
sys.exit(0 if ok else 1)
