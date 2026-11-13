# SPDX-License-Identifier: MIT
"""r9-ldpm: the generator is current, session.toml declares what the tables use, the rows are the
plan's (S9-ldpm, safe class, every probe row `expect:rc3-overflow`, no 8-pair row, a0 the argv
twin of r8-ldpm's a0), the offline steps OD-1 to OD-3 were frozen before their scoring and decide
what the generator reads (k2 does not run), and the program binary is the pinned one."""
import hashlib
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tomllib

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "gen"), str(KP / "kit"), str(KP / "mock")]
import plan as PL  # noqa: E402
import kitscore as K  # noqa: E402
import world as WD  # noqa: E402

DATA = pathlib.Path.home() / "src/resgx545-data"
CFG = tomllib.loads((KP / "session.toml").read_text())
R8 = DATA / "render/closing-r8-ldpm"
OFF = KP / "offline"


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def blob(repo, commit, path):
    return subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True,
                          check=True).stdout


def test_generator_current():
    assert subprocess.run([sys.executable, str(KP / "gen/plan.py"), "--check"]).returncode == 0


def test_job_counts_and_order():
    T = PL.tables()
    assert list(CFG["stages"]) == list(PL.STAGES) == ["a0", "m6b", "w", "f9b"]
    n = {s: len(T[s]) for s in T}
    assert n["a0"] == 6 and n["m6b"] == 34 and n["w"] == 8
    assert n["f9b"] == 3 + sum(len(x["cells"]) for x in PL.T["f9b"])
    assert "k2" not in T                     # OD-3: 7 of 20, below 18 (offline/od3_score.out)


def test_safe_class_only():
    for st in PL.STAGES:
        txt = (KP / "tables" / f"{st}.txt").read_text()
        assert "#limit 0" in txt
        for r in K.table(str(KP), st):
            assert r["risk"] == "safe"
            assert "expectfault" not in r["knobs"]
            assert not re.search(r"--kpoke|--fault|--poke|--vtx-coords|--slot", r["args"])


def test_every_probe_row_expects_the_overflow_and_runs_1500_vertices():
    for st in PL.STAGES:
        for r in K.table(str(KP), st):
            a = shlex.split(r["args"])
            kind = a[5]
            if kind == "probe":
                assert "expect:rc3-overflow" in r["knobs"], r["name"]
                assert a[6:8] == ["--tri", "pixel"] and a[a.index("--vertices") + 1] == "1500"
            else:
                assert r["name"] == "a0-qf-0xa2" and "expectdiff" in r["knobs"]


def test_session_toml_declares_the_tables():
    T = PL.tables()
    assert CFG["extra_knobs"] == PL.extra_knobs(T)
    assert CFG["knobs"]["render_pb_pages"]["values"] == PL.knob_values(T)
    assert CFG["knobs"]["render_pb_pages"]["default"] == "0x422"
    assert CFG["tools"]["rt"]["wraps"] is True
    assert CFG["srcversion"] == "B60AB0B475DD1E8972419B5" and CFG["prefix"] == "r9l"
    assert CFG["tools"]["t4"]["source_sha256"] == "703cbceaae8cdff3eda280b7ef89f3c5ef14ba7d378dd269bc66ef714aaead69"


def test_every_row_runs_t4_under_regtimeline_with_r5_registers():
    for st in PL.STAGES:
        for r in K.table(str(KP), st):
            a = shlex.split(r["args"])
            assert r["tool"] == "rt" and a[:5] == ["0", "0.3", PL.RT, "--", "$HOME/sgxfive-test-rgn4"]
            assert sum(k.startswith("dbg:render_pb_pages=") for k in r["knobs"]) == 1


def test_a0_is_r8_ldpms_a0_token_for_token():
    """The six a0 rows are r8-ldpm's (E935), their names, knobs and argv, as published."""
    c = CFG["freeze"]["data"]
    theirs = [ln for ln in blob(DATA, c, "render/closing-r8-ldpm/tables/a0.txt").decode().splitlines()
              if ln and not ln.startswith("#")]
    mine = [ln for ln in (KP / "tables/a0.txt").read_text().splitlines() if ln and not ln.startswith("#")]
    assert mine == theirs


def test_controls_can_fail_and_declare_reads():
    for st in PL.STAGES:
        for r in K.table(str(KP), st):
            if r["set"] == "control":
                assert r["reads"], r["name"]
    preds = K.predictions(str(KP), "m6b")
    vals = {preds[r["name"]]["gps_next"]["CTL"] for r in K.table(str(KP), "m6b") if r["set"] == "control"}
    assert vals == {"1", "2"}                # both readings frozen: a replicate can fail either way


