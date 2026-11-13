# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on.

dcmp: E977's kept z243-ctl output (drawn 2048) as z243-ctl and eq-m7 (PASS), z243-f1-less (drawn 0)
as eq-m0 (PASS) and in z243-ctl's place (FAILED); z243-ctl's output as nan-m3 holds H-UBITS and H-ABS
and fails H-IEEE and H-CLAMP0. zbits and isp0x: E977's kept z242-c-f0 (output and dump) as the
controls (PASS), z242-c-f1 in zb-ctl-f0's place (FAILED); z243-ctl's as zb-all-load (H-INERT held)
and zb-b0-load (H-INERT held, H-E665 FAILED). zov: no kept record has these planes, so a synthetic
pair: a full-pitch dump with a distinct float a dword and the 64 x 32 G 0 store H-LATE makes of it.
sb: E383's kept 0x208 images as the controls (PASS), its 0x207 ones in their place (FAILED), its
mode 15 image as sb-m20-f0-c0 (H-LOW16 held, H-M7 FAILED). win0: E502's kept A-m1-tee0-64x64-x as
its control (PASS), A-m1-te60-64x64-x in its place (FAILED), and H-IDENT's own image as a row."""
import gzip
import os
import struct
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import probes as P  # noqa: E402
import z as Z  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")


