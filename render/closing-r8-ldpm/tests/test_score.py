# SPDX-License-Identifier: MIT
"""r8-ldpm: the frozen scorer replayed on kept records, laid out as the kit keeps them (cases.tsv
in the kit's columns, the outputs and dumps under the row's name). It must hold on:

  a0    R7-dpm's six s-a0 jobs of the same commands (E915: 29 of 29 control values held)
  sp    the two control cells, R7-dpm s-k's k-b3 (thr0 0xe8 = S4, 3 global pages) and k-s4p1
        (0xe9, 4) on this module 37EC97AB (E918)
  m6    the two control cells, R7-dpm s-m's m-r6-0x1c2 (2 pages left) and m-r6-0x1c3 (1)
  v     R7-dpm s-v's v-cal-c4 as v-c4 (E917: 14 of 14 repeated); H-DET held on three copies of
        R7's v-cal-c8
  u     R7-dpm s-b's b-cal-s22 as u-c-s22 (need 78)

and must fail on: c4-b6's job in c4-b5's place (1 page left, not 2), k-s4p1's job as the 0xe8
control, v-cal-c8 as the N 4 control, R6's v-cal-c8 among the three written N 8 runs (H-DET
FAILED: E917's run-to-run difference), and a job whose knob proof is off (cannot tell)."""
import gzip
import pathlib
import shutil
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "kit")]
import score as SC  # noqa: E402
import kitscore as K  # noqa: E402

DATA = pathlib.Path.home() / "src/resgx545-data/render"
R7 = DATA / "closing-r7-dpm/out"
R6 = DATA / "closing-r6-dpm/out"


def kept(tmp, stage, jobs, rc=None):
    """A kit kept directory of `stage` holding the rows `jobs` {row: published job prefix}."""
    d = tmp / stage
    d.mkdir(parents=True)
    rows = {r["name"]: r for r in K.table(str(KP), stage)}
    hdr = "\t".join(K.COLUMNS) + "\n"
    lines = []
    for n, src in jobs.items():
        r = rows[n]
        for suf in (".txt.gz", ".p1139-green.param.bin.gz", ".p1139-green.tadata.bin.gz"):
            if pathlib.Path(str(src) + suf).exists():
                shutil.copy(str(src) + suf, d / (n + suf))
        text = gzip.open(str(src) + ".txt.gz").read().decode(errors="replace")
        code = (rc or {}).get(n, 3 if "scene overflowed" in text and r["args"].split(" -- ")[1].split()[1] == "probe" else 0)
        lines.append("\t".join((n, stage, r["set"], r["risk"], " ".join(r["knobs"]), r["tool"], r["args"],
                                str(code), "ok", "-", "-", "1")) + "\n")
    (d / "cases.tsv").write_text(hdr + "".join(lines))
    (d / "void.tsv").write_text(hdr)
    (d / "readings.tsv").write_text("name\tkeys\treading\n")
    return d


A0 = {n: R7 / "a1/s-a0" / n for n in ("a0-cal-2048", "a0-cal-2048f", "a0-c4-b5", "a0-c4-b6", "a0-t-s3m6", "a0-qf-0xa2")}


def test_a0_holds_on_r7s_jobs(tmp_path):
    c, lines, t = SC.verdicts("a0", kept(tmp_path, "a0", A0))
    assert c and all(v is True for v in c.values()), lines


def test_a0_fails_on_c4_b6_in_c4_b5s_place(tmp_path):
    jobs = dict(A0, **{"a0-c4-b5": R7 / "a1/s-a0/a0-c4-b6"})
    c, lines, t = SC.verdicts("a0", kept(tmp_path, "a0", jobs))
    # c4-b6's job ran at thr0 0xe3: its knob proof is off for c4-b5's row (cannot tell, not a pass)
    assert c["a0-c4-b5"] is not True
    assert not SC.SK.gate(c).ok


def test_sp_controls_hold_on_r7_s_k(tmp_path):
    d = kept(tmp_path, "sp", {"sp-c-0xe8": R7 / "b1/s-k/k-b3", "sp-c-0xe9": R7 / "b1/s-k/k-s4p1"})
    c, lines, t = SC.verdicts("sp", d)
    assert c == {"sp-c-0xe8": True, "sp-c-0xe9": True}, lines


def test_sp_control_fails_when_off(tmp_path):
    """k-s4p1's output with its knob read as 0xe8's: 4 global pages where 3 are frozen."""
    src = R7 / "b1/s-k/k-s4p1.txt.gz"
    text = gzip.open(src).read().decode().replace(" 000000e9 ", " 000000e8 ")
    p = tmp_path / "src" / "x"
    p.parent.mkdir()
    with gzip.open(str(p) + ".txt.gz", "wt") as f:
        f.write(text)
    d = kept(tmp_path, "sp", {"sp-c-0xe8": p, "sp-c-0xe9": R7 / "b1/s-k/k-s4p1"})
    c, lines, t = SC.verdicts("sp", d)
    assert c["sp-c-0xe8"] is False and c["sp-c-0xe9"] is True, lines


def test_m6_controls_hold_on_r7_s_m(tmp_path):
    d = kept(tmp_path, "m6", {"m6-c-0x1c2": R7 / "a1/s-m/m-r6-0x1c2", "m6-c-0x1c3": R7 / "a1/s-m/m-r6-0x1c3"})
    c, lines, t = SC.verdicts("m6", d)
    assert c == {"m6-c-0x1c2": True, "m6-c-0x1c3": True}, lines


