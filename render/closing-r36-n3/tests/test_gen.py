# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check, the inputs read at the
frozen commits), every path the generator reads is a [freeze] pin, emitsa.s at the frozen commit
stores what the scorer and the hooks read where they read it, and the hooks' fallback V0-V3 are
the pinned snap0's."""
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", "gen/make.py", "--check"], cwd=KP,
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pins_cover_what_the_generator_reads():
    import make
    import pins
    make.build()
    make.source_facts()
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_emitsa_stores_where_the_scorer_reads():
    import make
    import score
    f = make.source_facts()
    # res+0: the page; then slot 1 (entry 0), slots 2, 3, 4 (entry 1), as byte offsets
    assert f["patches"] == [0, 4 * score.SLOT1, 0, 4 * score.SLOT_PA, 4 * score.SLOT_SA,
                            4 * score.SLOT4]
    assert f["marks"] == [score.M1, score.M4] == [make.M1, make.M4]
    assert f["pa"] == ["pa0", "pa1", "pa2", "pa3"] and f["sa"] == ["sa0", "sa1", "sa2", "sa3"]
    import pins
    s = pins.blob("resgx545:asm/fwtask/emitsa.s").decode()
    assert len(re.findall(r"^\s+emitpds\.tasks\.taske #0, r2, r3, r4, #0x0$", s, re.M)) == 1
    assert "@patch pds0" in s and "@patch pds1" in s and "@patch pds2" in s


def test_the_hooks_fallback_is_the_pinned_snap0():
    import make
    v = make.snap_v()
    h = open(os.path.join(KP, "run/hooks.sh")).read()
    for i, x in enumerate(v):
        assert f"{i}) v=0x{x:08x} ;;" in h, (i, hex(x))
    import importlib.util
    spec = importlib.util.spec_from_file_location("world", os.path.join(KP, "mock/world.py"))
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    assert list(w.V) == v
    assert "\n".join(f"V{i} 0x{x:08x}" for i, x in enumerate(v)) in \
        open(os.path.join(KP, "gen/constants.txt")).read()