def kept(tmp, stage, outputs, files=()):
    """A kept directory: NAME.txt.gz per output, cases.tsv with each a completed job."""
    d = tmp / stage
    d.mkdir()
    table = {ln.split("|")[0]: ln.split("|") for ln in open(os.path.join(KP, "tables", stage + ".txt"))
             if ln.strip() and not ln.startswith("#")}
    rows = ["\t".join(COLS)]
    for n, text in outputs.items():
        (d / f"{n}.txt.gz").write_bytes(gzip.compress(text.encode()))
        t = table[n]
        rows.append("\t".join([n, stage, t[1], t[2], t[3], t[4], "x", "0", "ok", "-", "-", "0"]))
    for n, b in files:
        (d / n).write_bytes(b)
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text("name\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return d


def score(stage, d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), stage, str(d)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def line(out, kind, name):
    return [ln for ln in out.splitlines() if ln.startswith(f"{kind} {name}:") or
            ln.startswith(f"{kind} {name} (")][0]


def e977(job):
    return gzip.decompress(pins.blob(f"data:{Z.KEPT}/{job}.txt.gz")).decode()


def e977_dump(job):
    return gzip.decompress(pins.blob(f"data:{Z.KEPT}/{job}.depth.1.bin.gz"))


def test_dcmp(tmp_path):
    ctl, f1 = e977("z243-ctl"), e977("z243-f1-less")
    out = score("dcmp", kept(tmp_path, "dcmp", {"z243-ctl": ctl, "eq-m0": f1, "eq-m7": ctl,
                                               "nan-m3": ctl}))
    for n in ("z243-ctl", "eq-m0", "eq-m7"):
        assert line(out, "CONTROL", n).endswith(": PASS"), out
    assert "held H-UBITS, H-ABS" in line(out, "ROW", "nan-m3")
    assert "SUMMARY: dcmp: H-UBITS (1 of 14 rows decided)" in out
    assert "SUMMARY: dcmp: H-IEEE is not supported" in out
    (tmp_path / "b").mkdir()
    out = score("dcmp", kept(tmp_path / "b", "dcmp", {"z243-ctl": f1, "eq-m0": f1, "eq-m7": ctl}))
    assert line(out, "CONTROL", "z243-ctl").endswith(": FAILED")
    assert "controls FAILED" in out


def test_zbits_and_isp0x(tmp_path):
    c0, c1, ld = e977("z242-c-f0"), e977("z242-c-f1"), e977("z243-ctl")
    out = score("zbits", kept(tmp_path, "zbits", {
        "zb-ctl-f0": c0, "zb-ctl-f1": c1, "zb-all-load": ld, "zb-b0-load": ld}, [
        ("zb-ctl-f0.depth.1.bin", e977_dump("z242-c-f0")),
        ("zb-ctl-f1.depth.1.bin", e977_dump("z242-c-f1")),
        ("zb-all-load.depth.1.bin", e977_dump("z243-ctl")),
        ("zb-b0-load.depth.1.bin", e977_dump("z243-ctl"))]))
    assert line(out, "CONTROL", "zb-ctl-f0").endswith(": PASS"), out
    assert line(out, "CONTROL", "zb-ctl-f1").endswith(": PASS"), out
    assert line(out, "ROW", "zb-all-load").endswith("held H-INERT"), out
    assert line(out, "ROW", "zb-b0-load").endswith("held H-INERT"), out
    assert "SUMMARY: zbits: H-E665 is not supported" in out
    (tmp_path / "b").mkdir()
    out = score("zbits", kept(tmp_path / "b", "zbits", {"zb-ctl-f0": c1, "zb-ctl-f1": c1}, [
        ("zb-ctl-f0.depth.1.bin", e977_dump("z242-c-f1")),
        ("zb-ctl-f1.depth.1.bin", e977_dump("z242-c-f1"))]))
    assert line(out, "CONTROL", "zb-ctl-f0").endswith(": FAILED"), out
    (tmp_path / "c").mkdir()
    out = score("isp0x", kept(tmp_path / "c", "isp0x", {"x-ctl": c0, "x-w0b15": c0, "x-w0b16": c1}, [
        ("x-ctl.depth.1.bin", e977_dump("z242-c-f0")), ("x-w0b15.depth.1.bin", e977_dump("z242-c-f0")),
        ("x-w0b16.depth.1.bin", e977_dump("z242-c-f1"))]))
    assert line(out, "CONTROL", "x-ctl").endswith(": PASS")
    assert line(out, "ROW", "x-w0b15").endswith("held H-NULL")
    assert "dump differs" in line(out, "ROW", "x-w0b16") and "no frozen model held" in line(
        out, "ROW", "x-w0b16")


def test_zov_synthetic(tmp_path):
    w, h, g = 64, 32, 0
    tx, ty = Z.tiles(w, h)
    pages = (w * h * 4 + 4095) // 4096 + 16
    full = [0xDEADBEEF] * (pages * 1024)
    for i in range(512 * tx * ty):
        full[i] = struct.unpack("<I", struct.pack("<f", 0.25 + i / 65536))[0]
    late = list([0xDEADBEEF] * (pages * 1024))
    for i, v in Z.zov_predict(full, w, h, g, "H-LATE/HDR").items():
        late[i] = v
    text = (f"job: ok\ndepth #1: {pages * 1024} dwords, {512 * tx * ty} changed, x\n"
            f"target: {w}x{h} hash 0x0\ndiff: 0 of {w * h} pixels\ntri {w}x{h} #1: {w * h} triangle\n")
    pack = lambda v: struct.pack("<%dI" % len(v), *v)
    out = score("zov", kept(tmp_path, "zov", {"zov-64x32-ctl": text, "zov-64x32-g0": text}, [
        ("zov-64x32-ctl.depth.1.bin", pack(full)), ("zov-64x32-g0.depth.1.bin", pack(late))]))
    assert line(out, "CONTROL", "zov-64x32-ctl").endswith(": PASS"), out
    assert line(out, "ROW", "zov-64x32-g0").endswith("held H-LATE/HDR, H-LATE/RASTER"), out
    assert "SUMMARY: zov: cannot tell: controls: zov-128x32-ctl: cannot tell" in out  # 4 not run
    (tmp_path / "b").mkdir()
    same = list(full)
    same[5] = same[6]                                  # two dwords of one float: no map
    out = score("zov", kept(tmp_path / "b", "zov", {"zov-64x32-ctl": text}, [
        ("zov-64x32-ctl.depth.1.bin", pack(same))]))
    assert line(out, "CONTROL", "zov-64x32-ctl").endswith(": FAILED"), out


def case_text(raw, case):
    return "\n".join(ln for ln in raw.splitlines() if ln.startswith(f"probe {case}:")) + "\n"


def test_sb(tmp_path):
    raw = {c: pins.blob(f"data:{P.E383}/pbe-sideband-channels-{c:04x}/raw.txt").decode()
           for c in (0x208, 0x207, 0x20F)}
    ok = {f"sb-ctl-0208-c{c}": case_text(raw[0x208], f"pbe-sideband-channels-0208__{c}") for c in (0, 1)}
    ok["sb-m20-f0-c0"] = case_text(raw[0x20F], "pbe-sideband-channels-020f__0")
    out = score("sb", kept(tmp_path, "sb", ok))
    assert line(out, "CONTROL", "sb-ctl-0208-c0").endswith(": PASS"), out
    assert line(out, "ROW", "sb-m20-f0-c0").endswith("held H-LOW16"), out
    assert "SUMMARY: sb: H-M7 is not supported" in out
    (tmp_path / "b").mkdir()
    bad = {f"sb-ctl-0208-c{c}": case_text(raw[0x207], f"pbe-sideband-channels-0207__{c}") for c in (0, 1)}
    out = score("sb", kept(tmp_path / "b", "sb", bad))
    assert line(out, "CONTROL", "sb-ctl-0208-c1").endswith(": FAILED"), out


def test_win0(tmp_path):
    e502 = lambda n: gzip.decompress(pins.blob(f"data:{P.E502}/{n}.txt.gz")).decode()
    im = open(os.path.join(KP, "predictions/win0/w0-tee0-128x96-y.H-IDENT.txt")).read().split()
    rows = "".join(f"probe pos: row {y}: " + " ".join(im[128 * y:128 * y + 128]) + "\n"
                   for y in range(96))
    out = score("win0", kept(tmp_path, "win0", {
        "w0-ctl-m1-tee0-64x64-x": e502("A-m1-tee0-64x64-x"),
        "w0-ctl-m0-te20-64x64-x": e502("A-m0-te20-64x64-x"), "w0-tee0-128x96-y": rows}))
    assert line(out, "CONTROL", "w0-ctl-m1-tee0-64x64-x").endswith(": PASS"), out
    assert line(out, "CONTROL", "w0-ctl-m0-te20-64x64-x").endswith(": PASS"), out
    assert line(out, "ROW", "w0-tee0-128x96-y").endswith("held H-IDENT"), out
    (tmp_path / "b").mkdir()
    out = score("win0", kept(tmp_path / "b", "win0", {
        "w0-ctl-m1-tee0-64x64-x": e502("A-m1-te60-64x64-x"),
        "w0-ctl-m0-te20-64x64-x": e502("A-m0-te20-64x64-x")}))
    assert line(out, "CONTROL", "w0-ctl-m1-tee0-64x64-x").endswith(": FAILED"), out
