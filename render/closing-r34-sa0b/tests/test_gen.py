# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check, every kept input read at
the frozen data commit and the bound t10 source at its commit, sha256 checked against
TOOLSRC.sha256), every data path the generator reads is a [freeze] pin, and the programs say what
the plan's sketch says (assembled from the listing the assembler prints)."""
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
    assert CFG["freeze"]["resgx545"].startswith("914dd23")


def test_programs():
    import make
    w = make.program("w", 0x5A0C0A01)
    assert "iaddu32.testtaz.chan0 sa0, p0, r1, r2" in w and "#0x5A0C0A00" in w and "#0x00000001" in w
    assert "mov r3, sa0" in w and "stad [r29,+#0], r3" in w and "#0x%08X" % make.K1 in w
    r = make.program("r")
    assert "mov r10, sa0" in r and "stad [r29,+#0], r10" in r and "mov.skipinv.end o0, r10" in r
    assert "xor" not in r and not any(ln.split()[1].startswith(("sa", "pa"))
                                      for ln in r.splitlines()[2:] if ln.split()[0].startswith("mov"))
    p = make.program("p")
    assert "mov r10, pa0" in p and "xor" not in p
    assert make.posthoc_fit() == "R M 12 PREV 8 of 20; P PREV 8 of 8"
    k = make.program("k")
    assert "sa" not in k.split("phas")[1] and "pa0" not in k


def test_constants_distinct():
    import make
    marks = [make.marker(rep, i) for rep in "ab" for i in range(1, 9)]
    tri = make.tri_colours()
    colours = [make.K1, make.K3, make.fill_colour(), *tri]
    assert make.K2 == make.K4 == 0                  # E1139: readers output the value read
    vals = marks + colours
    assert len(vals) == len(set(vals))
    vals = set(vals)
    # no value the tool hides: the scratch fill of dword 0, the pixels' sentinel
    assert not vals & {0xD0000000, 0xDEADBEEF}
    assert tri == (0xFF00FF00, 0xFF203040) and make.fill_colour() == 0xFF336699
