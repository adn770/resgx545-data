#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A fake sgxfive-test for the R1-events mock tests: prints what the real tool prints for fill, copy, tri, probe (loop
programs, triangle targets, the vertex program) and tri --fault, and appends the job's kind with the submission time
(time.monotonic, system-wide) to MOCK_DIR/events, which the fake EDM (tests/mockfw/fwtask_run.py) delivers.  The Q082 loops
set CR_EVENT_STATUS2 bit 6 in MOCK_DIR/status2 by the model in MOCK_SCENARIO (t_iter, t_instr, t_time); a big 4096x4096 job
writes the job's facts to MOCK_DIR/lastjob.json and its control block to the mock debugfs buf09 (dword 38 = 0x20 on a raise).
MOCK_SCENARIO: tool_fail (rc 1, no diff line), tool_sleep (never returns within the test's timeout), d3_raise (the 0x3a0 job
raises too), no_o0 (the probe prints no o0 line)."""
import json
import os
import re
import struct
import sys
import time

MOCK = os.environ["MOCK_DIR"]
SC = set(os.environ.get("MOCK_SCENARIO", "").split(","))
a = sys.argv[1:]
cmd = a[0] if a else ""


def event(kind):
    t = time.monotonic()
    with open(os.path.join(MOCK, "events"), "a") as f:
        f.write(f"{t} {kind}\n")
    return t


def latch(model, kind, iters, shape):
    body = {"b8": 8, "b16": 16, "b4": 4, "ld8": 8}[kind]
    side = 0 if shape == "fill" else int(shape[3:]) if shape.startswith("tri") else 0
    if model == "t_iter":
        return iters >= 55
    if model == "t_instr":
        return iters * body >= 440
    # t_time: fewer resident instances run faster (the loop must be longer); a load's latency shows on 8x8 only
    f = {0: 1.0, 256: 1.0, 128: 1.3, 32: 2.0, 8: 6.0}.get(side, 1.0)
    if kind == "ld8":
        f = 0.6 if side == 8 else 1.0
    return iters * body / f >= 440


def set_status2(bit6):
    p = os.path.join(MOCK, "status2")
    cur = int(open(p).read().strip(), 0) if os.path.exists(p) else 0x400
    with open(p, "w") as f:
        f.write(f"0x{cur | (0x40 if bit6 else 0):x}\n")


if "tool_sleep" in SC:
    time.sleep(60)
if cmd == "tri" and "--fault" in a:
    with open(os.path.join(MOCK, "status2"), "w") as f:
        f.write("0x480\n")
    with open(os.environ.get("R1_KMSG", os.path.join(MOCK, "kmsg")), "a") as f:
        f.write("[3.0] gma500: sgxfive: BIF fault 0x90008 at 0x3e000001 stalls job 5, recovering\n"
                "[3.1] gma500: sgxfive: job 5 hung, recovery held\n")
    p = os.path.join(MOCK, "reset_count")
    n0 = open(p).read() if os.path.exists(p) else "0"
    for _ in range(400):
        time.sleep(0.05)
        if (open(p).read() if os.path.exists(p) else "0") != n0:
            break
    print("tri: FAILED after 0 renders: job faulted, context lost (Input/output error)")
    sys.exit(1)
if cmd == "probe":
    binf = [x for x in a if x.endswith(".bin")][-1]
    name = os.path.basename(binf)[:-4]
    m = re.match(r"loop-(b8|b16|b4|ld8)-i(\d+)$", name)
    tri = "--tri" in a
    kind_slot = a[a.index("--tri") + 1] if tri else ""
    side = int(a[a.index("--width") + 1]) if "--width" in a else 0
    print(f"probe {name}: scratch at 0x3e003000 (64 KiB)")
    if "tool_fail" in SC:
        print(f"probe {name}: failed: job hung")
        sys.exit(3)
    if m and not tri:
        kind, iters = m[1], int(m[2])
        t = event("fill")
        time.sleep(0.003)
        if latch(next((x for x in ("t_iter", "t_time") if x in SC), "t_instr"), kind, iters, "fill"):
            set_status2(True)
        us = 20 + iters * {"b8": 8, "b16": 16, "b4": 4, "ld8": 8}[kind] * 3
        print(f"probe {name}: job time: {us} us")
        if "no_o0" not in SC:
            print(f"probe {name}: o0 0x00000000 (2048 of 2048)")
        sys.exit(0)
    if m and tri and kind_slot == "pixel" and side < 1024:
        kind, iters = m[1], int(m[2])
        event("tri64")
        time.sleep(0.003)
        if latch(next((x for x in ("t_iter", "t_time") if x in SC), "t_instr"), kind, iters, f"tri{side}"):
            set_status2(True)
        cov = max(1, int(side * side * 0.26))
        print(f"probe {name}: tri {side}x{side}, pixel replaced")
        if "no_o0" not in SC:
            print(f"probe {name}: o0 mixed 0xff203040 x{side * side - cov} 0x00000000 x{cov}")
        sys.exit(0)
    if kind_slot == "vtxuse":
        event("tri64")
        print(f"probe {name}: tri 64x64, vtxuse replaced")
        print(f"probe {name}: o0 mixed 0xff00ff00 x1062 0xff203040 x3034")
        sys.exit(0)
    if kind_slot == "pixel" and side == 4096:                           # Q033's big jobs
        pb = int(open(os.path.join(MOCK, "dbg", "render_pb_pages")).read().strip(), 0)
        nparts = {0x320: 3, 0x3a0: 2, 0x422: 0}.get(pb, 1)
        raised = pb == 0x320 or (pb == 0x3a0 and "d3_raise" in SC)
        kind = f"big:{pb:#x}:{nparts}:{1 if raised else 0}"
        t = event(kind)
        time.sleep(0.01)
        words = [[8, 1]]
        info = {"pb": pb, "nparts": nparts, "raised": raised, "t": t, "kind": kind}
        with open(os.path.join(MOCK, "lastjob.json"), "w") as f:
            json.dump(info, f)
        b = [0] * 59
        if raised:
            b[38] = 0x20
        with open(os.path.join(MOCK, "dbg", "buf09"), "wb") as f:
            f.write(struct.pack("<59I", *b))
        dump = a[a.index("--dump-render") + 1] if "--dump-render" in a else None
        if dump:
            with open(os.path.join(dump, "probe.param.bin"), "wb") as f:
                f.write(b"param")
            with open(os.path.join(dump, "probe.tadata.bin"), "wb") as f:
                f.write(b"tadata")
        print(f"probe {name}: tri 4096x4096, pixel replaced")
        if nparts:
            print(f"probe {name}: failed: scene overflowed the parameter buffer, context kept ({nparts} partial renders)")
            sys.exit(3)
        print(f"probe {name}: o0 mixed 0xff203040 x16000000 0x00000000 x777216")
        sys.exit(0)
# fill, copy and the tri jobs of the controls
w = a[a.index("--width") + 1] if "--width" in a else "64"
kind = {"fill": "fill", "copy": "copy"}.get(cmd) or ("partial" if w == "1024" else "tri64")
event(kind)
time.sleep(0.005)
if "tool_fail" in SC:
    print("job: failed")
    sys.exit(1)
us = 900
if cmd in ("fill", "copy"):
    print(f"job: ok\njob time: {us} us\ndiff: 0 of 2048 pixels")
elif kind == "partial":
    print("tri 1024x768 #1: overflowed, 1 triangle\ntri 1024x768 #2: overflowed, 1 triangle\n"
          "tri: 0 of 2 renders ok, 2 overflowed")
else:
    print(f"tri 64x64 #1: 1062 triangle, 3034 background, 0 other\ntri 64x64 #1: {us} us\ndiff: 0 of 4096 pixels")
sys.exit(0)
