# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator and the model.

- gen/make.py --check: tables/, predictions/, gen/bgmask.txt and bins/ are what the generator
  writes from the pinned commits (bins/ with debug/asm's assemblers, which tests/run_all.sh builds
  from `git archive` of the pinned resgx545 commit);
- gen/bgmask.txt is E590's kept hardware control (3034 background, 1062 triangle pixels, E437's
  count), never the library mock's 2998;
- the model's vertex decoding is E590's analysis/bg_geometry.py (pinned), shifted by six words;
  the control object decodes to the render box (0, 0), (64, 0), (0, 64);
- the plan's shape: stages s0t, s0p, s1n, s1, s2, s3, s4 with 3, 4, 6, 44, 20, 21 and 2 rows
  (100 tabled, 94 on the H-ITER path, s1n only on H-NONE's), fit 14 and held-out 30 in s1;
- every held-out row of s1 separates H-VM from H-NOREAD on >= 20 % of the pixels both predict and
  every rival of the s1 gate is predicted wrong-able (>= 10 % apart) on >= 3 held-out rows;
- the predictions the scorer recomputes are the frozen ones (score.checked_preds)."""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, HERE)
import bgl_model as M  # noqa: E402
import kept as KD  # noqa: E402
import kitscore as K  # noqa: E402
import make as G  # noqa: E402

ASM = os.path.join(KP, "debug/asm/tools/usse-asm/pds-asm")
PY = sys.executable
MASK = M.load_mask()


@pytest.mark.skipif(not os.path.exists(ASM), reason="SKIPPED, NOT PASSED: no debug/asm (tests/run_all.sh builds it)")
def test_generator_is_current():
    r = subprocess.run([PY, "-B", os.path.join(KP, "gen/make.py"), "--check"], capture_output=True,
                       text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr


def test_mask_is_the_hardware_control():
    import gzip
    text = gzip.decompress(KD.git_show("data", G.MASK_SRC)).decode()
    assert "target: 64x64 hash %s" % M.HASH_OFF in text
    rows = M.tri_rows(text)
    lines = open(M.MASK).read().split()
    assert lines == M.mask_lines_from_rows(rows)
    assert sum(ln.count(".") for ln in lines) == 3034 == len(MASK)
    assert sum(ln.count("#") for ln in lines) == 1062
    assert all("?" not in ln for ln in lines)


def test_decoding_is_e590s():
    src = KD.git_show("data", "isp/bg-object-pokes/analysis/bg_geometry.py").decode()
    ns = {}
    body = src[src.index("def verts"):src.index("def inside")]
    exec(body, ns)              # noqa: S102 (the pinned file's own function)
    for pokes in ({}, {15: 0x000ff000}, {16: 0x0ff0}, {17: 0x10000000}, {18: 0x10500010},
                  {20: 0x00105000}, {21: 0x00001001}, {15: 0, 16: 0}):
        o = M.obj(pokes)
        w17 = [0] * 9 + [o[k] for k in range(15, 23)]
        theirs = ns["verts"](w17)
        ours = M.decoded_vertices(o)
        assert [tuple(float(c) for c in p) for p in ours] == [tuple(p) for p in theirs], pokes
    assert M.decoded_vertices(M.obj({})) == M.BOX


def test_plan_shape():
    rows = {s: K.table(KP, s) for s in G.STAGES}
    assert [len(rows[s]) for s in G.STAGES] == [3, 4, 6, 44, 20, 21, 2]
    assert sum(len(rows[s]) for s in G.STAGES if s != "s1n") == 94
    s1 = [r["set"] for r in rows["s1"]]
    assert s1.count("fit") == 14 and s1.count("heldout") == 30
    assert {r["set"] for r in rows["s2"]} == {"heldout"}
    assert {r["set"] for r in rows["s3"]} == {"explore"}
    names = [r["name"] for s in G.STAGES for r in rows[s]]
    assert len(names) == len(set(names))
    # every 0xffffffff of s3 after every other row of it (E209's broken copy last)
    s3 = [r["args"] for r in rows["s3"]]
    first_ff = min(i for i, a in enumerate(s3) if "0xffffffff" in a)
    assert all("0xffffffff" in a for a in s3[first_ff:])
    for s in G.STAGES:
        assert open(os.path.join(KP, "tables", s + ".txt")).read().startswith(
            "#stage %s\n#limit 0\n" % s)


def test_heldout_rows_separate_the_rivals():
    rows = G.all_rows(MASK)["s1"]
    wrongable = {m: 0 for m in ("H-LM", "H-SWAP", "H-NOREAD")}
    for r, p in rows:
        vm = M.predict_tex("H-VM", p, MASK)
        assert len(vm) >= M.MIN_SCORED
        if r["set"] != "heldout":
            continue
        assert len(vm) >= 0.4 * len(MASK)
        for m in wrongable:
            d, both = M.differ(vm, M.predict_tex(m, p, MASK))
            if both and d > 0.1 * both and both >= M.MIN_SCORED:
                wrongable[m] += 1
        d, both = M.differ(vm, M.predict_tex("H-NOREAD", p, MASK))
        assert d >= 0.2 * both
    assert all(v >= 3 for v in wrongable.values()), wrongable


def test_heldout_values_are_eighths_and_seeded():
    for r, p in G.all_rows(MASK)["s1"]:
        for w, v in p.items():
            assert 3 <= w <= 8 and v in G.EIGHTHS
    assert G.SEED == "r9-k1"


def test_scorer_recomputes_the_frozen_predictions():
    import score as S
    for st in ("s1n", "s1", "s2", "s3"):
        preds = S.checked_preds(st, MASK)
        assert set(preds) == {r["name"] for r in K.table(KP, st)}


def test_identity_and_texel_decode():
    assert M.decode(M.texel(0, 0)) == (0, 0) and M.decode(M.texel(63, 17)) == (63, 17)
    assert M.decode(M.TRI) is None and M.decode(M.BG) is None
    ident = M.predict_tex("H-VM", {}, MASK)
    assert len(ident) == 3034 and all(ident[p] == p for p in ident)
    # bg:5 at its own value changes nothing (c-noop)
    assert M.predict_tex("H-VM", {5: M.ONE}, MASK) == ident


def test_vertex_moves_are_the_named_ones():
    for name, p in G.S2:
        tl, tr, bl = M.decoded_vertices(M.obj(p))
        assert re.fullmatch(r"v-(b\d\d-[mx]|tl|box80|u96|v96)", name)
        if name == "v-b18-m":
            assert tr == (80, 0)
        if name == "v-b20-m":
            assert bl == (0, 80)
        if name == "v-b16-m":
            assert tl == (-16, 0)
        if name == "v-b15-m":
            assert tl == (0, -16)
        if name in ("v-b19-m", "v-b19-x", "v-b22-m", "v-b22-x"):
            assert (tl, tr, bl) == M.BOX
