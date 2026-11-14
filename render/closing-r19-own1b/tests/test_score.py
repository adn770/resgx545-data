# SPDX-License-Identifier: MIT
"""The scorer on kept records it must hold on and must fail on: E631's kept TA data
(resgx545-data dpm/partial-model-batch at the frozen data commit, pinned in session.toml):
ow-part-c-k (a 1024x768 owner after the second context's run), ow-kcopy-c and ow-kcopy-4 (64x64,
after the second render: the four owner words, and none); an empty copy after the close (E1085)
is cannot tell. And the DPM page locator against the fork's KUnit table."""
import gzip
import os
import subprocess
import sys

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import score as S  # noqa: E402

DATA = os.environ.get("RESGX545_DATA", os.path.expanduser("~/src/resgx545-data"))
DATA_COMMIT = "95df71e98c9575b7a135ff0b38ae5d58adc5ddee"
DUMPS = "dpm/partial-model-batch/dumps/owner-safe.c1/"


def rec(name):
    r = subprocess.run(["git", "-C", DATA, "show", f"{DATA_COMMIT}:{DUMPS}{name}"],
                       capture_output=True)
    assert r.returncode == 0, r.stderr
    return gzip.decompress(r.stdout)


CK = rec("ow-part-c-k.kept.bin.gz")
KC, K4 = rec("ow-kcopy-c.kept.1.bin.gz"), rec("ow-kcopy-4.kept.1.bin.gz")


def test_layout_is_the_forks():
    # sgx_render_test.c at 456404fcffe5 (sgx_render_test_tadata): control, otpm, state, size
    want = {(64, 64): (0x1000, 0x2000, 0x3000, 0x6000), (1024, 600): (0x4000, 0x5000, 0x6000, 0x11000),
            (333, 777): (0x4000, 0x5000, 0x6000, 0xd000), (640, 480): (0x1000, 0x2000, 0x3000, 0xa000),
            (2048, 2048): (0x10000, 0x11000, 0x12000, 0x43000), (4096, 1): (0x10000, 0x11000, 0x12000, 0x19000),
            (1, 4096): (0x40000, 0x41000, 0x42000, 0x4f000)}
    for (w, h), t in want.items():
        assert S.layout(w, h) == t, (w, h)
    assert S.layout(4096, 4096)[2] == 0x42000           # E627's 4096x4096 state page
    assert S.layout(1024, 768) == (0x4000, 0x5000, 0x6000, 0x11000)   # E631: 69632 bytes
    assert S.layout(2048, 1536)[2:] == (0x12000, 0x37000)


def kept_dir(tmp, stage, files, reading):
    """A kept directory as the runner leaves it: cases.tsv, void.tsv, readings.tsv, NAME.txt and
    the two copies of each row in files ({name: (closed, after)}; a row not there did not run)."""
    hdr = "\t".join(K.COLUMNS)
    lines = [hdr]
    for r in K.table(KP, stage):
        if r["name"] not in files:
            continue
        lines.append("\t".join([r["name"], stage, r["set"], r["risk"], " ".join(r["knobs"]), r["tool"],
                                r["args"], "0", "ok", "-", "-", "5000000"]))
        closed, after = files[r["name"]]
        for suf, b in ((".kept.closed.1.bin", closed), (".kept.1.bin", after)):
            if b is not None:
                with gzip.open(os.path.join(tmp, r["name"] + suf + ".gz"), "wb") as f:
                    f.write(b)
        with open(os.path.join(tmp, r["name"] + ".txt"), "w") as f:
            f.write("tri: 0 of 1 renders ok, 1 overflowed\n")
    open(os.path.join(tmp, "cases.tsv"), "w").write("\n".join(lines) + "\n")
    open(os.path.join(tmp, "void.tsv"), "w").write(hdr + "\n")
    open(os.path.join(tmp, "readings.tsv"), "w").write(
        "name\tkeys\treading\n" + "".join(f"{n}\tovf kept size\t{v}\n" for n, v in reading.items()))
    return tmp


def summary(stage, d):
    controls, rows, lines = S.verdicts(stage, d)
    return controls, rows, "\n".join(lines)


def own1(tmp, ctl, closed, after):
    files = {"o1-4": ctl, "o1-c-a": (closed, after), "o1-c-b": (closed, after),
             "o1-c-c": (closed, after), "o1-c-d": (closed, after), "o1-p200": (closed, after)}
    return kept_dir(str(tmp), "own1", files, {"o1-4": "ovf=0 kept=2 size=24576"})


def test_own1_holds_on_e631_kcopy(tmp_path):
    controls, rows, text = summary("own1", own1(tmp_path, (K4, K4), K4, KC))
    assert controls == {"o1-4": True}
    assert [v for g, v in rows if g == "own1a"] == [True, True, True, True, True], text
    assert [v for g, v in rows if g == "own1b"] == [None, None]


def test_own1_fails_on_words_at_the_close(tmp_path):
    controls, rows, text = summary("own1", own1(tmp_path, (K4, K4), KC, KC))
    assert [v for g, v in rows if g == "own1a"] == [False] * 5 and "fits H-CLOSE" in text


def test_own1_control_fails_on_words_with_flag_4(tmp_path):
    controls, rows, text = summary("own1", own1(tmp_path, (K4, KC), K4, KC))
    assert controls == {"o1-4": False}


def test_own1_b_on_a_1024_owner(tmp_path):
    # E631's 1024x768 kept TA data with E631's 64x64 state words written in its state page:
    # H-CONST; a count of 0x13 pages: H-COUNT; the partial owner as it is: H-NONE
    def with_state(w0, w1):
        b = bytearray(CK)
        b[0x6000:0x6008] = w0.to_bytes(4, "little") + w1.to_bytes(4, "little")
        return bytes(b)
    for (w0, w1), fit, held in (((0x00020001, 2), "H-CONST", False), ((0x00130001, 0x13), "H-COUNT", True),
                                ((0, 0), "H-NONE", False)):
        os.makedirs(tmp_path / fit)
        d = kept_dir(str(tmp_path / fit), "own1", {"o1-big-a": (CK, with_state(w0, w1))}, {})
        controls, rows, text = summary("own1", d)
        assert ("own1b", held) in rows and f"fits {fit}" in text, text


@pytest.mark.parametrize("stage", ["own1"])
def test_required_is_what_is_read(stage):
    assert set(S.REQUIRED[stage]) >= {".txt", ".kept.closed.1.bin", ".kept.1.bin", "cases.tsv"}


def test_own1_empty_copy_after_the_close_is_cannot_tell(tmp_path):
    # E1085's o1-c-a: the copy right after the close 0 bytes, the one after the render E631's
    controls, rows, text = summary("own1", own1(tmp_path, (K4, K4), K4, KC))
    d = str(tmp_path)
    with gzip.open(os.path.join(d, "o1-c-b.kept.closed.1.bin.gz"), "wb") as f:
        f.write(b"")
    controls, rows, text = summary("own1", d)
    assert [v for g, v in rows if g == "own1a"] == [True, None, True, True, True], text
    assert "o1-c-b: cannot tell" in text


def test_own1_control_with_an_empty_copy_cannot_tell(tmp_path):
    d = kept_dir(str(tmp_path), "own1", {"o1-4": (b"", K4)}, {"o1-4": "ovf=0 kept=1 size=0"})
    controls, rows, text = summary("own1", d)
    assert controls == {"o1-4": None}
