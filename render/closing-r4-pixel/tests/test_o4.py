#!/usr/bin/env python3
"""Stage p4-o4 offline tests: the table (36 jobs, sets, order), frozen predictions, programs through usse-asm and sgx-sim, the model
family by hand, the scorer on real records (G-o4 control on R3's p-c3 and R1 / S1b old-layout words) and on synthetic worlds for each
of the 12 models x gating, a failed control, a void job, a mixed class, the bit-4 pairs reading one class in both orders.
Prints ok / FAIL; exit 1 on any FAIL.   PY tests/test_o4.py"""
import collections
import gzip
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R4 / "gen"), str(R4 / "score")]
(R4 / "debug/tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(R4 / "debug/tmp")
import o4model as M  # noqa: E402
import r4_o4  # noqa: E402
import r4lib as L  # noqa: E402
import score_o4 as S  # noqa: E402
import r4common as K  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


# ---------------------------------------------------------------- the table
rows = [dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5)))
        for ln in (R4 / "tables/p4-o4.txt").read_text().splitlines() if ln and not ln.startswith("#")]
preds = L.load_preds(stage="p4-o4")
names = [r["name"] for r in rows]
check("36 jobs", len(rows) == 36, str(len(rows)))
cnt = collections.Counter(r["set"] for r in rows)
check("sets: 8 control, 26 heldout (14 value + 12 predicate), 2 replicate", dict(cnt) == {"control": 8, "heldout": 26, "replicate": 2}, str(dict(cnt)))
check("order: 8 controls, 14 value jobs, 12 predicate jobs, 2 replicates",
      [n.split("-")[1] for n in names[:8]] == ["e709"] * 2 + ["o4"] * 2 + ["o4s"] * 2 + ["u"] * 2 and
      all(n.startswith("c-v-") for n in names[8:22]) and all(re.match(r"c-p[as]-k[037]-", n) for n in names[22:34]) and names[34:] == ["c-o4-u-x-rep", "c-o4-u-y-rep"], str(names))
check("every x job and the replicate x job has frozen predictions (the y job of a pair is read with its x job)", all(n in preds for n in names if n.endswith("-x") or n.endswith("-x-rep")))
check("every non-e709 non-replicate job has a marker prediction on its x job",
      all("marker" in preds[n] for n in names if n.endswith("-x") and "e709" not in n))
check("value rows carry 12 model predictions, predicate rows 24", all(len(preds[f"c-v-{c}-x"]["o4_class"]) == 12 for c in M.VALUE)
      and all(len(preds[f"c-{c}-x"]["o4_class"]) == 24 for c in S.PRED_CFGS))
check("knobs stophang, no register or debugfs option", all(r["knobs"] == "stophang" and r["rt"] == "-" for r in rows))
mks = sorted(int(preds[n]["marker"][0][0], 16) for n in names if "marker" in preds[n] and "rep" not in n)
check("16 markers, unique, x job m and y job m + 1 (two apart), below 0x200",
      len(set(mks)) == 16 and all(b - a >= 2 for a, b in zip(mks, mks[1:])) and
      all(0x100 < int(preds[n]["marker"][0][0], 16) < 0x200 for n in names if "marker" in preds[n]))
check("replicate uses c-o4-u's own program", rows[34]["args"] == rows[2]["args"] and rows[35]["args"] == rows[3]["args"])

# ---------------------------------------------------------------- programs in sgx-sim
HARNESS = R4 / "debug/target/debug/simcheck"
if not HARNESS.exists():
    env = dict(os.environ, CARGO_TARGET_DIR=str(R4 / "debug/target"))
    r = subprocess.run(["cargo", "build", "--offline", "--manifest-path", str(R4 / "debug/simcheck/Cargo.toml")], env=env, capture_output=True, text=True)
    check("the scratch harness builds offline", r.returncode == 0, r.stderr[-200:])


def sim(text, name, extra):
    d = pathlib.Path(tempfile.mkdtemp(prefix="o4-"))
    f = d / (name + ".bin")
    K.probe._assemble(text, f)
    r = subprocess.run([str(HARNESS), str(f), "0x20", "--pixel", "--set", "pa0=0x3f000000", "--set", "pa1=0x3e800000"] + extra, capture_output=True, text=True)
    lines = r.stdout.splitlines()
    return lines[0], {m[1]: int(m[2], 16) for ln in lines if (m := re.fullmatch(r"(o\d+) = (0x[0-9a-f]+)", ln))}


