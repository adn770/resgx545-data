# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept directories it must hold on and must fail on.

zst2: E978's kept 64 x 32 jobs (r9-x, render/closing-r9-x out/20261113-081821/zst, pinned) under
this session's names: z120-ctl-s as z2x-f0 and z120-f4-s as z2x-f4 (controls PASS, H-E985's f4
layout held, the refuted stencil orders FAILED); E978's z120-f3-s scored as a y-plane f3 row on
z120-ctl-s's reference must hold H-E985 (the same depth); z120-f6-s's dump given as f3 must hold
no model; a control whose count is off FAILS. zbgc, zbg, zw: the mock world's dumps (the model
each world makes), a hand-made H-RAW dump, E977's kept z242-a-f0 as zw-c50 (PASS) and with one
dword changed (FAILED); a row whose job did not complete cannot tell."""
import gzip
import os
import struct
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "mock"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import world as Wd  # noqa: E402
import zbg as B  # noqa: E402

COLS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
        "fault_word", "free_kb")
X978 = "data:render/closing-r9-x/out/20261113-081821/zst/"
E977 = "data:render/closing-r9-x/out/20261113-081821/zls/z242-a-f0.depth.1.bin.gz"


def table(stage):
    return {ln.split("|")[0]: ln.rstrip("\n").split("|", 5)
            for ln in open(os.path.join(KP, f"tables/{stage}.txt"))
            if ln.strip() and not ln.startswith("#")}


def kept(d, stage, jobs):
    """jobs: {name: (text, {suffix: bytes}, class)}"""
    d.mkdir(parents=True)
    t = table(stage)
    rows = ["\t".join(COLS)]
    for n, (text, files, cls) in jobs.items():
        (d / f"{n}.txt.gz").write_bytes(gzip.compress(text.encode()))
        for suf, b in files.items():
            (d / f"{n}.{suf}.gz").write_bytes(gzip.compress(b))
        r = t[n]
        rows.append("\t".join([n, stage, r[1], r[2], r[3], r[4], "x", "1", cls, "-", "-", "0"]))
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text("name\n")
    (d / "readings.tsv").write_text("name\tstage\treading\n")
    return d


def score(stage, d, *roots):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), stage, str(d),
                        *map(str, roots)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def line(out, n, tag=("ROW", "CONTROL")):
    return [ln for ln in out.splitlines() if ln.split(" ")[0] in tag and ln.split(" ")[1].rstrip(":") == n][0]


def e978(name):
    return (pins.blob(X978 + name + ".depth.1.bin.gz"),
            pins.blob(X978 + name + ".stencil.1.bin.gz") if name != "z120-ctl-s" else None)


def zst_text(depth_changed, sst_changed):
    return (f"job: ok\ndepth #1: 18432 dwords, {depth_changed} changed, 2 distinct\n"
            f"stencil store #1: 18432 dwords, {sst_changed} changed, 1 distinct\n")


def test_zst2_holds_on_e978(tmp_path):
    ref, _ = e978("z120-ctl-s")
    f4, st4 = e978("z120-f4-s")
    f3, st3 = e978("z120-f3-s")
    f6, _ = e978("z120-f6-s")
    jobs = {"z2x-f0": (zst_text(2048, 512), {"depth.1.bin": ref, "stencil.1.bin": st3}, "ok"),
            "z2x-f4": (zst_text(640, 0), {"depth.1.bin": f4, "stencil.1.bin": st4}, "ok"),
            "z2y-f0": (zst_text(2048, 512), {"depth.1.bin": ref, "stencil.1.bin": st3}, "ok"),
            "z2y-f3": (zst_text(2560, 0), {"depth.1.bin": f3, "stencil.1.bin": st3}, "ok"),
            "z2y-f5": (zst_text(2560, 0), {"depth.1.bin": f6, "stencil.1.bin": st3}, "ok"),
            "z2y-f6": (zst_text(2048, 0), {"depth.1.bin": f6, "stencil.1.bin": st3}, "ok")}
    out = score("zst2", kept(tmp_path / "k", "zst2", jobs))
    assert line(out, "z2x-f0").endswith("PASS") and line(out, "z2x-f4").endswith("PASS")
    lay = line(out, "z2x-f4", ("CONTROL-LAYOUT",))
    assert lay.endswith("held H-E985"), lay
    assert line(out, "z2y-f3").endswith("held H-E985"), line(out, "z2y-f3")
    assert line(out, "z2y-f5").endswith("no frozen model")
    assert line(out, "z2y-f6").endswith("held H-E985")
    assert "READING z2x-f0: byte for byte E978's z120-ctl-s: True" in out
    assert "READING z2y: f3 and f5 byte-identical: False" in out
    summ = [ln for ln in out.splitlines() if ln.startswith("SUMMARY")]
    # the d, e controls did not run: every headline cannot tell
    assert summ and all("cannot tell" in ln for ln in summ), summ


def test_zst2_control_fails(tmp_path):
    ref, _ = e978("z120-ctl-s")
    f4, st4 = e978("z120-f4-s")
    out = score("zst2", kept(tmp_path / "k", "zst2", {
        "z2x-f0": (zst_text(2047, 512), {"depth.1.bin": ref, "stencil.1.bin": st4}, "ok"),
        "z2x-f4": (zst_text(640, 0), {"depth.1.bin": f4, "stencil.1.bin": st4}, "fault")}))
    assert line(out, "z2x-f0").endswith("FAILED")
    assert line(out, "z2x-f4").endswith("cannot tell")
    assert "controls FAILED" in out


def world_job(stage, n, world="model"):
    args = table(stage)[n][5].replace('"$W"', "/W").split()
    a = Wd.answer("t9", args, {world})
    return a["out"], {"depth.1.bin": a["files"]["/W/depth.1.bin"]}


def test_bg_controls_gate_and_rows(tmp_path):
    root = tmp_path / "att"
    c = {n: (*world_job("zbgc", n), "ok") for n in B.CONTROLS}
    out = score("zbgc", kept(root / "zbgc", "zbgc", c))
    assert line(out, "zbg-c1").endswith("PASS") and line(out, "zbg-c25").endswith("PASS")
    assert "READING zbg-c25: triangle pixels: 0x3e800000" in out      # the mock draws nothing there
    g = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "gate", "zbg",
                        str(root)], capture_output=True, text=True)
    assert g.returncode == 0, g.stdout
    rows = {n: (*world_job("zbg", n), "ok") for n in table("zbg")}
    # a hand-made H-RAW dump of zbg-n-f1: every background dword 0xc00000
    o, f, _ = rows["zbg-n-f1"]
    z = list(struct.unpack("<%dI" % (len(f["depth.1.bin"]) // 4), f["depth.1.bin"]))
    for i in B.bg_dwords(1):
        z[i] = 0xC00000
    rows["zbg-n-f1"] = (o, {"depth.1.bin": struct.pack("<%dI" % len(z), *z)}, "ok")
    out = score("zbg", kept(root / "zbg", "zbg", rows), root)
    assert line(out, "zbg-n-f1").endswith("held H-RAW, H-B19-INT"), line(out, "zbg-n-f1")
    assert line(out, "zbg-n-f0").endswith("held H-CLAMP0, H-CLAMP0P")
    assert line(out, "zbg-n-f0-b19").endswith("held H-CLAMP0")       # the mock: 0, then negated
    assert line(out, "zbg-z-f1").endswith("held H-ZERO")
    assert "SUMMARY: zbg: H-CLAMP0 is not supported: 5 held, 1 FAILED" in out
    assert "SUMMARY: zbg: H-RAW is not supported: 1 held, 5 FAILED" in out


def test_bg_gate_shut_when_c25_off(tmp_path):
    root = tmp_path / "att"
    c = {n: (*world_job("zbgc", n, "bgoff"), "ok") for n in B.CONTROLS}
    out = score("zbgc", kept(root / "zbgc", "zbgc", c))
    assert line(out, "zbg-c1").endswith("PASS") and line(out, "zbg-c25").endswith("FAILED")
    g = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "gate", "zbg",
                        str(root)], capture_output=True, text=True)
    assert g.returncode == 1 and "zbg-c25: FAILED" in g.stdout
    g = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "gate", "zbg",
                        str(tmp_path / "none")], capture_output=True, text=True)
    assert g.returncode == 1 and "has not run" in g.stdout


def test_zw(tmp_path):
    ref = pins.blob(E977)
    jobs = {n: (*world_job("zw", n), "ok") for n in table("zw")}
    assert jobs["zw-c50"][1]["depth.1.bin"] == ref                    # the mock makes E977's dump
    out = score("zw", kept(tmp_path / "a", "zw", jobs))
    assert line(out, "zw-c50").endswith("PASS")
    for n in ("zw-075", "zw-100", "zw-0125"):
        assert line(out, n).endswith("held H-LIN"), line(out, n)
    assert "SUMMARY: zw: H-LIN (3 of 3 rows decided)" in out
    assert "SUMMARY: zw: H-OFF is not supported" in out
    bad = bytearray(ref)
    bad[0] ^= 1
    jobs["zw-c50"] = (jobs["zw-c50"][0], {"depth.1.bin": bytes(bad)}, "ok")
    jobs["zw-100"] = (jobs["zw-100"][0], {}, "fault")
    out = score("zw", kept(tmp_path / "b", "zw", jobs))
    assert line(out, "zw-c50").endswith("FAILED") and line(out, "zw-100").endswith("cannot tell")
    assert "controls FAILED" in out
