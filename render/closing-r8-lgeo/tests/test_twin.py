# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin. Every row against the plan (closing8/leftovers/exp-leftovers-r8.md,
session L2) and against the fake tool, which refuses what the rgn4 tool refuses:

- tx3: type 3 at 2 x 16, 4 x 8, 4 x 32, 2 x 8, 1 x 16 and type 1 at 2 x 16, 1 x 16 held out, three
  controls; tx4: 64 x 64 (2 windows), 128 x 64 (4), 128 x 128 (8), 256 x 32 (4), two controls, three
  soft linear rows last; tx5: the plan's stored values and dwords, four plain fills, four soft
  explore rows last;
- zs2: 165 rows, five steps a sweep, the plan's grid points, aims and targets, the aimed pixel on
  screen;
- q139: the plan's strides only inside the ranges that drew without a fault in the kept data, the
  four residue jobs with their datasets' own pokes;
- safe class: #limit 0 in every table, risk safe, no knob that expects a fault or a debugfs write;
- the plan's Q139 counts (closing8/leftovers/q139_o3_rivals.out) from gen/q139model.py."""
import os
import re
import shlex
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, HERE)
import kitscore as K  # noqa: E402
import kept as KD  # noqa: E402
import q139model as Q  # noqa: E402

STAGES = ("tx3", "tx4", "tx5", "zs2", "q139")
LEFT = "/Users/jtorra/src/scratch/resgx545/closing8/leftovers"


def rows(stage):
    return K.table(KP, stage)


def test_safe_class_only():
    for s in STAGES:
        head = [ln for ln in open(os.path.join(KP, "tables", s + ".txt")) if ln.startswith("#limit")]
        assert head == ["#limit 0\n"], s
        for t in rows(s):
            assert t["risk"] == "safe", t["name"]
            assert not {w for w in t["knobs"] if w == "expectfault" or w.startswith("dbg:")}, t["name"]
            assert "--kpoke " not in t["args"] and "--poke" not in t["args"].split(), t["name"]


def test_every_argv_is_one_the_tool_takes(tmp_path):
    W = KD._world()
    for s in STAGES:
        for t in rows(s):
            a = shlex.split(t["args"].replace("$S", KP).replace("$W", str(tmp_path)))
            if a[0] == "tri" and "--width" in a and a[a.index("--width") + 1] == "1280":
                continue                        # answered in test_score's worlds; 10 MB of text here
            r = W.answer(t["tool"], a, {"model"})
            assert r is not None and r.get("rc", 0) in (0, 1), (t["name"], r and r.get("err"))


def test_fake_refuses_what_the_tool_refuses(tmp_path):
    W = KD._world()
    b = os.path.join(KP, "bins/r8l-ty3-2x16.bin")
    assert W.answer("t4", ["probe", "--coords", "--pixels", "--bogus", b], {"model"})["rc"] == 2
    assert W.answer("t4", ["probe", "--scratch-pages", "8", b], {"model"})["rc"] == 2
    assert W.answer("t4", ["probe", "--pixels", str(tmp_path / "none.bin")], {"model"})["rc"] == 1
    assert W.answer("t4", ["tri", "--width", "33", "--height", "18", "--tri-unit", "12", "--tri-v", "0,0,1,1,2,2"],
                    {"model"})["rc"] == 1
    assert W.answer("t4", ["tri", "--width", "64", "--height", "64", "--frobnicate"], {"model"})["rc"] == 2


def sizes(stage, prefix, sset=None):
    out = []
    for t in rows(stage):
        if t["name"].startswith(prefix) and (sset is None or t["set"] == sset):
            out.append(t["name"])
    return out


def test_tx_rows_are_the_plans():
    assert sizes("tx3", "tx3-ctl") == ["tx3-ctl-ty3-32x16", "tx3-ctl-ty3-4x16", "tx3-ctl-ty1-4x16"]
    assert sizes("tx3", "tx3-ty", "heldout") == ["tx3-ty3-2x16", "tx3-ty3-4x8", "tx3-ty3-4x32", "tx3-ty3-2x8", "tx3-ty3-1x16",
                                                 "tx3-ty1-2x16", "tx3-ty1-1x16"]
    w = [n for n in sizes("tx4", "tx4-ty4-", "heldout")]
    assert len(w) == 18 and sum("64x64" in n for n in w) == 2 and sum("128x64" in n for n in w) == 4
    assert sum("128x128" in n for n in w) == 8 and sum("256x32" in n for n in w) == 4
    assert [t["name"] for t in rows("tx4")][-3:] == ["tx4-lin-ty3-32x16", "tx4-lin-ty3-24x8", "tx4-lin-ty3-40x8"]
    assert all("soft" in t["knobs"] for t in rows("tx4")[-3:])
    t5 = [t["name"] for t in rows("tx5")]
    for v in ("00000001", "00000002", "fffffffe", "fffffffd", "00000004", "00000008", "00010000", "80000000"):
        assert "tx5-8x8-v" + v in t5
    assert [n for n in t5 if "-j" in n] == ["tx5-8x8-j0", "tx5-8x8-j1", "tx5-8x8-j3", "tx5-8x8-j7", "tx5-16x16-j0",
                                            "tx5-16x16-j5", "tx5-16x16-j31"]
    assert [n for n in t5 if n.startswith("tx5-16x16-v")] == ["tx5-16x16-v00000001", "tx5-16x16-v00000002"]
    assert len([n for n in t5 if "plain" in n]) == 4
    assert [t["set"] for t in rows("tx5")][-4:] == ["explore"] * 4 and all("soft" in t["knobs"] for t in rows("tx5")[-4:])
    for s in ("tx3", "tx4", "tx5"):
        assert all("after" in t["knobs"] for t in rows(s))