bad = []
m0 = 0x123
base = m0 * 64
cases = [("u", dict()), ("o4-u", dict()), ("o4s-u", dict())] + [("value", dict(writes=w)) for w in M.VALUE.values()]
want = {"u": [M.A], "o4-u": [M.A3, M.A], "o4s-u": [M.A, M.A3]}
for kind, kw in cases:
    for ax, pa in (("x", 0x3f000000), ("y", 0x3e800000)):
        st, o = sim(r4_o4.program(kind, ax, m0, **kw), f"{kind}-{ax}", [])
        ws = kw.get("writes") or want[kind]
        exp = pa | (base + ws[-1])
        if not st.startswith("ended") or o.get("o4") != exp or o.get("o0") != (pa | base + 1) or o.get("o1") != (pa | base + 2):
            bad.append((kind, ax, st, o.get("o4"), hex(exp)))
check("unpredicated programs end in sgx-sim: o0, o1 (tag 2 last), o4 = the last write (the sim does not model the hardware's landing)", not bad, str(bad[:3]))
bad = []
for order in ("pa", "ps"):
    for k in M.PRED_K:
        txt = r4_o4.program("pred", "x", m0, k=k, order=order).replace("g25", "pa2")
        for pa2, p1 in ((k, True), (k + 1, False)):
            st, o = sim(txt, f"pred-{order}-{k}", ["--set", f"pa2={pa2}"])
            exp = 0x3f000000 | (base + (M.A if p1 else M.A4))
            if not st.startswith("ended") or o.get("o4") != exp:
                bad.append((order, k, p1, st, o.get("o4"), hex(exp)))
check("predicate programs (g25 replaced by pa2 in the sim): p1 true leaves A, p1 false leaves A4, both orders, k = 0, 3, 7", not bad, str(bad[:3]))
check("the staged programs are the generator's (assembled once, 36 of them)", len(list((R4 / "bins").glob("r4o-*.bin"))) == 34)

# ---------------------------------------------------------------- the model family
ms = M.models()
check("12 models, the ones that fit E808", len(ms) == 12 and all(M.lands(b, r, [M.A3, M.A]) == "A" and M.lands(b, r, [M.A, M.A3]) == "A" for b, r in ms))
check("V3 with last, first or or is outside the family (E808 refutes it)", not any(m[0] == "V3" and m[1] in ("last", "first", "or") for m in ms))
by = {M.name(m): [M.value_pred(m, c) for c in M.VALUE] for m in ms}
check("hand-worked: V1/last", by["V1/last"] == ["A", "A4", "A4", "A", "A5", "A", "A4"], str(by["V1/last"]))
check("hand-worked: V2/first (A3 dropped; A3 then A4 leaves A4)", by["V2/first"] == ["none", "A4", "A", "A4", "A", "A5", "A4"])
check("hand-worked: V3/and (13 and 21 = 5) and V3/min (13 < 21)", by["V3/and"][6] == "A" and by["V3/min"][6] == "A3" and by["V3/and"][0] == "A3")
check("hand-worked: OR reads A4 in both orders of the bit-4 pair, AND reads A in both",
      by["V1/or"][2] == by["V1/or"][3] == "A4" and by["V1/and"][2] == by["V1/and"][3] == "A")
check("predicate rows: gated k = 0 reads A, k = 3 and 7 read A4; ignored follows the rule",
      all(M.pred_lands(m, "gated", o, 0) == "A" and M.pred_lands(m, "gated", o, 3) == "A4" and M.pred_lands(m, "gated", o, 7) == "A4"
          for m in ms for o in ("pa", "ps")) and M.pred_lands(("V1", "last"), "ignored", "pa", 0) == "A4"
      and M.pred_lands(("V1", "last"), "ignored", "ps", 0) == "A" and M.pred_lands(("V1", "first"), "ignored", "pa", 3) == "A")
vec = collections.defaultdict(list)
for m in ms:
    vec[tuple(by[M.name(m)] + [M.pred_lands(m, g, o, k) for g in ("gated", "ignored") for o in ("pa", "ps") for k in M.PRED_K])].append(M.name(m))
check("equivalent models: V1/and = V1/min and V2/and = V2/min are indistinguishable by design", any(set(v) == {"V1/and", "V1/min"} for v in vec.values())
      and any(set(v) == {"V2/and", "V2/min"} for v in vec.values()))

