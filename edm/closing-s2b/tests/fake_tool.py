#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A fake sgxfive-test for the S2 mock tests: prints what the real tool prints for fill, copy and tri, and appends
its job's kind with the submission time (time.monotonic, system-wide) to MOCK_DIR/events, which the fake EDM
(tests/mockfw/fwtask_run.py) delivers.  While the fake EDM holds (MOCK_DIR/busy), the job completes only at the
hold's end, so its time grows.  MOCK_SCENARIO: tool_fail (rc 1, no diff line), tool_hang_in_hold (a held job fails
as a hung one: rc 3), tool_sleep (never returns within the test's timeout)."""
import os
import sys
import time

MOCK = os.environ["MOCK_DIR"]
SC = set(os.environ.get("MOCK_SCENARIO", "").split(","))
a = sys.argv[1:]
cmd = a[0] if a else ""
w = a[a.index("--width") + 1] if "--width" in a else "64"
kind = {"fill": "fill", "copy": "copy"}.get(cmd) or {"256": "tri256n3", "1024": "partial"}.get(w, "tri64")
if "tool_sleep" in SC:
    time.sleep(60)
time.sleep(0.005)
t = time.monotonic()
with open(os.path.join(MOCK, "events"), "a") as f:
    f.write(f"{t} {kind}\n")
try:
    busy = float(open(os.path.join(MOCK, "busy")).read())
except (OSError, ValueError):
    busy = 0
held = t < busy
if held and "tool_hang_in_hold" in SC:
    print("tri 64x64 #1: job hung, context lost")
    sys.exit(3)
if held:
    time.sleep(max(0, busy - time.monotonic()))
us = int((time.monotonic() - t) * 1e6) + 900
if "tool_fail" in SC:
    print("job: failed")
    sys.exit(1)
if cmd in ("fill", "copy"):
    print(f"job: ok\njob time: {us} us\ndiff: 0 of 2048 pixels")
elif kind == "partial":
    print("tri 1024x768 #1: overflowed, 1 triangle\ntri 1024x768 #2: overflowed, 1 triangle")
else:
    side = {"tri256n3": "256x256"}.get(kind, "64x64")
    print(f"tri {side} #1: 1062 triangle, 3034 background, 0 other\ntri {side} #1: {us} us\ndiff: 0 of 4096 pixels")
sys.exit(0)
