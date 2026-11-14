# SPDX-License-Identifier: MIT
"""r19-k0: the reader on the kept twins gives the frozen k0 values (the scorer must hold on them);
score/r10read.py is r10-dpm's reader byte for byte; the runner's awk words (run/hooks.sh rd_words)
equal score/read.py's on the kept twins and on the mock's outputs of every row."""
import subprocess

import pytest

from common import KP, R9, R10, R13, Z13, kept_dir, mock_job, pin, table
import plan as PL
import read as R


def awk_words(out, w=None):
    r = subprocess.run(["bash", "-c", f'sha() {{ shasum -a 256 "$@"; }}; . "{KP}/run/hooks.sh"; '
                        'rd_words "$1" "$2"', "x", str(out), str(w or "")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return dict(x.split("=", 1) for x in r.stdout.split())


def test_r10read_copy():
    assert (KP / "score/r10read.py").read_bytes() == pin("render/closing-r10-dpm/score/read.py")


KEPT = {  # kept job -> (its files, the values the frozen predictions give its k0 row)
    "pr2-c1-1": ({".txt": f"{R13}/pr2-c1-1.txt.gz"}, {"nparts": 1, "knob": 0x294}),
    "pr2-c1-2": ({".txt": f"{R13}/pr2-c1-2.txt.gz"}, {"nparts": 1, "knob": 0x294}),
    "pr2-c4-1": ({".txt": f"{R13}/pr2-c4-1.txt.gz"}, {"nparts": 4, "knob": 0xC0}),
    "pr2-c4-2": ({".txt": f"{R13}/pr2-c4-2.txt.gz"}, {"nparts": 4, "knob": 0xC0}),
    "a0-r10": ({".txt": f"{R10}/a0-cal-2048.txt.gz",
                ".p1139-green.param.bin": f"{R10}/a0-cal-2048.p1139-green.param.bin.gz",
                ".p1139-green.tadata.bin": f"{R10}/a0-cal-2048.p1139-green.tadata.bin.gz"},
               {"nparts": 1, "knob": 0x140, "param": PL.A0_PARAM, "tadata": PL.A0_TADATA,
                "pmask": PL.A0_PMASK,
                **{f"s{k}": v for k, v in PL.A0_S.items()}}),
    "zb-c-ctl": ({".txt": f"{Z13}/zb-c-ctl.txt.gz",
                  ".depth-store.1.bin": f"{Z13}/zb-c-ctl.depth-store.1.bin.gz"},
                 {"drawn": 2048, "dst": 2048, "dsha": PL.Z_DSHA, "ovf1": 0}),
}


@pytest.mark.parametrize("job", sorted(KEPT))
def test_kept_twins(job, tmp_path):
    files, want = KEPT[job]
    for suf, path in files.items():
        (tmp_path / f"{job}{suf}").write_bytes(pin(path))
    rd = R.reading(str(tmp_path), job)
    assert {k: rd.get(k) for k in want} == want
    w = tmp_path / "w"
    w.mkdir()
    for suf in files:               # the job's $W as the tool left it
        if suf != ".txt":
            (w / suf[1:]).write_bytes((tmp_path / f"{job}{suf}").read_bytes())
    assert awk_words(tmp_path / f"{job}.txt", w) == R.words(rd)


def test_a0_dumps_equal_in_r9_and_r10():
    for f in ("param", "tadata"):
        assert pin(f"{R9}/a0-cal-2048.p1139-green.{f}.bin.gz") == \
            pin(f"{R10}/a0-cal-2048.p1139-green.{f}.bin.gz")


@pytest.mark.parametrize("world", ["model", "ign", "late"])
@pytest.mark.parametrize("stage", ["k0", "kg", "f0"])
def test_awk_twin_on_mock(stage, world, tmp_path):
    for n, row in table(stage).items():
        rc, files = mock_job(row, (world,), tmp_path / n)
        d = kept_dir(tmp_path / "kept" / n, stage, {n: (rc, files)})
        w = tmp_path / n / "w"
        rd = R.reading(str(d), n)
        aw = awk_words(d / f"{n}.txt", w)
        assert aw == R.words(rd), n
        assert set(aw) >= {k for k in row["knobs"].split() if k.startswith("reads:")
                           for k in k[6:].split(",")}, n


def test_pmask_holds_on_the_stopped_attempt():
    """r19-k0's kept k0-a0 (20261114-223342, the lead's stop) differs from r10-dpm's in 4 dwords
    past a stream's end only: pmask equal, the plain sha256 not."""
    p = KP.parent / "r19-k0" / "out" / "20261114-223342" / "k0" / "k0-a0.p1139-green.param.bin.gz"
    if not p.exists():
        pytest.skip("r19-k0's kept attempt is not here")
    import gzip
    b = gzip.decompress(p.read_bytes())
    assert R.pmask(b) == PL.A0_PMASK and R.sha(b) != PL.A0_PARAM
    old = pin(f"{R10}/a0-cal-2048.p1139-green.param.bin.gz")
    assert R.pmask(old) == PL.A0_PMASK and R.sha(old) == PL.A0_PARAM