def test_v_control_holds_on_r7_and_fails_on_n8(tmp_path):
    c, lines, t = SC.verdicts("v", kept(tmp_path / "a", "v", {"v-c4": R7 / "a1/s-v/v-cal-c4"}))
    assert c == {"v-c4": True}, lines
    c, lines, t = SC.verdicts("v", kept(tmp_path / "b", "v", {"v-c4": R7 / "a1/s-v/v-cal-c8"}))
    assert c["v-c4"] is False


def test_h_det_holds_on_one_run_thrice_and_fails_on_r6_among_them(tmp_path):
    c8, r6 = R7 / "a1/s-v/v-cal-c8", R6 / "a2/r-v/v-cal-c8"
    jobs = {"v-c4": R7 / "a1/s-v/v-cal-c4", "v-w8-1": c8, "v-w8-2": c8, "v-w8-3": c8}
    c, lines, t = SC.verdicts("v", kept(tmp_path / "a", "v", jobs))
    assert t["H-DET"][0] == [True, True, True], lines
    jobs["v-w8-2"] = r6
    c, lines, t = SC.verdicts("v", kept(tmp_path / "b", "v", jobs))
    assert t["H-DET"][0] == [False, False, False], lines


def test_blocks_read_as_ol7_a():
    """The scorer's block reader gives OL7 (a)'s sizes (gen/ol7/ol7_a_dumps.out)."""
    got = SC.blocks(str(R7 / "a1/s-v/v-cal-c8.p1139-green."))
    out = (KP / "gen/ol7/ol7_a_dumps.out").read_text()
    assert f"R7-dpm N 8: {len(got)} objects, block sizes (first 8) {got[:8]}" in out


def test_u_control_holds_on_r7_s22(tmp_path):
    c, lines, t = SC.verdicts("u", kept(tmp_path, "u", {"u-c-s22": R7 / "a1/s-b/b-cal-s22"}))
    assert c == {"u-c-s22": True}, lines


def test_m6_alignment_voids_a_target_off_the_window(tmp_path):
    """A calibration whose S_6 lies 8 pages above the model's moves the A_6 cell out of the run's
    window (A_6 - 1 .. A_6 + 3): the target's rows are cannot tell, never held or FAILED."""
    import read as R
    rows = {r["name"]: r for r in K.table(str(KP), "m6")}
    cal = {"iv": {6: (0x333 + 8, 0x333 + 8)}, "S": {}, "gps_left": None}
    S, A, B, U = SC.PL.model(2560, 3072)
    rds = {"m6-cal-c1012": cal}
    cells = [r for n, r in rows.items() if n.startswith("m6-c1012-")]
    for r in cells:
        rds[r["name"]] = {"gps_left": 1}
    res = SC.m6_rows(rds, list(rows.values()))
    st = [s for r, s, _ in res["H-SPAN"] if r["name"].startswith("m6-c1012-")]
    assert st and all(s is None for s in st)
    rds["m6-cal-c1012"] = {"iv": {6: (S[6], S[6])}}
    res = SC.m6_rows(rds, list(rows.values()))
    st = {r["name"]: s for r, s, _ in res["H-SPAN"] if r["name"].startswith("m6-c1012-")}
    assert st[f"m6-c1012-0x{A[6]:x}"] is True and st[f"m6-c1012-0x{A[6] - 1:x}"] is False
    assert R  # the reader is the scorer's


# ---- post-run fix (POSTRUN-FIX.md) -----------------------------------------------------------
def test_a_tri_calibration_ending_rc1_with_its_diff_line_is_read(tmp_path):
    """k's calibrations ended rc 1 with their diff line (expectdiff: class ok, a completed job of
    the runner); the frozen scorer read them as not completed (kitscore.completed counts rc 0 and
    `expect:` outcomes only) and printed cannot tell. A kept k calibration must be read."""
    run = KP / "out/20261113-021431/k"
    if not run.exists():
        import pytest
        pytest.skip("the run's kept k stage is not here")
    d = kept(tmp_path, "k", {"k-cal-k22-n2": run / "k-cal-k22-n2"}, rc={"k-cal-k22-n2": 1})
    rds = SC.readings("k", d)
    assert rds["k-cal-k22-n2"] is not None and rds["k-cal-k22-n2"]["nparts"] == 0


def test_rc1_without_a_diff_line_stays_unread(tmp_path):
    src = KP / "out/20261113-021431/k/k-cal-k22-n2"
    if not (src.parent).exists():
        import pytest
        pytest.skip("the run's kept k stage is not here")
    text = gzip.open(str(src) + ".txt.gz").read().decode(errors="replace")
    p = tmp_path / "src" / "x"
    p.parent.mkdir()
    with gzip.open(str(p) + ".txt.gz", "wt") as f:
        f.write("\n".join(ln for ln in text.splitlines() if not ln.startswith("diff:")) + "\n")
    d = kept(tmp_path, "k", {"k-cal-k22-n2": p}, rc={"k-cal-k22-n2": 1})
    assert SC.readings("k", d)["k-cal-k22-n2"] is None
