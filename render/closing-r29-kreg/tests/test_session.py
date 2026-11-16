# SPDX-License-Identifier: MIT
"""r29-kreg's own tests: the generator current, the tables as the plan says (closing29/kreg/
design.md section 5), and the scorer on kept records built from E396's timings (it must hold) and
from E141's two slow values on both passes (it must fail), plus its cannot-tell premises."""
import itertools
import os
import pathlib
import re
import subprocess
import sys
import tomllib

import pytest

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KP / "gen"))
sys.path.insert(0, str(KP / "kit"))
import gen  # noqa: E402
import kitscore as K  # noqa: E402

PY = sys.executable
SCORE = KP / "score/score.py"
COLS = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n"


def test_the_tables_and_predictions_are_what_gen_writes():
    r = subprocess.run([PY, str(KP / "gen/gen.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_k1_writes_every_value_once_a_pass_with_a_0x2c_control_every_8_rows():
    t = K.table(str(KP), "k1")
    vals = [(r["set"], r["knobs"][0]) for r in t if r["set"] in ("fit", "held")]
    for sset in ("fit", "held"):
        assert sorted(w for s, w in vals if s == sset) == \
            [f"kreg:0x0a78={v}" for v in gen.VALUES]
    a, b = gen.passes()
    assert a != b and sorted(a) == sorted(b) == gen.VALUES
    names = [r["name"] for r in t]
    ctl = [r for r in t if r["set"] == "control" and r["knobs"][0].startswith("kreg:")]
    assert len(ctl) == 16 and all(r["knobs"][0] == "kreg:0x0a78=0x2c" for r in ctl)
    assert all(names[i] == f"c{i // 9 + 1:02d}" for i in range(0, 144, 9)), names
    assert names[-1] == "c-end" and t[-1]["knobs"] == ["reads:diff"] and len(t) == 145
    assert all(r["args"] == gen.TIMED for r in t[:-1]) and t[-1]["args"] == gen.EXACT
    assert all(r["risk"] == "flagged" for r in t)


def test_s0_is_safe_and_k1_flagged_gated_and_ending_the_session():
    c = tomllib.loads((KP / "session.toml").read_text())
    assert list(c["stages"]) == ["s0", "k1"]
    assert c["stages"]["s0"].get("class", "safe") == "safe"
    assert c["stages"]["k1"] == {"alarm": 7200, "gate": True, "class": "flagged",
                                 "on_stop": "end"}
    assert c["kregs"] == {"0x0a78": {"values": gen.VALUES}}
    assert c["srcversion"] == "E0CC40275493F8AEAD8180B" and c["prefix"] == "r29k"
    assert "kreg" not in (KP / "tables/s0.txt").read_text().split("\n", 6)[-1]
    for st in ("s0", "k1"):
        assert re.search(r"^#limit 0$", (KP / f"tables/{st}.txt").read_text(), re.M)


def test_the_scorer_s_frozen_numbers_are_the_generator_s():
    sys.path.insert(0, str(KP / "score"))
    import score
    assert score.SPREAD_PCT == gen.SPREAD_PCT
    p = K.predictions(str(KP), "k1")
    assert {v["H0"] for q in p.values() for k, v in q.items() if k == "dev_pct_le"} == \
        {str(gen.BOUND_PCT)}
    assert {v["H-CTL"] for q in p.values() for k, v in q.items() if k == "ref_pct_le"} == \
        {str(gen.REF_PCT)}


# ---- kept records -------------------------------------------------------------------------
def out_text(w, h, renders):
    s = f"tri: render context for targets up to {w}x{h}\n"
    for i, t in enumerate(renders, 1):
        s += (f"job: ok\ntarget: {w}x{h} hash 0x0\ndiff: 0 of {w * h} pixels\noutside: 0 dwords\n"
              f"tri {w}x{h} #{i}: 1 triangle, 0 background, 0 other; wrong 0 inside, 0 outside, "
              f"0 at edges; 0 if flipped; guard 0\ntri {w}x{h} #{i}: {t} us\n")
    return s + f"tri: {len(renders)} renders ok\n"


def kept(root, stage, times):
    """A kept stage directory: every row of the table ok, a 256x256 row's renders `times(row)`
    (six numbers), a 64x64 row one render."""
    d = root / stage
    d.mkdir(parents=True)
    rows = ""
    for r in K.table(str(KP), stage):
        big = r["args"] == gen.TIMED
        (d / f"{r['name']}.txt").write_text(out_text(256, 256, times(r)) if big
                                            else out_text(64, 64, [5585]))
        rows += f"{r['name']}\t{stage}\t{r['set']}\t{r['risk']}\t{' '.join(r['knobs'])}\tt10\t" \
            f"{r['args']}\t0\tok\t0\t0x0\t9999999\n"
    (d / "cases.tsv").write_text(COLS + rows)
    (d / "void.tsv").write_text(COLS)
    (d / "readings.tsv").write_text("name\tkeys\treading\n")
    return d


def flat(mean):
    return lambda r: [73400] + [mean] * 5


def value_of(r):
    return next((w.split("=")[1] for w in r["knobs"] if w.startswith("kreg:")), None)


def score(root):
    r = subprocess.run([PY, str(SCORE), "k1", str(root / "k1"), str(root)], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def summary(out):
    return next(ln for ln in out.splitlines() if ln.startswith("SUMMARY: k1: "))


def by_value(table):
    """times(row) from {value: (fit mean, held mean)}; any other row 67400."""
    def times(r):
        v = value_of(r)
        if r["set"] in ("fit", "held") and v in table:
            return [73400] + [table[v][r["set"] == "held"]] * 5
        return [73400] + [67400] * 5
    return times


def test_the_scorer_holds_on_flat_times(tmp_path):
    kept(tmp_path, "s0", flat(67400))
    kept(tmp_path, "k1", flat(67400))
    s = summary(score(tmp_path))
    assert "(64 of 64 rows decided)" in s and "not supported" not in s, s


def test_the_scorer_fails_a_value_slow_on_both_passes_and_holds_one_slow_on_its_fit_only(tmp_path):
    kept(tmp_path / "x", "s0", flat(67400))
    kept(tmp_path / "x", "k1", by_value({"0x01": (68900, 68900)}))
    out = score(tmp_path / "x")
    assert "is not supported" in summary(out) and "ROW 0x01: fit +2.23 %, held +2.23 %" in out, out
    kept(tmp_path / "y", "s0", flat(67400))
    kept(tmp_path / "y", "k1", by_value({"0x01": (68900, 67450), "0x02": (66000, 68900)}))
    out = score(tmp_path / "y")
    assert "(64 of 64 rows decided)" in summary(out), out
    assert re.search(r"ROW 0x01: .*held \(fit pass outside", out), out


def test_the_scorer_cannot_tell_when_the_controls_spread_and_fails_a_moved_control(tmp_path):
    def spread(r):
        if r["set"] == "control" and value_of(r):
            return [73400] + [67400 + (500 if int(r["name"][1:]) % 2 else -500)] * 5
        return [73400] + [67400] * 5
    kept(tmp_path / "x", "s0", flat(67400))
    kept(tmp_path / "x", "k1", spread)
    s = summary(score(tmp_path / "x"))
    assert s.startswith("SUMMARY: k1: cannot tell:") and "spread: cannot tell" in s, s
    kept(tmp_path / "y", "s0", flat(66000))
    kept(tmp_path / "y", "k1", flat(67400))
    s = summary(score(tmp_path / "y"))
    assert "controls FAILED" in s, s


# ---- E396 (must hold) and E141 (must fail) -----------------------------------------------------
def e396():
    """{value: [the six renders of each run]} from E396's kept output at the pinned data commit."""
    c = tomllib.loads((KP / "session.toml").read_text())
    data = pathlib.Path(os.environ.get("RESGX545_DATA", pathlib.Path.home() / "src/resgx545-data"))
    r = subprocess.run(["git", "-C", str(data), "show",
                        f"{c['freeze']['data']}:pds/reg-0a78-timing/output.txt"],
                       capture_output=True, text=True)
    if r.returncode:
        pytest.skip(f"E396's output is not in {data}")
    out = {}
    for m in re.finditer(r"^case \d+ 0x0a78=(0x\w+): +(\d+) us avg of 5 ok \| ([\d ]+)$",
                         r.stdout, re.M):
        runs = [int(x) for x in m[3].split()]
        assert sum(runs[1:]) // 5 == int(m[2])      # the reading is E396's own mean
        out.setdefault(m[1], []).append(runs)
    assert sorted(out) == ["0x00", "0x01", "0x08", "0x20", "0x2c", "0x3f"]
    assert all(len(v) == 5 for v in out.values())
    return out


def e396_times(runs):
    ctl = itertools.cycle(runs["0x2c"])

    def times(r):
        v = value_of(r)
        if r["set"] in ("fit", "held") and v in runs and v != "0x2c":
            return runs[v][r["set"] == "held"]
        return next(ctl)
    return times


def test_the_scorer_holds_on_e396(tmp_path):
    runs = e396()
    kept(tmp_path, "s0", e396_times(runs))
    kept(tmp_path, "k1", e396_times(runs))
    out = score(tmp_path)
    assert "(64 of 64 rows decided)" in summary(out) and "FAILED" not in out, out


def test_the_scorer_fails_on_e141_s_slow_values_twice(tmp_path):
    """E141's means: 0x01 70977 and 0x20 69038 us against 0x2c's 67288 (5.5 and 2.6 percent)."""
    runs = e396()
    base = e396_times(runs)

    def times(r):
        v = value_of(r)
        if r["set"] in ("fit", "held") and v in ("0x01", "0x20"):
            m = {"0x01": 70977, "0x20": 69038}[v] * 67452 // 67288
            return [73400] + [m] * 5
        return base(r)
    kept(tmp_path, "s0", base)
    kept(tmp_path, "k1", times)
    out = score(tmp_path)
    assert "is not supported" in summary(out), out
    assert re.search(r"ROW 0x01: .*FAILED", out) and re.search(r"ROW 0x20: .*FAILED", out), out
