# SPDX-License-Identifier: MIT
"""r13-dpm: the runner's reading (run/hooks.sh rd_words, awk) equals the scorer's (score/read.py
words) on kept r8-ldpm jobs of the scene's kinds and on the mock's outputs; the reader's counts on
kept 3072x2048 jobs are the ones the plan's counts and the builder's look at bit 2 rest on."""
import gzip
import pathlib
import subprocess
import sys

import pytest

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score")]
import read as R  # noqa: E402

R8 = pathlib.Path.home() / "src/resgx545-data/render/closing-r8-ldpm/out/20261113-021431"
# job -> (nparts, clr lines with 0x0748 bit 2 clear), the kept readings of the scene
KEPT = {"f9/f9-cal-c1208": (0, 0), "f9/f9-c1208-0xc0": (4, 1), "f9/f9-c1208-0x120": (3, 1),
        "f9/f9-c1208-0x1a0": (2, 0), "f9/f9-c1208-0x60": (7, 0), "m6/m6-c1208-0x292": (1, 1),
        "m6/m6-c1208-0x293": (1, 0), "m6/m6-c1208-0x294": (1, 0), "m6/m6-c1208-0x296": (1, 1),
        "m6/m6-cal-c1208": (0, 0)}


def awk_words(path):
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; rd_words "$1"', "x", str(path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return dict(w.split("=", 1) for w in r.stdout.split())


@pytest.mark.parametrize("job", sorted(KEPT))
def test_awk_twin_and_kept_counts(job, tmp_path):
    p = tmp_path / "x.out"
    p.write_bytes(gzip.open(R8 / f"{job}.txt.gz").read())
    text = p.read_text(errors="replace")
    w = awk_words(p)
    assert w and w == R.words(R.reading(text))
    rd = R.reading(text)
    assert (rd["nparts"], rd["clr"]) == KEPT[job]
    assert rd["hi10"] == 0 and rd["pulses"] <= rd["clr"]


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
    p.write_text("timeline: regs 0x0624 0x0658 0x0710 0x0724 0x072c 0x0748 samples 2 seconds 0 start 0 end 0 rc 0\n"
                 "tl 0 00000100 00000000 0 00010001 00010001 1f\ntl 5 00000100 0000\n")
    assert awk_words(p) == {} and R.words(R.reading(p.read_text())) == {}


def test_pulses_count_runs_of_clear_lines():
    head = "timeline: regs 0x0624 0x0658 0x0710 0x0724 0x072c 0x0748 samples 6 seconds 0 start 0 end 0 rc 0\n"
    rows = [0x1F, 0x1B, 0x1B, 0x1F, 0x0B, 0x1F]
    body = "".join(f"tl {i} 00000100 00000000 0 00010001 00010001 {m:x}\n" for i, m in enumerate(rows))
    rd = R.reading(head + body)
    assert (rd["clr"], rd["pulses"], rd["n"]) == (3, 2, 6)
