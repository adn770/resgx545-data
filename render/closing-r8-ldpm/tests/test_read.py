# SPDX-License-Identifier: MIT
"""r8-ldpm: the runner's reading (run/hooks.sh rd_words, awk) equals the scorer's (score/read.py
words) on kept R7-dpm jobs of every kind the session runs and on the mock's outputs; read.py
reads R7-dpm's kept a0 readings as R7's own reader did (its cases.tsv note column)."""
import csv
import gzip
import pathlib
import subprocess
import sys

import pytest

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score")]
import read as R  # noqa: E402

R7 = pathlib.Path.home() / "src/resgx545-data/render/closing-r7-dpm/out"
JOBS = ["a1/s-a0/a0-cal-2048", "a1/s-a0/a0-cal-2048f", "a1/s-a0/a0-c4-b5", "a1/s-a0/a0-qf-0xa2",
        "a1/s-m/m-c33-0x32c", "a1/s-m/m-cal-c32", "a1/s-b/b-s17-0x9", "a1/s-b/b-cal-s22",
        "a1/s-b/b-s44a-0x9a", "a1/s-v/v-cal-c8", "b1/s-k/k-b3", "b1/s-k/k-creep"]


def awk_words(path):
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; rd_words "$1"', "x", str(path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return dict(w.split("=", 1) for w in r.stdout.split())


@pytest.mark.parametrize("job", JOBS)
def test_awk_twin_on_kept_r7_jobs(job, tmp_path):
    p = tmp_path / "x.out"
    p.write_bytes(gzip.open(R7 / f"{job}.txt.gz").read())
    w = awk_words(p)
    assert w and w == R.words(R.reading(p.read_text(errors="replace")))


def test_a0_readings_are_r7s():
    """R7's runner wrote its reader's line in cases.tsv's note: the same values here."""
    rows = {r["name"]: r for r in csv.DictReader(open(R7 / "a1/s-a0/cases.tsv"), delimiter="\t")}
    for n, r in rows.items():
        note = dict(w.split("=", 1) for w in r["note"].split() if "=" in w)
        w = R.words(R.reading(gzip.open(R7 / f"a1/s-a0/{n}.txt.gz").read().decode(errors="replace")))
        for k in ("nparts", "gps_left", "gps_abort", "runpeaks"):
            if note.get(k, "-") != "-":
                assert w[k] == note[k] or int(w[k], 0) == int(note[k], 0), (n, k)
        for k in range(2, 8):
            if f"S{k}" in note:
                assert w[f"s{k}"] == note[f"S{k}"], (n, k)


def test_awk_twin_on_mock_outputs():
    outs = sorted(KP.glob("debug/mock.*/model/out/model/*/*.txt.gz"))
    if not outs:
        pytest.skip("no mock run kept in debug/")
    for p in outs[:40]:
        if p.name.count(".") > 2:
            continue
        text = gzip.open(p).read().decode(errors="replace")
        if "timeline: regs" not in text:
            continue
        q = KP / "debug" / "awk_twin.out"
        q.write_text(text)
        assert awk_words(q) == R.words(R.reading(text)), p.name


def test_a_cut_capture_reads_nothing(tmp_path):
    p = tmp_path / "cut.out"
    p.write_text("timeline: regs 0x0624 0x0658 0x0724 0x072c samples 2 seconds 0 start 0 end 0 rc 0\n"
                 "tl 0 00000100 00000000 00010001 00010001\ntl 5 00000100 0000\n")
    assert awk_words(p) == {} and R.words(R.reading(p.read_text())) == {}
