# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check, the kept inputs read
at the frozen data commit and the bound tool sources at their commits, sha256 checked against
TOOLSRC.sha256), every data path the generator reads is a [freeze] pin, t30's source says what
the rows rely on, the programs say what the plan's sketch says, and no two values collide."""
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", "gen/make.py", "--check"], cwd=KP, capture_output=True,
                       text=True, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pins_cover_what_the_generator_reads():
    import make
    import pins
    make.build()
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_t30_facts():
    import make
    assert make.t30_facts() == dict(pixels=True, coords=True, context=True, attrs16=True)


def test_programs():
    import make
    w = make.program("w", {15: 0x5A35110F})
    assert "iaddu32.testtaz.chan0 sa15, p0, r1, r2" in w and "#0x5A35110E" in w
    assert "mov r3, sa15" in w and "stad [r29,+#0], r3" in w and "#0x%08X" % make.K1 in w
    w = make.program("w", {1: 0x5A351201, 5: 0x5A351205, 7: 0x5A351207})
    assert all(f"sa{n}, p0" in w for n in (1, 5, 7)) and "stad [r29,+#2], r3" in w
    x = make.program("x", {1: 0x5A351401})
    assert "sa1, p0" in x and "#0x%08X" % make.K2 in x
    r = make.program("r", n=5)
    assert "mov r10, sa5" in r and "mov.skipinv.end o0, r10" in r and "xor" not in r
    u = make.program("u")
    assert "mov r10, r20" in u and "r20," not in u.replace("mov r10, r20", "")
    t = make.program("t", 0x7E000114)
    assert "mov.skipinv r20, #0x7E000114" in t
    t8 = make.program("t8", make.t8_markers(6))
    assert all(f"r{k}" in t8 for k in range(8)) and not any(f"r{k}" in t8 for k in range(8, 32))
    k = make.program("k")
    assert "sa" not in k.split("phas")[1] and "r20" not in k
    assert "mov r10, pa0" in make.program("c")


def test_constants_distinct():
    import make
    ra, rt = make.a_rows(), make.t_rows()
    vals = [m for r in ra + rt if r["ms"] for m in r["ms"].values()]
    vals += [make.K1, make.K2, make.K3, make.fill_colour(), *make.tri_colours()]
    assert len(vals) == len(set(vals))
    assert not {v for v in vals if v >> 16 in (0x5CAF, 0x5CB0, 0x5CB1, 0xD000)}
    assert not set(vals) & {0xDEADBEEF} and all(v > 0x001F003F for v in vals)
