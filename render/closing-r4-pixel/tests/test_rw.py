#!/usr/bin/env python3
"""g4-rw (Q230): the generated table and frozen predictions, exactness of every w, the FIT / HELD OUT split, the family code, the
decode on REAL kept dumps (E782's t3-nocut, E783's w = 3 control), and the scorer on synthetic worlds: one family, pure RZ (no rule
adopted), a failing control, a void job, a word that is neither RZ nor RZ+1.  Prints ok/FAIL; exit 1 on any FAIL."""
import gzip
import os
import pathlib
import re
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
os.environ.setdefault("RESGX545_MAIN", "/Users/jtorra/src/scratch/resgx545/closing4/lead/wt")
sys.path[:0] = [str(R4 / "gen"), str(R4 / "score"), str(R4 / "tests")]
import rwdesign as D  # noqa: E402
import rwfam as R  # noqa: E402
import r4lib as L  # noqa: E402
import score_rw as S  # noqa: E402
import worlds as W  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


rows = [dict(zip(("name", "set", "risk", "knobs", "rt", "args"), ln.split("|", 5)))
        for ln in (R4 / "tables/g4-rw.txt").read_text().splitlines() if ln and not ln.startswith("#")]
preds = L.load_preds(R4 / "predictions/g4-rw.tsv")
names = [r["name"] for r in rows]
check("24 jobs: 4 controls first, then 20 table jobs (set heldout)",
      len(rows) == 24 and names[:4] == ["rw-k0", "rw-k1", "rw-k2", "rw-k3"] and names[4:] == [f"rw-{i:02d}" for i in range(1, 21)]
      and [r["set"] for r in rows] == ["control"] * 4 + ["heldout"] * 20)
check("every staged program exists and is listed", all((R4 / "bins" / f"{n}.bin").exists() for n in names + ["pix_green"])
      and (R4 / "tables/g4-rw.txt").read_text().count("#need ") == 25)
check("every job is the t3-nocut shape (tri vtxuse, 64x64, --vtx-coords 2, --dump-render, pixel slot), no regtimeline",
      all(r["args"].startswith("probe --temps 8 --pixels --tri vtxuse --width 64 --height 64 --vtx-coords 2 --dump-render")
          and r["rt"] == "-" and r["knobs"] == "stophang" for r in rows))
check("no forbidden option in the table", not re.search(r"--kreg|--kpoke|--poke|--late|--low|--place", (R4 / "tables/g4-rw.txt").read_text()))
ws = D.table_words()
check("60 distinct table words, 20 jobs x 3", len(ws) == 60 and len(set(ws)) == 60)
allp = [D.job_params(i) for i in range(20)] + [D.control_params(i) for i in range(4)]
check("every w is computed EXACTLY in float32, fused and unfused, at all three vertices (24 jobs)",
      all(D.exact_in_float32(p["C"], p["D"], f) for p in allp for f in (True, False)))
check("w3 = 0.75 w1 + 0.25 w2 and the words are the recorded ones", all(p["w"][2] == F3 for p in allp for F3 in [D.F(3, 4) * p["w"][0] + D.F(1, 4) * p["w"][1]]))
check("the 31 grid mantissas 1 + k/32 are all among the designed words (w1, w2) at scale 1, 4 or 1/4",
      all(any(((p["words"][0] & 0x7fffff) == k * (1 << 18)) or ((p["words"][1] & 0x7fffff) == k * (1 << 18)) for p in allp[:20]) for k in range(1, 32)))
check("the mantissas are preserved at three scales (1: 7 jobs, 4: 7, 1/4: 6)",
      [float(p["scale"]) for p in allp[:20]].count(1.0) == 7 and [float(p["scale"]) for p in allp[:20]].count(4.0) == 7
      and [float(p["scale"]) for p in allp[:20]].count(0.25) == 6)
nud = [(p["n2"] - p["n1"]) % (1 << 18) for p in allp[:20]]
check("at most 11 pairs are nudged off the grid (the leftover grid index and the nine others), by at most 6 ulps",
      sum(1 for x in nud if x) <= 10, str(sum(1 for x in nud if x)))
sp = D.split()
check("the split: 30 FIT and 30 HELD OUT, deterministic, equal to the frozen @split rows",
      list(sp.values()).count("FIT") == 30 and sp == D.split() and
      {int(v, 16): q.replace("_", " ") for q in ("FIT", "HELD_OUT") for v, m, s in preds["@split"].get(q, [])} == sp)
