#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A fake sgxfive-test for the R3-events mock tests: the lines the landed gate (fill, tri) and the health script grep for.
MOCK_SCENARIO: tool_fail (rc 1, no diff line)."""
import os
import sys

SC = set(os.environ.get("MOCK_SCENARIO", "").split(","))
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if "tool_fail" in SC:
    print("job: failed")
    sys.exit(1)
if cmd == "fill":
    print("job: ok\njob time: 100 us\ndiff: 0 of 2048 pixels")
elif cmd == "tri":
    print("tri 64x64 #1: 1062 triangle, 3034 background, 0 other\ndiff: 0 of 4096 pixels")
else:
    print("fake tool: unknown command", cmd)
    sys.exit(2)
