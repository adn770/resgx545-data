#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r36-n3's post hoc reading (not frozen before the run): the EDM's tick (HostCtl
dword 12, the counter fwtask_run.py's alive() reads) and USE0_SERV_EVENT (0x0b14) in e1-a's
registers right before the job (snap0), in fwtask_run.py's stop dump after the 200 ms window
(stop0-regs) and after the job (snap9), with the kernel-log times of the marks around them, and
the results page's protocol and slot dwords.

  python3 fold/posthoc.py out/ATT/own"""
import gzip
import json
import os
import re
import sys


def text(d, n):
    p = os.path.join(d, n)
    b = open(p + ".gz", "rb").read() if os.path.exists(p + ".gz") else open(p, "rb").read()
    return (gzip.decompress(b) if os.path.exists(p + ".gz") else b).decode(errors="replace")


def regs(t):
    hc = re.search(r"^hostctl 0x30 (0x[0-9a-f]+)$", t, re.M)
    if hc is None:      # the stop dump's form: `hostctl[ 8]: b0 b1 ...` (dword 12 = bytes 16-19)
        m = re.search(r"^hostctl\[ 8\]: (.*)$", t, re.M)
        b = m.group(1).split()[16:20]
        tick = int("".join(reversed(b)), 16)
    else:
        tick = int(hc.group(1), 16)
    ev = re.search(r"^reg 0x0?b14 =? ?(0x[0-9a-f]+)$", t, re.M)
    fault = re.search(r"^reg 0x0?c04 =? ?(0x[0-9a-f]+)$", t, re.M)
    return tick, int(ev.group(1), 16), int(fault.group(1), 16)


def main(d):
    for n in ("e1-a.snap0.regs", "e1-a.stop0-regs.txt", "e1-a.snap9.regs"):
        tick, ev, bif = regs(text(d, n))
        print(f"{n}: tick (HostCtl dword 12) {tick} (0x{tick:x}), USE0_SERV_EVENT 0x{ev:08x}, "
              f"BIF_INT_STAT 0x{bif:08x}")
    for ln in text(d, "e1-a.dmesg").splitlines():
        print("kmsg: " + ln)
    k = text(d, "kernel.log")
    for pat in (r"snap e1-a 0 ", r"case e1-a ", r"class e1-a ", r"SGX reset: BIF_FAULT",
                r"health e1-a try"):
        for ln in k.splitlines():
            if re.search(pat, ln):
                print("journal: " + ln)
    p = json.loads(text(d, "e1-a.own_res.json"))["page"]
    print("page dwords 0-5: " + " ".join(f"0x{x:08x}" for x in p[:6]))
    for s in range(1, 5):
        print(f"page slot {s}: " + " ".join(f"0x{x:08x}" for x in p[0x40 + 4 * s:0x44 + 4 * s]))
    run = json.loads(text(d, "e1-a.txt"))
    print("run: done %s, ms %.1f, stop %r" % (run["records"][0]["done"], run["records"][0]["ms"],
                                             run["stop"]))
    for n in ("e1-a.fill2.txt", "e1-a.health2.txt"):
        print(n + ": " + "; ".join(ln for ln in text(d, n).splitlines()
                                   if ln.startswith(("job:", "diff:"))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
