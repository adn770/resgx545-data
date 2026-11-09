# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""p1141/tex: every `sgxfive-test tri` option set of the plan is accepted by the newest tool (no tool change is
needed: --keep-going already reaches --dump-render after a failed image check, source lines of cmd_tri). Run
against the mock:

    SGXFIVE_TEST=.../p1140/tool/userspace/libsgxfive/build/sgxfive-test \
        ~/src/sgxhumation/.venv/bin/pytest p1141/tex/tool-tests -q
"""
import json
import os
import pathlib
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve().parent
TOOL = os.environ.get("SGXFIVE_TEST", str(HERE.parent.parent.parent / "p1140/tool/userspace/libsgxfive/build/sgxfive-test"))
CASES = [c for c in json.loads((HERE.parent / "gen/cases.json").read_text()) if c["kind"] == "tri"]


@pytest.fixture(scope="module", autouse=True)
def tool_exists():
    if not pathlib.Path(TOOL).exists():
        pytest.skip(f"{TOOL} not built")


@pytest.fixture(scope="module")
def fake_debugfs(tmp_path_factory):
    d = tmp_path_factory.mktemp("debugfs")
    (d / "kpoke").write_text("")
    for n in ("render_param", "render_tadata"):
        (d / n).write_bytes(b"\0" * 4096)
    return d


@pytest.mark.parametrize("c", CASES, ids=[c["name"] for c in CASES])
def test_tri_options_accepted(c, tmp_path, fake_debugfs):
    opts = [o.replace("@D@", str(tmp_path)) for o in c["opts"]]
    r = subprocess.run([TOOL, "--mock", "tri", *opts], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "SGXFIVE_DEBUGFS": str(fake_debugfs), "SGXFIVE_KPOKE": str(fake_debugfs / "kpoke")})
    out = r.stdout + r.stderr
    assert "bad option" not in out and "unknown option" not in out and "usage:" not in out.lower(), out[:400]
    assert "job: ok" in out or "diff:" in out, out[:400]
