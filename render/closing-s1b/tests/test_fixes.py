#!/usr/bin/env python3
"""The scorer and generator fixes of the S1 analysis (closing/s1/analysis/README.md, "Scorer and generator fixes
before freezing"), each tested on S1's own kept data and frozen predictions.  Every test FAILS on S1's code and
passes on S1b's:

    PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
    $PY -I tests/test_fixes.py                       # S1b's code: all ok
    CODE=~/src/scratch/resgx545/closing/s1 $PY -I tests/test_fixes.py    # S1's code: every fix FAILs

Read-only: S1's out/ and predictions/ are read, nothing is written there (the generator test builds into a
temporary directory).  Prints ok/FAIL per fix; exit 1 if any fails.
"""
import sys
sys.dont_write_bytecode = True     # the data repo's modules are imported: no __pycache__ there

import gzip  # noqa: E402
import os  # noqa: E402
import pathlib  # noqa: E402
import tempfile
import traceback

HERE = pathlib.Path(__file__).resolve().parent.parent
CODE = pathlib.Path(os.environ.get("CODE", HERE)).expanduser()
S1 = pathlib.Path(os.environ.get("S1_DIR", pathlib.Path.home() / "src/scratch/resgx545/closing/s1"))
OUT, PRED = S1 / "out", S1 / "predictions"
sys.path.insert(0, str(CODE / "gen"))
sys.path.insert(0, str(CODE / "score"))
import numpy as np  # noqa: E402
from s1lib import Kept, load_preds  # noqa: E402
import score_geo as G  # noqa: E402
import score_pix as P  # noqa: E402

results = []


def fix(name):
    def deco(fn):
        try:
            fn()
            results.append((name, True, ""))
        except Exception as e:                    # an assertion or an old code path that cannot run
            results.append((name, False, f"{type(e).__name__}: {str(e)[:160]}"))
            if os.environ.get("VERBOSE"):
                traceback.print_exc()
        return fn
    return deco


def summary(text):
    return next(ln for ln in text.splitlines() if ln.startswith("SUMMARY:"))


def score(fn, stage):
    return fn(Kept(OUT / stage), load_preds(PRED / f"{stage}.tsv"))[0]


@fix("score_geo e2b (185-192): open-kick check, 10 of 12 jobs are K-scene tests; count jobs void")
def _():
    s = summary(score(G.score_e2b, "g-e2b"))
    assert "on 12" not in s, s
    assert "10" in s and "b-2s-lo" in s and "b-4s-lo" in s, s
    assert "k-4a-P1" in s and "void" in s, s


@fix("score_geo e3 (280-284): per-group gate, a failed control voids its own group only")
def _():
    s = summary(score(G.score_e3, "g-e3"))
    assert not s.startswith("SUMMARY: cannot tell"), s
    assert "e3k: cannot tell" in s and "e3z:" in s and "e3c:" in s, s


@fix("score_geo e3 (246): the cut scored by vertex identity (e3z-cut-m: 3 vertices, not the original three)")
def _():
    k = Kept(OUT / "g-e3")
    preds = load_preds(PRED / "g-e3.tsv")
    d = G.decode_object(k.dump("e3z-cut-m", "param.bin"), k.dump("e3z-cut-m", "tadata.bin"))
    h = G._hits(preds, "e3z-cut-m", d)
    assert d["nvert"] == 3, d["nvert"]
    assert h[("nvert", "HC-poly")] is True and h[("nvert", "HC-orig")] is False, h


@fix("score_geo e5 (374-386): HO is the frozen base histogram, a12's 2582 is neither HD nor HO")
def _():
    s = summary(score(G.score_e5, "g-e5"))
    assert "r-n8-a12: HO" not in s, s
    assert "r-n8-a12: neither" in s, s


@fix("score_geo e1 (69-72): positive controls only from frozen control rows (raises already measured)")
def _():
    s = summary(score(G.score_e1, "g-e1"))
    assert "METHOD BROKEN" not in s, s


@fix("score_pix 49: row_ranges excludes the clear depth 1.0 (g-dyadic fits 32 of 32 rows)")
def _():
    k = Kept(OUT / "p-b1")
    rr = P.row_range(P.depth_image(k.depth("g-dyadic"), 1024, 32))
    assert rr is not None and rr[2] == 32, rr


@fix("gen/b2model 45: deviation excludes the clear depth 1.0 (d-shift: no deviating pixel)")
def _():
    import b2model
    k = Kept(OUT / "p-b2")
    w, h, V, Z = P.parse_depth_job("d-shift", k.cases)
    d, cov = b2model.deviation(k.depth("d-shift"), w, h, V, Z)
    assert int(((d != 0) & cov).sum()) == 0 and int(cov.sum()) == 18432, (int(((d != 0) & cov).sum()), int(cov.sum()))


