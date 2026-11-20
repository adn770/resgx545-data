# SPDX-License-Identifier: MIT
"""tests/test_hooks.py: run/hooks.sh's hook_check under bash on results pages and snap0s shaped
as the laptop's: a good row passes; each marker stop (cmd, state, echo, M1, X0, S1, M4 with job
1's run id, M6 with the last run id) prints a reason; in stage c an sa0-sa3 change or an
after-read that is not the pre survey stops (C-DIFF); in every other stage it is printed to the
runner log (stderr), never a stop (design K4); stage t has no command 6 to check."""
import json
import os
import subprocess

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = (0x32004000, 0x32005000, 0x32002000, 0)


def page(last=2, **edit):
    p = [0] * 1024
    p[0], p[1], p[2], p[3], p[5] = 0x4E574F53, 0, 2, last, last
    p[0x44:0x47] = [0x5A5A3301, 1, 0x5A5A3303]
    p[0x54] = 0x5A5A3304
    p[0x48:0x4C] = [V[0], 0x43000, V[2], 0]
    p[0x4C:0x50] = list(V)
    p[0x50:0x52] = [0x5A5A3302, 1]
    p[0x58:0x5A] = [0x5A5A3306, last]
    pre = list(V) + [0x5100 + k for k in range(4, 32)]
    p[128:160] = pre
    p[224:256] = pre
    for k, x in edit.items():
        p[int(k[1:], 16)] = x
    return p


def check(tmp_path, p, stage="c", snapv=V):
    jw = tmp_path / "jw"
    w = jw / "w"
    w.mkdir(parents=True, exist_ok=True)
    (w / "own_res.json").write_text(json.dumps({"page": p}))
    snap = "sgxfive regs 1\nreg 0x0c04 0x00080000\n"
    if snapv:
        snap += "".join(f"ta3dctl 0x{4 * i:02x} 0x{x:08x}\n" for i, x in enumerate(snapv))
    (jw / "snap0.regs").write_text(snap + "end\n")
    r = subprocess.run(["bash", "-c", f'JW="{jw}"; W="{w}"; tool="owntask"; STAGE="{stage}"; '
                        '. run/hooks.sh; hook_check n1; hook_reading n1'],
                       cwd=KP, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout, r.stderr


def test_a_good_row_passes_in_every_stage(tmp_path):
    for st in ("c", "x", "y", "lc", "t"):
        assert check(tmp_path, page(), st) == ("", ""), st


def test_each_marker_stop(tmp_path):
    for edit, word in (({"x1": 6}, "not cleared"), ({"x2": 0}, "not 2"), ({"x5": 9}, "echo"),
                       ({"x44": 0}, "slot 1"), ({"x46": 0xDEADC0DE}, "X0"),
                       ({"x54": 0xDEADC0DE}, "S1"), ({"x50": 0xDEADC0DE}, "slot 4"),
                       ({"x51": 2}, "slot 4"), ({"x58": 0xDEADC0DE}, "slot 6"),
                       ({"x59": 1}, "slot 6")):
        for st in ("c", "x"):
            out, err = check(tmp_path, page(**edit), st)
            assert word in out and "n1" in out, (edit, st, out)


def test_stage_t_reads_no_slot_6(tmp_path):
    assert check(tmp_path, page(last=1, x58=0, x59=0, x45=1, x51=1), "t") == ("", "")


def test_c_stops_on_an_sa_change_or_a_different_after_read(tmp_path):
    for edit in ({"x4d": 0x04400000}, {"xe1": 0x04400000}):
        out, err = check(tmp_path, page(**edit), "c")
        assert "C-DIFF" in out and not err, (edit, out)


def test_other_stages_print_the_change_and_never_stop(tmp_path):
    for st in ("x", "y", "lc"):
        out, err = check(tmp_path, page(x4d=0x04400000, xe1=0x04400000), st)
        assert out == "" and "printed, not a stop" in err and "sa1" in err and "after-read" in err
    out, err = check(tmp_path, page(x4d=0x04400000, xe1=0x04400000), "t")
    assert out == "" and "sa1" in err and "after-read" not in err


def test_the_rows_snap0_wins_over_the_fallback(tmp_path):
    moved = (0x32104000, 0x32105000, 0x32102000, 0)
    p = page()
    p[0x4C:0x50] = list(moved)
    assert "sa0" not in check(tmp_path, p, "c", snapv=moved)[0]
    assert "sa0" in check(tmp_path, p, "c", snapv=V)[0]
    assert "sa0" in check(tmp_path, p, "c", snapv=None)[0]
