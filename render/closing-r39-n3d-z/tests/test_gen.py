# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check, the inputs read at the
frozen commits), every path the generator and the test attempts read is a [freeze] pin, the
blob's source at the frozen commit stores what the scorer and the hooks read where they read it
(X0 right after the emit, S1 entry 1's first work), gates the emit on pa1 bit 8 with cmd untouched
before it and holds the STEP's emit word, and the hooks' fallback V0-V3 are the pinned snap0's."""
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.dont_write_bytecode = True
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", "gen/make.py", "--check"], cwd=KP,
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pins_cover_what_the_generator_and_the_attempts_read(tmp_path):
    import attempt
    import make
    import pins
    make.build()
    make.source_facts()
    attempt.build(str(tmp_path), ("past",))
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_the_blob_stores_where_the_scorer_reads():
    import make
    import score
    f = make.source_facts()
    # res+0: the page; slot 1 (entry 0); slot 5 (S1, entry 1's first); then res+0 and slots 2,
    # 3, 4 (entry 1), as byte offsets
    assert f["patches"] == [0, 4 * 0x44, 4 * score.S1_AT, 0, 4 * score.SLOT_PA,
                            4 * score.SLOT_SA, 4 * 0x50]
    assert f["marks"] == [make.M1, make.X0, make.S1, make.M4]
    assert f["after_emit"] == ["mov r7, #0x5a5a3303", "stad [r9,+#2], r7", "idf drc0, bif",
                               "wdf drc0"]
    assert score.X0_AT == 0x44 + 2 == make.X0_AT == 70
    assert f["entry1"][1:3] == ["mov r7, #0x5a5a3304", "stad [r9,+#0], r7"]
    assert score.S1_AT == make.S1_AT == 84
    # the gate's pa1 read (entry 0), then entry 1's pa0-pa3
    assert f["pa"] == ["pa1", "pa0", "pa1", "pa2", "pa3"] and f["sa"] == ["sa0", "sa1", "sa2", "sa3"]
    assert f["emit"] == 1
    import pins
    s = pins.blob(f"resgx545:asm/fwtask/{make.BLOB}.s").decode()
    assert len(re.findall(r"^\s+emitpds\.", s, re.M)) == 1
    assert len(re.findall(r"^\s+" + re.escape(make.EMIT[make.STEP]) + "$", s, re.M)) == 1
    assert f["emit_word"] == make.EMIT[make.STEP]
    assert "@patch pds0" in s and "@patch pds1" in s and "@patch pds2" in s


def test_the_blob_emits_only_on_a_pass_with_pa1_bit_8():
    """c1 (cmd 1) reads pa1, tests it against 0x100 and tail-calls without it before any store."""
    import make
    f = make.source_facts()
    assert f["c1"] == ["mov r5, pa1", "mov r8, #0x00000100",
                       "and.testtanz.chan0 !c0, p0, r5, r8  ; p0 = pa1 bit 8 (a host kick pass, E746)",
                       "p0 br @kick", "br @tail", "kick:"]
    assert make.KICK_GATE == 0x100


def test_the_step_is_one_everywhere():
    import make
    import score
    assert make.STEP == score.STEP
    assert CFG["stages"]["own"]["owntask"]["arm"] == make.ARM
    assert CFG["stages"]["own"]["owntask"]["blob"] == make.BLOB


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
