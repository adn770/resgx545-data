# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer on synthetic attempts, each row's kept files written from
mock/world.py's answer under a world (the fork's read-out lines, the tool's lines, the kernel's
BIF fault line), as the runner keeps them: the clause rule must RETIRE on the frozen hypotheses
and on each decided rival, and NARROW when a control fails or a stage did not run; and
run/hooks.sh's hook_reading and hook_check (bash, on the same files) are the scorer's twin and
stop where the plan says."""
import os
import subprocess
import sys

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "mock"))
import make as M  # noqa: E402
import score as S  # noqa: E402
import world as W  # noqa: E402

HEADER = "\t".join(S.K.COLUMNS) + "\n"


def knobs_of(words):
    return {w[4:].split("=")[0]: w.split("=")[1] for w in words.split() if w.startswith("dbg:")}


def run_row(tmp, row, world, monkeypatch):
    """(answer, the row's class as the runner classifies it) with the row's knobs written."""
    dbg = tmp / "dbg"
    dbg.mkdir(exist_ok=True)
    k = knobs_of(row["knobs"])
    for n in ("vm_pde_addr", "vm_pde_size", "vm_pde_layout"):
        (dbg / n).write_text(k.get(n, "0") + "\n")
    monkeypatch.setenv("FAKE_DBGREAL", str(dbg))
    wd = tmp / "w"
    wd.mkdir(exist_ok=True)
    for f in wd.iterdir():
        f.unlink()
    argv = M.job(row["kind"], *row["va"]).replace('"$W"', str(wd)).split()
    a = W.answer("t30", argv, set(world.split(",")))
    for p, data in a.get("files", {}).items():
        open(p, "w").write(data)
    blob = a.get("out", "") + "\n".join(a.get("kmsg", []))
    rc = a.get("rc", 0)
    if "BIF fault" in blob or "faulted" in blob:
        cls = "fault"
    elif "hung" in blob:
        cls = "hang"
    elif rc == 0 or (rc == 1 and "expectdiff" in row["knobs"] and "job: ok" in blob and "diff:" in blob):
        cls = "ok"
    else:
        cls = "fail"
    return a, cls, argv, wd


def attempt(tmp, world, monkeypatch, stages=M.STAGES, limit=True):
    """Write an attempt ROOT/STAGE/... as the runner keeps it; the #limit and the gates as the
    driver applies them (a stage whose gate closes is not written)."""
    root = tmp / "att"
    rows = M.rows()
    for st in stages:
        if st != "s0" and subprocess.run([sys.executable, "-B", os.path.join(KP, "score", "score.py"),
                                          "gate", st, str(root)], capture_output=True).returncode:
            continue
        d = root / st
        d.mkdir(parents=True)
        cases, void, events, stop = [HEADER], [HEADER], 0, False
        for r in rows[st]:
            if stop:
                break
            (tmp / st).mkdir(exist_ok=True)
            a, cls, argv, wd = run_row(tmp / st, r, world, monkeypatch)
            n = r["name"]
            (d / f"{n}.txt").write_text(a.get("out", ""))
            (d / f"{n}.dmesg").write_text("".join(f"gma500: [drm] {ln}\n" for ln in a.get("kmsg", [])))
            (d / f"{n}.snap9.regs").write_text("reg 0x0c04 0x00000000\nreg 0x0c08 0x00000000\n")
            if (wd / "vm_large.txt").exists():
                (d / f"{n}.vm_large.txt").write_text((wd / "vm_large.txt").read_text())
            line = "\t".join([n, st, r["set"], "risky", r["knobs"], "t30", " ".join(argv),
                              str(a.get("rc", 0)), cls, "-", "-", "1000"]) + "\n"
            (void if cls == "fail" else cases).append(line)
            if cls in ("fault", "hang"):
                events += 1
                stop = limit and events >= M.LIMIT[st]
        (d / "cases.tsv").write_text("".join(cases))
        (d / "void.tsv").write_text("".join(void))
        (d / "readings.tsv").write_text("name\treads\treading\n")
    return root


def q109(root):
    return "\n".join(S.q109_rule(str(root)))


def test_model_world_retires(tmp_path, monkeypatch):
    out = q109(attempt(tmp_path, "model", monkeypatch))
    assert "Q109 RULE: RETIRE" in out, out
    for c in (1, 2, 3, 4, 5):
        assert f"CLAUSE 1 code {c}: translates" in out
    assert "index H-DENSE" in out and "mask H-MASK-S" in out and "offset H-PTOFF-IGN" in out
    assert "CLAUSE 3 code 6: faults, BIF status 0x30005 both times" in out


def test_layout_world_retires_on_the_rivals(tmp_path, monkeypatch):
    out = q109(attempt(tmp_path, "layout", monkeypatch))
    assert "Q109 RULE: RETIRE" in out and "mask H-MASK4K" in out and "offset H-PTOFF-USE" in out, out


def test_alt_world_retires_with_the_size_field_ignored(tmp_path, monkeypatch):
    out = q109(attempt(tmp_path, "alt", monkeypatch))
    assert "CLAUSE 1 code 3: as 4 KiB" in out and "CLAUSE 2: moot" in out, out
    assert "CLAUSE 3 code 7: taken as a size" in out and "RETIRE" in out, out


def test_hangs_on_the_unnamed_codes_are_a_reading(tmp_path, monkeypatch):
    out = q109(attempt(tmp_path, "f67hang", monkeypatch))
    assert "CLAUSE 3 code 6: stalls" in out and "RETIRE" in out, out


def test_a_failed_control_or_a_stopped_stage_narrows(tmp_path, monkeypatch):
    out = q109(attempt(tmp_path / "a", "s0kdiff", monkeypatch))
    assert "NARROW" in out and "s0 controls" in out, out
    out = q109(attempt(tmp_path / "b", "faultall", monkeypatch, stages=("s0", "f1")))
    assert "NARROW" in out and "clause 1 code 3" in out and "clause 3 code 6" in out, out
    out = q109(attempt(tmp_path / "c", "nowarm", monkeypatch))
    assert "NARROW" in out and "clause 1 code 4" in out and "clause 1 code 5" in out, out


def test_s0_scores_and_gates(tmp_path, monkeypatch):
    root = attempt(tmp_path, "model", monkeypatch, stages=("s0",))
    out = "\n".join(S.score_s0(str(root / "s0"), [str(root)]))
    assert "8 of 8 references passed; s0-warm held" in out, out
    assert all(f"GATE {st}: open" in out for st in ("f1", "f2", "f45", "f67")), out
    root = attempt(tmp_path / "w", "nowarm", monkeypatch, stages=("s0",))
    out = "\n".join(S.score_s0(str(root / "s0"), [str(root)]))
    assert "GATE f1: open" in out and "GATE f45: closed" in out, out


def test_flagged_stage_summary_names_the_frozen_hypothesis(tmp_path, monkeypatch):
    root = attempt(tmp_path, "model", monkeypatch)
    out = "\n".join(S.score_stage("f1", str(root / "f1"), [str(root)]))
    assert "SUMMARY: f1: H-DENSE: a PDE of size S translates" in out and "(9 of 9 rows decided)" in out, out
    assert "SUMMARY: f1: H-4K: " in out and "is not supported" in out


# ---- run/hooks.sh, the twin -------------------------------------------------------------------
def hook(fn, name, d, wd, row):
    """Run a hook in bash with the runner's variables, on a row's kept files."""
    jw = d / "jw"
    jw.mkdir(exist_ok=True)
    (jw / f"{name}.out").write_text((d / f"{name}.txt").read_text())
    (jw / f"{name}.dmesg").write_text((d / f"{name}.dmesg").read_text())
    w = d / "jw-w"
    w.mkdir(exist_ok=True)
    for f in w.iterdir():
        f.unlink()
    if (d / f"{name}.vm_large.txt").exists():
        (w / "vm_large.txt").write_text((d / f"{name}.vm_large.txt").read_text())
    script = (f'. "{KP}/run/hooks.sh"; JW="{jw}"; W="{w}"; STAGED="{KP}"; STAGE=x; class=ok; '
              f'knobs="{row["knobs"]}"; args="{M.job(row["kind"], *row["va"])}"; {fn} "{name}"')
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


@pytest.mark.parametrize("world", ["model", "layout", "alt"])
def test_hook_reading_is_the_scorers_twin(tmp_path, monkeypatch, world):
    root = attempt(tmp_path, world, monkeypatch, limit=False)
    n = 0
    for st, rows in M.rows().items():
        d = root / st
        if not d.exists():
            continue
        cases = S.K.rows(str(d), "cases.tsv")
        for r in rows:
            if r["name"] not in cases or cases[r["name"]]["class"] != "ok":
                continue
            got = dict(ln.split("=", 1) for ln in hook("hook_reading", r["name"], d, None, r).split())
            want = {k: v for k, v in S.reading(cases, str(d), r["name"]).items()
                    if k in ("job", "diff", "large", "table", "changed", "tags")}
            assert got == want, (r["name"], got, want)
            assert hook("hook_check", r["name"], d, None, r) == "", r["name"]
            n += 1
    assert n >= 20


@pytest.mark.parametrize("world,row,why", [
    ("outside", "c1-f", "page 0:1 changed, outside"),
    ("copychg", "c2-a", "a copy changed the region"),
    ("tablechg", "c3-m", "the table page changed"),
])
def test_hook_check_stops_where_the_plan_says(tmp_path, monkeypatch, world, row, why):
    root = attempt(tmp_path, world, monkeypatch, limit=False)
    for st, rows in M.rows().items():
        for r in rows:
            if r["name"] == row:
                assert why in hook("hook_check", row, root / st, None, r)
                return
    raise AssertionError(row)


def test_hook_check_wants_the_kernels_vm_map_line(tmp_path, monkeypatch):
    root = attempt(tmp_path, "model", monkeypatch, stages=("s0",))
    r = [x for x in M.rows()["s0"] if x["name"] == "s0-kcopy-1"][0]
    (root / "s0" / "s0-kcopy-1.dmesg").write_text("")
    assert "no kernel vm_map line" in hook("hook_check", "s0-kcopy-1", root / "s0", None, r)
