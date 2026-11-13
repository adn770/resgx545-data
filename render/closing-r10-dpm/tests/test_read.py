# SPDX-License-Identifier: MIT
"""r10-dpm: the runner's reading (run/hooks.sh rd_words, awk) equals the scorer's (score/read.py
words) on kept R7-dpm and r8-ldpm jobs of every kind the session runs (among them the two band 6
cells whose last sample in the partial render read 6 and the next 2, OD-2 (a)) and on the mock's
outputs; gps_next reads those two cells as 2."""
import gzip
import pathlib
import subprocess
import sys

import pytest

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score")]
import read as R  # noqa: E402

DATA = pathlib.Path.home() / "src/resgx545-data/render"
R7 = DATA / "closing-r7-dpm/out"
R8 = DATA / "closing-r8-ldpm/out/20261113-021431"
JOBS = [R7 / "a1/s-a0/a0-cal-2048", R7 / "a1/s-a0/a0-cal-2048f", R7 / "a1/s-a0/a0-c4-b5",
        R7 / "a1/s-a0/a0-qf-0xa2", R7 / "a1/s-m/m-c33-0x32c", R7 / "a1/s-m/m-cal-c32",
        R7 / "b1/s-k/k-b3", R7 / "b1/s-k/k-creep",
        R8 / "a0/a0-cal-2048", R8 / "a0/a0-qf-0xa2", R8 / "m6/m6-map-c1212-0x3cf", R8 / "m6/m6-c0404-0x82",
        R8 / "m6/m6-c0606-0x109", R8 / "m6/m6-c1608-0x362", R8 / "m6/m6-cal-c1208", R8 / "f9/f9-c0404-0x48",
        R8 / "sp/sp-c23-0x234", R8 / "sp/sp-c-0xe8"]


def awk_words(path):
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; rd_words "$1"', "x", str(path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return dict(w.split("=", 1) for w in r.stdout.split())


@pytest.mark.parametrize("job", JOBS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_awk_twin_on_kept_jobs(job, tmp_path):
    p = tmp_path / "x.out"
    p.write_bytes(gzip.open(f"{job}.txt.gz").read())
    w = awk_words(p)
    assert w and w == R.words(R.reading(p.read_text(errors="replace")))


def test_gps_next_reads_the_trimmed_list():
    for job, left, nxt in (("m6/m6-map-c1212-0x3cf", 6, 2), ("m6/m6-c0404-0x82", 6, 2),
                           ("m6/m6-c0606-0x10a", 2, 2), ("m6/m6-c0606-0x10b", 1, 1),
                           ("sp/sp-c23-0x234", 1, 2)):
        rd = R.reading(gzip.open(R8 / f"{job}.txt.gz").read().decode(errors="replace"))
        assert (rd["gps_left"], rd["gps_next"]) == (left, nxt), job


def test_awk_twin_on_mock_outputs(tmp_path):
    outs = sorted(KP.glob("debug/mock.*/model/out/model/*/*.txt.gz"))
    if not outs:
        pytest.skip("no mock run kept in debug/")
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
        if n >= 40:
            break


def test_a_cut_capture_reads_nothing(tmp_path):
    p = tmp_path / "cut.out"
    p.write_text("timeline: regs 0x0624 0x0658 0x0724 0x072c samples 2 seconds 0 start 0 end 0 rc 0\n"
                 "tl 0 00000100 00000000 00010001 00010001\ntl 5 00000100 0000\n")
    assert awk_words(p) == {} and R.words(R.reading(p.read_text())) == {}
