# SPDX-License-Identifier: MIT
"""tests/test_hooks.py: run/hooks.sh's hook_check under bash on results pages shaped as the
laptop's: emitsn's good job passes; each stop (cmd not cleared, state, echo, slot 1 marker or run
id, X0, slot 4 marker or run id, a dword of the host's fill changed) prints a reason; th (rt)
never stops; post's tri and fill checks; hook_reading's diff."""
import json
import os
import subprocess

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILL = 0xDEADC0DE


def page(runid=3, **edit):
    p = [0] * 1024
    p[0], p[1], p[2], p[3], p[5] = 0x4E574F53, 0, 2, runid, runid
    p[0x44:0x47] = [0x5A5A3301, runid, 0x5A5A3303]
    p[0x48:0x58] = [FILL] * 16
    p[0x50:0x52] = [0x5A5A3302, runid]
    for k, x in edit.items():
        p[int(k[1:], 16)] = x
    return p


def check(tmp_path, p, tool="owntask", args="", out=""):
    jw = tmp_path / "jw"
    w = jw / "w"
    w.mkdir(parents=True, exist_ok=True)
    (w / "own_res.json").write_text(json.dumps({"page": p}))
    (jw / "snap0.regs").write_text("sgxfive regs 1\nreg 0x0c04 0x00080000\nend\n")
    (jw / "n1.out").write_text(out)
    r = subprocess.run(["bash", "-c", f'JW="{jw}"; W="{w}"; tool="{tool}"; args=\'{args}\'; '
                        '. run/hooks.sh; hook_check n1; hook_reading n1'],
                       cwd=KP, capture_output=True, text=True)
    assert r.returncode == 0 and not r.stderr, r.stderr
    return r.stdout


def test_a_good_job_passes(tmp_path):
    assert check(tmp_path, page()) == ""


def test_each_stop(tmp_path):
    for edit, word in (({"x1": 1}, "not cleared"), ({"x2": 0}, "not 2"),
                       ({"x5": 9}, "echo"), ({"x44": 0}, "slot 1"), ({"x45": 9}, "slot 1"),
                       ({"x46": FILL}, "X0"), ({"x50": FILL}, "slot 4"), ({"x51": 2}, "slot 4"),
                       ({"x48": 0}, "dwords 72 are not"), ({"x54": 0x5A5A3304}, "dwords 84 are"),
                       ({"x52": 1, "x57": 0}, "dwords 82 87 are")):
        out = check(tmp_path, page(**edit))
        assert word in out and "n1" in out, (edit, out)


def test_th_never_stops(tmp_path):
    assert check(tmp_path, page(x2=0), "rt", "0.06 0.005 0x0acc -- x probe") == ""


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
