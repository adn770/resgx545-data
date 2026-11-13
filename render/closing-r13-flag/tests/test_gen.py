# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r13-flag's generator and the published records it rests on. The generator is
current; every repository file it reads is pinned; the programs that rerun a kept job rebuild its
published program byte for byte; the frozen models reproduce the kept jobs they rest on (E561's
tile law on E566's tw32-ctl, E383's bit-11 faults and bit-12 words, E700's counter on its own
series); the rivals part where the plan needs them to; every move model's reads fit the scratch."""
import gzip
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import f1  # noqa: E402
import f2  # noqa: E402
import f3  # noqa: E402
import law  # noqa: E402
import pins  # noqa: E402
import tex  # noqa: E402

PY = sys.executable
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def binfile(name):
    return open(os.path.join(KP, "bins", name), "rb").read()


def test_generator_current():
    r = subprocess.run([PY, "-B", os.path.join(KP, "gen/make.py"), "--check"], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    f1.jobs()
    f2.jobs(pins.blob)
    f2.e383_faults(pins.blob)
    f3.blue_text(pins.blob)
    pins.blob(f3.GREEN)
    pins.blob(f3.GREEN_SRC)
    pins.blob(f3.PROGS)
    for p in ("data:render/closing-r10-tex/gen/pins.py", "data:render/closing-r10-tex/gen/tex.py",
              "data:render/closing-r10-tex/gen/addr.py"):
        pins.blob(p)
    assert pins.READ <= set(CFG["freeze"]["pins"]), sorted(pins.READ - set(CFG["freeze"]["pins"]))


def test_copied_generators_are_r10_tex_s():
    """gen/pins.py and gen/tex.py are r10-tex's with the session's name; gen/law.py's tile law is
    r10-tex addr.py's morton and index, character for character."""
    for f in ("pins.py", "tex.py"):
        pub = pins.blob(f"data:render/closing-r10-tex/gen/{f}").decode()
        mine = open(os.path.join(KP, "gen", f)).read()
        strip = lambda t: [ln for ln in t.splitlines() if "r10" not in ln and "r13" not in ln]
        assert strip(pub) == strip(mine), f
    import ast

    def fns(src):
        out = {}
        for n in ast.parse(src).body:
            if isinstance(n, ast.FunctionDef) and n.name in ("morton", "index"):
                if isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
                    n.body = n.body[1:]
                out[n.name] = ast.dump(n)
        return out
    addr = fns(pins.blob("data:render/closing-r10-tex/gen/addr.py").decode())
    assert addr and addr == fns(open(os.path.join(KP, "gen/law.py")).read())


# ---- f1 ------------------------------------------------------------------------------------
def test_f1_pair_a_rebuilds_e566s_programs():
    """f1-ref-a is E566's published tw32-ctl program byte for byte; f1-tw32 differs from it only
    in T3's immediate (bit 14), the published tw32-t3b14 program not being kept."""
    pub = pins.blob(f1.PUB_CTL)
    assert binfile("f1-ref-a.bin") == pub
    a, b = binfile("f1-ref-a.bin"), binfile("f1-tw32.bin")
    assert len(a) == len(b)
    diff = [i for i in range(0, len(a), 8) if a[i:i + 8] != b[i:i + 8]]
    assert len(diff) == 1
    sa, sb = tex.text(f1.specs()[f1.SPEC_A_CTL]["spec"]), tex.text(f1.specs()[f1.SPEC_A_B14]["spec"])
    d = [(x, y) for x, y in zip(sa.splitlines(), sb.splitlines()) if x != y]
    assert d == [("mov r23, #0x00800800", "mov r23, #0x00804800")], d


def test_f1_tile_law_gives_e566s_kept_control_texmodel_does_not():
    kept = pins.kept_pixels(f1.E566_CTL)
    assert f1.ref_a() == kept
    tm = pins.module(tex.TEXMODEL)
    plain = tm.render(dict(f1.specs()[f1.SPEC_A_CTL]["spec"], pages=16), {})
    assert sum(a != b for a, b in zip(plain, kept)) == 1024


def test_f1_pair_b_coordinates_are_exact():
    for y in range(32):
        for x in range(64):
            u = tex.coord(f1.U_SMALL, x, y)
            assert tex.exact_f32(u) and u * 4096 == x
            assert tex.exact_f32(tex.coord(f1.V_ROW, x, y))
            assert f1.texel_b(x, y) == (0, y, x)


def test_f1_models_part_and_fit_the_scratch():
    b = f1.models_b()
    ims = {m: b[m][1] for m in f1.MOVE_MODELS}
    for m in f1.MOVE_MODELS:
        for n in f1.MOVE_MODELS:
            if m < n:
                assert sum(x != y for x, y in zip(ims[m], ims[n])) >= 1024, (m, n)
    ref = f1.image_b("REF")
    assert all(sum(x != y for x, y in zip(ims[m], ref)) >= 2016 for m in ("H-TWIDX", "H-TWX"))
    # no move model reads past the probe's default scratch (16 pages) on pair B, and H-TWIDX not
    # on pair A either (so its no-fault prediction there is the scratch's, not the mapping's end)
    assert f1.reach(ims.values()) < f1.PAGES * 1024
    a = f1.models_a()
    assert f1.reach([a["H-TWIDX"][1]]) == 1023 + 4096 < f1.PAGES * 1024
    # H-TWX's pair-A read is 65536 dwords on: past the 16 pages, on one page (the texture is 4 KiB)
    assert a["H-TWX"] == ("fault", 0x40000) and 65536 * 4 == 0x40000


def test_f1_rows():
    js = f1.jobs()
    assert [j[0] for j in js] == ["f1-ref-a", "f1-tw32", "f1-ref-b", "f1-small"]
    assert [j[3]["t3"] >> 14 & 1 for j in js] == [0, 1, 0, 1]
    assert all(j[3]["t1"] == 0x0C01F01F for j in js)


# ---- f2 ------------------------------------------------------------------------------------
def test_f2_programs_are_e383s():
    for n, pin in f2.BINS.items():
        assert binfile(n) == pins.blob(pin)


def test_f2_e383_faults_are_the_frozen_status_and_page():
    f = f2.e383_faults(pins.blob)
    assert len(f) == 9
    assert {s for s, _ in f} == {f2.STAT}
    assert {f"{int(a, 16) & ~0xFFF:#x}" for _, a in f} == {f2.PAGE}
    assert [f[m][1] for m in f2.MODES] == ["0x3700103b", "0x37001003", "0x37001013"]


def test_f2_control_rule_holds_on_e383s_runs():
    w = set(f2.mode0_words(pins.blob))
    rows = {}
    for m in f2.ROW.finditer(pins.blob(f2.RAW12).decode()):
        rows.setdefault(m.group(1), {})[int(m.group(2))] = [int(t, 16) for t in m.group(3).split()]
    for r in rows.values():
        px = [v for y in sorted(r) for v in r[y]]
        assert len(px) == 4096 and sum(v in w for v in px) >= f2.INSET_MIN


# ---- f3 ------------------------------------------------------------------------------------
def test_f3_programs():
    assert binfile("p1131-green__0.bin") == pins.blob(f3.GREEN)
    green = tex.assemble(pins.blob(f3.GREEN_SRC).decode())
    assert green == pins.blob(f3.GREEN)
    progs = tomllib.loads(pins.blob(f3.PROGS).decode())
    blue = next(p for p in progs["probe"] if p["name"] == "p1131-blue")
    assert blue["source"] == "pix_op.s" and blue["cases"] == [[f3.BLUE_OP]]
    assert binfile("p1131-blue__0.bin") == tex.assemble(f3.blue_text(pins.blob))


def test_f3_forms_are_e700s_and_e413s():
    """The two-block args are E700's table form (vdm/verification-1141ta, the $S/ names aside); the
    one-block form is E413's poke (probes/vdm/templates/state1-hang.sh)."""
    assert f3.two(4, 2).endswith('--vdm 1^=0x00000c00 "$S/bins/p1131-blue__0.bin"')
    assert f3.two(2, 1).endswith('--vdm 9^=0x00000600 "$S/bins/p1131-blue__0.bin"')
    assert f3.two(7, 2).endswith('--vdm 1^=0x00000a00 "$S/bins/p1131-blue__0.bin"')
    assert f3.one(7) == "tri --poke vdm:1^=0xa00"
    assert f3.one(7, 128) == "tri --width 128 --height 128 --poke vdm:1^=0xa00"
    assert f3.TWO.startswith("probe --tri pixel --temps 32 --pixels --width 64 --height 64 "
                             "--vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0")


def test_f3_counter_reproduces_e700s_series():
    """gen/f3.py's counter (M1) on E700's five series, each opened by a reset: the 15 hangs E700
    lists (A1 at jobs 5 and 10, A2 at 9, A3 at 2, 4, 6, A4 at 4, 5, 7, 9, 11, 13, 15, A5 at 3, 6)."""
    walk = [(4, 2), (2, 4), (2, 4), (2, 6), (7, 7), (5, 4), (5, 6), (7, 2), (6, 7), (5, 7), (4, 3),
            (5, 5), (5, 3), (5, 7), (6, 4), (6, 4)]
    series = {"A1": [(4, 2)] * 12, "A2": [(3, 2)] * 12, "A3": [(7, 2)] * 6, "A4": walk,
              "A5": [(5, 3)] * 6}
    want = {"A1": [5, 10], "A2": [9], "A3": [2, 4, 6], "A4": [4, 5, 7, 9, 11, 13, 15], "A5": [3, 6]}
    for s, jobs in series.items():
        c, hung = 0, []
        for i, (a, b) in enumerate(jobs, 1):
            add = f3.g(a) + f3.g(b)
            if c + add > 8:
                hung.append(i)
                c = 0
            else:
                c += add
        assert hung == want[s], s


def test_f3_predictions():
    p = f3.predictions()
    m1 = {n: v["M1"] for n, v in p.items()}
    m3 = f3.simulate("M3")
    assert [n for n, v in m3.items() if v == "hang"] == [
        "f3-c-b", "f3-v1c0", "f3-shape-b", "f3-idle-b", "f3-fill-b", "f3-hl-b"]
    assert m1["f3-v1c0"] == "ok" and p["f3-v1c5"]["H-C05"] == "hang" and p["f3-v1c5"]["M3"] == "ok"
    # every clause rival parts from M1 on its row
    for m, rows in f3.CLAUSE.items():
        if m in ("M3", "H-C05"):
            continue
        assert all(p[r][m] != m1[r] for r in rows), m
