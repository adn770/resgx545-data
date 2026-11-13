# SPDX-License-Identifier: MIT
"""r10-dpm: the generator is current, session.toml declares what the table uses, the rows are the
plan's (S10-dpm of closing10/seeds/exp-seeds-r10.md section 10: safe class, calibrations only, 17
rows, every row `expect:rc3-overflow` and `dbg:render_pb_pages=0x422` but the a0 pair's first), the
a0 pair is r9-ldpm's published a0 pair token for token, the frozen rivals are in the predictions in
the form the scorer reads, and the data the generator copies is the published blob."""
import hashlib
import os
import pathlib
import re
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

DATA = pathlib.Path.home() / "src/resgx545-data"
CFG = tomllib.loads((KP / "session.toml").read_text())
ROWS = K.table(str(KP), "s6rep")


def blob(repo, commit, path):
    return subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True,
                          check=True).stdout


def test_generator_current():
    assert subprocess.run([sys.executable, str(KP / "gen/plan.py"), "--check"]).returncode == 0


def test_one_stage_of_17_rows_in_order():
    assert list(CFG["stages"]) == list(PL.STAGES) == ["s6rep"]
    assert len(ROWS) == 17
    names = [r["name"] for r in ROWS]
    assert names[:2] == ["a0-cal-2048", "a0-cal-2048f"]
    assert [r["set"] for r in ROWS] == ["control"] * 2 + ["heldout"] * 15


def test_three_replicates_per_target_round_robin():
    reps = ROWS[2:]
    tags = [PL.tag(*t) for t in PL.TARGETS]
    assert tags == ["c1604", "c1606", "c1404", "c0802", "c0809"]
    assert [r["name"] for r in reps] == [f"s6r-{t}-{k}" for k in (1, 2, 3) for t in tags]
    for k in range(3):                                     # a replicate never follows its own target
        assert len({PL.target(r) for r in reps[5 * k:5 * k + 5]}) == 5


def test_safe_class_only():
    txt = (KP / "tables/s6rep.txt").read_text()
    assert "#limit 0" in txt
    for r in ROWS:
        assert r["risk"] == "safe"
        assert "expectfault" not in r["knobs"] and "expectdiff" not in r["knobs"]
        assert not re.search(r"--kpoke|--fault|--poke|--vtx-coords|--slot", r["args"])


def test_every_row_is_a_probe_calibration_with_its_premise():
    for r in ROWS:
        a = shlex.split(r["args"])
        assert r["tool"] == "rt" and a[:5] == ["0", "0.3", PL.RT, "--", "$HOME/sgxfive-test-rgn4"]
        assert a[5:8] == ["probe", "--tri", "pixel"] and a[a.index("--vertices") + 1] == "1500"
        assert "expect:rc3-overflow" in r["knobs"]
        assert sum(k.startswith("dbg:render_pb_pages=") for k in r["knobs"]) == 1
        w, h = PL.target(r)
        S, A, U, _ = PL.model(w, h)
        if r["set"] == "heldout":
            assert "dbg:render_pb_pages=0x422" in r["knobs"] and PL.thr0_of(r) == 0x400 > U
            assert (w, h) in PL.TARGETS and "--dump-render" not in a
        else:
            assert (w, h) == (2048, 2048)


def test_session_toml_declares_the_table():
    T = PL.tables()
    assert CFG["extra_knobs"] == PL.extra_knobs(T)
    assert CFG["knobs"]["render_pb_pages"]["values"] == PL.knob_values(T) == ["0x162", "0x422"]
    assert CFG["knobs"]["render_pb_pages"]["default"] == "0x422"
    assert CFG["tools"]["rt"]["wraps"] is True
    assert CFG["srcversion"] == "B60AB0B475DD1E8972419B5" and CFG["prefix"] == "r10d"
    assert CFG["tools"]["t4"]["source_sha256"] == "703cbceaae8cdff3eda280b7ef89f3c5ef14ba7d378dd269bc66ef714aaead69"
    assert CFG["tools"]["t4"]["sha256"] == "e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a"
    for p in ("gen/r9_tables.json", "score/read.py", "bins/p1139-green.bin"):
        assert f"data:render/closing-r9-ldpm/{p}" in CFG["freeze"]["pins"]


