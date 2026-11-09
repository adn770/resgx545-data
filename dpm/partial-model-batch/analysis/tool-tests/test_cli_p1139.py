# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39 tool changes, test first (written, not applied to the repository; tool-new/ holds a scratch copy
with T2, T3 and T4 applied, tool/ the unchanged 11.35 source). The 11.39 batch needs:

  T2  tri --keep-overflow --ctx2 [--close-first-early]: an overflowed first render does not stop the
      second context (11.34's disclosure: "0 of 1 renders ok"); an overflowed second render is counted.
  T3  tri --tadata-fill-render N:PAGE:VALUE[:ramp]: debugfs tadata_fill written just before render N, so
      that a page of the TA data can be changed between a geometry kick and the final render (Q045).
  T4  tri --ctx2 --kept-copy DIR: debugfs render_kept copied to DIR/kept.N.bin after the second
      context's render N and before any close (Q191: was the kept owner's page written by then).
  T1  probe --tri ... --depth-scratch [--depth-ctl V]: the probe's own scratch buffer is the ZLS depth
      buffer (the pokes of tri --depth), so that objects with --vertices, --copy-depth and --obj2 and the
      reload background (bgpixel, bgpds) meet a depth buffer (Q038's last open case). NOT implemented in
      tool-new: its test fails against both tools, as it should until the change is made.

Run (the tests fail on T1 always and on T2 to T4 against the unchanged tool):
    SGXFIVE_TEST=.../p1139/tool/userspace/libsgxfive/build/sgxfive-test  pytest p1139/tool-tests -q
    SGXFIVE_TEST=.../p1139/tool-new/userspace/libsgxfive/build/sgxfive-test pytest p1139/tool-tests -q
"""
from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve().parent
TOOL = os.environ.get("SGXFIVE_TEST", str(HERE.parent / "tool/userspace/libsgxfive/build/sgxfive-test"))
GREEN = HERE.parent / "stage-bins/p1139-green.bin"


def run(*args: str, dbg: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if dbg is not None:
        env["SGXFIVE_DEBUGFS"] = str(dbg)
    return subprocess.run([TOOL, *args], capture_output=True, text=True, timeout=60, env=env)


@pytest.fixture(scope="module", autouse=True)
def tool_exists():
    if not pathlib.Path(TOOL).exists():
        pytest.skip(f"{TOOL} not built")


def test_keep_overflow_alone_still_counts():
    r = run("--mock", "--mock-pb-pages=0x28", "tri", "--width", "1024", "--height", "768", "--keep-overflow")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 overflowed" in r.stdout


def test_t2_second_context_after_an_overflowed_first_render():
    r = run("--mock", "--mock-pb-pages=0x28", "tri", "--width", "1024", "--height", "768",
            "--keep-overflow", "--ctx2", "--close-first-early")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "tri2 1024x768 #1: overflowed" in r.stdout, r.stdout


def test_t3_tadata_fill_before_render_n(tmp_path):
    (tmp_path / "tadata_fill").write_text("")
    r = run("--mock", "tri", "--width", "64", "--height", "64", "-n", "2", "--geometry", "1",
            "--tadata-fill-render", "2:6:0xa5000000:ramp", dbg=tmp_path)
    assert "tri: tadata_fill before render 2: 6 0xa5000000 ramp" in r.stdout, r.stdout + r.stderr
    assert (tmp_path / "tadata_fill").read_text() == "6 0xa5000000 ramp\n"


def test_t3_rejects_a_bad_spec():
    r = run("--mock", "tri", "--tadata-fill-render", "x")
    assert r.returncode != 0
    assert "bad --tadata-fill-render" in r.stderr


def test_t4_kept_copy_after_the_second_render(tmp_path):
    (tmp_path / "render_kept").write_bytes(bytes(range(256)) * 4)
    out = tmp_path / "out"
    out.mkdir()
    r = run("--mock", "tri", "--width", "64", "--height", "64", "--ctx2", "--close-first-early",
            "--kept-copy", str(out), dbg=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (out / "kept.1.bin").read_bytes() == bytes(range(256)) * 4


def test_t4_needs_ctx2():
    r = run("--mock", "tri", "--kept-copy", "/tmp")
    assert r.returncode == 2
    assert "--kept-copy is for tri --ctx2" in r.stderr


def test_t1_probe_depth_scratch(tmp_path):
    # the option exists: on the mock the run gets as far as the kernel poke (no debugfs: ENOENT), it is
    # not a usage error (exit 2)
    r = run("--mock", "probe", "--tri", "pixel", "--width", "64", "--height", "64", "--depth-scratch",
            str(GREEN), dbg=tmp_path)
    assert r.returncode != 2, r.stdout + r.stderr
    assert "kpoke" in (r.stdout + r.stderr)