def vertices(t):
    a = t["args"].split()
    return int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1]), [int(x) for x in a[a.index("--tri-v") + 1].split(",")]


def test_zs2_rows_are_the_plans():
    P = K.predictions(KP, "zs2")
    r = rows("zs2")
    assert len(r) == 165 and sum(t["set"] == "control" for t in r) == 5
    g = [t for t in r if t["name"].startswith("zs2-g-")]
    lr = [t for t in r if t["name"].startswith("zs2-l-")]
    tr = [t for t in r if t["name"].startswith("zs2-t-")]
    assert (len(g), len(lr), len(tr)) == (40, 80, 40)
    for t in g + lr + tr:
        w, h, v = vertices(t)
        off = [i for i, n in enumerate(v) if n % 16]
        assert len(off) == 1, t["name"]                      # one coordinate off the 1/256 grid, the swept one
        n = v[off[0]]
        assert (n - 8) % 16 in (14, 15, 0, 1, 2), t["name"]  # d = -2 .. +2 about the 1/512 tie
        x, y = (int(c) for c in P[t["name"]]["aimed_px"]["all"].split(","))
        assert 0 <= x < w and 0 <= y < h, t["name"]
        assert (w, h) == ((256, 512) if t in tr else (512, 256)), t["name"]
    names = {re.sub(r"-d(m\d|p\d|0)$", "", t["name"]) for t in g}
    assert names == {"zs2-g-m1o256-x", "zs2-g-m1o256-y", "zs2-g-m1.25-x", "zs2-g-m1.25-y", "zs2-g-m17.75-x",
                     "zs2-g-m17.75-y", "zs2-g-m200.5-x", "zs2-g-m100.5-y"}
    aims = {re.sub(r"-d(m\d|p\d|0)$", "", t["name"]) for t in lr}
    assert len(aims) == 16 and {a.rsplit("-a", 1)[1] for a in aims} == {"65", "68", "100", "300", "200", "1", "4", "190"}


def test_q139_rows_are_the_plans():
    r = rows("q139")
    st = {}
    for t in r:
        a = t["args"]
        assert "--keep-going" in a and '--dump-render "$W"' in a and "--tri-full --pixels" in a, t["name"]
        m = re.search(r"--kpoke-render 1:ta:146=(0x[0-9a-f]+)", a)
        w = int(re.search(r"--width (\d+)", a).group(1))
        if m:
            s = int(m.group(1), 16)
            st.setdefault((t["set"], w), []).append(s)
            assert (w == 256 and 0 <= s <= 31) or (w == 640 and 4 <= s <= 63), t["name"]   # drew without a fault
    assert st == {("control", 256): [4], ("fit", 256): [1, 2], ("heldout", 256): [3, 5, 6, 7, 12, 20],
                  ("heldout", 640): [5, 6, 7, 8, 12]}
    res = [t for t in r if t["set"] == "residue"]
    assert [t["name"] for t in res] == ["q139-res-256x256-m1-B2-10", "q139-res-256x256-m1-B2-11", "q139-res-640x480-m1-B1-23",
                                        "q139-res-1280x720-m2-B3p1"]
    assert [re.search(r"--kpoke-render (\S+)", t["args"]).group(1) for t in res] == [
        "1:ta:143=0x0100a004", "1:ta:143=0x0100b004", "1:ta:143=0x85c10018", "1:ta:144=0x03018025"]


@pytest.mark.skipif(not os.path.exists(os.path.join(LEFT, "q139_o3_rivals.out")), reason="SKIPPED, NOT PASSED: no plan outputs")
def test_q139_model_gives_the_plans_counts():
    """The planner's q139_o3_rivals.out: blkrow's wrong count and its distance to each rival."""
    names = {"raster": "raster", "blkdown": "blkdown", "mtblk": "mtblk"}
    n = 0
    for ln in open(os.path.join(LEFT, "q139_o3_rivals.out")):
        m = re.match(r"new +(\d+)x(\d+) stride +(\d+) blkrow +(\d+) wrong; differs from it in tiles: (.*)$", ln)
        if not m:
            continue
        w, h, s, nw = (int(x) for x in m.groups()[:4])
        diffs = dict(p.split(":") for p in m.group(5).split())
        a = "--kpoke-render 1:ta:146=0x%x" % s
        b = Q.wrong(Q.predict(w, h, a, "blkrow"))
        assert len(b) == nw
        for o, k in names.items():
            assert len(Q.wrong(Q.predict(w, h, a, o)) ^ b) == int(diffs[k]), (w, s, o)
        n += 1
    assert n == 13
