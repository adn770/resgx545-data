# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept directories it must hold on and must fail on.

Kept records (pinned, read at the frozen data commit): E977's z243-ctl and z242-c-f0, E995's
eq-m0, E997's zb-clr-f0, E988's st1-b0, E989's q071-b0, E986's z2y-f0, z2y-f6, z2x-f7-s00 and
-sff. The controls PASS on their kept records; a ramp row given E997's linear dump holds every L
model that clears its bit and FAILS the rest; a stencil row given E989's 2048 holds Z-ANY and its
bit's models; F6C holds on E986's z2y-f6 against z2y-f0 (E1015's 8 groups, through the zf-y48 rows'
path) and F6RAW FAILS; F7K holds on the kept s00 and sff dumps at their own fill and FAILS at
another; zbase's rows made under H-MOVED hold it and FAIL the rivals, and a changed control
dump FAILS. Rows not given cannot tell."""
import gzip
import os
import struct
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "mock"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import score as SC  # noqa: E402
import world as Wd  # noqa: E402
import z13 as Z  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")
R9X = "data:render/closing-r9-x/out/20261113-081821/zls/"
R10X = "data:render/closing-r10-x/out/20261113-101116/"
ST1 = "data:render/closing-r10-st1/out/20261113-103934/st1/"
R10Z = "data:render/closing-r10-zls/out/20261113-102039/zst2/"


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


def mock_job(stage, n):
    a = Wd.answer("t10", table(stage)[n][5].replace('"$W"', "/W").split(), {"model"})
    return a["out"], {"." + k[3:]: v for k, v in a["files"].items()}


def b(p):
    return pins.blob(p)


def t(p):
    return pins.blob(p).decode()


# ---- zbase ------------------------------------------------------------------------------------
def zbase_controls():
    return {"zb-c-ctl": (t(R9X + "z243-ctl.txt.gz"),
                         {".depth-store.1.bin": b(R9X + "z243-ctl.depth-store.1.bin.gz")}),
            "zb-c-eq0": (t(R10X + "dcmp/eq-m0.txt.gz"),
                         {".depth-store.1.bin": b(R10X + "dcmp/eq-m0.depth-store.1.bin.gz")})}


def test_zbase_kept_controls_and_moved_rows(tmp_path):
    jobs = zbase_controls()
    for n in ("zb-c-id", "zb-c-off", *Z.ZB_MOVES):
        jobs[n] = mock_job("zbase", n)
    out = score("zbase", kept(tmp_path / "k", "zbase", jobs))
    for n in ("zb-c-ctl", "zb-c-eq0", "zb-c-id", "zb-c-off"):
        assert line(out, "CONTROL", n).endswith("PASS"), line(out, "CONTROL", n)
    assert "SUMMARY: zbase: H-MOVED (7 of 7 rows decided)" in out
    for m in ("H-ALIGN4K", "H-ALIGNTILE", "H-STOREBASE", "H-UNMOVED"):
        assert f"SUMMARY: zbase: {m} is not supported" in out
    assert "READING zb-m4: store dword k = depth dword k + d = 1;" in out


def test_zbase_aligned_rows_fail_moved_and_controls_fail(tmp_path):
    jobs = zbase_controls()
    text, files = mock_job("zbase", "zb-m40")
    st = list(struct.unpack("<%dI" % (len(files[".depth-store.1.bin"]) // 4),
                            files[".depth-store.1.bin"]))
    st[:Z.ZB_N] = range(Z.ZB_N)                 # the base rounded down: the identity
    jobs["zb-m40"] = (text, {".depth-store.1.bin": struct.pack("<%dI" % len(st), *st)})
    t2, f2 = jobs["zb-c-eq0"]
    jobs["zb-c-eq0"] = (t2, {".depth-store.1.bin": b"\1" + f2[".depth-store.1.bin"][1:]})
    jobs["zb-c-id"] = mock_job("zbase", "zb-c-id")
    out = score("zbase", kept(tmp_path / "k", "zbase", jobs))
    assert line(out, "ROW", "zb-m40").endswith("held H-ALIGN4K, H-ALIGNTILE, H-UNMOVED")
    assert line(out, "CONTROL", "zb-c-eq0").endswith("FAILED")
    assert "controls FAILED" in out
    assert "ROW zb-m4: " in out and line(out, "ROW", "zb-m4").endswith("cannot tell")


def test_zbase_other_addresses_cannot_tell(tmp_path):
    text, files = mock_job("zbase", "zb-m1000")
    text = text.replace("depth store: 0x3e015000", "depth store: 0x3e016000")
    out = score("zbase", kept(tmp_path / "k", "zbase", {"zb-m1000": (text, files)}))
    assert line(out, "ROW", "zb-m1000").endswith("cannot tell")


# ---- zbits ------------------------------------------------------------------------------------
def zbits_controls():
    return {"zbs-base": (t(ST1 + "st1-b0.txt.gz"), {".depth.1.bin": b(ST1 + "st1-b0.depth.1.bin.gz")}),
            "zbs-q071": (t(ST1 + "q071-b0.txt.gz"), {".depth.1.bin": b(ST1 + "q071-b0.depth.1.bin.gz")}),
            "zbr-ctl": (t(R9X + "z242-c-f0.txt.gz"), {".depth.1.bin": b(R9X + "z242-c-f0.depth.1.bin.gz")})}


def test_zbits_kept_records(tmp_path):
    jobs = zbits_controls()
    lin = (t(R10X + "zbits/zb-clr-f0.txt.gz"), {".depth.1.bin": b(R10X + "zbits/zb-clr-f0.depth.1.bin.gz")})
    jobs["zbr-c16"] = lin
    jobs["zbr-c12-16"] = lin
    jobs["zbr-c12"] = jobs["zbr-ctl"]
    jobs["zbs-c16"] = jobs["zbs-q071"]
    jobs["zbs-c12"] = jobs["zbs-base"]
    out = score("zbits", kept(tmp_path / "k", "zbits", jobs))
    for n in ("zbs-base", "zbs-q071", "zbr-ctl"):
        assert line(out, "CONTROL", n).endswith("PASS"), line(out, "CONTROL", n)
    assert "READING zbr-c16: layout linear;" in out and "READING zbr-c12: layout tiled;" in out
    assert "SUMMARY: zbits: L-BIT-16 (3 of 6 rows decided)" in out
    assert "SUMMARY: zbits: L-BIT-12 is not supported" in out
    assert "SUMMARY: zbits: L-ANY is not supported" in out
    assert "SUMMARY: zbits: Z-BIT-16 (2 of 7 rows decided)" in out
    assert "SUMMARY: zbits: Z-BIT-12 is not supported" in out
    assert "READING zbs-c12: drawn 1024; image = zbs-base's" in out


def test_zbits_control_fails(tmp_path):
    jobs = zbits_controls()
    tx, f = jobs["zbr-ctl"]
    jobs["zbr-ctl"] = (tx, {".depth.1.bin": f[".depth.1.bin"][:-1] + b"\1"})
    jobs["zbr-c16"] = jobs["zbr-ctl"]
    out = score("zbits", kept(tmp_path / "k", "zbits", jobs))
    assert line(out, "CONTROL", "zbr-ctl").endswith("FAILED")
    assert line(out, "ROW", "zbr-c16").endswith("no frozen model")
    assert "controls FAILED" in out


# ---- zfmt -------------------------------------------------------------------------------------
def test_zfmt_kept_records(tmp_path):
    rule = SC.c7()
    for s, fill in (("s00", 0x00), ("sff", 0xFF)):
        dw = Z.dwords(b(R10Z + f"z2x-f7-{s}.depth.1.bin.gz"))
        p = Z.f7_pred(fill, rule, False)
        assert all(dw[i] == v for i, v in p.items())
        assert all(v == Z.FILL_DEAD for i, v in enumerate(dw) if i not in p)
        assert not all(dw[i] == v for i, v in Z.f7_pred(fill, rule, True).items())
    y6 = (t(R10Z + "z2y-f6.txt.gz"), {".depth.1.bin": b(R10Z + "z2y-f6.depth.1.bin.gz")})
    y0 = (t(R10Z + "z2y-f0.txt.gz"), {".depth.1.bin": b(R10Z + "z2y-f0.depth.1.bin.gz")})
    f7 = mock_job("zfmt", "zf-7k-3f")[0]
    dw = [Z.FILL_DEAD] * 18432
    for i, v in Z.f7_pred(0x3F, rule, False).items():
        dw[i] = v
    jobs = {"zf-y6-ctl": y6, "zf-y48-f0": y0, "zf-y48-f6": y6,
            "zf-7k-3f": (f7, {".depth.1.bin": struct.pack("<18432I", *dw)}),
            "zf-7k-1f": (f7, {".depth.1.bin": struct.pack("<18432I", *dw)})}
    out = score("zfmt", kept(tmp_path / "k", "zfmt", jobs))
    assert line(out, "CONTROL", "zf-y6-ctl").endswith("PASS")
    assert line(out, "ROW", "zf-y48-f6").startswith("ROW zf-y48-f6: F6C 8/8 groups; F6RAW 0/8")
    assert line(out, "ROW", "zf-7k-3f").endswith("held F7K")
    assert line(out, "ROW", "zf-7k-1f").endswith("no frozen model")      # 0x3f's template at 0x1f
    assert "SUMMARY: zfmt: F6RAW is not supported" in out
    assert "SUMMARY: zfmt: F7K is not supported: 1 held, 1 FAILED" in out
    assert line(out, "ROW", "zf-flat-f6").endswith("cannot tell")


def test_flat_prediction_covers_every_tile():
    rule = SC.c7()
    g = Z.f6_groups(Z.flat_rows(64, 32), 64, 32, rule)
    assert len(g) == 16 and sorted({x[0] for x in g}) == [0, 1, 2, 3]
