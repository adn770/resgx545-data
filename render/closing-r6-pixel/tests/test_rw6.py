#!/usr/bin/env python3
"""Stages g6-rwa and g6-rw offline tests (plan closing6/pixel/exp-pixel-r6.md sections 4 and 5).
  - the design premise: every window has 36 distinct mantissas inside [2^23, 2^24), disjoint from every mantissa read before (the
    w column of R4's and R5's kept tables and the early records), from the other windows and from B; every job exact (w = C x + D in
    float32) and inside the viewport; B's 24 mantissas all have frac in [0.42, 0.62); E's rows are R4's four rows with the most RZ + 1
    words at exponents -12, -6, -3, 5, 8, 12 with every w in [2^e, 2^(e+1)); the replicates are L jobs' programs; R4's design stays
    the fixture the viewport check flags (rw-15..rw-20);
  - the frozen predictions: frac and H-FRAC per L / B word, R4's delta per E word, R5's six words for d-01 and d-02;
  - the scorers on mock worlds (M-G), each built by running the frozen tables' own commands through the argv-driven fake tool:
    e smooth (H-SMOOTH held at strides 1 and 2^8, H-FRAC held), e hashed (no window separable), one RZ + 1 below frac 0.5 (H-FRAC
    refuted), a delta that depends on the exponent (H-MANT refuted at 5, 8, 12 only), jobs clipped at 2^12 ("no object at this
    exponent", not a miss), RZ always (part a fails), R4's unscaled design (part a fails), jobs off their window (L and B void).
Prints ok / FAIL; exit 1 on any FAIL.   PY tests/test_rw6.py"""
import collections
import pathlib
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True
R6 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R6 / "gen"), str(R6 / "score"), str(R6 / "tests")]
import mockstage as MS  # noqa: E402
import r4lib as L  # noqa: E402
import rwdesign as D4  # noqa: E402
import rwdesign6 as D  # noqa: E402
import score_r6 as SR  # noqa: E402
import score_rw6 as W  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


read = D.read_mantissas()
check("the read mantissas: 130 or more (R4's 60 words, R5's 126 words, the early records)", len(read) >= 130, str(len(read)))
wins = D.windows()
wm = {t: D.window_mantissas(s, b) for t, s, b in wins}
check("six windows, tags 1a 1b 8a 8b 16a 16b, strides 1, 2^8, 2^16", [t for t, _, _ in wins] == ["1a", "1b", "8a", "8b", "16a", "16b"]
      and [s for _, s, _ in wins] == [1, 1, 256, 256, 65536, 65536])
check("each window: 36 distinct mantissas Bw + o s (o in 0..41), inside [2^23, 2^24)", all(len(v) == 36 and min(v) >= 1 << 23 and max(v) < 1 << 24 for v in wm.values()))
allw = [m for v in wm.values() for m in v]
check("windows disjoint from every read mantissa and from each other", not (set(allw) & read) and len(set(allw)) == len(allw))
ls = D.l_rows()
check("L: 72 jobs whose words are exactly the windows' mantissas", len(ls) == 72 and sorted(D.mant(w) for p in ls for w in p["words"]) != []
      and set(D.mant(w) for p in ls for w in p["words"]) == set(allw))
bs = D.b_rows()
bm = [D.mant(w) for p in bs for w in p["words"]]
check("B: 8 jobs, 24 distinct new mantissas, every frac in [0.42, 0.62)", len(bs) == 8 and len(set(bm)) == 24 and not (set(bm) & (read | set(allw)))
      and all(F(42, 100) <= D.frac(m) < F(62, 100) for m in bm), str(sorted(round(float(D.frac(m)), 3) for m in bm)[:4]))
es = D.e_rows()
check("E: R4's four rows with the most RZ + 1 words (ties by name) at six exponents, every w in [2^e, 2^(e+1))", len(es) == 24
      and all(F(2) ** p["exp"] <= x < F(2) ** (p["exp"] + 1) for p in es for x in p["w"]), str(D.e_source()))
r4 = D.__dict__["D5"].r4_words()
cnt = {n: sum(1 for v in range(3) if r4[(n, v)][2] - r4[(n, v)][1] == 1) for n in D.e_source()}
check("  the E rows' frozen deltas are R4's (E842) and hold RZ + 1 words", all(p["hmant"] == tuple(r4[(p["r4"], v)][2] - r4[(p["r4"], v)][1] for v in range(3)) for p in es)
      and sum(cnt.values()) >= 6, str(cnt))
