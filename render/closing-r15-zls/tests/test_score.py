# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py and gen/z15.py's models on kept records they must hold on
and must fail on (read at the frozen data commit), and on rows built from one model's prediction.

Kept records: E977's z243-ctl, z243-f1-less and z243-f2-less (the pass rule, H-INT-PASS; H-INT-WORD
fails on z243-f1-less), E988's st1-e-b0 (40 x 20: H-EDGE holds, -CLEAR and -SKIP fail), E1042's
zb2-c-base, zb2-b15, zb2-b23 and zb2-g21-23 (E988's rule, H15-FAIL and H15-READFF, H23-MOD16 and
H23-LOADED, H-PAIR-ZERO's read), E1043's zl-f6-0p25 (FL-REC0) and zl-f6-0p1234 (not), E1041's
zo-65-f1 and zo-65-f2 (the floor rule from zo-65-f0 at full pitch), E996's zov-64x32-g0-f1
(H-LATE/HDR in format 1), E1041's zo-g3 (H-E465-EXT at G 3), E981's z2-b-f1 (H-INT-SAT's 0). The
controls PASS on their kept records and FAIL on a changed byte; rows built from a model's
prediction hold it and fail its rivals; a row not given cannot tell."""
import gzip
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import score as SC  # noqa: E402
import z15 as Z  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")
R9X = "data:render/closing-r9-x/out/20261113-081821/zls/"
R10X = "data:render/closing-r10-x/out/20261113-101116/zov/"
R10S = "data:render/closing-r10-st1/out/20261113-103934/st1/"
R13Z = "data:render/closing-r13-zls/out/20261113-213117/"
R14Z = "data:render/closing-r14-zls/out/20261114-054846/"


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


def summary(out, stage, m):
    return [ln for ln in out.splitlines() if ln.startswith(f"SUMMARY: {stage}: {m}")][0]


def b(p):
    return pins.blob(p)


def t(p):
    return pins.blob(p).decode()


def pack(v):
    import struct
    return struct.pack("<%dI" % len(v), *v)


def flip(x, at=100):
    y = bytearray(x)
    y[at] ^= 1
    return bytes(y)


def txt(w, h, drawn=None, depth=None, dst=None, sst=None, extra=""):
    out = [extra] if extra else []
    if depth is not None:
        out.append(f"depth #1: 20480 dwords, {depth} changed, 2 distinct")
    if dst is not None:
        out.append(f"depth store #1: 20480 dwords, {dst} changed, 2 distinct")
    if sst is not None:
        out.append(f"stencil store #1: 18432 dwords, {sst} changed, 2 distinct")
    out.append("job: ok")
    if drawn is not None:
        out.append(f"tri {w}x{h} #1: {drawn} triangle, {w * h - drawn} background, 0 other")
    return "\n".join(out) + "\n"


def stencil_txt(w, h, pixels):
    rows = [f"row {y}: " + " ".join(f"{Z.TRI_COLOUR if (x, y) in pixels else 0xFF203040:#010x}"
                                    for x in range(w)) for y in range(h)]
    return txt(w, h, drawn=len(pixels), sst=1) + "\n".join(rows) + "\n"


# ---- the models on kept records ------------------------------------------------------------


def test_pass_rule_on_e977():
    for n, args, held, failed in (
            ("z243-ctl", (64, 32, 0x0017500E, "0x3f400000", "0.5", Z.LESS), ("H-EDGE",), ()),
            ("z243-f1-less", (64, 32, 0x0117500E, "0x00400000", "0.125", Z.LESS), ("H-INT-PASS",),
             ("H-INT-WORD",)),
            ("z243-f2-less", (64, 32, 0x0217500E, "0x3fff3fff", "0.5", Z.LESS), ("H-INT-PASS",), ())):
        st = Z.dwords(b(R9X + n + ".depth-store.1.bin.gz"))
        dc = SC.drawn_count(t(R9X + n + ".txt.gz"))
        for m in held + failed:
            p, d = Z.pass_model(*args, m)
            ok = SC._dict_fit(st, p, SC.fill_ok)[0] and dc == d
            assert ok == (m in held), (n, m)


def test_stencil_rules_on_kept():
    g23 = SC.g23_map()
    for n, ctl, held in (("zb2-c-base", Z.ST_CTL, ("E988", "H-PAIR-BASE")),
                         ("zb2-b23", Z.ST_CTL | 1 << 23, ("H23-MOD16", "H23-LOADED", "H-PAIR-23")),
                         ("zb2-b15", Z.ST_CTL | 1 << 15, ("H15-FAIL", "H15-READFF")),
                         ("zb2-g21-23", Z.ST_CTL | 7 << 21, ("H-PAIR-ZERO",))):
        st = b(R14Z + "zbits2/" + n + ".stencil-store.1.bin.gz")
        dc = SC.drawn_count(t(R14Z + "zbits2/" + n + ".txt.gz"))
        for m in ("E988", "H15-FAIL", "H23-MOD16", "H-PAIR-ZERO", *held):
            p, d, _ = Z.stencil_model(64, 32, ctl, "bytes", 0, m, g23)
            ok = SC._dict_fit(st, p, SC.sfill_ok)[0] and dc == d
            assert ok == (m in held or (m == "E988" and "H-PAIR-BASE" in held)), (n, m)
    # E988's edge row at 40 x 20 (post hoc there): H-EDGE holds, the rivals fail
    st = b(R10S + "st1-e-b0.stencil-store.1.bin.gz")
    dc = SC.drawn_count(t(R10S + "st1-e-b0.txt.gz"))
    for m in Z.EDGE_MODELS:
        p, d, _ = Z.stencil_model(40, 20, Z.ST_CTL, "bytes", 0, m)
        assert (SC._dict_fit(st, p, SC.sfill_ok)[0] and dc == d) == (m == "H-EDGE"), m


def test_flat_rec0_on_e1043():
    ref = b(R13Z + "zfmt/zf-flat-f6.depth.1.bin.gz")[:176]
    d25 = b(R14Z + "zflat/zl-f6-0p25.depth.1.bin.gz")
    assert Z.rec0_check(d25, ref, 0x3E800000)[0] and Z.rec0_any(d25, ref) == 0x3E800000
    assert not Z.rec0_check(d25, ref, 0x3E800001)[0]
    d1234 = b(R14Z + "zflat/zl-f6-0p1234.depth.1.bin.gz")
    assert Z.rec0_any(d1234, ref) is None


def test_floor_and_owner_rules_on_kept():
    full = Z.dwords(b(R14Z + "zodd/zo-65-f0.depth.1.bin.gz"))
    for f in (1, 2):
        dw = Z.dwords(b(R14Z + f"zodd/zo-65-f{f}.depth.1.bin.gz"))
        assert SC._dict_fit(dw, Z.ov_predict(full, 65, 33, 2, f, 2, "H-LATE/HDR"), SC.fill_ok)[0]
    full = Z.dwords(b(R10X + "zov-64x32-ctl.depth.1.bin.gz"))
    dw = Z.dwords(b(R10X + "zov-64x32-g0-f1.depth.1.bin.gz"))
    for m in Z.OV_MODELS:
        ok = SC._dict_fit(dw, Z.ov_predict(full, 64, 32, 0, 1, 1, m), SC.fill_ok)[0]
        assert ok == m.startswith("H-LATE"), m           # one macrotile: header order is raster
    dw = Z.dwords(b(R14Z + "zodd/zo-g3.depth.1.bin.gz"))
    got = {p: sum(1 for v in dw[1024 * p:1024 * p + 1024] if v == 0x3F000000) for p in range(20)}
    assert {p for p, c in got.items() if c} == {12 + 4 * ty // 2 for ty in range(4)}
    # E981: the offset at -0.25 stored 0 in format 1 (H-INT-SAT's negative)
    dw = Z.dwords(b("data:render/closing-r9-z2/out/20261113-082522/z2/z2-b-f1.depth.1.bin.gz"))
    assert {v for v in dw if v != Z.FILL_DEAD} == {0}


# ---- the scorer -------------------------------------------------------------------------------


def zpass_job(n, m):
    w, h = Z.ZPASS[n][:2]
    p, d = Z.pass_predict(n, m)
    st = [Z.FILL_DEAD] * (Z.ZPASS[n][6] * 1024)
    for i, v in p.items():
        st[i] = v
    return txt(w, h, drawn=d, dst=len(p)), {".depth-store.1.bin": pack(st)}


def test_zpass(tmp_path):
    jobs = {"zp-c-id": (t(R13Z + "zbase/zb-c-id.txt.gz"),
                        {".depth-store.1.bin": b(R13Z + "zbase/zb-c-id.depth-store.1.bin.gz")})}
    for n in ("zp-c-467", "zp-c-band"):
        jobs[n] = zpass_job(n, "H-EDGE")
    held = {"zp-e-dp": "H-EDGE", "zp-19-nv": "H-19-RENEG", "zp-19-ls": "H-19-ABS",
            "zp-f1": "H-INT-PASS", "zp-f2": "H-INT-PASS", "zp-z0": "H-PASS-Z",
            "zp-z75": "H-PASS-LE"}
    for n, m in held.items():
        jobs[n] = zpass_job(n, m)
    out = score("zpass", kept(tmp_path / "a", "zpass", jobs))
    for c in ("zp-c-id", "zp-c-467", "zp-c-band"):
        assert line(out, "CONTROL", c).endswith("PASS"), c
    assert line(out, "ROW", "zp-e-dp").endswith("held H-EDGE")
    assert line(out, "ROW", "zp-19-nv").endswith("held H-19-RENEG")
    assert line(out, "ROW", "zp-19-ls").endswith("held H-19-ABS")
    assert line(out, "ROW", "zp-f2").endswith("held H-INT-PASS")
    assert line(out, "ROW", "zp-z75").endswith("held H-PASS-LE")
    assert line(out, "ROW", "zp-z0").endswith("held H-PASS-Z, H-PASS-LE")
    assert line(out, "ROW", "zp-z1").endswith("cannot tell")
    assert "SUMMARY: zpass: H-19-RENEG is not supported" in out
    # a changed byte of a kept control fails it, and the headlines say so
    jobs["zp-c-id"] = (jobs["zp-c-id"][0], {".depth-store.1.bin": flip(jobs["zp-c-id"][1][
        ".depth-store.1.bin"])})
    jobs["zp-c-band"] = zpass_job("zp-c-band", "H-EDGE-SKIP")
    out = score("zpass", kept(tmp_path / "b", "zpass", jobs))
    assert line(out, "CONTROL", "zp-c-id").endswith("FAILED")
    assert "H-EDGE (" not in summary(out, "zpass", "H-EDGE")


def zbits3_job(n, m, g23=None):
    w, h = Z.ZBITS3[n][:2]
    p, d, px = Z.stencil_predict(n, m, g23)
    st = bytearray(b"\xef\xbe\xad\xde" * 18432)
    for i, v in p.items():
        st[i] = v
    return stencil_txt(w, h, px), {".stencil-store.1.bin": bytes(st)}


def test_zbits3(tmp_path):
    jobs = {}
    for n, k in (("zb3-c-base", "zb2-c-base"), ("zb3-c-set", "zb2-c-set"), ("zb3-c-b23", "zb2-b23")):
        jobs[n] = (t(R14Z + f"zbits2/{k}.txt.gz"),
                   {".stencil-store.1.bin": b(R14Z + f"zbits2/{k}.stencil-store.1.bin.gz")})
    jobs["zb3-c-ref1"] = zbits3_job("zb3-c-ref1", "E988")
    g23 = SC.g23_map()
    held = {"zb3-b15-96": "H15-FAIL", "zb3-b15-r1": "H15-READFF", "zb3-b23-96": "H23-MOD16",
            "zb3-b23-idx": "H23-LOADED", "zb3-p21-23": "H-PAIR-23", "zb3-p22-23": "H-PAIR-BASE",
            "zp-e-st": "H-EDGE"}
    for n, m in held.items():
        jobs[n] = zbits3_job(n, m, g23)
    out = score("zbits3", kept(tmp_path / "a", "zbits3", jobs))
    for c in ("zb3-c-base", "zb3-c-set", "zb3-c-b23", "zb3-c-ref1"):
        assert line(out, "CONTROL", c).endswith("PASS"), c
    assert line(out, "ROW", "zb3-b15-96").endswith("held H15-FAIL, H15-READFF")
    assert line(out, "ROW", "zb3-b15-r1").endswith("held H15-READFF")
    assert line(out, "ROW", "zb3-b23-96").endswith("held H23-MOD16, H23-LOADED")
    assert line(out, "ROW", "zb3-b23-idx").endswith("held H23-LOADED")
    assert line(out, "ROW", "zb3-p22-23").endswith("held H-PAIR-BASE")
    assert line(out, "ROW", "zp-e-st").endswith("held H-EDGE")
    assert summary(out, "zbits3", "H-EDGE ").startswith("SUMMARY: zbits3: H-EDGE (1 of 1")
    jobs["zb3-c-set"] = (jobs["zb3-c-set"][0], {".stencil-store.1.bin": flip(
        jobs["zb3-c-set"][1][".stencil-store.1.bin"], 0)})
    out = score("zbits3", kept(tmp_path / "b", "zbits3", jobs))
    assert line(out, "CONTROL", "zb3-c-set").endswith("FAILED")


def flat_dump(ref176, v):
    d = bytearray(pack([Z.FILL_DEAD] * 18432))
    for k in range(4):
        d[2048 * k:2048 * k + 176] = Z.rec0_block(ref176, v)
    return bytes(d)


def test_zflat2(tmp_path):
    ref176 = b(R13Z + "zfmt/zf-flat-f6.depth.1.bin.gz")[:176]
    jobs = {
        "zl2-c-flat": (txt(64, 32, depth=176), {".depth.1.bin": b(R13Z + "zfmt/zf-flat-f6.depth.1.bin.gz")}),
        "zl2-c-y6": (txt(64, 32, depth=212), {".depth.1.bin": b(
            "data:render/closing-r10-zls/out/20261113-102039/zst2/z2y-f6.depth.1.bin.gz")}),
        "zl2-c-f5": (txt(64, 32, depth=944), {".depth.1.bin": b(R14Z + "zflat/zl-f5-flat.depth.1.bin.gz")}),
    }
    for n, z in Z.REC0_DEPTHS.items():
        jobs[n] = (txt(64, 32, depth=176), {".depth.1.bin": flat_dump(ref176, Z.f32_bits(z))})
    # 0.1: the twin is not flat, the format-6 row another form; 0.5 + 2^-20: the twin flat and
    # the format-6 row FL-REC0 of its value (H-FLATPLANE; H-LOW16 fails)
    v = Z.f32_bits(Z.TWIN_DEPTHS["0p5e20"])
    jobs["zl2-f0-0p1"] = (txt(64, 32, depth=2048), {".depth.1.bin": pack(
        [0x3DCCCCCD + (i & 1) for i in range(2048)] + [Z.FILL_DEAD] * 16384)})
    jobs["zl2-f6-0p1"] = (txt(64, 32, depth=200), {".depth.1.bin": b(R14Z + "zflat/zl-f6-0p1234.depth.1.bin.gz")})
    jobs["zl2-f0-0p5e20"] = (txt(64, 32, depth=2048), {".depth.1.bin": pack([v] * 2048 + [Z.FILL_DEAD] * 16384)})
    jobs["zl2-f6-0p5e20"] = (txt(64, 32, depth=176), {".depth.1.bin": flat_dump(ref176, v)})
    out = score("zflat2", kept(tmp_path / "a", "zflat2", jobs))
    for c in ("zl2-c-flat", "zl2-c-y6", "zl2-c-f5"):
        assert line(out, "CONTROL", c).endswith("PASS"), c
    for n in Z.REC0_DEPTHS:
        assert line(out, "ROW", n).endswith("held FL-REC0"), n
    assert line(out, "ROW", "zl2-f6-0p1").endswith("held H-LOW16, H-FLATPLANE")
    assert line(out, "ROW", "zl2-f6-0p5e20").endswith("held H-FLATPLANE")
    assert line(out, "ROW", "zl2-f6-0p3").endswith("cannot tell")
    assert summary(out, "zflat2", "FL-REC0").startswith("SUMMARY: zflat2: FL-REC0 (4 of 4")
    jobs["zl2-c-f5"] = (jobs["zl2-c-f5"][0], {".depth.1.bin": flip(jobs["zl2-c-f5"][1][".depth.1.bin"])})
    out = score("zflat2", kept(tmp_path / "b", "zflat2", jobs))
    assert line(out, "CONTROL", "zl2-c-f5").endswith("FAILED")


def g_job(n, m):
    c, pages = Z.G_CTLS[n]
    dw = [Z.FILL_DEAD] * (pages * 1024)
    for p, (k, v) in Z.g_pages(n, m).items():
        dw[1024 * p:1024 * p + k] = [v] * k
    head = (f"depth: 0x3e001000 {pages} pages, fill 0xdeadbeef, base 0x3e000000, control {c:#010x}\n"
            f"tri: kpoke before render 1: rd:13=0xd000")
    return txt(64, 64, depth=sum(k for k, _ in Z.g_pages(n, m).values()), extra=head), {
        ".depth.1.bin": pack(dw)}


def test_zovl(tmp_path):
    jobs = {"zv-c-ov": (t(R10X + "zov-64x32-g0.txt.gz"), {".depth.1.bin": b(R10X + "zov-64x32-g0.depth.1.bin.gz")}),
            "zv-c-g3": (t(R14Z + "zodd/zo-g3.txt.gz"), {".depth.1.bin": b(R14Z + "zodd/zo-g3.depth.1.bin.gz")}),
            "zv-c-075": (txt(64, 32, depth=2048), {".depth.1.bin": pack([Z.ZV_C075] * 2048 + [Z.FILL_DEAD] * 16384)}),
            "zv-r-hi": (txt(64, 32, depth=2048), {".depth.1.bin": pack([Z.OFF_HI] * 2048 + [Z.FILL_DEAD] * 16384)})}
    for n, (w, h, g, f, ref, gref) in Z.OV_ROWS.items():
        p = Z.ov_predict(Z.dwords(SC.kept(ref)), w, h, g, f, gref, "H-LATE/HDR")
        dw = [Z.FILL_DEAD] * (max(p) + 1)
        for i, v in p.items():
            dw[i] = v
        jobs[n] = (txt(w, h, depth=len(p)), {".depth.1.bin": pack(dw)})
    for n, m in (("zv-i125-f1", "H-INT-SAT"), ("zv-im25-f2", "H-INT-WRAP")):
        p = Z.int_out_predict(n, m)
        jobs[n] = (txt(64, 32, depth=len(p)), {".depth.1.bin": pack(list(p.values()) + [Z.FILL_DEAD] * 16384)})
    jobs["zv-b25"] = g_job("zv-b25", "H-B25-FLOOR")
    jobs["zv-g5"] = g_job("zv-g5", "H-E465-EXT")
    jobs["zv-g9"] = g_job("zv-g9", "H-STOP16")
    out = score("zovl", kept(tmp_path / "a", "zovl", jobs))
    assert line(out, "READING", "zv-r-hi").endswith("distinct 1 (0x3fa00000)")
    for c in ("zv-c-ov", "zv-c-g3", "zv-c-075"):
        assert line(out, "CONTROL", c).endswith("PASS"), c
    for n in Z.OV_ROWS:
        assert "held H-LATE/HDR" in line(out, "ROW", n), n
    assert "H-EARLY/HDR" not in line(out, "ROW", "zv-ov-640-f1").split("held")[1]
    assert line(out, "ROW", "zv-i125-f1").endswith("held H-INT-SAT, H-INT-SIGN")
    assert line(out, "ROW", "zv-im25-f2").endswith("held H-INT-WRAP")
    assert line(out, "ROW", "zv-b25").endswith("held H-B25-FLOOR")
    assert line(out, "ROW", "zv-g5").endswith("held H-E465-EXT")
    assert line(out, "ROW", "zv-g9").endswith("held H-STOP16")
    assert line(out, "ROW", "zv-g17").endswith("cannot tell")
    jobs["zv-c-g3"] = (jobs["zv-c-g3"][0], {".depth.1.bin": flip(jobs["zv-c-g3"][1][".depth.1.bin"],
                                                                 4 * 12 * 1024)})
    out = score("zovl", kept(tmp_path / "b", "zovl", jobs))
    assert line(out, "CONTROL", "zv-c-g3").endswith("FAILED")
    assert "H-E465-EXT (" not in summary(out, "zovl", "H-E465-EXT")
