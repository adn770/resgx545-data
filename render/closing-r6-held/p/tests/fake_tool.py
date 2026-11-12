#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A fake sgxfive-test for the R5-events mock tests (R4-events' fake, with every call's argv logged to MOCK_DIR/tool.log under the job the
kernel log's last case marker names: the argv-twin test reads it).  Originally the fake for the R3k mock tests: the lines the landed gate (fill, tri) and the health script grep for, and the jobs the sessions
run through the pinned tools: `probe PROG` (the loop fill of e3h / e3a: it latches STATUS2 bit 6 in the mock's status2 file; L1's dd-p1 and
L2's t-ctl-green-16x16 for k0t: the kept outputs of those runs), `fill` while ring_skip3 is armed (the fill of e3b: the simulated EDM takes
it from files, see tests/mockfw/kmock.py).
MOCK_SCENARIO: tool_fail (rc 1, no diff line)  loop_nolatch  tool_diff."""
import gzip
import os
import sys
import time

SC = set(os.environ.get("MOCK_SCENARIO", "").split(","))
MOCK = os.environ.get("MOCK_DIR", "")
HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
cmd = args[0] if args else ""


def _job():
    try:
        lines = [ln for ln in open(os.environ.get("R3_KMSG", os.path.join(MOCK, "kmsg"))).read().splitlines() if " case " in ln]
    except OSError:
        return ""
    return lines[-1].split(" case ")[1].split()[0] if lines else ""


if MOCK and not os.environ.get("FAKE_TOOL_NOLOG"):
    with open(os.path.join(MOCK, "tool.log"), "a") as f:
        f.write(f"[{_job()}] {os.path.basename(sys.argv[0])} {' '.join(args)}\n")
if "tool_fail" in SC:
    print("job: failed")
    sys.exit(1)


def fixture(name):
    with gzip.open(os.path.join(os.environ.get("MOCK_FIXTURES", os.path.join(HERE, "fixtures")), name), "rb") as f:
        return f.read()


if cmd == "fill":
    print("job: ok\njob time: 100 us\ndiff: 0 of 2048 pixels")
elif cmd == "tri":
    print("tri 64x64 #1: 1062 triangle, 3034 background, 0 other\ndiff: 0 of 4096 pixels")
elif cmd == "probe":
    prog = args[-1]
    if "loop-b16-i56" in prog:
        if "loop_nolatch" not in SC:
            with open(os.path.join(MOCK, "status2"), "w") as f:
                f.write("0x440\n")
        print("programs asm\nprobe loop-b16-i56: scratch at 0x3e00b000 (64 KiB)\nprobe loop-b16-i56: fill ok")
    elif "dd-p1__0" in prog:
        text = fixture("dd-p1.txt.gz").decode()
        if "tool_diff" in SC:
            text = text.replace("ff00ff00", "ff00fe00", 1)
        i = args.index("--dump-render") + 1
        d = args[i]
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "dd-p1__0.param.bin"), "wb") as f:
            f.write(fixture("dd-p1.dd-p1__0.param.bin.gz"))
        with open(os.path.join(d, "dd-p1__0.tadata.bin"), "wb") as f:
            f.write(fixture("dd-p1.dd-p1__0.tadata.bin.gz"))
        sys.stdout.write(text)
    else:
        print("programs asm\nprobe pix_green: scratch at 0x3e00b000 (64 KiB)\nprobe pix_green: tri 16x16, pixel replaced\n"
              "probe pix_green: triangle (0,0) (48,0) (0,48)\nprobe pix_green: o0 0xff00ff00 (256 of 256)")
else:
    print("fake tool: unknown command", cmd)
    sys.exit(2)
