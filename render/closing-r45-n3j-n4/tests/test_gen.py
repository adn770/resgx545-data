# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check, the inputs read at the
frozen commits), every path the generator and the test attempts read is a [freeze] pin, each
stage's blob at the frozen commit is its base (emitsb_sbc43) with the cmd 6 branch and nothing
else, stores what the scorer and the hooks read where they read them (job 1's B11
slots and survey, command 6's after-read at 224-255 and M6 in slot 6), holds the form's emit word
once, the generator's, the scorer's and the world's step, stages, plant pairing and declared begin
draws agree, and the hooks' fallback V0-V3 are the pinned snap0's."""
import importlib.util
import os
import re
import struct
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


def world():
    spec = importlib.util.spec_from_file_location("world", os.path.join(KP, "mock/world.py"))
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    return w


def code(text):
    return [ln.split(";")[0].strip() for ln in text.splitlines()
            if ln.split(";")[0].strip()]


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", "gen/make.py", "--check"], cwd=KP,
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pins_cover_what_the_generator_and_the_attempts_read(tmp_path):
    """Every kept file the generator and the test attempts read (round 44's N1 wa and ff, N3 lf at
    the data commit) is a [freeze] pin."""
    import attempt
    import make
    import pins
    make.build()
    pins.blob(f"resgx545:asm/fwtask/{make.BLOB}.s")
    pins.blob(f"resgx545:asm/fwtask/{make.BASE_BLOB}.s")
    for st in make.STAGES[make.STEP]:
        for k, tok in enumerate(((), ("serve",), ("keep",))):
            attempt.build(str(tmp_path / f"{st[0]}{k}"), st[0], tok)
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_each_blob_is_its_base_with_the_cmd_6_branch_only():
    """At the frozen commit: the base's code with the dispatch's last `br @tail` as `br @more` and
    `more:`/`c6:` after its last line (resgx545 r41-n3f's test, per blob)."""
    import make
    import pins
    for st in make.STAGES[make.STEP]:
        s = code(pins.blob(f"resgx545:asm/fwtask/{make.BLOB}.s").decode())
        b = code(pins.blob(f"resgx545:asm/fwtask/{make.BASE_BLOB}.s").decode())
        i = s.index("work:")
        assert s[i + 3] == "br @more"
        assert s[:i + 3] + ["br @tail"] + s[i + 4:s.index("more:")] == b, st
        assert s[s.index("more:"):s.index("c6:") + 1] == [
            "more:", "xor.testtaz.chan0 !c0, p1, r2, #6", "p1 br @c6", "br @tail", "c6:"]
        assert len([x for x in s if x.startswith("emitpds")]) == 1


def test_the_blob_stores_where_the_scorer_and_hooks_read():
    import make
    import pins
    import score
    for st in make.STAGES[make.STEP]:
        src = pins.blob(f"resgx545:asm/fwtask/{make.BLOB}.s").decode()
        patches = [int(x) for x in re.findall(r"@patch res\+(\d+)", src)]
        # B11's: res+0, slot 1, S1, res+0, slots 2 and 3, post sa, post pa, slot 4, pre; then
        # command 6's after-read (224) and slot 6
        assert patches == [0, 4 * 0x44, 4 * 0x54, 0, 4 * 0x48, 4 * 0x4C, 4 * 160, 4 * 192,
                           4 * 0x50, 4 * 128, 4 * 224, 4 * 0x58]
        assert (score.PRE_AT, score.POST_SA_AT, score.POST_PA_AT, score.AFTER_AT) == \
            (make.PRE_AT, make.POST_SA_AT, make.POST_PA_AT, make.AFTER_AT) == (128, 160, 192, 224)
        assert score.AFTER_SLOTS == make.AFTER_SLOTS and 0x40 + 4 * make.AFTER_SLOTS[0] == 224
        marks = [int(x, 16) for x in re.findall(r"mov r7, #(0x5a5a33[0-9a-f]{2})", src)]
        assert marks == [make.M1, make.X0, make.S1, make.M4, make.M6] and score.M6 == make.M6
        c6 = code(src)[code(src).index("c6:"):]
        assert [x for x in c6 if re.fullmatch(r"mov r[4-7], sa\d+", x)] == \
            [f"mov r{4 + k % 4}, sa{k}" for k in range(32)]


def test_each_blob_holds_its_form_s_word_once():
    import make
    import pins
    for st in make.STAGES[make.STEP]:
        sb = make.SIDEBAND
        src = pins.blob(f"resgx545:asm/fwtask/{make.BLOB}.s").decode()
        assert len(re.findall(r"^\s+emitpds\.tasks\.taske #0, r2, r3, r4, #0x%x$" % sb, src,
                              re.M)) == 1
        w = 0xFB20B00000008184 | (sb & 0x3F) << 22 | (sb >> 6 & 0x3F) << 35 | (sb >> 12 & 3) << 54
        blob = open(os.path.join(KP, f"owntask/{make.BLOB}.blob"), "rb").read()
        n = struct.unpack_from("<H", blob, 8)[0]
        assert struct.unpack_from(f"<{n}Q", blob, 16).count(w) == 1


def test_the_step_is_one_everywhere():
    import make
    import score
    w = world()
    assert make.STEP == score.STEP == w.STEP == attempt_step()
    assert list(CFG["stages"]) == [s[0] for s in make.STAGES[make.STEP]] == list(score.STAGES)
    assert {k: (v[0], v[1]) for k, v in score.STAGES.items()} == \
        {s[0]: (s[1], s[4]) for s in make.STAGES[make.STEP]}
    mine = {s[0] for s in make.STAGES[make.STEP]}
    assert score.PLANT.keys() >= {k for k in make.PLANT if k in mine}
    assert {k: v for k, v in score.PLANT.items() if k in mine} == \
        {k: v for k, v in make.PLANT.items() if k in mine}
    assert {k: v for k, v in score.DRAWS.items() if k in mine} == \
        {k: v for k, v in make.DRAWS.items() if k in mine} == \
        {k: dict(CFG["stages"][k])["begin_draws"] for k in mine
         if "begin_draws" in CFG["stages"][k]}
    assert score.READS == make.READS and score.LANDS == make.LANDS
    assert {k: v for k, v in score.ENDS.items() if k in mine} == \
        {k: v for k, v in make.ENDS.items() if k in mine and v}
    assert all(set(v[1]) <= set(CFG["stages"]) for v in w.EXPECT.values())
    for st, m, image, keys, jobs in make.STAGES[make.STEP]:
        d = CFG["stages"][st]
        assert d["owntask"] == {"blob": make.BLOB, "arm": make.arm(image)}
        assert {k: d[k] for k in ("own_gate", "begin_draws", "end_draws", "on_gate_fail",
                                  "gate_order") if k in d} == dict(keys)


def attempt_step():
    import attempt
    return attempt.make.STEP


def test_the_hooks_fallback_is_the_pinned_snap0():
    import make
    v = make.snap_v()
    h = open(os.path.join(KP, "run/hooks.sh")).read()
    for i, x in enumerate(v):
        assert f"{i}) v=0x{x:08x} ;;" in h, (i, hex(x))
    assert list(world().V) == v
    assert "\n".join(f"V{i} 0x{x:08x}" for i, x in enumerate(v)) in \
        open(os.path.join(KP, "gen/constants.txt")).read()
