#!/usr/bin/env python3
"""stop_dumps.py: the kept dumps of a firmware past its boot (HostCtl dword 12 above 20) of the published sessions, by CR_CLKGATESTATUS (reg 0x008),
with HostCtl dwords 3, 8, 12, sw_events and TA3DCtl dwords 56..58.  Read-only; roots as arguments; paths printed as walked (relative roots give relative paths)."""
import os, re, sys
R8 = re.compile(r"reg 0x008 = 0x([0-9a-f]{8})")
H0 = re.compile(r"hostctl\[ 0\]:((?: [0-9a-f]{2}){32})")
H8 = re.compile(r"hostctl\[ 8\]:((?: [0-9a-f]{2}){32})")
T56 = re.compile(r"ta3dctl\[56\]:((?: [0-9a-f]{2}){12})")
SW = re.compile(r"sw_events (\d+)")
def dw(s):
    b = bytes(int(x, 16) for x in s.split())
    return [int.from_bytes(b[i:i+4], "little") for i in range(0, len(b), 4)]
SKIP = ("firmware", "clean-room", ".git")  # the data repository only
n = live = 0
rows = []
for root in sys.argv[1:]:
    for d, dn, fn in os.walk(root):
        dn[:] = sorted(x for x in dn if x not in SKIP)
        for f in sorted(fn):
            if not f.endswith((".txt", ".dmesg", ".log")):
                continue
            p = os.path.join(d, f)
            try:
                if os.path.getsize(p) > 64 << 20: continue
                t = open(p, errors="replace").read()
            except OSError:
                continue
            if "hostctl[ 0]" not in t: continue
            cur = {}
            for ln in t.splitlines():
                m = SW.search(ln)
                if m: cur = {"sw": int(m.group(1))}
                m = R8.search(ln)
                if m: cur["r8"] = int(m.group(1), 16)
                m = H0.search(ln)
                if m: cur["h0"] = dw(m.group(1))
                m = H8.search(ln)
                if m: cur["h8"] = dw(m.group(1))
                m = T56.search(ln)
                if m and "h0" in cur and "h8" in cur:
                    n += 1
                    if cur["h8"][4] > 20:
                        live += 1
                        rows.append((cur.get("r8"), p, cur["h0"][3], cur["h8"][0], cur["h8"][4], cur["h8"][6],
                                     cur.get("sw"), dw(m.group(1))))
                    cur = {}
busy = [r for r in rows if r[0] not in (0x20, None, 0)]
print(f"dumps {n}, with dword 12 above 20 (a running or stopped firmware, not a fresh boot) {live}, of them CLKGATESTATUS not 0x20: {len(busy)}")
for r in busy:
    print(f"clk {r[0]:#x} {r[1]} dw3 {r[2]} dw8 {r[3]} dw12 {r[4]} dw14 {r[5]:#x} sw {r[6]} ta3d56..58 {[hex(x) for x in r[7]]}")
idle = [r for r in rows if r[0] == 0x20]
print(f"idle dumps past the boot: {len(idle)}; with dw3 or dw8 not 0: {sum(1 for r in idle if r[2] or r[3])}; with a ta3d 56 or 58 sample: {sum(1 for r in idle if r[7][0] or r[7][2])}")
