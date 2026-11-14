# SPDX-License-Identifier: MIT
"""r15-dpm: the runner's reading (run/hooks.sh rd_words, awk) equals the scorer's (score/read.py
words) on kept jobs (r8-ldpm's and r13-dpm's 16-register timelines, which carry 0x0748 and the
header's samples and end, so the period is read the same way) and on the mock's outputs; the
period the plan's [check] rests on is read from kept timelines."""
import gzip
import pathlib
import subprocess
import sys

import pytest

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score")]
import read as R  # noqa: E402

DATA = pathlib.Path.home() / "src/resgx545-data/render"
R8 = DATA / "closing-r8-ldpm/out/20261113-021431"
R13 = DATA / "closing-r13-dpm/out/20261113-212348/pr2"
# job -> (clr, pulses) from the command's start on, the kept readings
KEPT = {R8 / "f9/f9-cal-c1208": (0, 0), R8 / "f9/f9-c1208-0xc0": (1, 1), R8 / "f9/f9-c1208-0x60": (0, 0),
        R8 / "m6/m6-c1208-0x294": (0, 0), R13 / "pr2-c4-2": (1, 1), R13 / "pr2-c0-1": (0, 0)}


def awk_words(path):
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; rd_words "$1"', "x", str(path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return dict(w.split("=", 1) for w in r.stdout.split())


@pytest.mark.parametrize("job", sorted(KEPT))
def test_awk_twin_and_kept_counts(job, tmp_path):
    p = tmp_path / "x.out"
    p.write_bytes(gzip.open(f"{job}.txt.gz").read())
    text = p.read_text(errors="replace")
    w = awk_words(p)
    assert w and w == R.words(R.reading(text))
    rd = R.reading(text)
    assert (rd["clr"], rd["pulses"]) == KEPT[job] and len(rd["widths"]) == rd["pulses"]
    assert rd["short"] == 0 and 7000 <= rd["period"] <= 8600        # 16 registers: E1032's 7.5 us


def test_awk_twin_on_mock_outputs(tmp_path):
    outs = sorted(KP.glob("debug/mock.*/*/out/*/*/*.txt.gz"))
    n = 0
    for p in outs:
        if p.name.count(".") > 2:
            continue
        text = gzip.open(p).read().decode(errors="replace")
        if "timeline: regs" not in text:
            continue
        q = tmp_path / "x.out"
        q.write_text(text)
        assert awk_words(q) == R.words(R.reading(text)), p.name
        n += 1
    if not n:
        pytest.skip("no mock run kept in debug/")


def test_a_cut_capture_reads_nothing(tmp_path):
    p = tmp_path / "cut.out"
    p.write_text("timeline: regs 0x0748 samples 2 seconds 0 start 0 end 500 rc 0\n"
                 "tl 0 1f\ntl 5 1\n")
    p.write_text(p.read_text().replace("tl 5 1\n", "tl 5\n"))
    assert awk_words(p) == {} and R.words(R.reading(p.read_text())) == {}


def test_a_capture_without_the_register_or_samples_reads_nothing(tmp_path):
    p = tmp_path / "x.out"
    p.write_text("timeline: regs 0x0624 samples 2 seconds 0 start 0 end 500 rc 0\ntl 0 1f\n")
    assert awk_words(p) == {} and R.words(R.reading(p.read_text())) == {}
    p.write_text("timeline: regs 0x0748 samples 0 seconds 0 start 0 end 0 rc 0\ntl 0 1f\n")
    assert awk_words(p) == {} and R.words(R.reading(p.read_text())) == {}


def test_pulses_count_runs_of_clear_lines_after_the_start():
    head = "timeline: regs 0x0748 samples 7000 seconds 0 start 10 end 7000000 rc 0\n"
    rows = [(0, 0x1B), (5, 0x1F), (10, 0x1F), (20, 0x1B), (30, 0x1B), (40, 0x1F), (50, 0x0B), (60, 0x1F)]
    body = "".join(f"tl {t} {m:x}\n" for t, m in rows)
    rd = R.reading(head + body)
    # the clear at t 0 is before the start (idle); runs at 20-30 (2 lines) and 50 (1 line)
    assert (rd["clr"], rd["pulses"], rd["n"], rd["widths"]) == (3, 2, 8, [20, 10])
    assert rd["period"] == 1000 and rd["short"] == 1


def test_period_is_end_over_samples_and_short_means_at_most_2000_ns(tmp_path):
    t = "timeline: regs 0x0748 samples %d seconds 0 start 0 end 1500000000 rc 0\ntl 0 1f\n"
    assert R.reading(t % 3260869)["period"] == 460 and R.reading(t % 3260869)["short"] == 1
    assert R.reading(t % 200000)["period"] == 7500 and R.reading(t % 200000)["short"] == 0
    for n in (3260869, 200000):
        (tmp_path / "x.out").write_text(t % n)
        assert awk_words(tmp_path / "x.out") == R.words(R.reading(t % n))


def test_gate_is_2000_ns_and_e1044s_1682_ns_passes(tmp_path):
    t = "timeline: regs 0x0748 samples %d seconds 0 start 0 end 1500000000 rc 0\ntl 0 1f\n"
    for n, period, short in ((891795, 1682, 1), (750000, 2000, 1), (749000, 2002, 0), (2000000, 750, 1)):
        rd = R.reading(t % n)
        assert (rd["period"], rd["short"]) == (period, short)
        (tmp_path / "x.out").write_text(t % n)
        assert awk_words(tmp_path / "x.out") == R.words(rd)
