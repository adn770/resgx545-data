#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""out/fold/post_read.py ATT: the fold's post hoc readings of r8-k2 (added 2026-11-13, after the
run; nothing here was frozen). Standard library only; reads the kept files of out/ATT/{xf,tri}.

- every knob row: the job line, the image (hash, wrong pixels), the kernel's PTE line, and each
  `BIF fault S at A` line decoded with hw_spec.md section 5.5's fields (BIF_INT_STAT FAULT_REQ
  15:0 and FAULT_TYPE 18:16; BIF_FAULT CID 3:0, SB 8:4, page 31:12), the page's place in the
  mapping (which of its pages, the last image page or the guard);
- why xf-c-end did not run: the stage's fault events against its #limit, row by row;
- the health fill and triangle the runner kept after each row (diff 0 of N or not)."""
import gzip
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "gen"))
import make as G  # noqa: E402


def text(d, name):
    p = os.path.join(d, name)
    if os.path.exists(p + ".gz"):
        return gzip.open(p + ".gz", "rb").read().decode(errors="replace")
    return open(p).read() if os.path.exists(p) else ""


def cases(d):
    out = []
    lines = text(d, "cases.tsv").splitlines()
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) >= 9:
            out.append(dict(name=f[0], knobs=f[4], args=f[6], rc=int(f[7]), cls=f[8]))
    return out


def decode(stat, addr):
    req = [b for b in range(16) if stat >> b & 1]
    return (f"BIF_INT_STAT 0x{stat:x} (FAULT_REQ bit {','.join(map(str, req)) or '-'}, "
            f"FAULT_TYPE {stat >> 16 & 7}), BIF_FAULT 0x{addr:08x} (page 0x{addr & ~0xfff:08x}, "
            f"SB {addr >> 4 & 0x1f}, CID {addr & 0xf})")


def image_pages(cmd):
    # the image's own pages (the mapping's last page is the guard): fill and copy 64 x 32 stride
    # 256 = 2 pages, tri 64 x 64 = 4 pages
    return 2 if cmd in ("fill", "copy") else 4


def main(att):
    rows = {r[1]: r for r in G.ROWS}
    for st in ("xf", "tri"):
        d = os.path.join(att, st)
        print(f"== {st}: knob rows")
        events = 0
        cs = cases(d)
        for c in cs:
            n, r = c["name"], rows[c["name"]]
            out, dm = text(d, n + ".txt"), text(d, n + ".dmesg")
            if c["cls"] in ("fault", "hang"):
                events += 1
            job = (re.search(r"^job: .*$", out, re.M) or [""])[0]
            img = (re.search(r"^target: .*$", out, re.M) or [""])[0]
            diff = (re.search(r"^diff: .*$", out, re.M) or [""])[0]
            line = f"{n}: class {c['cls']} rc {c['rc']} (fault events {events} of #limit {G.LIMIT[st]}); {job}; {img}; {diff}"
            print(line)
            if r[4] == "isolation":
                print("  " + "; ".join(re.findall(r"^(?:PASS|FAIL) .*$", out, re.M)))
                for a, b in re.findall(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", dm):
                    print(f"  fault: {decode(int(a, 16), int(b, 16))}")
            if r[5] is None:
                continue
            start, size, ro, acc = G.MAPS[r[5]]
            pte = re.findall(r"vm_map (0x[0-9a-f]+) \+(0x[0-9a-f]+): PTE flags (0x[0-9a-f]+)", dm)
            print(f"  knob: {r[5]} ({acc}) 0x{start:08x} +0x{size:x}; kernel PTE lines {pte}")
            for s, a in re.findall(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", dm):
                s, a = int(s, 16), int(a, 16)
                pg = ((a & ~0xfff) - start) // 0x1000
                img = r[5] != "tri-gen"
                where = "outside the mapping" if not 0 <= pg < size // 0x1000 else \
                    f"page {pg} of the mapping" + ("" if not img else
                                                   " (the image's last)" if pg == image_pages(r[4]) - 1 else
                                                   " (the guard)" if pg == size // 0x1000 - 1 else
                                                   " (the image's first)" if pg == 0 else "")
                print(f"  fault: {decode(s, a)}: {where}")
        ran = {c["name"] for c in cs}
        notrun = [r[1] for r in G.ROWS if r[0] == st and r[1] not in ran]
        print(f"  not run: {notrun or 'none'}")
        print(f"== {st}: health after rows (the runner's kept fill and triangle)")
        for f in sorted(os.listdir(d)):
            m = re.match(r"(.+)\.(fill|health)(\d+)\.txt\.gz$", f)
            if m:
                t = text(d, f[:-3])
                dl = (re.search(r"^diff: .*$", t, re.M) or ["no diff line"])[0]
                print(f"  {m[1]} {m[2]} try {m[3]}: {dl}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