@fix("score_pix 241: the replicate c-k7-x-rep is compared with c-k7-x")
def _():
    t = score(P.score_c, "p-c")
    assert any(ln.startswith("replicate c-k7-x-rep") for ln in t.splitlines()), t[-600:]


@fix("score_pix 271: the c-u control criterion is the frozen one (>= 0.98), not exact 1.0")
def _():
    preds = load_preds(PRED / "p-c.tsv")
    for n in ("c-u-x", "c-u-y"):
        preds[n]["ctl_min_frac"].append(("0.98", "control criterion", "control"))
    s = summary(P.score_c(Kept(OUT / "p-c"), preds)[0])
    assert "controls failed" not in s, s


@fix("score_pix 394: `tri: 0 of N renders ok, N overflowed` with every diff 0 is exact (f-dpm-dc0)")
def _():
    s = summary(score(P.score_f, "p-f"))
    assert "f-dpm-dc0: exact 2 of 2" in s, s


@fix("score_pix 413-414: two faults are HJ only when the mask leaves buffer 0 in (f-dpm-1f: mask 0x1f)")
def _():
    s = summary(score(P.score_f, "p-f"))
    seg = next(x for x in s.split("; ") if x.startswith("f-dpm-1f"))
    assert "HJ" not in seg and "buffer 0" in seg, seg


@fix("gen/s1pix 356: A4 predicted at the job's own pages (d-L2e2-64 is not cases.json's all-OOB hash)")
def _():
    import json
    import s1pix
    tex = pathlib.Path.home() / "src/resgx545-data/texture/p1141"
    cj = {c["name"]: c for c in json.load(open(tex / "gen/cases.json"))}
    with tempfile.TemporaryDirectory() as t:
        s1pix.BINS = pathlib.Path(t)                 # the generator builds its programs here, not in S1's bins
        rows, preds, needs, head = s1pix.p_d()
    got = next(v for n, q, v, m, st in preds if n == "d-L2e2-64" and q == "pix_sha256_if_complete")
    assert got != cj["ad-tw64x64-L2e2"]["preds"]["A4"], "cases.json's 16-page hash"
    k = Kept(OUT / "p-d")
    from s1lib import pixel_sha, rows_of
    assert got == pixel_sha(rows_of(k.out("d-L2e2-64"))), "not the image S1 measured (post hoc A4 fit)"


# ---- post-run fixes (POSTRUN-FIX.md, 2026-11-11): these FAIL on S1b's frozen code (score/score_geo.as-run.py) ----------
@fix("post-run C8, score_geo e2b: a hung job is void, never 'completed as predicted' (b-3a-hi hung, in a copy of S1's g-e2b)")
def _():
    import shutil
    with tempfile.TemporaryDirectory() as t:
        d = pathlib.Path(t) / "g-e2b"
        shutil.copytree(OUT / "g-e2b", d)
        p = d / "b-3a-hi.txt.gz"
        p.write_bytes(gzip.compress(gzip.decompress(p.read_bytes()) + b"\ntri 64x64: job hung, recovering\n"))
        text = G.score_e2b(Kept(d), load_preds(PRED / "g-e2b.tsv"))[0]
    row = next(ln for ln in text.splitlines() if ln.startswith("b-3a-hi"))
    s = summary(text)
    assert "hang" in row and "yes" not in row, row
    assert "holds on" not in s and "cannot tell" in s and "b-3a-hi" in s, s


@fix("post-run C8, score_geo ladder_verdict: HP1 is refuted only when its C interval and the limit are disjoint")
def _():
    lad = lambda Pa, Pb: {V: [(Pa - 0x20, True), (Pa, True), (Pb, False)] for V in (1350, 1500)}
    v = G.ladder_verdict(lad(0x2d0, 0x2f0))           # C in [0x2ce, 0x2ee): disjoint from [0x2fe, 0x3de)
    assert "REFUTED by its limit" in v, v
    v = G.ladder_verdict(lad(0x2f0, 0x310))           # C in [0x2ee, 0x30e): overlaps the limit, not inside it
    assert "REFUTED" not in v and "overlaps" in v, v
    v = G.ladder_verdict(lad(0x320, 0x340))           # inside: the wording is unchanged
    assert v == ("HP1: one step for both scenes, last raise 0x320, first silent 0x340: C in [0x31e, 0x33e) inside "
                 "[0x2fe, 0x3de)"), v


for name, ok, why in results:
    print(("ok   " if ok else "FAIL ") + name + (f"\n       {why}" if why else ""))
print(f"code: {CODE}; {sum(ok for _, ok, _ in results)} of {len(results)} fixes ok")
sys.exit(0 if all(ok for _, ok, _ in results) else 1)
