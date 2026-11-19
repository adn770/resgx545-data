# SPDX-License-Identifier: MIT
"""tests/test_hooks.py: run/hooks.sh's hook_check under bash on results pages and snap0s shaped
as the laptop's: a good job passes; each stop (r36-n3's: cmd not cleared, slot 1 or slot 4 marker
or run id wrong, sa0-sa3 not TA3DCtl dwords 0-3; N3b's: X0 or S1 absent) prints a reason; the row's snap0 V0-V3
win over the fallback; post's tri and fill checks; hook_reading's diff."""
import json
import os
import subprocess

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = (0x32004000, 0x32005000, 0x32002000, 0)


def page(runid=3, **edit):
    p = [0] * 1024
    p[0], p[1], p[2], p[3], p[5] = 0x4E574F53, 0, 2, runid, runid
    p[0x44:0x47] = [0x5A5A3301, runid, 0x5A5A3303]
    p[0x54] = 0x5A5A3304
    p[0x48:0x4C] = [V[0], 7, V[2], 0]
    p[0x4C:0x50] = list(V)
    p[0x50:0x52] = [0x5A5A3302, runid]
    for k, x in edit.items():
        p[int(k[1:], 16)] = x
    return p


def check(tmp_path, p, tool="owntask", args="", snapv=V, out=""):
    jw = tmp_path / "jw"
    w = jw / "w"
    w.mkdir(parents=True, exist_ok=True)
    (w / "own_res.json").write_text(json.dumps({"page": p}))
    snap = "sgxfive regs 1\nreg 0x0c04 0x00080000\n"
    if snapv:
        snap += "".join(f"ta3dctl 0x{4 * i:02x} 0x{x:08x}\n" for i, x in enumerate(snapv))
    (jw / "snap0.regs").write_text(snap + "end\n")
    (jw / "n1.out").write_text(out)
    r = subprocess.run(["bash", "-c", f'JW="{jw}"; W="{w}"; tool="{tool}"; args="{args}"; '
                        '. run/hooks.sh; hook_check n1; hook_reading n1'],
                       cwd=KP, capture_output=True, text=True)
    assert r.returncode == 0 and not r.stderr, r.stderr
    return r.stdout


def test_a_good_job_passes(tmp_path):
    assert check(tmp_path, page()) == ""


def test_each_stop(tmp_path):
    for edit, word in (({"x1": 1}, "not cleared"), ({"x2": 0}, "not 2"),
                       ({"x5": 9}, "echo"), ({"x44": 0}, "slot 1"), ({"x45": 9}, "slot 1"),
                       ({"x50": 0xDEADC0DE}, "slot 4"), ({"x51": 2}, "slot 4"),
                       ({"x46": 0xDEADC0DE}, "X0"), ({"x54": 0xDEADC0DE}, "S1"),
                       ({"x4c": 0x12345678}, "sa0"), ({"x4d": 0}, "sa1"),
                       ({"x4e": 0}, "sa2"), ({"x4f": 5}, "sa3")):
        out = check(tmp_path, page(**edit))
        assert word in out and "n1" in out, (edit, out)


def test_pa_values_never_stop(tmp_path):
    assert check(tmp_path, page(x48=0, x4a=0, x49=V[0])) == ""


def test_the_rows_snap0_wins_over_the_fallback(tmp_path):
    moved = (0x32104000, 0x32105000, 0x32102000, 0)
    p = page()
    p[0x4C:0x50] = list(moved)
    assert check(tmp_path, p, snapv=moved) == ""
    assert "sa0" in check(tmp_path, p, snapv=V)
    assert "sa0" in check(tmp_path, p, snapv=None)     # the fallback is V


def test_post_checks(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("world", os.path.join(KP, "mock/world.py"))
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    assert check(tmp_path, page(), "t30", "tri", out=w.TRI) == "diff=0\n"
    assert check(tmp_path, page(), "t30", "fill", out=w.FILL) == "diff=0\n"
    assert "job: ok" in check(tmp_path, page(), "t30", "tri", out=w.TRI.replace("job: ok\n", ""))
    assert "did not fill" in check(tmp_path, page(), "t30", "fill",
                                   out=w.FILL.replace("diff: 0", "diff: 3"))
    assert "does not plan" in check(tmp_path, page(), "t30", "probe")