rows = D.g6_rows()
check("every g6-rw job exact in float32 and inside the viewport; mantissas of E equal R4's", all(D.exact(p) and D.viewport_ok(p["w"], p["S"]) for p in rows)
      and all({D.mant(w) for w in p["words"]} == {D.mant(w) for w in D4.job_params(int(p["r4"][3:]) - 1)["words"]} for p in es))
check("the viewport check still flags exactly rw-15..rw-20 on R4's design (the fixture that must fail)",
      [D4.job_params(i)["name"] for i in range(20) if not D.viewport_ok(D4.job_params(i)["w"])] == [f"rw-{i}" for i in range(15, 21)])
fr = [D.frac(m) for m in allw]
check("about half the window words have frac < 0.5 (H-FRAC's test)", 80 <= sum(1 for f in fr if f < F(1, 2)) <= 136, str(sum(1 for f in fr if f < F(1, 2))))
pa = L.load_preds(stage="g6-rwa")
check("g6-rwa: d-01 and d-02 frozen to R5's six words (two RZ + 1), rw-k4 RZ, rw-k5 RZ + 1",
      pa["d-01"]["rhw_known"][0][0] == "0x407c0fc1,0x4066c2b4,0x4076603d" and pa["d-02"]["rhw_known"][0][0] == "0x3fb40b40,0x3fa8e83f,0x3fb11fd4")
pb = L.load_preds(stage="g6-rw")
check("g6-rw: frac and hfrac on every L and B row, H-MANT and exp on every E row, same_as on the replicates",
      all("frac" in pb[p["name"]] and "hfrac" in pb[p["name"]] for p in ls + bs) and all("hmant" in pb[p["name"]] and "exp" in pb[p["name"]] for p in es)
      and pb["rl-1a-00"]["same_as"][0][0] == "l-1a-00")


def world(rule):
    env = {"FAKE_RW_RULE": rule}
    ka, kb = MS.build("g6-rwa", env), MS.build("g6-rw", env)
    p = SR.preds_rw()
    ta, ra = W.score_a(L.Kept(ka), {n: v for n, v in p.items() if n.startswith(("rw-k", "d-"))})
    t, r = W.score(L.Kept(ka), L.Kept(kb), p)
    return ra, r, t.splitlines()[-1]


ra, r, s = world("smooth")
check("world e smooth: part a PASS; H-FRAC held; H-SMOOTH held at 2^1 and 2^8; H-MANT held at all six exponents; replicates agree",
      ra["gate"].ok and r["hfrac"] is True and r["hsmooth"]["1"] == "held" and r["hsmooth"]["8"] == "held"
      and all(v.startswith("held") for v in r["hmant"].values()) and all(r["replicate"]), s[:200])
ra, r, s = world("hash")
check("world e hashed: no stride held (inversions), H-FRAC held", r["hfrac"] is True and all(v in ("refuted", "mixed") for v in r["hsmooth"].values()), str(r["hsmooth"]))
ra, r, s = world("below")
check("world with RZ + 1 below frac 0.5: H-FRAC refuted", r["hfrac"] is False, s[:160])
ra, r, s = world("exp")
check("world whose delta depends on the exponent: H-MANT refuted at 5, 8, 12, held at -12, -6, -3",
      [r["hmant"][e].split()[0] for e in D.EXPS] == ["held"] * 3 + ["REFUTED"] * 3, str(r["hmant"]))
ra, r, s = world("clip12")
check("world clipped at 2^12: 'no object at this exponent' at 12, not a miss; the rest held",
      r["hmant"][12].startswith("no object") and all(r["hmant"][e].startswith("held") for e in D.EXPS[:-1]), r["hmant"][12])
ra, r, s = world("rz")
check("world RZ always: the controls with RZ + 1 words fail part a (the gate stops before g6-rw)", not ra["gate"].ok and ra["gate"].failed)
ra, r, s = world("noscale")
check("R4's unscaled design in the fake (x and y not scaled): the controls at S != 1 fail part a (the gate stops before g6-rw)",
      ra["gate"].failed and {n for n, v in ra["controls"].items() if v is False} == {"rw-k4", "rw-k5", "d-01", "d-02"}, str(ra["controls"]))
ra, r, s = world("badwin")
check("a world where the new jobs land off their frozen window: L and B FAILED shape -> L and B void, H-FRAC cannot tell; E held",
      ra["gate"].ok and r["lb_void"] and r["hfrac"] is None and all(v.startswith("held") for v in r["hmant"].values()), s[:160])
sys.exit(0 if ok else 1)
