#!/usr/bin/env python3
"""Post hoc analyses of the p1141/tex batch (not frozen, written after the dumps were read).

    python3 -I post_1141tex.py DUMPS LANDED_TE_DUMPS

DUMPS is the copy of the laptop's ~/p1141tex-dumps, LANDED_TE_DUMPS the data repo's isp/msaa-te-dumps/dumps.
Standard library only. Sections: guard, types, cube, addr, q140, te29.
"""
import collections
import gzip
import json
import re
import struct
import sys

D, L = sys.argv[1].rstrip("/") + "/", sys.argv[2].rstrip("/") + "/"
CASES = {c["name"]: c for c in json.load(open(__file__.rsplit("/draft-records/", 1)[0] + "/gen/cases.json"))}


def txt(script, name):
    return gzip.open(f"{D}{script}/{name}.txt.gz", "rt", errors="replace").read()


def pixels(script, name):
    rows = {}
    for ln in txt(script, name).splitlines():
        m = re.search(r"row (\d+): (.*)$", ln)
        if m:
            rows[int(m.group(1))] = [int(v, 16) for v in m.group(2).split()]
    return rows


def words(path):
    b = gzip.open(path).read()
    return struct.unpack("<%dI" % (len(b) // 4), b)


def mort(x, y):
    r = 0
    for k, (v, b) in enumerate([(y, 0), (x, 0), (y, 1), (x, 1), (y, 2), (x, 2), (y, 3), (x, 3)]):
        r |= ((v >> b) & 1) << k
    return r | (((x >> 4) & 1) << 8)


def guard():
    print("== guard: stored = depth word is not the background 1.0 (0x3f800000); E465's 924 of the 34 x 18 target")
    tot = 0
    for name, c in CASES.items():
        if c["script"] != "isp-a-guard":
            continue
        m = c["meta"]
        W, H, G = m["W"], m["H"], m["G"]
        buf = words(f"{D}isp-a-guard/{name}.depth.1.bin.gz")
        tw, th = (W + 31) // 32, (H + 15) // 16
        idx = lambda x, y: 512 * ((y // 16) * (G + 1) + x // 32) + mort(x % 32, y % 16)
        area = [(x, y) for y in range(th * 16) for x in range(tw * 32)]
        obs = {p for p in area if buf[idx(*p)] != 0x3F800000}
        dead = sum(buf[idx(*p)] == 0xDEADBEEF for p in area)
        rule = {p for p in area if p[0] + .5 < 1.25 * W and p[1] + .5 < 1.25 * H}
        notbg_all = sum(1 for p in area if buf[idx(*p)] != 0xDEADBEEF)
        ok = obs == rule
        tot += ok
        print(f"  {name:16s} tile area {len(area):5d} written (not deadbeef) {notbg_all:5d}; "
              f"not background {len(obs):5d}; rule x+.5<1.25W, y+.5<1.25H {len(rule):5d}; "
              f"sets equal {ok}; deadbeef in area {dead}")
    print(f"  jobs with the set equal to the rule: {tot} of 12")


def types():
    print("\n== types: window (x % w, y % h) -> index tag; stride per type")
    for ty, script in ((3, "tex-f-types"), (1, "tex-g-types-risky"), (4, "tex-g-types-risky")):
        for w, h in ((8, 8), (32, 32), (32, 16), (16, 32)):
            r = pixels(script, f"ty{ty}-{w}x{h}")
            row = lambda y: [v & 0xFFFFFFF for v in r[y][:w]]
            sy = r[1][0] - r[0][0]
            xs = {r[0][x + 1] - r[0][x] for x in range(w - 1)}
            S = {3: w, 1: w, 4: 32}[ty]
            ok = sum(r[y][x] == 0xD0000000 | ((y % h) * S + x % w) for y in range(32) for x in range(64))
            print(f"  ty{ty}-{w}x{h}: x step {sorted(xs)}, y step {sy}; stride {'w' if ty != 4 else '32'} wrap at the size: {ok} of 2048")


def cube():
    print("\n== cube (type 2, 16 x 16 faces, tag = face * 256 + texel index in the face)")
    for n in ("cu-xp", "cu-xn", "cu-yp", "cu-yn", "cu-zp", "cu-zn", "cu-w02", "cu-w11"):
        r = pixels("tex-h-cube", n)
        p = [v for y in sorted(r) for v in r[y]]
        faces = collections.Counter(((v & 0xFFFFFFF) >> 8) for v in p)
        local = {v & 255 for v in p}
        print(f"  {n}: faces {dict(sorted(faces.items()))}, {len(set(p))} distinct, face-local index {min(local)}..{max(local)}")


def addr():
    print("\n== addr: A4's last word read = ((sum of the level sizes below L) + size of level L) << e, in bytes (4 a word)")
    fault = {"ad-tw64x64-L2e2", "ad-tw64x64-L3e3", "ad-st128x32-L3e2"}
    for name, c in CASES.items():
        if c["script"] != "tex-c-addr":
            continue
        m = re.match(r"ad-(tw|st)(\d+)x(\d+)-L(\d)e(\d)(b10)?", name)
        w, h, L_, e = int(m[2]), int(m[3]), int(m[4]), int(m[5])
        if m[6]:
            print(f"  {name:22s} bit 10 set: one texel; {'FAULT' if name in fault else 'completed'}")
            continue
        off = sum(max(1, w >> j) * max(1, h >> j) for j in range(L_))
        end = (off + max(1, w >> L_) * max(1, h >> L_)) << e
        print(f"  {name:22s} {end * 4:7d} bytes {hex(end * 4):8s} {'FAULT' if name in fault else 'completed'}")


def q140():
    print("\n== q140: kernel log per job (first fault is the job's, later ones the health triangles after it)")
    lines = gzip.open(f"{D}msaa-c-q140/journal-k.txt.gz", "rt", errors="replace").read().splitlines()
    cur = None
    for ln in lines:
        m = re.search(r"p1141tex case (\S+)", ln)
        if m:
            cur = m[1]
            print(f"  case {cur}")
        m = re.search(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+) .* stalls job (\d+)", ln)
        if m:
            print(f"    fault {m[1]} at {m[2]} (page {int(m[2], 16) >> 12:#x}) job {m[3]}")
    for n in ("q140-288x144", "q140-256x288", "q140-384x384"):
        t = txt("msaa-c-q140", n)
        print(f"  {n}: tool output tail: {[l for l in t.splitlines() if 'health' in l or 'FAILED' in l]}")


def te29():
    print("\n== te29: param buffer of the TE 0x40/0x80/0xc0 job against the landed job with bit 29 set")
    pairs = (("t29-m0-40-64x64", "te-m0-60-64x64"), ("t29-m0-80-64x64", "te-m0-a0-64x64"),
             ("t29-m2-40-64x64", "te-m2-60-64x64"), ("t29-m2-80-64x64", "te-m2-a0-64x64"),
             ("t29-m2-c0-64x64", "te-m2-e0-64x64"), ("t29-m2-c0-128x128", "te-m2-e0-128x128"))
    for n, ref in pairs:
        a = words(f"{D}msaa-b-te29/{n}.tri.param.bin.gz")
        b = words(f"{L}/{ref}.param.txt.gz")
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        # the stretch: is a[i+1] == b[i] over diff[0]..diff[-1]?
        lo, hi = diff[0], diff[-1]
        eq = sum(a[i + 1] == b[i] for i in range(lo, hi))
        nz = sum(1 for x in a if x)
        print(f"  {n} vs {ref}: {len(a)} dwords ({nz} non-zero), {len(diff)} differ at {lo}..{hi}; "
              f"a[i+1] == b[i] for {eq} of {hi - lo} dwords of the stretch; other dwords equal {len(a) - len(diff)}")
    print("  tadata, equal to the landed bit-29-set job where one is landed (non-zero dwords of the job):")
    for n, ref in pairs:
        a = words(f"{D}msaa-b-te29/{n}.tri.tadata.bin.gz")
        b = words(f"{L}/{ref}.tadata.txt.gz")
        print(f"  {n} vs {ref}: {len(a)} dwords ({sum(1 for x in a if x)} non-zero), {sum(x != y for x, y in zip(a, b))} differ")


if __name__ == "__main__":
    for f in (guard, types, cube, addr, q140, te29):
        f()
