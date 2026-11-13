# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on.

t3: E566's kept s64x32-ctl and s64x32-t3b14 (controls PASS), s64x16-ctl in t3-ctl's place (FAILED);
E566's s64x32-t3b11 and -t3b12 (E566: the control's image) held as b11/b12, s64x32-t3b10 (which
moves the texel) FAILED; E564's an-ctl, an-t3b11, an-t3b12 (PASS, held). srgb: E723's g-bl-st-a
(PASS), g-bl-st-b in its place (FAILED). far: E684's far21d0 (1401720, PASS) and far21d4 (1401724,
another geometry: FAILED), their run-length rows written as `row N:` lines. zls: no kept record has
these geometries, so a synthetic pair: a format-0 dump of a ramp over [0.5, 1) and the format-1 dump
H-ROUND makes of it: H-ROUND held, H-FLOOR FAILED, and the control's count PASS or FAILED."""
import gzip
import os
import re
import struct
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import zls as Z  # noqa: E402
from test_gen import e684_image  # noqa: E402

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


def k(pin):
    return gzip.decompress(pins.blob(pin)).decode(errors="replace")


E566 = "data:texture/p1132/tx-t3/%s.txt.gz"
E564 = "data:texture/p1132/tx-lod/%s.txt.gz"


def test_t3_holds_and_fails(tmp_path):
    out = score("t3", kept(tmp_path, "t3", {
        "t3-ctl": k(E566 % "s64x32-ctl"), "t3-b14ref": k(E566 % "s64x32-t3b14"),
        "b11-s64x32": k(E566 % "s64x32-t3b11"), "b12-s64x32": k(E566 % "s64x32-t3b10"),
        "an-ctl": k(E564 % "an-ctl"), "an-t3b11": k(E564 % "an-t3b11"),
        "an-t3b12": k(E564 % "an-t3b12")}))
    assert line(out, "CONTROL", "t3-ctl").endswith("PASS")
    assert line(out, "CONTROL", "t3-b14ref").endswith("PASS")
    assert line(out, "CONTROL", "an-ctl").endswith("PASS")
    assert "held H-CTL" in line(out, "ROW", "b11-s64x32")
    assert "no frozen model exact" in line(out, "ROW", "b12-s64x32")
    assert "held H-E564" in line(out, "ROW", "an-t3b11")
    assert "held H-E564" in line(out, "ROW", "an-t3b12")
    out = score("t3", kept(_sub(tmp_path, "b"), "t3", {"t3-ctl": k(E566 % "s64x16-ctl"),
                                                       "b12-s64x32": k(E566 % "s64x32-t3b12")}))
    assert line(out, "CONTROL", "t3-ctl").endswith("FAILED")
    assert "held H-CTL" in line(out, "ROW", "b12-s64x32")
    assert "controls FAILED" in out


def _sub(tmp, n):
    p = tmp / n
    p.mkdir()
    return p


def test_srgb_control(tmp_path):
    a = "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/g-bl-st-%s.txt.gz"
    out = score("srgb", kept(_sub(tmp_path, "a"), "srgb", {"srgb-ctl": k(a % "a")}))
    assert line(out, "CONTROL", "srgb-ctl").endswith("PASS")
    out = score("srgb", kept(_sub(tmp_path, "b"), "srgb", {"srgb-ctl": k(a % "b")}))
    assert line(out, "CONTROL", "srgb-ctl").endswith("FAILED")


def far_text(case):
    img = e684_image(case)
    return "job: ok\n" + "".join("row %d: %s\n" % (y, " ".join("0x%08x" % v for v in img[y * 64:(y + 1) * 64]))
                                 for y in range(64))


def test_far_control(tmp_path):
    out = score("far", kept(_sub(tmp_path, "a"), "far", {"far-ctl": far_text(1401720)}))
    assert line(out, "CONTROL", "far-ctl").endswith("PASS")
    out = score("far", kept(_sub(tmp_path, "b"), "far", {"far-ctl": far_text(1401724)}))
    assert line(out, "CONTROL", "far-ctl").endswith("FAILED")


def ramp_dumps(w, h, rule):
    """format-0 and format-1 dumps of z = 1 - (x + 0.5) / (2W) (float32) over the target's tiles."""
    tx, ty = Z.tiles(w, h)
    g = tx - 1
    n = 512 * tx * ty + 1024 * 16
    f0, f1 = [0xDEADBEEF] * n, [0xDEADBEEF] * n
    for y in range(16 * ty):
        for x in range(32 * tx):
            z = struct.unpack("<f", struct.pack("<f", 1 - (x + 0.5) / (2 * w)))[0]
            i = 512 * ((y >> 4) * (g + 1) + (x >> 5)) + Z.in_tile_index(x, y)
            f0[i] = struct.unpack("<I", struct.pack("<f", z))[0]
            f1[i] = rule(z)
    pack = lambda v: gzip.compress(struct.pack("<%dI" % len(v), *v))
    return pack(f0), pack(f1), sum(v != 0xDEADBEEF for v in f0)


def test_zls_rules(tmp_path):
    f0, f1, n = ramp_dumps(80, 40, lambda z: int(z * 16777215 + 0.5))
    txt = f"job: ok\ndepth #1: 20480 dwords, {n} changed, 2 distinct\n"
    out = score("zls", kept(tmp_path, "zls", {"z242-c-f0": txt, "z242-c-f1": txt},
                            [("z242-c-f0.depth.1.bin.gz", f0), ("z242-c-f1.depth.1.bin.gz", f1)]))
    assert line(out, "CONTROL", "z242-c-f0").endswith("PASS")
    r = line(out, "ROW", "z242-c-f1")
    assert "held H-ROUND" in r and "H-FLOOR" not in r.split("held")[1], r
    f0, f1, n = ramp_dumps(80, 40, lambda z: min(int(z * 16777216), 0xFFFFFF))
    out = score("zls", kept(_sub(tmp_path, "b"), "zls",
                            {"z242-c-f0": "job: ok\ndepth #1: 20480 dwords, 4000 changed\n",
                             "z242-c-f1": "job: ok\n"},
                            [("z242-c-f0.depth.1.bin.gz", f0), ("z242-c-f1.depth.1.bin.gz", f1)]))
    assert line(out, "CONTROL", "z242-c-f0").endswith("FAILED")
    assert "held H-FLOOR" in line(out, "ROW", "z242-c-f1")


def test_zls_layouts_are_permutations():
    assert sorted(Z.in_tile_index(x, y) for y in range(16) for x in range(32)) == list(range(512))
    assert all(Z.in_tile_pixel(Z.in_tile_index(x, y)) == (x, y) for y in range(16) for x in range(32))
    assert sorted(Z.in_tile_index16(x, y) for y in range(0, 16, 2) for x in range(32)) == list(range(256))
    # sgx-pipe zls.rs (pinned): the in-tile order y0 x0 y1 x1 y2 x2 y3 x3 x4
    rs = pins.blob("resgx545:crates/sgx-pipe/src/zls.rs").decode()
    assert "fn in_tile_order_is_y0_x0_y1_x1_y2_x2_y3_x3_x4" in rs
    assert Z.in_tile_index(1, 0) == 2 and Z.in_tile_index(0, 1) == 1 and Z.in_tile_index(16, 0) == 256
