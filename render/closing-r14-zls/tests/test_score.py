# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept directories it must hold on and must fail on.

Kept records (pinned, read at the frozen data commit): E977's z243-ctl and z242-c-f0/f1/f2, E1029's
zb-m4 and zb-m40, E1030's zbs-base, zbs-c12, zbs-c16, zbs-set and zbr-c16, E996's zov rows, E1031's
zf-flat-f6, E986's z2y-f6, z2y-f7 and z2d-f7. The controls PASS on their kept records and FAIL on a
changed byte; the model-free stencil read explains E1030's kept stencil stores (2048 of 2048) and
the pitch rivals all hold at 64 x 32 G 1 (why zbits2 runs G 2); the floor rule and E996's owner
rule hold on E977's and E996's kept dumps; rows built from one model's prediction hold that model
and fail its rivals; E1031's flat dump held FL-CONST and FL-SHAPE and fails FL-HEAD at 0.25; E986's
z2y-f7 holds both F7I models; E977's z242-c-f2 holds L16-TILED only. Rows not given cannot tell."""
import gzip
import os
import struct
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import score as SC  # noqa: E402
import z14 as Z  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")
R9X = "data:render/closing-r9-x/out/20261113-081821/zls/"
R10X = "data:render/closing-r10-x/out/20261113-101116/"
R10Z = "data:render/closing-r10-zls/out/20261113-102039/zst2/"
R13Z = "data:render/closing-r13-zls/out/20261113-213117/"


def table(stage):
    return {ln.split("|")[0]: ln.rstrip("\n").split("|", 5)
            for ln in open(os.path.join(KP, f"tables/{stage}.txt"))
            if ln.strip() and not ln.startswith("#")}


