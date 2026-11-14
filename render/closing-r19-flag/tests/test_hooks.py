# SPDX-License-Identifier: MIT
"""tests/test_hooks.py: run/hooks.sh on synthetic job files, the way the runner sources it (JW the
job's files, W its work directory, class the runner's end)."""
import os
import subprocess

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD = ("tri: render context for targets up to 1024x768\n"
        "job: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"
        "tri 1024x768 #1: overflowed, 300 triangle, 3 background, 0 other; wrong 0 inside\n")
FILL = "tri: tadata_fill before render 2: 6 0xa5000000 ramp\n"
TAIL = "job: ok\nreg 0x0624 0x000000de\ntarget: 1024x768 hash 0x1\ndiff: 0 of 786432 pixels\n"
BIF = "[1.0] sgxfive: BIF fault 0x90200 at 0x30011a40 (PD 0x1) stalls job 7, recovering\n"


def hook(tmp, fn, name, out, dmesg="", cls="ok", page6=18, rows=7):
    jw, w = tmp / "jw", tmp / "w"
    w.mkdir(parents=True, exist_ok=True)
    jw.mkdir(exist_ok=True)
    (jw / f"{name}.out").write_text(out)
    (jw / f"{name}.dmesg").write_text(dmesg)
    pages = bytearray(4096 * rows)
    for i in range(page6):
        pages[6 * 4096 + 4 * i] = 1
    (w / "tri.1.tadata.bin").write_bytes(bytes(pages))
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; class={cls}; {fn} {name}'],
                       capture_output=True, text=True,
                       env=dict(os.environ, JW=str(jw), W=str(w), STAGE="fl"))
    return r.stdout.strip()


def test_control_reading_and_check(tmp_path):
    out = HEAD + TAIL
    assert hook(tmp_path, "hook_reading", "fl-ctl", out).split() == ["job=ok", "ovf=1", "thr=0xde", "lists=yes"]
    assert hook(tmp_path, "hook_check", "fl-ctl", out) == ""


def test_control_stops_without_each_premise(tmp_path):
    ok = HEAD + TAIL
    for bad in (ok.replace("0x000000de", "0x00000006"),          # H-IGN: the update did not happen
                ok.replace("#1: overflowed, ", "#1: geometry only, "),   # the kick did not overflow
                ok.replace("job: ok", "job: failed: x")):
        assert "without the premise" in hook(tmp_path, "hook_check", "fl-ctl", bad)
    assert "without the premise" in hook(tmp_path, "hook_check", "fl-ctl", ok, page6=0)   # no lists


def test_junk_row_that_completes_needs_the_kick_not_the_threshold(tmp_path):
    ok = HEAD + FILL + TAIL
    assert hook(tmp_path, "hook_check", "fl-junk-a", ok) == ""
    assert hook(tmp_path, "hook_check", "fl-junk-a", ok.replace("0x000000de", "0x00000006")) == ""
    assert "without the premise" in hook(tmp_path, "hook_check", "fl-junk-a", ok, page6=0)


def test_fault_rules(tmp_path):
    out = HEAD + FILL + "job: failed: job faulted, context lost (Input/output error)\n"
    assert hook(tmp_path, "hook_fault", "fl-junk-a", out, BIF, "fault") == ""
    assert "without a kernel BIF" in hook(tmp_path, "hook_fault", "fl-junk-a", out, "", "fault")
    assert "SGX recovery failed" in hook(tmp_path, "hook_fault", "fl-junk-a", out,
                                               BIF + "gma500: SGX recovery failed: -110\n", "fault")
    assert "before the fill was armed" in hook(tmp_path, "hook_fault", "fl-junk-a", HEAD + "job: failed\n",
                                                     BIF, "fault")
    assert "before the geometry kick" in hook(tmp_path, "hook_fault", "fl-junk-a", "job: failed\n", BIF,
                                                    "fault")
    hang = HEAD + FILL + "job: failed: job hung, context lost (Connection timed out)\n"
    assert hook(tmp_path, "hook_fault", "fl-junk-a", hang, "sgxfive: job 12 hung, recovering\n", "hang") == ""
    assert "without the kernel's hung" in hook(tmp_path, "hook_fault", "fl-junk-a", hang, "", "hang")
