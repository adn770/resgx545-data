# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin. Every row against the plan (closing9/seeds/exp-seeds-r9.md
sections 5 and 6, session S9-lgeo) and against the fake tool, which refuses what the rgn4 tool
refuses:

- tx6: two controls (E910's type 4 64 x 32, E725's type 3 32 x 16, their programs byte for byte),
  seven type 4 windows of 48 x 64, 96 x 32 and 80 x 64, two type 3 rows of format 5, then the
  three soft linear type 1 rows last (the bridge first); every row `after needrows`, the default
  scratch;
- q139b: the two baselines (controls, `reads:hash,dump`), then 768 x 640 and 1280 x 720 m2-B3p1
  with their datasets' own poke (ta/mtile-fields/cases.tsv); every row the datasets' command with
  `--keep-going --dump-render "$W"` and `expectdiff` (a reading needs `job: ok`, E946's rule);
- safe class: #limit 0 in every table, risk safe, no knob that expects a fault or writes debugfs,
  no --kpoke or --poke, no --scratch-pages."""
import os
import re
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, HERE)
import kitscore as K  # noqa: E402
import kept as KD  # noqa: E402

STAGES = ("tx6", "q139b")


def rows(stage):
    return K.table(KP, stage)


def test_safe_class_only():
    for s in STAGES:
        head = [ln for ln in open(os.path.join(KP, "tables", s + ".txt")) if ln.startswith("#limit")]
        assert head == ["#limit 0\n"], s
        for t in rows(s):
            assert t["risk"] == "safe", t["name"]
            assert not {w for w in t["knobs"] if w == "expectfault" or w.startswith("dbg:") or w.startswith("expect:")}, t["name"]
            a = t["args"].split()
            assert "--kpoke" not in a and "--poke" not in a and "--scratch-pages" not in a, t["name"]


def test_every_argv_is_one_the_tool_takes(tmp_path):
    W = KD._world()
    for s in STAGES:
        for t in rows(s):
            a = shlex.split(t["args"].replace("$S", KP).replace("$W", str(tmp_path)))
            if a[0] == "tri" and "--width" in a and a[a.index("--width") + 1] == "1280":
                continue                        # answered in test_score's worlds; 10 MB of text here
            r = W.answer(t["tool"], a, {"model"})
            assert r is not None and r.get("rc", 0) in (0, 1), (t["name"], r and r.get("err"))
            if a[0] == "tri":
                assert "job: ok" in r["out"] and "\ndiff: " in r["out"], t["name"]


def test_fake_refuses_what_the_tool_refuses(tmp_path):
    W = KD._world()
    b = os.path.join(KP, "bins/r9l-ty3-f5-4x8.bin")
    assert W.answer("t4", ["probe", "--coords", "--pixels", "--bogus", b], {"model"})["rc"] == 2
    assert W.answer("t4", ["probe", "--scratch-pages", "8", b], {"model"})["rc"] == 2
    assert W.answer("t4", ["probe", "--pixels", str(tmp_path / "none.bin")], {"model"})["rc"] == 1
    assert W.answer("t4", ["tri", "--width", "33", "--height", "18", "--tri-full", "--dump-render", str(tmp_path)],
                    {"model"})["rc"] == 1
    assert W.answer("t4", ["tri", "--width", "64", "--height", "64", "--frobnicate"], {"model"})["rc"] == 2
    assert W.answer("t4", ["tri", "--width", "64", "--height", "64", "--tri-full", "--dump-render",
                           str(tmp_path / "nodir")], {"model"})["rc"] == 1


def test_tx6_rows_are_the_plans():
    r = rows("tx6")
    names = [t["name"] for t in r]
    assert names[:2] == ["tx6-ctl-ty4-64x32", "tx6-ctl-ty3-32x16"]
    assert all(t["set"] == "control" and "reads:rows" in t["knobs"] for t in r[:2])
    w4 = [n for n in names if n.startswith("tx6-ty4-")]
    assert w4 == ["tx6-ty4-48x64-x0y0", "tx6-ty4-48x64-x0y32", "tx6-ty4-96x32-x64y0", "tx6-ty4-80x64-x0y0",
                  "tx6-ty4-80x64-x64y0", "tx6-ty4-80x64-x0y32", "tx6-ty4-80x64-x64y32"]
    assert [n for n in names if n.startswith("tx6-ty3-f5-")] == ["tx6-ty3-f5-4x8", "tx6-ty3-f5-8x8"]
    assert names[-3:] == ["tx6-lin-ty1-32x16", "tx6-lin-ty1-24x8", "tx6-lin-ty1-40x8"]
    assert [t["set"] for t in r[-3:]] == ["bridge", "heldout", "heldout"]
    assert all("soft" in t["knobs"] for t in r[-3:]) and not any("soft" in t["knobs"] for t in r[:-3])
    assert all({"after", "needrows"} <= set(t["knobs"]) for t in r)
    assert all(t["args"].startswith("probe --temps 32 --coords --pixels \"$S/bins/") for t in r)


def test_q139b_rows_are_the_plans():
    r = rows("q139b")
    assert [(t["name"], t["set"]) for t in r] == [("q139b-ctl-1280x720", "control"), ("q139b-ctl-768x640", "control"),
                                                  ("q139b-res-768x640-m2-B3p1", "heldout"),
                                                  ("q139b-res-1280x720-m2-B3p1", "residue")]
    ds = {}
    for ln in KD.blob("ta/mtile-fields/cases.tsv").decode().splitlines()[1:]:
        p = ln.split("\t")
        ds[p[0]] = p[4] if len(p) > 4 else ""
    for t in r:
        a = t["args"]
        assert a.startswith("tri --tri-full --pixels ") and a.endswith(' --keep-going --dump-render "$W"'), t["name"]
        assert {"expectdiff", "needhash"} <= set(t["knobs"]), t["name"]
        assert ("reads:hash,dump" in t["knobs"]) == (t["set"] == "control"), t["name"]
        w, h = (int(x) for x in re.search(r"--width (\d+) --height (\d+)", a).groups())
        assert "--max-width %d --max-height %d" % (w, h) in a
        dsn = "q100-%dx%d-%s" % (w, h, "ctl-r1" if t["set"] == "control" else "m2-B3p1")
        assert " ".join(re.findall(r"--kpoke-render \S+", a)) == ds[dsn], t["name"]
