# SPDX-License-Identifier: MIT
"""r9-ldpm: the frozen scorer replayed on kept records (render-closing-r8-ldpm, the published run
out/20261113-021431), laid out as the kit keeps them (cases.tsv in the kit's columns, the outputs
under the row's name). It must hold on:

  a0    r8-ldpm's six a0 jobs of the same commands (E935: every control PASS)
  m6b   the six replicate controls on r8-ldpm's m6 cells of the same target and thr0 (E936:
        1536x1536 0x109, 0x10a, 0x10b and 4096x2048 0x362, 0x363, 0x364)

and must fail on: c4-b6's job in c4-b5's place (cannot tell: its knob proof is off), 0x10b's job
read as 0x109's (1 page where 2 are frozen: FAILED, and every m6b verdict gated), another target's
calibration as an f9b calibration (FAILED) and as a w calibration (FAILED, its H-REPLAY row FAILED,
its own cell gated while the other targets' cells are not)."""
import gzip
import pathlib
import shutil
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "kit"), str(KP / "gen")]
import score as SC  # noqa: E402
import kitscore as K  # noqa: E402
import plan as PL  # noqa: E402

R8 = pathlib.Path.home() / "src/resgx545-data/render/closing-r8-ldpm/out/20261113-021431"


def kept(tmp, stage, jobs, text_edit=None):
    """A kit kept directory of `stage` holding the rows `jobs` {row: published job prefix}; the
    rc is the kept job's (3 for a probe that overflowed); text_edit {row: (old, new)} rewrites a
    job's output (a knob proof moved)."""
    d = tmp / stage
    d.mkdir(parents=True)
    rows = {r["name"]: r for r in K.table(str(KP), stage)}
    lines = []
    for n, src in jobs.items():
        r = rows[n]
        text = gzip.open(str(src) + ".txt.gz").read().decode(errors="replace")
        if text_edit and n in text_edit:
            text = text.replace(*text_edit[n])
        with gzip.open(d / (n + ".txt.gz"), "wt") as f:
            f.write(text)
        probe = r["args"].split(" -- ")[1].split()[1] == "probe"
        code = 3 if probe and "scene overflowed" in text else 0
        lines.append("\t".join((n, stage, r["set"], r["risk"], " ".join(r["knobs"]), r["tool"], r["args"],
                                str(code), "ok", "-", "-", "1")) + "\n")
    (d / "cases.tsv").write_text("\t".join(K.COLUMNS) + "\n" + "".join(lines))
    (d / "void.tsv").write_text("\t".join(K.COLUMNS) + "\n")
    (d / "readings.tsv").write_text("name\tkeys\treading\n")
    return d


A0 = {n: R8 / "a0" / n for n in ("a0-cal-2048", "a0-cal-2048f", "a0-c4-b5", "a0-c4-b6", "a0-t-s3m6", "a0-qf-0xa2")}
REPL = {"m6b-r-c0606-0x109": R8 / "m6/m6-c0606-0x109", "m6b-r-c0606-0x10a": R8 / "m6/m6-c0606-0x10a",
        "m6b-r-c0606-0x10b": R8 / "m6/m6-c0606-0x10b", "m6b-r-c1608-0x362": R8 / "m6/m6-c1608-0x362",
        "m6b-r-c1608-0x363": R8 / "m6/m6-c1608-0x363", "m6b-r-c1608-0x364": R8 / "m6/m6-c1608-0x364"}


def test_a0_holds_on_r8s_jobs(tmp_path):
    c, lines, t = SC.verdicts("a0", kept(tmp_path, "a0", A0))
    assert c and all(v is True for v in c.values()), lines


def test_a0_fails_on_c4_b6_in_c4_b5s_place(tmp_path):
    jobs = dict(A0, **{"a0-c4-b5": R8 / "a0/a0-c4-b6"})
    c, lines, t = SC.verdicts("a0", kept(tmp_path, "a0", jobs))
    assert c["a0-c4-b5"] is not True and not SC.SK.gate(c).ok


def test_m6b_replicates_hold_on_r8s_cells(tmp_path):
    c, lines, t = SC.verdicts("m6b", kept(tmp_path, "m6b", REPL))
    assert c == {n: True for n in REPL}, lines


def test_m6b_replicate_fails_when_off_and_gates_the_stage(tmp_path):
    jobs = dict(REPL, **{"m6b-r-c0606-0x109": R8 / "m6/m6-c0606-0x10b"})
    d = kept(tmp_path, "m6b", jobs, text_edit={"m6b-r-c0606-0x109": (" 0000010b ", " 00000109 ")})
    c, lines, t = SC.verdicts("m6b", d)
    assert c["m6b-r-c0606-0x109"] is False, lines
    assert all(s is None for s in t["H-NEXT1"][0]) and not SC.SK.gate(c).ok


def test_f9b_calibration_fails_on_another_targets(tmp_path):
    n = next(r["name"] for r in K.table(str(KP), "f9b") if r["name"].startswith("f9b-cal-"))
    c, lines, t = SC.verdicts("f9b", kept(tmp_path, "f9b", {n: R8 / "f9/f9-cal-c0404"}))
    assert c[n] is False, lines


def test_w_calibration_off_fails_h_replay_and_gates_only_its_cell(tmp_path):
    rows = K.table(str(KP), "w")
    cal = rows[0]["name"]
    assert cal.startswith("w-cal-")
    c, lines, t = SC.verdicts("w", kept(tmp_path, "w", {cal: R8 / "m6/m6-cal-c1208"}))
    assert c[cal] is False
    rep = [ln for ln in lines if ln.startswith(f"ROW {cal} [H-REPLAY")]
    assert any(": FAILED: need 0x305" in ln for ln in rep), rep
    cell = rows[1]["name"]
    states = {ln.split()[1] for ln in lines if ln.startswith("ROW ") and "cannot tell" in ln}
    assert cell in states


def test_left_by_parts_h_next1_from_h_span():
    for m in PL.T["m6b"]:
        S, A, U, after = PL.model(m["w"], m["h"])
        E = int(m["E6"], 16)
        for t in range(A[6] - 1, A[6] + 4):
            assert PL.left_by(t, S, A[6]) == (2 if t < A[6] else 1)
            assert PL.left_by(t, S, E) == (2 if t < E else 1)