def test_m6b_cells_are_band_6_and_not_steps():
    for m in PL.T["m6b"]:
        S, A, U, after = PL.model(m["w"], m["h"])
        assert U < 0x3F0
        for d in range(PL.WIN[0], PL.WIN[1] + 1):
            t = A[6] + d
            assert S[6] < t < S[7] and t not in S.values()
    parting = [m for m in PL.T["m6b"] if m["E6"] != m["A6"]]
    assert len(parting) >= 1, "no m6b target parts H-NEXT1 from H-SPAN"


def test_w_and_f9b_targets_are_below_the_clamp_and_new():
    seen = {(2048, 2048), (3072, 2048), (2048, 3072), (1536, 1536), (1024, 1024), (4096, 2048),
            (2560, 2560), (2560, 3072), (3072, 2560), (3072, 3072), (2048, 4096), (4096, 4096)}
    for x in PL.T["w"] + PL.T["f9b"]:
        assert int(x["U"], 16) < 0x3F0 and (x["w"], x["h"]) not in seen


def test_the_world_takes_every_row():
    os.environ.setdefault("FAKE_DBGREAL", "/nonexistent")
    for st in PL.STAGES:
        for r in K.table(str(KP), st):
            a = shlex.split(r["args"].replace("$HOME", "/h").replace("$W", "/w").replace("$S", str(KP)))
            assert WD.answer("rt", a, {"model"}) is None, r["name"]
            got = WD.answer("t4", a[5:], {"model"})
            assert got is not None and got.get("rc") != 2, (r["name"], got)
    assert WD.answer("t4", ["probe", "--tri", "pixel", "--vtx-coords", "8", str(KP / "bins/p1139-green.bin")],
                     {"model"})["rc"] == 2


def test_p1139_is_the_pinned_r7_program():
    b = blob(DATA, CFG["freeze"]["data"], "render/closing-r7-dpm/bins/p1139-green.bin")
    assert b == (KP / "bins/p1139-green.bin").read_bytes()


# ---- the offline steps -------------------------------------------------------------------------
def freeze_lines(name):
    return (OFF / name).read_text().splitlines()


def test_offline_freezes_name_the_files_as_they_are():
    """Every `<sha256>  <file>` line of the FREEZE files names a file of offline/ with that hash
    (the last line of a name wins: a script frozen, kept as-run, then fixed). The one path outside
    offline/, r8-ldpm's reader, is the published blob (test_offline_copies_are_the_published_r8_files)."""
    for frz in ("FREEZE-od1.sha256", "FREEZE-od2.sha256", "FREEZE-od3.sha256", "FREEZE-tables.sha256"):
        last = {}
        for ln in freeze_lines(frz):
            p = ln.split()
            if len(p) == 2 and re.fullmatch(r"[0-9a-f]{64}", p[0]) and not p[1].startswith("../"):
                last[p[1]] = p[0]
        for f, h in last.items():
            assert sha(OFF / f) == h, (frz, f)


def test_offline_copies_are_the_published_r8_files():
    c = CFG["freeze"]["data"]
    for mine, theirs in (("ol7lib.py", "gen/ol7/ol7lib.py"), ("ol7_b_multikick.py", "gen/ol7/ol7_b_multikick.py")):
        assert (OFF / mine).read_bytes() == blob(DATA, c, f"render/closing-r8-ldpm/{theirs}")
    want = hashlib.sha256(blob(DATA, c, "render/closing-r8-ldpm/score/read.py")).hexdigest()
    assert f"{want}  ../../../closing8/r8-ldpm/score/read.py" in (OFF / "FREEZE-od2.sha256").read_text()


def test_tables_are_the_offline_run():
    assert (KP / "gen/r9_tables.json").read_bytes() == (OFF / "r9_tables.json").read_bytes()
    t = json.loads((OFF / "r9_tables.json").read_text())
    assert t["od2_frozen"] == json.loads((OFF / "od2_band6.json").read_text())["frozen"] == "H-NEXT1"
    assert t["w"] == json.loads((OFF / "od1_wide.json").read_text())["w"]


def test_od3_decides_no_k2():
    out = (OFF / "od3_score.out").read_text()
    assert "OD-3 VERDICT: H-FLUSH gives 7 of 20 counts: stage k2 does NOT run (fewer than 18)" in out
    assert "frozen candidate: H-FLUSH" in (OFF / "FREEZE-od3.sha256").read_text()
