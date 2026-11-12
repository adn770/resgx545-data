#!/usr/bin/env python3
"""hwr_scan.py: every kept register dump (text) whose HostCtl dword 3 (ukernel_detected_lockups) or dword 8
(interrupt_flags) is not 0, and the count of dumps read.  Read-only; explicit roots given as arguments.
Reads lines 'hostctl[ 0]: b0 b1 ...' (8 dwords a line) and 'hostctl[ 8]: ...', and ta3dctl[56] when present."""
import os, re, sys
H0 = re.compile(r"hostctl\[ 0\]:((?: [0-9a-f]{2}){32})")
H8 = re.compile(r"hostctl\[ 8\]:((?: [0-9a-f]{2}){32})")
T56 = re.compile(r"ta3dctl\[56\]:((?: [0-9a-f]{2}){12})")
SW = re.compile(r"sw_events (\d+)")
def dw(s):
    b = bytes(int(x, 16) for x in s.split())
    return [int.from_bytes(b[i:i+4], "little") for i in range(0, len(b), 4)]
SKIP = ("firmware", "clean-room", ".git")  # the data repository only
tot = hits = files = 0
for root in sys.argv[1:]:
    for d, dn, fn in os.walk(root):
        dn[:] = [x for x in dn if x not in SKIP]
        for f in fn:
            if not f.endswith((".txt", ".dmesg", ".log")):
                continue
            p = os.path.join(d, f)
            try:
                if os.path.getsize(p) > 64 << 20:
                    continue
                t = open(p, errors="replace").read()
            except OSError:
                continue
            if "hostctl[ 0]" not in t:
                continue
            files += 1
            lines = t.splitlines()
            cur = {}
            for i, ln in enumerate(lines):
                m = SW.search(ln)
                if m: cur = {"sw": int(m.group(1)), "line": i + 1}
                m = H0.search(ln)
                if m: cur["h0"] = dw(m.group(1)); cur.setdefault("line", i + 1)
                m = H8.search(ln)
                if m: cur["h8"] = dw(m.group(1))
                m = T56.search(ln)
                if m:
                    cur["t56"] = dw(m.group(1))
                if (m or (H8.search(ln) and "ta3dctl" not in t)) and "h0" in cur and "h8" in cur:
                    tot += 1
                    if cur["h0"][3] or cur["h8"][0] or (cur.get("t56") and any(cur["t56"])):
                        hits += 1
                        t56 = cur.get("t56")
                        print(f"{p}:{cur['line']}: dw3 {cur['h0'][3]} dw8 {cur['h8'][0]} dw9 {cur['h8'][1]} dw12 {cur['h8'][4]} "
                              f"dw14 {cur['h8'][6]:#x} sw_events {cur.get('sw')} ta3d56..58 {[hex(x) for x in t56] if t56 else None}")
                    cur = {}
print(f"TOTAL: {files} files, {tot} dumps read, {hits} with dword 3, dword 8 or ta3dctl 56..58 not 0")
