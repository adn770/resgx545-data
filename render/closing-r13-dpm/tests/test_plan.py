# SPDX-License-Identifier: MIT
"""r13-dpm: the generator is current, session.toml declares what the table uses, the rows are the
plan's (rank-round13.md section 2, pr2: one scene at partial-render counts 0, 1, 2, 4, two replicates
each, safe class, regtimeline over t10), the counts are r8-ldpm's kept counts of the scene, the
frozen rivals are in the predictions in the form the scorer reads, and the program is the published
blob."""
import gzip
import hashlib
import os
import pathlib
import shlex
import subprocess
import sys
import tomllib

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "gen"), str(KP / "kit"), str(KP / "mock"), str(KP / "score")]
import plan as PL  # noqa: E402
import kitscore as K  # noqa: E402
import world as WD  # noqa: E402
import score as SC  # noqa: E402
import read as R  # noqa: E402

DATA = pathlib.Path.home() / "src/resgx545-data"
CFG = tomllib.loads((KP / "session.toml").read_text())
ROWS = K.table(str(KP), "pr2")
R8 = DATA / "render/closing-r8-ldpm/out/20261113-021431"


def blob(repo, commit, path):
    return subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True,
                          check=True).stdout


def test_generator_current():
    assert subprocess.run([sys.executable, str(KP / "gen/plan.py"), "--check"]).returncode == 0


def test_one_stage_of_8_rows_two_per_count():
    assert list(CFG["stages"]) == list(PL.STAGES) == ["pr2"]
    assert len(ROWS) == 8
    prs = [PL.pr_of(r) for r in ROWS]
    assert sorted(prs) == [0, 0, 1, 1, 2, 2, 4, 4]
    assert all(a != b for a, b in zip(prs, prs[1:]))              # no row follows its own count
    assert [r["set"] for r in ROWS] == ["control" if p == 0 else "heldout" for p in prs]
    assert [r["name"] for r in ROWS][:2] == ["pr2-c0-1", "pr2-c1-1"]


def test_safe_class_only():
    assert "#limit 0" in (KP / "tables/pr2.txt").read_text()
    for r in ROWS:
        assert r["risk"] == "safe"
        assert not {"expectfault", "expectdiff", "soft", "after"} & set(r["knobs"])
        assert "--kpoke" not in r["args"] and "--fault" not in r["args"] and "--poke" not in r["args"]


def test_every_row_is_the_same_scene_under_regtimeline_over_t10():
    for r in ROWS:
        a = shlex.split(r["args"])
        assert r["tool"] == "rt" and a[:5] == ["0", "0.3", PL.RT, "--", "$HOME/sgxfive-test-t10"]
        assert a[5:8] == ["probe", "--tri", "pixel"] and a[a.index("--vertices") + 1] == "1500"
        assert (int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])) == (3072, 2048)
        assert a[-1] == "$S/bins/p1139-green.bin"
        assert "expect:rc3-overflow" in r["knobs"]
        assert sum(k.startswith("dbg:render_pb_pages=") for k in r["knobs"]) == 1
        assert PL.thr0_of(r) == PL.THR0[PL.pr_of(r)]


def test_counts_are_r8_ldpms_kept_counts_of_the_scene():
    """thr0 -> partial renders, read from the published r8-ldpm jobs of 3072x2048 (the counts the
    session repeats): 0x400 0, 0x294 1, 0x1a0 2, 0xc0 4."""
    kept = {0x400: R8 / "f9/f9-cal-c1208", 0x294: R8 / "m6/m6-c1208-0x294", 0x1A0: R8 / "f9/f9-c1208-0x1a0",
            0xC0: R8 / "f9/f9-c1208-0xc0"}
    for c, thr0 in PL.THR0.items():
        rd = R.reading(gzip.open(f"{kept[thr0]}.txt.gz").read().decode(errors="replace"))
        assert (rd["nparts"], rd["knob"]) == (c, thr0)


def test_session_toml_declares_the_table():
    T = PL.tables()
    assert CFG["extra_knobs"] == PL.extra_knobs(T) == ["ctl:nparts=0"]
    assert CFG["knobs"]["render_pb_pages"]["values"] == PL.knob_values(T) == ["0xe2", "0x1c2", "0x2b6", "0x422"]
    assert CFG["knobs"]["render_pb_pages"]["default"] == "0x422"
    assert CFG["tools"]["rt"]["wraps"] is True
    assert CFG["srcversion"] == "B60AB0B475DD1E8972419B5" and CFG["prefix"] == "r13d"
    t = CFG["tools"]["t10"]
    assert t["sha256"] == "9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb"
    assert t["built_from"].startswith("a581c06bb24d2f77e03d9b64f7ca1b2d5487b59f:")
    assert CFG["health_tool"] == "t10"
    for p in ("bins/p1139-green.bin",):
        assert f"data:render/closing-r9-ldpm/{p}" in CFG["freeze"]["pins"]


def test_controls_can_fail_and_declare_reads():
    preds = K.predictions(str(KP), "pr2")
    for r in ROWS:
        if r["set"] == "control":
            assert r["reads"] == ("nparts", "knob", "clr") and "ctl:nparts=0" in r["knobs"]
            assert preds[r["name"]]["nparts"]["CTL"] == "0" and preds[r["name"]]["clr"]["CTL"] == "0"
        else:
            assert not r["reads"]
    assert SC.producible(ROWS[0]) >= set(ROWS[0]["reads"])


def test_the_frozen_rivals_are_in_the_predictions_as_the_scorer_reads_them():
    preds = K.predictions(str(KP), "pr2")
    assert SC.frozen_constants(preds) == (0.1708, 0.00108, 0.439)
    for r in ROWS:
        c, p = PL.pr_of(r), preds[r["name"]]
        assert p["nparts"]["H-COUNT"] == str(c) and p["hi10"]["H0"] == "0"
        assert p["knob"]["CTL"] == hex(PL.THR0[c])
        assert ("H-PR-STRICT" in p["clr"]) == (c > 0)
        if c:
            assert p["clr"]["H-PR-STRICT"] == f">={c}"
        assert p["p_clear"]["H-R-PR"] == f"1-exp(-0.1708*{c})"


def test_the_world_takes_every_row():
    os.environ.setdefault("FAKE_DBGREAL", "/nonexistent")
    for r in ROWS:
        a = shlex.split(r["args"].replace("$HOME", "/h").replace("$W", "/w").replace("$S", str(KP)))
        assert WD.answer("rt", a, {"model"}) is None, r["name"]
        got = WD.answer("t10", a[5:], {"model"})
        assert got is not None and got.get("rc") != 2, (r["name"], got)
    prog = str(KP / "bins/p1139-green.bin")
    for bad in (["--vtx-coords", "8"], ["--dump-render", "/w"], ["--cmd", "16=0x3c"]):
        assert WD.answer("t10", ["probe", "--tri", "pixel", *bad, prog], {"model"})["rc"] == 2
    assert WD.answer("rt", ["0", "0.3", "0x0748", "--", "x"], {"model"})["rc"] == 2


def test_the_program_is_the_published_blob():
    c = CFG["freeze"]["data"]
    assert (KP / "bins/p1139-green.bin").read_bytes() == blob(DATA, c, "render/closing-r9-ldpm/bins/p1139-green.bin")
    assert hashlib.sha256((KP / "bins/p1139-green.bin").read_bytes()).hexdigest().startswith("dae26442")
