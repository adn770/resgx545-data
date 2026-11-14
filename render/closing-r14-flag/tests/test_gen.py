# SPDX-License-Identifier: MIT
"""tests/test_gen.py: r14-flag's generator and the published records it rests on. The generator is
current; every repository file it reads is pinned; the copied readers are the published ones; the
programs that rerun a kept job rebuild its published program byte for byte; the frozen forms
reproduce E1033's two fault pages (the post hoc fit), read inside t14's 1 MiB scratch, and part
from each other where the plan needs them to; f2's words were never run, cover the target (H-COVER's
premise) and part H-EVEN from R7-BLK (and, at 768 x 640, H-LASTBLOCK from H-HIGHSLOT)."""
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
import law  # noqa: E402
import pins  # noqa: E402
import q139_fit as Fit  # noqa: E402
import q139even as E  # noqa: E402
import tex  # noqa: E402

PY = sys.executable
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
R13F = "data:render/closing-r13-flag/out/20261113-220930/f1/"
COPIES = {"gen/q139_fit.py": "data:render/closing-r10-geo/gen/q139_fit.py",
          "gen/q139model.py": "data:render/closing-r10-geo/gen/q139model.py",
          "gen/q139even.py": "data:render/closing-r10-geo/gen/q139even.py",
          "score/lib_dump.py": "data:render/closing-r10-geo/score/lib_dump.py",
          "score/pbdump_dump.py": "data:render/closing-r10-geo/score/pbdump_dump.py",
          "score/region_tiles_dump.py": "data:render/closing-r10-geo/score/region_tiles_dump.py"}


def binfile(name):
    return open(os.path.join(KP, "bins", name), "rb").read()


