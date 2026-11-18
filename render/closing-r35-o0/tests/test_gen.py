# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check), every repository file
the generator reads is pinned, and the offline known-value checks of the forms (D1, before the
laptop): A''s pa values are E081's kept oreg-x/oreg-y images exactly (1062 of 1062 each), the
assembler at the frozen commit reproduces E417's kept K and P bytes and E081's kept oreg-x case,
A' is injective over both targets and never one of the session's colours, and the mock's masks
are E417's kept images."""
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import make as M  # noqa: E402
import pins  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
PY = sys.executable


def test_generated_files_are_current():
    r = subprocess.run([PY, os.path.join(KP, "gen", "make.py"), "--check"], capture_output=True,
                       text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    M.build()
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_a_prime_reads_e081s_pa_values():
    """D1 offline: pa0 / pa1 under this pixpds and vtxuse are (c + 0.5) * 2 / 64 - 1 (E081)."""
    for axis, nm in ((0, "x"), (1, "y")):
        img = M.kept_image(M.E081 % nm, 0)
        bg = img[(0, 0)]
        tri = {p: v for p, v in img.items() if v != bg}
        assert len(tri) == 1062
        assert all(v == M.clip(p[axis], 64) for p, v in tri.items())
    assert pins.blob(M.E081_BINS % "pds_iter_xy.bin") == open(
        os.path.join(KP, "bins", "pds_iter_xy.bin"), "rb").read()
    toml = pins.blob("resgx545:probes/usse/output-registers.toml").decode()
    block = toml.split('name = "usse-output-registers-oreg-x"')[1].split("[[probe]]")[0]
    assert 'slots = { pixpds = "pds_iter_xy.s", vtxuse = "vtx_coords.s" }' in block
    assert "vtx_coords = 2" in block and "eot" not in block


def test_assembler_reproduces_kept_bytes():
    toml = pins.blob(M.E417_TOML).decode()
    assert '"mov.skipinv.end o0, #0xFF00FF00"' in toml and '"mov.skipinv.end o0, o0"' in toml
    assert M.asm(M.program(["mov.skipinv.end o0, #0xFF00FF00"])) == pins.blob(M.E417_BIN % 0)
    assert M.asm(M.program(["mov.skipinv.end o0, o0"])) == pins.blob(M.E417_BIN % 1)
    oreg = pins.blob(M.E081_BINS % "usse-output-registers-oreg-x__0.bin")
    assert M.asm(M.program(["mov.skipinv.end o0, pa0"])) == oreg


def test_a_prime_is_injective_and_distinct():
    for n in (64, 128):
        vals = [M.f_a(x, y, n, n) for y in range(n) for x in range(n)]
        assert len(set(vals)) == n * n
        assert not {M.K, 0xFF203040, M.fill_colour(), 0x0BAD0000} & set(vals)
        assert not [v for v in vals if v >> 16 == 0x0BAD]


def test_constants():
    c = dict(ln.split("=", 1) for ln in open(os.path.join(KP, "gen", "constants.txt")).read().split())
    assert c["K"] == "0xff00ff00" and c["BG"] == "0xff203040" and c["FILL"] == "0xff336699"
    assert M.background() == 0xFF203040


def test_mock_masks_are_e417s():
    tri = open(os.path.join(KP, "mock", "kept", "tri64.txt")).read().splitlines()
    left = open(os.path.join(KP, "mock", "kept", "left64.txt")).read().splitlines()
    assert len(tri) == 1062 and len(left) == 450
    assert len(open(os.path.join(KP, "mock", "kept", "tri128.txt")).read().splitlines()) == 4284
    assert len(open(os.path.join(KP, "mock", "kept", "left128.txt")).read().splitlines()) == 183
    raw = pins.blob(M.E417 % 64).decode()
    assert re.search(r"isp-o0-start-64__1: o0 mixed 0xff203040 x3646 0xff00ff00 x450", raw)