def test_a0_pair_is_r9_ldpms_token_for_token():
    c = CFG["freeze"]["data"]
    theirs = {ln.split("|")[0]: ln for ln in blob(DATA, c, "render/closing-r9-ldpm/tables/a0.txt").decode().splitlines()
              if ln.startswith("a0-cal-2048")}
    mine = {ln.split("|")[0]: ln for ln in (KP / "tables/s6rep.txt").read_text().splitlines()
            if ln.startswith("a0-cal-2048")}
    assert len(mine) == 2 and mine == theirs


def test_controls_can_fail_and_declare_reads():
    for r in ROWS:
        if r["set"] == "control":
            assert r["reads"], r["name"]
    preds = K.predictions(str(KP), "s6rep")
    assert preds["a0-cal-2048"]["gps_left"]["CTL"] == "0x2"
    assert preds["a0-cal-2048f"]["need"]["CTL"] == "0x213" and preds["a0-cal-2048f"]["s6"]["H-STEPMODEL"] == "0x181"


def test_the_frozen_rivals_are_in_the_predictions_as_the_scorer_reads_them():
    preds = K.predictions(str(KP), "s6rep")
    for w, h in PL.TARGETS:
        S, A, U, _ = PL.model(w, h)
        R = S[6]
        Rv, span, bias = SC.frozen_target(preds, w, h)
        assert (Rv, span, bias) == (R, 2, (1, 2))
        assert PL.KEPT[(w, h)] - R in (1, 2)               # the kept reads E962 and E936 quote
        for k in (1, 2, 3):
            p = preds[f"s6r-{PL.tag(w, h)}-{k}"]
            assert p["S6"]["H-REPLAY6"] == hex(R) and p["S6"]["H-BIAS-SAME"] == hex(PL.KEPT[(w, h)])
            assert p["need"]["H-REPLAY"] == hex(U) and p["nparts"]["H-REPLAY"] == "0"
            assert ("S6_range" in p) == (k == 1)
    assert {k: hex(v) for k, v in PL.KEPT.items()} == {
        (4096, 1024): "0x17e", (4096, 1536): "0x22b", (3584, 1024): "0x14f", (2048, 512): "0x6f",
        (2048, 2304): "0x1ad"}


def test_the_replay_s6_are_e962s():
    got = {k: PL.model(*k)[0][6] for k in PL.TARGETS}
    assert got == {(4096, 1024): 0x17c, (4096, 1536): 0x229, (3584, 1024): 0x14d, (2048, 512): 0x6e,
                   (2048, 2304): 0x1ac}


def test_the_world_takes_every_row():
    os.environ.setdefault("FAKE_DBGREAL", "/nonexistent")
    for r in ROWS:
        a = shlex.split(r["args"].replace("$HOME", "/h").replace("$W", "/w").replace("$S", str(KP)))
        assert WD.answer("rt", a, {"model"}) is None, r["name"]
        got = WD.answer("t4", a[5:], {"model"})
        assert got is not None and got.get("rc") != 2, (r["name"], got)
    assert WD.answer("t4", ["probe", "--tri", "pixel", "--vtx-coords", "8", str(KP / "bins/p1139-green.bin")],
                     {"model"})["rc"] == 2


def test_the_copies_are_the_published_blobs():
    c = CFG["freeze"]["data"]
    for mine, theirs in (("gen/r9_tables.json", "gen/r9_tables.json"), ("score/read.py", "score/read.py"),
                         ("bins/p1139-green.bin", "bins/p1139-green.bin")):
        assert (KP / mine).read_bytes() == blob(DATA, c, f"render/closing-r9-ldpm/{theirs}")
    assert hashlib.sha256((KP / "bins/p1139-green.bin").read_bytes()).hexdigest().startswith("dae26442")