# ---------------------------------------------------------------- the scorer: real records
FX = R4 / "tests/fixtures/p4o4"
kr = L.Kept(FX)
grid = {n: S.read_grid(kr, n) for n in kr.names()}
check("real R3 p-c3 grids decode (8 of 8)", all(g is not None for g in grid.values()))
for c in ("c-e709", "c-o4-u", "c-o4s-u"):
    cx, cy = S.class_counts(grid[c + "-x"], False), S.class_counts(grid[c + "-y"], False)
    src, _ = S.decode_pairs(grid[c + "-x"], grid[c + "-y"], None, False)
    bad_par = sum(1 for s in src[5] if s[0] & 1 or s[1] & 1)
    okc, why = S.g_o4_control(cx, cy, len(src[5]), bad_par, cx.get("A3", 0))
    check(f"real R3 record {c}: G-o4 structural control passes (tag-only reading), class {S.read_class(cx, cy)}", okc and S.read_class(cx, cy) == "A", str(why or dict(cx)))
r1 = L.Kept(R4 / "tests/fixtures/r1-p-c2")
for c in ("c-e709", "c-o4-u"):
    gx, gy = S.read_grid(r1, c + "-x"), S.read_grid(r1, c + "-y")
    cx, cy = S.class_counts(gx, False), S.class_counts(gy, False)
    src, _ = S.decode_pairs(gx, gy, None, False)
    okc, why = S.g_o4_control(cx, cy, len(src[5]), sum(1 for s in src[5] if s[0] & 1 or s[1] & 1), cx.get("A3", 0))
    check(f"real R1 p-c2 record {c}: G-o4 passes", okc, str(why))
# the marker decode of the real c-u (old layout: marker << 4), proves decode_pairs's marker rule on a real image
srcu, mok = S.decode_pairs(grid["c-u-x"], grid["c-u-y"], None, False)
check("real c-u: >= 300 o1 sources, tag-2 fraction >= 0.98 (G-o1)", len(srcu[2]) + len(srcu[12]) >= 300 and len(srcu[2]) / (len(srcu[2]) + len(srcu[12])) >= 0.98)

# ---------------------------------------------------------------- synthetic worlds from the real records
HEAD = "name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tnote"
W = pathlib.Path(tempfile.mkdtemp(prefix="o4world-"))
LOW6 = {"A": M.A, "A4": M.A4, "A5": M.A5, "A3": M.A3}


def relayout(g, m, o4=None):
    """The template grid with the new layout: marker m, variant bits 0; the tag-5/13 words take the class(es) in o4
    (a label, 'none', or a list alternating)."""
    out, n5 = [], 0
    for r in g:
        row = []
        for v in r:
            if v == S.BG:
                row.append(v)
                continue
            tag = v & 15
            w = (v & 0xffff0000) | (m << 6) | tag
            if tag in S.O4_TAGS and o4 is not None:
                lab = o4[n5 % len(o4)] if isinstance(o4, list) else o4
                n5 += 1
                if lab == "none":
                    row.append(S.BG)
                    continue
                w = (v & 0xffff0000) | (m << 6) | LOW6[lab]
            row.append(w)
        out.append(row)
    return out


def txt(name, g):
    return "\n".join(f"probe {name}: row {y}: " + " ".join(f"{v:08x}" for v in r) for y, r in enumerate(g)) + "\n"