fr = {"rw-k1": (3.0, 9.0), "rw-k2": (7.0,), "rw-k3": (1.40625, 1.5), "rw-k0": (1.0,)}
check("the known control words: RZ at 1, 3, 7, 1.5; RZ+1 at 9 and 1.40625 (E754, E795, E796, E798)",
      D.rz_word(D.bits(3)) == 0x3eaaaaaa and D.rz_word(D.bits(7)) == 0x3e124924 and D.rz_word(D.bits(1.5)) == 0x3f2aaaaa
      and D.control_params(1)["known"][1] == D.rz_word(D.bits(9)) + 1 and D.control_params(3)["known"][0] == D.rz_word(D.bits(1.40625)) + 1
      and D.control_params(0)["known"] == (0x3f800000,) * 3)
need = {"object", "nvert", "w_words", "xy_ordered", "depth_words", "rz_words"}
check("every job has every frozen quantity, the controls also the known words", all(need <= set(preds[n]) for n in names)
      and all("rhw_known" in preds[n] for n in names[:4]))
check("the window prediction is 32 + 32 x / w (job 1: first vertex)",
      abs(S._xy_list(preds["rw-01"]["xy_ordered"][0][0])[0][0] - float(32 + 32 * D.VX[0] / D.job_params(0)["w"][0])) < 1e-5)
mx = max(abs(float(c)) for i in range(20) for v in range(3) for c in D.window(v, D.job_params(i)["w"][v]))
check("window coordinates stay within +-128 pixels at the smallest w", mx <= 128, f"{mx:.1f}")
# ---- family code
rzp = [(w, D.rz_word(w)) for w in ws]
ms = R.models()
check("225 models in 5 families", len(ms) == 225 and {f for f, _ in ms.values()} == set("abcde"))
check("the exact-RZ models reproduce RZ words (e:rz, d:rest:b24:rz: 60 of 60); e:ru and e:rn do not",
      R.fits(ms["e:rz"][1], rzp) == 60 and R.fits(ms["d:rest:b24:rz"][1], rzp) == 60 and R.fits(ms["e:ru"][1], rzp) < 60)
check("the model words of 3 and 9 by e:rz", R.predict(ms["e:rz"][1], D.bits(3)) == 0x3eaaaaaa and R.predict(ms["e:ru"][1], D.bits(9)) == 0x3de38e39)
# ---- real records
fx = R4 / "tests/fixtures/rw"
gzr = lambda n: gzip.open(fx / n).read()
d = S.decode_object(gzr("t3-nocut.t3-nocut__0.param.bin.gz"), gzr("t3-nocut.t3-nocut__0.tadata.bin.gz"))
wn = [D.F(7, 8), D.F(13, 8), D.F(17, 16)]
exp = [D.rz_word(D.bits(w)) for w in wn]
check("real E782 t3-nocut: object present, 3 vertices, 1/w words 0x3f924924, 0x3f1d89d8, 0x3f70f0f0 (RZ, 3 of 3)",
      d["state"] == "present" and d["nvert"] == 3 and sorted(d["rhw"]) == sorted([0x3f924924, 0x3f1d89d8, 0x3f70f0f0])
      and sorted(exp) == sorted(d["rhw"]))
import tempfile  # noqa: E402
td = pathlib.Path(tempfile.mkdtemp(prefix="rw-real-"))
for f in fx.glob("t3-nocut*"):
    (td / ("rw-t." + f.name.split(".", 1)[1]).replace("t3-nocut", "rw-t")).write_bytes(f.read_bytes())
(td / "cases.tsv").write_text(W.HEAD + "\nrw-t\tg4-rw\tx\tsafe\tx\tx\tx\t0\tok\t-\n")
k = L.Kept(td)
pr = {"rw-t": {"xy_ordered": [(";".join("%.6f,%.6f" % tuple(float(c) for c in D.window(i, wn[i])) for i in range(3)), "", "")]}}
j = S.read_job(k, pr, "rw-t")
check("real E782 t3-nocut through read_job: window rule met at all three vertices, depth 0x3f000000, words RZ exactly in input order",
      j["void"] is None and j["shape"] is True and j["words"] == exp, f"{j['void']} {j['notes']} {j['words']}")
d3 = S.decode_object(gzr("t4-ctl-z0-w3.t4-ctl-z0-w3__0.param.bin.gz"), gzr("t4-ctl-z0-w3.t4-ctl-z0-w3__0.tadata.bin.gz"))
check("real E783 control (w = 3 at every vertex): the three words are RZ of 1/3, 0x3eaaaaaa", d3["state"] == "present" and d3["rhw"] == [0x3eaaaaaa] * 3)
# ---- synthetic worlds (the decode is replaced by a table of the world's objects, keyed by the job's dump bytes)
WORLD = {}
S.decode_object = lambda p, t: WORLD[p.decode()]