def test_generator_current():
    r = subprocess.run([PY, "-B", os.path.join(KP, "gen/make.py"), "--check"], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    f1.jobs()
    for p in ("data:render/closing-r10-tex/gen/pins.py", "data:render/closing-r10-tex/gen/tex.py",
              "data:render/closing-r10-tex/gen/addr.py", *COPIES.values(), *f2.DATASETS):
        pins.blob(p)
    for n in ("cases.tsv", "f1-ref-a.txt.gz", "f1-ref-b.txt.gz", "f1-tw32.txt.gz", "f1-tw32.dmesg.gz",
              "f1-small.txt.gz", "f1-small.dmesg.gz"):
        pins.blob(R13F + n)
    assert pins.READ <= set(CFG["freeze"]["pins"]), sorted(pins.READ - set(CFG["freeze"]["pins"]))


def test_copied_files_are_the_published_ones():
    """gen/pins.py and gen/tex.py are r10-tex's with the session's name; gen/law.py's tile law is
    r10-tex addr.py's morton and index; r10-geo's Q139 readers byte for byte."""
    for f in ("pins.py", "tex.py"):
        pub = pins.blob(f"data:render/closing-r10-tex/gen/{f}").decode()
        mine = open(os.path.join(KP, "gen", f)).read()
        strip = lambda t: [ln for ln in t.splitlines() if "r10" not in ln and "r14" not in ln]  # noqa: E731
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
    for mine, pub in COPIES.items():
        assert open(os.path.join(KP, mine), "rb").read() == pins.blob(pub), mine


# ---- f1 ------------------------------------------------------------------------------------
def kept_px(name):
    return pins.pixels(gzip.decompress(pins.blob(R13F + name + ".txt.gz")).decode(errors="replace"))


def test_f1_programs_rebuild_e566s_and_differ_in_t3_only():
    assert binfile("f1-ref-a.bin") == pins.blob(f1.PUB_CTL)
    for ref, b14 in (("f1-ref-a", "f1-tw32"), ("f1-ref-b", "f1-small")):
        a, b = binfile(ref + ".bin"), binfile(b14 + ".bin")
        assert len(a) == len(b)
        assert len([i for i in range(0, len(a), 8) if a[i:i + 8] != b[i:i + 8]]) == 1
    s = {n: sp for n, _, _, sp, _, _ in f1.jobs()}
    assert s["f1-zero"]["t3"] == s["f1-small"]["t3"] and s["f1-zero"]["u"] == f1.U_ZERO
    sa, sb = tex.text(s["f1-small"]), tex.text(s["f1-zero"])
    d = [(x, y) for x, y in zip(sa.splitlines(), sb.splitlines()) if x != y]
    assert len(d) >= 1 and all("r24" in x or "#0x" in x for x, _ in d), d


def test_f1_references_are_e1033s_kept_images():
    """The controls' frozen images are what E1033's references drew at 16 pages (E566's kept
    tw32-ctl, the tile law's column 0): the scratch size is the only change."""
    assert f1.image("f1-ref-a", "REF") == pins.kept_pixels(f1.E566_CTL) == kept_px("f1-ref-a")
    assert f1.image("f1-ref-b", "REF") == kept_px("f1-ref-b")


def test_f1_coordinates_are_exact():
    for y in range(32):
        for x in range(64):
            for u_spec, u_want in ((f1.U_SMALL, f1.F(x, 4096)), (f1.U_ZERO, 0)):
                u = tex.coord(u_spec, x, y)
                assert tex.exact_f32(u) and u == u_want
            assert tex.exact_f32(tex.coord(f1.V_ROW, x, y))


def kept_fpage(name):
    dm = gzip.decompress(pins.blob(R13F + name + ".dmesg.gz")).decode()
    txt = gzip.decompress(pins.blob(R13F + name + ".txt.gz")).decode()
    a = int(re.findall(r"BIF fault 0x[0-9a-f]+ at (0x[0-9a-f]+)", dm)[-1], 16)
    sc = int(re.search(r"scratch at (0x[0-9a-f]+)", txt).group(1), 16)
    return (a & ~0xFFF) - sc


def test_f1_forms_fit_e1033s_fault_pages():
    """Post hoc: E1033's kept pages are + 0x21000 and + 0x40000; every form puts f1-small's
    unmapped reads on + 0x40000 (and the page after, at most), the lowest, and f1-tw32's pixel
    (16, 0) on + 0x21000 (the order caveat: f1.py's docstring)."""
    assert {n: kept_fpage(n) for n in f1.E1033_FPAGE} == f1.E1033_FPAGE
    for m in f1.FORMS:
        p = f1.e1033_pages("f1-small", m)
        assert p[0] == 0x40000 and set(p) <= {0x40000, 0x41000}, (m, p)
        i = f1.indices("f1-tw32", m)[16]
        assert (i * 4) & ~0xFFF == 0x21000, (m, hex(i * 4))
        assert 0x21000 in f1.e1033_pages("f1-tw32", m)


def test_f1_forms_read_inside_the_1mib_scratch_and_part():
    rows = ("f1-tw32", "f1-small", "f1-zero")
    r = f1.reach([(row, m) for row in rows for m in f1.FORMS])
    assert f1.E1033_PAGES * 1024 * 4 < r < f1.PAGES * 1024, r
    for row in rows:
        ims = {m: f1.image(row, m) for m in f1.FORMS}
        ref = f1.image(row, "REF")
        for a in f1.FORMS:
            assert sum(x != y for x, y in zip(ims[a], ref)) >= 1024, (row, a)
            for b in f1.FORMS:
                if a < b and not (row != "f1-tw32" and {a, b} == {"H-TWP4096", "H-TWP4096-NS"}):
                    assert sum(x != y for x, y in zip(ims[a], ims[b])) >= 1024, (row, a, b)
    # where s = 0 (f1-small, f1-zero) the two pitch-4096 forms are one image: f1-tw32 parts them
    for row in ("f1-small", "f1-zero"):
        assert f1.image(row, "H-TWP4096") == f1.image(row, "H-TWP4096-NS")
    assert f1.models("f1-zero")["H-MOVE0"][1] == f1.image("f1-zero", "REF") == f1.image("f1-ref-b", "REF")


# ---- f2 ------------------------------------------------------------------------------------
def planned():
    return [(n, w, h, fx) for n, st, w, h, fx in f2.ROWS if st != "control"]


def test_f2_words_were_never_run():
    text = "".join(pins.blob(p).decode(errors="replace").lower() for p in f2.DATASETS)
    for n, w, h, fx in planned():
        assert "0x%08x" % f2.word(w, h, fx) not in text, n


def test_f2_rows_cover_the_target_at_fx_2_or_3_mod_4():
    for n, w, h, fx in planned():
        m1 = f2.word(w, h, fx)
        nn, bx, by = Fit.bounds(m1, Fit.rule(w, h)[6])
        assert bx[1] == fx and fx % 4 in (2, 3) and fx >= -(-w // 32), n
        assert (m1 ^ Fit.rule(w, h)[5]) & ~(0xFF << (12 if nn == 2 else 22)) == 0, n


def test_f2_rows_part_the_rivals():
    for n, w, h, fx in planned():
        k = f2.kp(w, h, fx)
        pe, pb = E.predict(w, h, k, "H-EVEN"), E.predict(w, h, k, "blkrow")
        assert sum(pe[t] != pb[t] for t in pe) >= 4, n
        fs = f2.flags(w, h, k)
        if w == 768:
            assert fs["H-LASTBLOCK"][0] != fs["H-HIGHSLOT"][0], n
            assert fs["H-LASTBLOCK"][1] != fs["H-HIGHSLOT"][1], n
    for n, st, w, h, fx in f2.ROWS:
        if st == "control":
            k = f2.kp(w, h, None)
            assert E.predict(w, h, k, "H-EVEN") == E.predict(w, h, k, "blkrow")
            assert not E.wrong(E.predict(w, h, k, "H-EVEN"))