def mk_world(cls, void=(), unmarked=()):
    """cls: {cfg: label | 'none' | list} for the configurations with a marker; e709 is the real record."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="w-", dir=W))
    cases = [HEAD]
    files = {}
    files["c-e709-x"], files["c-e709-y"] = grid["c-e709-x"], grid["c-e709-y"]
    for cfg in ["o4-u", "o4s-u", "u"] + S.VALUE_CFGS + S.PRED_CFGS:
        mx = int(preds[f"c-{cfg}-x"]["marker"][0][0], 16)
        tpl = "c-u" if cfg == "u" else "c-o4-u"
        lab = cls.get(cfg, "A")
        mxx = mx + (7 if cfg in unmarked else 0)
        files[f"c-{cfg}-x"] = relayout(grid[tpl + "-x"], mxx, None if cfg == "u" else lab)
        files[f"c-{cfg}-y"] = relayout(grid[tpl + "-y"], mx + 1, None if cfg == "u" else lab)
    for n, g in files.items():
        if n in void:
            cases.append("\t".join([n, "p4-o4", "x", "safe", "x", "x", "x", "124", "fail", "-"]))
            continue
        cases.append("\t".join([n, "p4-o4", "x", "safe", "x", "x", "x", "0", "ok", "-"]))
        with gzip.open(d / f"{n}.txt.gz", "wb") as f:
            f.write(txt(n, g).encode())
    (d / "cases.tsv").write_text("\n".join(cases) + "\n")
    return L.Kept(d)


def model_world(m, g):
    cls = {c: M.value_pred(m, c.split("v-", 1)[1]) for c in S.VALUE_CFGS}
    cls = {c: M.value_pred(m, c[2:]) for c in S.VALUE_CFGS}
    cls.update({c: M.pred_lands(m, g, c[:2], int(c[-1])) for c in S.PRED_CFGS})
    return cls


# sanity: the clean world scores the controls PASS and the survivors include the generating model
text, res = S.score(mk_world({}), preds)
check("a clean world (every o4 class A) passes the controls", all(v is True for v in res["controls"].values()), str(res["controls"]))
fails = []
for m in ms:
    for g in ("gated", "ignored"):
        t, r = S.score(mk_world(model_world(m, g)), preds)
        mine = f"{M.name(m)}"
        eq = {M.name(x) for x in ms if all(M.value_pred(x, c) == M.value_pred(m, c) for c in M.VALUE)}
        bit4_same = M.value_pred(m, "a-a4") == M.value_pred(m, "a4-a")
        vs = set(r["value_survivors"])
        if vs != eq or M.name(m) not in vs:
            fails.append((M.name(m), g, "value", sorted(vs), sorted(eq)))
            continue
        if bit4_same:
            if r["pred_survivors"] or r["answered"] or "predicate rows cannot tell" not in t.splitlines()[-1] + t:
                fails.append((M.name(m), g, "bit4", r["pred_survivors"]))
            continue
        want = {f"{x}+{g}" for x in vs if all(M.pred_lands(tuple(x.split("/")), g, c[:2], int(c[-1])) == M.pred_lands(m, g, c[:2], int(c[-1])) for c in S.PRED_CFGS)}
        if set(r["pred_survivors"]) != want or M.name(m) + "+" + g not in r["pred_survivors"]:
            fails.append((M.name(m), g, "pred", r["pred_survivors"], sorted(want)))
check("synthetic worlds: each of the 12 models x {gated, ignored} (24): the scorer names exactly the value survivors and the (model, gating) survivors, "
      "and the predicate rows cannot tell when the bit-4 pairs read one class", not fails, str(fails[:3]))
answered = [(M.name(m), g) for m in ms for g in ("gated", "ignored") if S.score(mk_world(model_world(m, g)), preds)[1]["answered"]]
check("answered only where the survivors are one prediction class and one gating (e.g. V1/last gated, V1/or ignored when the bit-4 pairs differ)",
      ("V1/last", "ignored") in answered and ("V1/first", "ignored") in answered and ("V1/and", "ignored") not in answered and ("V1/or", "ignored") not in answered,
      str(answered))
# control fails: c-o4-u reads A4 (the world's G-o4 control fails) -> every value row cannot tell
t, r = S.score(mk_world({"o4-u": "A4"}), preds)
check("a failing G-o4 control (c-o4-u reads A4) makes every row cannot tell", r["value_survivors"] == [] and not r["answered"] and "cannot tell" in t.splitlines()[-1], t.splitlines()[-1][:120])
t, r = S.score(mk_world({"o4s-u": "A3"}), preds)
check("c-o4s-u reading tag 13 (E808 not reproduced) shuts the gate", not r["answered"] and not r["controls"]["c-o4s-u reads A (E808)"], t.splitlines()[-1][:100])
t, r = S.score(mk_world(model_world(ms[0], "gated"), void=("c-u-x",)), preds)
check("a void c-u (G-o1) shuts the predicate rows only: value survivors stay, no answer", r["value_survivors"] == ["V1/last"] and not r["answered"]
      and "predicate rows cannot tell" in t.splitlines()[-1], t.splitlines()[-1][:140])
t, r = S.score(mk_world({}, void=("c-v-a-a4-y",)), preds)
check("a void value job is cannot tell, never a pass", not r["answered"] and "void" in t.splitlines()[-1], t.splitlines()[-1][:100])
t, r = S.score(mk_world({"v-a4-a": ["A", "A4"]}), preds)
check("a mixed class (A and A4 in one job) matches no model: family refuted, not answered", not r["answered"] and "mixed" in t and "REFUTED" in t.splitlines()[-1], t.splitlines()[-1][:120])
t, r = S.score(mk_world({}, unmarked=("v-a3",)), preds)
check("a wrong marker (not the frozen program) voids the configuration", "marker proof failed" in t and not r["answered"])
cl = model_world(ms[0], "gated")
cl["v-a-a4"] = cl["v-a4-a"] = "A"
t, r = S.score(mk_world(cl), preds)
check("bit-4 pairs reading one class in both orders: predicate rows cannot tell", "predicate rows: cannot tell" in t and not r["answered"])
check("no family fits the value rows (A5 where no model gives it) is refuted", "REFUTED" in S.score(mk_world({"v-a3": "A5"}), preds)[0].splitlines()[-1])
sys.exit(0 if ok else 1)
