# SPDX-License-Identifier: MIT
"""tests/test_blkadd.py: the mock (mock/world.py) takes `--blk-add` as strictly as t10 does. The
tool itself is the judge: t10's library mock (sgxfive-test built on libsgxfive's in-process mock
from session.toml's pinned source, a581c06, by the kit's own libmock_build into debug/libmock/)
runs each form, and every form the tool refuses with its usage line the world refuses too (bit 7
takes exactly two words; bits 2 to 5 one; nothing else). The world may refuse more (README.md:
a sign or blank, a second --blk-add of a bit, a bit other than 7), never less. The source's parse
and add_words are checked at the pinned commits too."""
import hashlib
import os
import subprocess
import sys

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("kit", "mock", "gen"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import session as S  # noqa: E402
import world as W  # noqa: E402

PROG = os.path.join(KP, "bins", "pix_green.bin")
FORMS = [
    "7=0x80000001,0x00000003", "7=1,2", "7=0,0", "7=0xffffffff,0xffffffff", "7=010,0x8",
    "0x7=1,2", "07=1,2",                                          # accepted by the tool
    "7=1", "7=1,", "7=,1", "7=1,2,3", "7=1;2", "7=0x100000000,1", "7=1,0x100000000",
    "7=", "7", "=1,2", "6=1,2", "6=1", "8=1,2", "1=1", "0=1", "16=1", "7=1 ,2", "7=0x,1",
    "7=1,2x", "7:1,2", "x7=1,2", "7=1.0,2",
]


@pytest.fixture(scope="module")
def tool():
    c = S.config(KP)
    b, why = S.libmock_build(KP, c, "t10")
    assert b is not None, why
    return str(b)


def run_tool(tool, form):
    argv = [tool, "--mock", "probe", "--tri", "pixel", "--temps", "32", "--pixels", "--width", "64",
            "--height", "64", "--tri-full", "--blk-add", form, PROG]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=120, cwd=KP)
    return r


@pytest.mark.parametrize("form", FORMS)
def test_world_refuses_what_the_tool_refuses(tool, form):
    r = run_tool(tool, form)
    refused = r.returncode == 2 and "usage" in (r.stdout + r.stderr).lower()
    w = W.answer("t10", ["probe", "--tri", "pixel", "--temps", "32", "--pixels", "--width", "64",
                         "--height", "64", "--tri-full", "--blk-add", form, PROG], {"model"})
    if refused:
        assert w["rc"] == 2, (form, w)
    else:
        # the tool took it; the world takes it too unless it is a bit other than 7 (stricter)
        assert r.returncode == 0, (form, r.stdout[-300:], r.stderr[-300:])
        assert "(blk-add 0x%02x)" % (1 << W.blk_add(form)[0]) in r.stdout
        if W.blk_add(form)[0] == 7:
            assert w["rc"] == 0, (form, w)


def test_the_rows_forms_run_on_the_library_mock(tool):
    r = run_tool(tool, "7=0x80000001,0x00000003")
    assert r.returncode == 0 and "tri 64x64 (blk-add 0x80)" in r.stdout


def test_bit7_takes_exactly_two_words():
    assert W.blk_add("7=1,2") == (7, [1, 2])
    assert W.blk_add("7=0x80010001,0x00010003") == (7, [0x80010001, 0x00010003])
    for bad in ("7=1", "7=1,2,3", "7=1,", "7=,2", "7=1,2,", "7=0x100000000,0"):
        assert W.blk_add(bad) is None, bad
    assert W.blk_add("3=5") == (3, [5]) and W.blk_add("3=5,6") is None


def test_world_refuses_a_second_blk_add_and_other_options():
    base = ["probe", "--tri", "pixel", "--temps", "32", "--pixels", "--width", "64", "--height",
            "64", "--tri-full"]
    assert W.answer("t10", base + ["--blk-add", "7=1,2", "--blk-add", "7=1,2", PROG], {"model"})["rc"] == 2
    assert W.answer("t10", base + ["--blk-add", "3=1", PROG], {"model"})["rc"] == 2
    assert W.answer("t10", base + ["--blk", "3=1", PROG], {"model"})["rc"] == 2
    assert W.answer("t10", base + ["--blk-add", PROG], {"model"})["rc"] == 2
    assert W.answer("t10", base + [PROG, PROG], {"model"})["rc"] == 2
    assert W.answer("t10", base + ["--blk-add", "7=1,2", PROG], {"model"})["rc"] == 0


def test_tool_source_parse_and_block_at_the_pinned_commits():
    c = S.config(KP)
    rev, _, path = c["tools"]["t10"]["source"].partition(":")
    main = S.repo_dirs()["resgx545"]
    src = subprocess.run(["git", "-C", str(main), "show", "%s:%s" % (rev, path)], capture_output=True,
                         check=True, timeout=60).stdout
    assert hashlib.sha256(src).hexdigest() == c["tools"]["t10"]["source_sha256"]
    s = src.decode()
    assert "want = bit == 7 ? 2 : 1;" in s
    assert "!((bit >= 2 && bit <= 5) || bit == 7)" in s
    assert "(n + 1 < want ? *end != ',' : *end != '\\0')" in s
    tp = subprocess.run(["git", "-C", str(main), "show", "%s:userspace/libsgxfive/src/tri_probe.c"
                         % c["freeze"]["resgx545"]], capture_output=True, check=True, timeout=60).stdout.decode()
    assert "#define ADD_ALLOWED\t(0x3cu | 1u << 7)" in tp
    assert "{ 1, 1, 1, 1, 1, 1, 3, 2, 6, 1, 1, 1, 1, 1, 1, 1 }" in tp   # bit 7: two words, E347
    rc = subprocess.run(["git", "-C", str(main), "show", "%s:userspace/libsgxfive/src/render.c"
                         % c["freeze"]["resgx545"]], capture_output=True, check=True, timeout=60).stdout.decode()
    assert "blk[i++] = 0xdf43;" in rc and "blk[i++] = half_h;" in rc     # bit 7 absent; vp3 > 0
    assert "p->bg_colour = 0xff203040;" in rc
    pins = c["freeze"]["pins"]
    assert "resgx545:userspace/libsgxfive/src/tri_probe.c" in pins
    assert "resgx545:userspace/libsgxfive/src/render.c" in pins