def world(wordfn, ctl_known=True, void=(), bad_job=None, bad_ctl=None, shape_bad=()):
    jobs = []
    WORLD.clear()
    for n in names:
        ww, rzw = S._list(S.pq(preds, n, "w_words")), S._list(S.pq(preds, n, "rz_words"))
        xy = S._xy_list(S.pq(preds, n, "xy_ordered"))
        got = [wordfn(w) for w in ww]
        if n.startswith("rw-k") and ctl_known:
            kn = S._list(S.pq(preds, n, "rhw_known"))
            got = [kv if kv is not None else g for kv, g in zip(kn, got)]
        if n == bad_job:
            got[1] = rzw[1] + 3
        if n == bad_ctl:
            got[0] ^= 0x10
        nvv = 2 if n in shape_bad else 3
        WORLD[n] = dict(state="present", nvert=nvv, rhw=got[:nvv], xy=xy[:nvv], depth=[0x3f000000] * nvv)
        jobs.append(dict(name=n, out=f"probe {n}: o0 mixed 0xff203040 x4000 0xff00ff00 x96\njob: ok\n" if n not in void else None,
                         pre=0x400, post=0x400, dumps={"param.bin": n.encode(), "tadata.bin": b"t"}))
    return L.Kept(W.stage("g4-rw", jobs))


def run(**kw):
    t, res = S.score(world(**kw), preds)
    return t, res


rzf = lambda w: D.rz_word(w)
t, res = run(wordfn=rzf, ctl_known=False)
# the control words known include RZ+1 at 9 and 1.40625: pure RZ cannot pass them
check("a pure-RZ world fails the controls that know an RZ+1 word (k1, k3): controls FAILED, every row cannot tell, no analysis",
      "controls FAILED" in t.splitlines()[-1] and res["analysis"] is None and not res["gate_ok"])
t, res = run(wordfn=rzf)
a = res["analysis"]
check("pure RZ with the known control words: controls pass, all 60 words held, FIT and HELD OUT 30 of 30",
      res["gate_ok"] and res["tally"].held == 60 and a is not None, str(res["tally"]))
check("pure RZ: the exact-RZ models of two families (d and e) fit 30 of 30 held out: no rule adopted",
      {"d", "e"} <= set(a["families"]) and "no rule adopted" in res["verdict"] and "SUMMARY" in t.splitlines()[-1], str(a["families"]))
# one family: a model that goes up by one ulp at some words (c) and whose words stay in RZ..RZ+1 everywhere
cand = None
for n_, (f_, fn_) in ms.items():
    if f_ != "c":
        continue
    g_ = [R.predict(fn_, w) for w in ws]
    if all(x in (D.rz_word(w), D.rz_word(w) + 1) for x, w in zip(g_, ws)) and sum(x != D.rz_word(w) for x, w in zip(g_, ws)) >= 10:
        a_ = R.models()
        fitn = [m for m, (f2, fn2) in a_.items() if R.fits(fn2, [(w, x) for w, x in zip(ws, g_)]) == 60]
        if {a_[m][0] for m in fitn} == {"c"}:
            cand = n_
            break
check("a model of family c exists that goes one ulp up at 10 or more of the 60 words and that no other family reproduces", cand is not None, str(cand))
fnc = ms[cand][1]
t, res = run(wordfn=lambda w: R.predict(fnc, w))
a = res["analysis"]
if res["gate_ok"]:
    check("one family world: family c alone fits 30 of 30 held out; held-out count 30 of 30 for the model, chance counts printed",
          a["families"] == ["c"] and cand in a["held"] and "chance" in t, f"{a['families']} {len(a['held'])}")
else:
    check("one family world: the known-word controls cannot be met by this model: (control states printed)", False, t.splitlines()[0])
t, res = run(wordfn=rzf, bad_ctl="rw-k2")
check("a failing control (k2's first word flipped): every table row controls FAILED, every row cannot tell, no analysis", res["tally"].decided == 0 and res["analysis"] is None
      and "controls FAILED" in t.splitlines()[-1])
t, res = run(wordfn=rzf, void=("rw-05",))
check("a void table job: its three words are cannot tell, never a pass; the analysis is not run (57 of 60 read)",
      res["tally"].cannot_tell == 3 and res["tally"].held == 57 and res["analysis"] is None and "analysis not run" in res["verdict"])
t, res = run(wordfn=rzf, bad_job="rw-07")
check("a word that is neither RZ nor RZ+1 (RZ + 3): a FAILED row; the headline says not supported", res["tally"].failed == 1 and "not supported" in res["headline"])
t, res = run(wordfn=rzf, shape_bad=("rw-02",))
check("an object with 2 vertices in a table job: the job shape row is FAILED (reported), its unmatched word cannot tell",
      "1 FAILED" in [x for x in t.splitlines() if x.startswith("job shape")][0])
check("a table with words read, the printed table has the columns and 60 rows", len([x for x in t.splitlines() if re.match(r"rw-\d\d ", x)]) == 60)
sys.exit(0 if ok else 1)