def kept(d, stage, jobs):
    """jobs: {name: (text, {suffix: bytes})}"""
    d.mkdir(parents=True)
    t = table(stage)
    rows = ["\t".join(COLS)]
    for n, (text, files) in jobs.items():
        (d / f"{n}.txt.gz").write_bytes(gzip.compress(text.encode()))
        for suf, b in files.items():
            (d / f"{n}{suf}.gz").write_bytes(gzip.compress(b))
        r = t[n]
        rows.append("\t".join([n, stage, r[1], r[2], r[3], r[4], "x", "1", "ok", "-", "-", "0"]))
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text("name\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return d


def score(stage, d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), stage, str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def line(out, kind, n):
    return [ln for ln in out.splitlines() if ln.startswith(f"{kind} {n}:")][0]


def b(p):
    return pins.blob(p)


def t(p):
    return pins.blob(p).decode()


def pack(v):
    return struct.pack("<%dI" % len(v), *v)


def flip(x):
    return x[:-1] + bytes([x[-1] ^ 1])


# ---- zgran ------------------------------------------------------------------------------------
ZB_TXT = t(R13Z + "zbase/zb-m4.txt.gz")       # 20 pages: depth 0x3e001000, store 0x3e015000


def store_of(pred, fill):
    st = [fill] * (Z.ZB_PAGES * 1024)
    for i, v in pred.items():
        st[i] = v
    return pack(st)


def zgran_controls():
    return {"zg-c-ctl": (t(R9X + "z243-ctl.txt.gz"),
                         {".depth-store.1.bin": b(R9X + "z243-ctl.depth-store.1.bin.gz")}),
            "zg-c-m4": (ZB_TXT, {".depth-store.1.bin": b(R13Z + "zbase/zb-m4.depth-store.1.bin.gz")}),
            "zg-c-m40": (ZB_TXT, {".depth-store.1.bin": b(R13Z + "zbase/zb-m40.depth-store.1.bin.gz")})}


def test_zgran_kept_controls_and_model_rows(tmp_path):
    jobs = zgran_controls()
    for n, m in Z.GRAN_MOVES.items():
        jobs[n] = (ZB_TXT, {".depth-store.1.bin": store_of(dict(enumerate(Z.gran_predict("G16", m))),
                                                           Z.ZB_SFILL)})
    for n, f in Z.INT_ROWS.items():
        jobs[n] = (ZB_TXT, {".depth-store.1.bin": store_of(Z.int_predict(f, "I-MOVED-L32"),
                                                           Z.INT_SFILL)})
    jobs["zb2-d12"] = (ZB_TXT, {".depth-store.1.bin": store_of(
        dict(enumerate(Z.d12_predict("H-DEPTH-LIN"))), Z.ZB_SFILL)})
    out = score("zgran", kept(tmp_path / "k", "zgran", jobs))
    for n in ("zg-c-ctl", "zg-c-m4", "zg-c-m40"):
        assert line(out, "CONTROL", n).endswith("PASS"), line(out, "CONTROL", n)
    assert "SUMMARY: zgran: G16 (5 of 5 rows decided)" in out
    for m in ("G8", "G32", "G64", "H-BYTE"):
        assert f"SUMMARY: zgran: {m} is not supported" in out
    assert "SUMMARY: zgran: I-MOVED-L32 (2 of 2 rows decided)" in out
    assert "SUMMARY: zgran: I-MOVED-L16 is not supported" in out
    assert "SUMMARY: zgran: I-UNMOVED-L32 is not supported" in out
    assert "SUMMARY: zgran: H-DEPTH-LIN (1 of 1 rows decided)" in out
    assert "READING zg-m10: store dword k = depth dword k + d = 4" in out


def test_zgran_controls_fail_and_addresses(tmp_path):
    jobs = zgran_controls()
    tx, f = jobs["zg-c-m40"]
    jobs["zg-c-m40"] = (tx, {".depth-store.1.bin": flip(f[".depth-store.1.bin"])})
    jobs["zg-m8"] = (ZB_TXT.replace("depth store: 0x3e015000", "depth store: 0x3e016000"),
                     {".depth-store.1.bin": store_of(dict(enumerate(Z.gran_predict("G8", 8))),
                                                     Z.ZB_SFILL)})
    out = score("zgran", kept(tmp_path / "k", "zgran", jobs))
    assert line(out, "CONTROL", "zg-c-m40").endswith("FAILED")
    assert "controls FAILED" in out
    assert line(out, "ROW", "zg-m8").endswith("cannot tell")
    assert line(out, "ROW", "zg-f1").endswith("cannot tell")


# ---- zbits2 (the stencil rows) ----------------------------------------------------------------
def r13(n):
    return (t(R13Z + f"zbits/{n}.txt.gz"),
            {".stencil-store.1.bin": b(R13Z + f"zbits/{n}.stencil-store.1.bin.gz")})


def test_stencil_read_on_kept_records():
    for n in ("zbs-base", "zbs-c12", "zbs-c16"):
        text, f = r13(n)
        st, dr = f[".stencil-store.1.bin"], SC.drawn_set(text)
        s, txt = SC.stencil_fit(st, dr, "S-UNMOVED", "bytes")
        assert s == (n == "zbs-base"), (n, txt)
        # with the bytes fill a 0x1000 move reads the same bytes: why zgran's rows fill `index`
        assert SC.stencil_fit(st, dr, "S-MOVED", "bytes")[0] == s
        if n != "zbs-base":
            for m in Z.P_MODELS:                 # at 64 x 32 G 1 the three pitches are one
                ok, tot = Z.pitch_check(st, dr, 64, int(n[-2:]), m, g=1)
                assert ok == tot == 2048
    st, dr = r13("zbs-base")[1][".stencil-store.1.bin"], SC.drawn_set(r13("zbs-base")[0])
    assert Z.pitch_check(st, dr, 64, 12, "P-64", g=1)[0] < 2048


def stencil_job(n, model_load, w=64, bit=None, pm=None, drawn_rows=True):
    """a stencil row's text and store under a load model: pixels of even y drawn"""
    drawn = {(x, y) for y in range(0, 32, 2) for x in range(w)} if drawn_rows else set()
    st = bytearray(b"\xef\xbe\xad\xde" * (18 * 1024))
    for y in range(32):
        for x in range(w):
            inv = 0xFF if (x, y) in drawn else 0
            if bit is None:
                st[Z.st_pos(x, y)] = Z.s_loaded(model_load, x, y) ^ inv
            elif bit == 12:
                st[Z.st_pos(x, y, 2)] = Z.fill_byte("bytes", Z.pitch(pm, w) * y + x) ^ inv
            else:
                st[Z.pitch(pm, w) * y + x] = Z.fill_byte("bytes", Z.st_pos(x, y, 2)) ^ inv
    text = t(R13Z + "zbits/zbs-base.txt.gz").split("\ntarget:")[0]
    text = text.replace("fill bytes", "fill index")
    text += "\n" + "\n".join(f"row {y}: " + " ".join(
        f"{Z.TRI_COLOUR if (x, y) in drawn else 0xff203040:#010x}" for x in range(w)) for y in range(32))
    text += f"\ntri {w}x32 #1: {len(drawn)} triangle, {w * 32 - len(drawn)} background, 0 other\n"
    return text, {".stencil-store.1.bin": bytes(st)}


def test_zbits2_kept_and_model_rows(tmp_path):
    jobs = {"zb2-c-base": r13("zbs-base"), "zb2-c-set": r13("zbs-set"),
            "zg-c-sid": stencil_job("zg-c-sid", "S-UNMOVED"), "zg-s14": stencil_job("zg-s14", "S-MOVED")}
    for k in Z.SET_BITS:
        jobs[f"zb2-b{k}"] = r13("zbs-set") if k == 21 else r13("zbs-base")
    jobs["zb2-g21-23"] = r13("zbs-set")
    jobs["zb2-g27-31"] = r13("zbs-base")
    for n, (w, bit) in Z.PITCH_ROWS.items():
        jobs[n] = stencil_job(n, None, w, bit, "P-G")
    out = score("zbits2", kept(tmp_path / "k", "zbits2", jobs))
    for n in ("zb2-c-base", "zb2-c-set", "zg-c-sid"):
        assert line(out, "CONTROL", n).endswith("PASS"), line(out, "CONTROL", n)
    assert "SUMMARY: zbits2: Z-ONE-21 (11 of 11 rows decided)" in out
    assert "SUMMARY: zbits2: Z-GROUP is not supported" in out
    assert "SUMMARY: zbits2: Z-GRP-21-23 is not supported" in out
    assert "SUMMARY: zbits2: P-G (4 of 4 rows decided)" in out
    assert "SUMMARY: zbits2: P-64 is not supported" in out and "SUMMARY: zbits2: P-W is not supported" in out
    assert "SUMMARY: zbits2: S-MOVED (1 of 1 rows decided)" in out
    assert "SUMMARY: zbits2: S-UNMOVED is not supported" in out


def test_zbits2_control_fails(tmp_path):
    tx, f = r13("zbs-set")
    jobs = {"zb2-c-base": r13("zbs-base"), "zb2-c-set": (tx, {".stencil-store.1.bin": b"\0" + f[
        ".stencil-store.1.bin"][1:]}), "zb2-b15": r13("zbs-base")}
    out = score("zbits2", kept(tmp_path / "k", "zbits2", jobs))
    assert line(out, "CONTROL", "zb2-c-set").endswith("FAILED")
    assert "SUMMARY: zbits2: Z-ONE-15: controls FAILED" in out
    assert line(out, "ROW", "zg-s14").endswith("cannot tell")


# ---- zodd -------------------------------------------------------------------------------------
def test_floor_and_owner_rules_on_kept_records():
    f0 = Z.dwords(b(R9X + "z242-c-f0.depth.1.bin.gz"))
    for fmt in (1, 2):
        d = Z.dwords(b(R9X + f"z242-c-f{fmt}.depth.1.bin.gz"))
        for m in Z.INT_PAST_MODELS:
            p = Z.int_past_predict(f0, 80, 40, 2, fmt, m)
            assert SC._dict_fit(d, p, lambda i, v: v == Z.FILL_DEAD)[0] == (m == "INT-FLOOR-EXT")
    full = Z.dwords(b(R10X + "zov/zov-256x64-ctl.depth.1.bin.gz"))
    d = Z.dwords(b(R10X + "zov/zov-256x64-g3.depth.1.bin.gz"))
    held = [m for m in Z.OV_MODELS if SC._dict_fit(d, Z.ov_predict(full, 256, 64, 3, m),
                                                   lambda i, v: v == Z.FILL_DEAD)[0]]
    assert held == ["H-LATE/HDR", "H-EARLY/RASTER"]          # E996's row that parted HDR


def depth_job(dw, n_pages=None):
    d = list(dw) + [Z.FILL_DEAD] * ((n_pages or 0) * 1024 - len(dw))
    ch = sum(1 for v in d if v != Z.FILL_DEAD)
    return (f"depth: 0x3e001000 {n_pages or 18} pages, fill 0xdeadbeef, base 0x3e000000, control 0\n"
            f"job: ok\ndepth #1: {len(d)} dwords, {ch} changed, 9 distinct\n",
            {".depth.1.bin": pack(d)})


def test_zodd_rows(tmp_path):
    ov = b(R10X + "zov/zov-64x32-g0.depth.1.bin.gz")
    jobs = {"zo-c-ov": (t(R10X + "zov/zov-64x32-g0.txt.gz"), {".depth.1.bin": ov})}
    for k, (w, h, g) in Z.ODD.items():
        tw, th = Z.tiles(w, h)
        ref = [0x3E000000 + 0x1000 * i for i in range(512 * tw * th)]
        jobs[f"zo-{k}-f0"] = depth_job(ref, 20)
        for fmt in (1, 2):
            p = Z.int_past_predict(ref, w, h, g, fmt, "INT-FLOOR-EXT")
            d = [Z.FILL_DEAD] * (20 * 1024)
            for i, v in p.items():
                d[i] = v
            jobs[f"zo-{k}-f{fmt}"] = depth_job(d, 20)
    ref = [0x3E000000 + 0x1000 * i for i in range(512 * 9)]
    d = [Z.FILL_DEAD] * (20 * 1024)
    for i, v in Z.ov_predict(ref, 65, 33, 1, "H-LATE/HDR").items():
        d[i] = v
    jobs["zo-65-f0"] = depth_job(ref, 20)
    jobs["zo-65-ov"] = depth_job(d, 20)
    g3 = [Z.FILL_DEAD] * (20 * 1024)
    for p in (12, 14, 16, 18):
        g3[1024 * p:1024 * p + 1024] = [0x3F000000] * 1024
    jobs["zo-g3"] = depth_job(g3, 20)
    jobs["zb2-c-r16"] = ("job: ok\ndepth #1: 20480 dwords, 4608 changed, 9 distinct\n",
                         {".depth.1.bin": b(R13Z + "zbits/zbr-c16.depth.1.bin.gz")})
    jobs["zb2-f2-16"] = ("job: ok\n", {".depth.1.bin": b(R9X + "z242-c-f2.depth.1.bin.gz")})
    out = score("zodd", kept(tmp_path / "k", "zodd", jobs))
    assert line(out, "CONTROL", "zo-c-ov").endswith("PASS"), line(out, "CONTROL", "zo-c-ov")
    assert line(out, "CONTROL", "zb2-c-r16").endswith("PASS"), line(out, "CONTROL", "zb2-c-r16")
    assert "SUMMARY: zodd: INT-FLOOR-EXT (4 of 4 rows decided)" in out
    assert "SUMMARY: zodd: INT-ZERO-PAST is not supported" in out
    assert "SUMMARY: zodd: INT-EDGE-CLAMP is not supported" in out
    assert "SUMMARY: zodd: H-NEXTTILE (1 of 1 rows decided)" in out
    assert "SUMMARY: zodd: H-STRAY is not supported" in out
    assert "SUMMARY: zodd: H-LATE/HDR (1 of 2 rows decided)" in out     # zo-640-ov not given
    assert "SUMMARY: zodd: H-EARLY/HDR is not supported" in out
    assert "SUMMARY: zodd: L16-TILED (1 of 1 rows decided)" in out
    assert "SUMMARY: zodd: L16-PAIR is not supported" in out
    assert line(out, "ROW", "zo-640-ov").endswith("cannot tell")


def test_zodd_control_fails_only_its_own(tmp_path):
    ov = b(R10X + "zov/zov-64x32-g0.depth.1.bin.gz")
    jobs = {"zo-c-ov": (t(R10X + "zov/zov-64x32-g0.txt.gz"), {".depth.1.bin": flip(ov)}),
            "zb2-c-r16": ("job: ok\ndepth #1: 20480 dwords, 4608 changed, 9 distinct\n",
                          {".depth.1.bin": b(R13Z + "zbits/zbr-c16.depth.1.bin.gz")}),
            "zb2-f2-16": ("job: ok\n", {".depth.1.bin": b(R9X + "z242-c-f2.depth.1.bin.gz")})}
    out = score("zodd", kept(tmp_path / "k", "zodd", jobs))
    assert line(out, "CONTROL", "zo-c-ov").endswith("FAILED")
    assert "SUMMARY: zodd: L16-TILED (1 of 1 rows decided)" in out     # gated by zb2-c-r16 only
    assert "SUMMARY: zodd: H-NEXTTILE: cannot tell" in out or "SUMMARY: zodd: H-NEXTTILE: controls FAILED" in out


# ---- zflat ------------------------------------------------------------------------------------
def test_zflat_kept_records(tmp_path):
    flat = (t(R13Z + "zfmt/zf-flat-f6.txt.gz"), {".depth.1.bin": b(R13Z + "zfmt/zf-flat-f6.depth.1.bin.gz")})
    y6 = ("job: ok\ndepth #1: 18432 dwords, 212 changed, 9 distinct\n",
          {".depth.1.bin": b(R10Z + "z2y-f6.depth.1.bin.gz")})
    jobs = {"zl-c-flat": flat, "zl-c-y6": y6, "zl-f6-0p25": flat, "zl-f5-flat": flat,
            "zl-f7-idx": ("job: ok\n", {".depth.1.bin": b(R10Z + "z2y-f7.depth.1.bin.gz")})}
    out = score("zflat", kept(tmp_path / "k", "zflat", jobs))
    assert line(out, "CONTROL", "zl-c-flat").endswith("PASS"), line(out, "CONTROL", "zl-c-flat")
    assert line(out, "CONTROL", "zl-c-y6").endswith("PASS"), line(out, "CONTROL", "zl-c-y6")
    r = line(out, "ROW", "zl-f6-0p25")
    assert "FL-HEAD 0/4 blocks" in r and r.endswith("held FL-CONST, FL-SHAPE")
    assert line(out, "ROW", "zl-f5-flat").endswith("held F5-EQ-F6")
    assert line(out, "ROW", "zl-f7-idx").endswith("held F7I-COMMON, F7I-COUNT")
    assert line(out, "ROW", "zl-f6-0p0").endswith("cannot tell")
    tx, f = y6
    jobs = {"zl-c-y6": (tx, {".depth.1.bin": flip(f[".depth.1.bin"])})}
    out = score("zflat", kept(tmp_path / "k2", "zflat", jobs))
    assert line(out, "CONTROL", "zl-c-y6").endswith("FAILED")


def test_flat_head_at_its_own_depth():
    flat = Z.dwords(b(R13Z + "zfmt/zf-flat-f6.depth.1.bin.gz"))
    for k in range(4):
        assert flat[512 * k:512 * k + 4] == Z.f6c_head(0x3F000000)
    assert Z.f6c_head(Z.f32_bits("0.25")) != Z.f6c_head(0x3F000000)
