#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fit/o18_1.py: O18-1 (record E1073), Q139's faulting words fitted offline on E509's kept kernel
lines, post hoc (rank-round18.md section 2 "f3"). Standard library only. Reads, at the data commit
of session.toml [freeze] (git show, never the working tree): ta/mtile-fields{,-risky}/cases.tsv
and kernel.log (the case markers `resgx545 case NAME` and the kernel's `sgxfive: BIF fault S at A`
lines; a case's kind is its FIRST fault line, the job's own: the later lines of a case are its
health triangles, E509's script).

A word's fields (gen/q139_fit.py's reading, r10-geo's byte copy): n = 4 when CR_TE_MTILE1 bit 31 is
set, else 2; the bounds of an axis are (0, B1, B2, B3) at n = 4 and (0, B2) at n = 2 (B1 bits
29:22, B2 21:12, B3 11:0 of the axis's word, CR_TE_MTILE1 across, CR_TE_MTILE2 down); the stride is
CR_TE_MACROTILE_STRIDE (ta:146) or the rule's mx * my.

Forms (each a function of the case's size and pokes only; frozen by this file's sha256):

  H-KIND      0x90004 (FAULT_REQ bit 2, the TA's header write past the kernel's layout, hw_spec
              5.5) iff an axis has every bound at 0 (all of the axis's tiles in its last
              macrotile) or the stride puts the last macrotile, n * n - 1, at or past slot 3072
              (S (n n - 1) >= 3072: a threshold between E509's S = 128 and S = 256 at 640 x 480,
              [post hoc, one case]); every other faulting word 0x90100
              (FAULT_REQ bit 8, the 3D's read at the parameter heap's first page 0x10000, SB 1:
              E869's zero stream offset [infer])
  H-ONE-KIND  every faulting word faults one way: 0x90100 (E1048's H-COVER read as one mechanism)

Pages of 0x90004 (reported, not fitted: E509 ran on module 14D099861204842EA496D85, whose TA data
layout is not kept): the x side at 0x20008 (256 x 256) and 0x2000a (640 x 480), the y side at
0x20010 at both sizes. On B60AB0B4 the kernel's layout (sgx_render_tadata_layout_in, fork
2a650d74) gives 256 x 256 and 384 x 256 one TA data of 0x6000 bytes (E1048's f2-ctl-256 dump:
24576), so its first unmapped page is 0x20006 (H-PAGE-END [infer]).

  python3 fit/o18_1.py [DATA_COMMIT]   the cases, each form's count, the 95 % rule, f3's rows
"""
import hashlib
import os
import re
import subprocess
import sys

DATA = os.environ.get("RESGX545_DATA_REPO", "/Users/jtorra/src/resgx545-data")
SETS = ("ta/mtile-fields", "ta/mtile-fields-risky")
FORMS = ("H-KIND", "H-ONE-KIND")
RULE95 = 0.95


def show(commit, path):
    return subprocess.run(["git", "-C", DATA, "show", f"{commit}:{path}"], check=True,
                          capture_output=True).stdout.decode(errors="replace")


def cdiv(a, b):
    return -(-a // b)


def rule(w, h):
    tx, ty = cdiv(w, 32), cdiv(h, 16)
    n = 4 if w * h >= 640 * 480 else 2
    mx = cdiv(cdiv(tx, n), 4) * 4
    my = cdiv(cdiv(ty, n), 4) * 4
    b = (1, 2, 3) if n == 4 else (1, 1, 1)
    m1 = ((1 if n == 4 else 0) << 31) | (mx * b[0] << 22) | (mx * b[1] << 12) | (mx * b[2])
    m2 = (my * b[0] << 22) | (my * b[1] << 12) | (my * b[2])
    return m1, m2, mx * my


def words(w, h, args):
    m1, m2, s = rule(w, h)
    for idx, val in re.findall(r"ta:(\d+)=(0x[0-9a-fA-F]+)", args):
        v = int(val, 16)
        if idx == "143":
            m1 = v
        elif idx == "144":
            m2 = v
        elif idx == "146":
            s = v
        else:
            raise ValueError(idx)
    return m1, m2, s


def bounds(m1, m2):
    n = 4 if (m1 >> 31) & 1 else 2
    x = ((m1 >> 22) & 0xff, (m1 >> 12) & 0xff, m1 & 0xff)
    y = ((m2 >> 22) & 0x1ff, (m2 >> 12) & 0x1ff, m2 & 0x1ff)
    if n == 4:
        return n, x, y
    return n, (x[1],), (y[1],)


def kind(form, w, h, args):
    """The predicted fault word of a faulting case."""
    if form == "H-ONE-KIND":
        return 0x90100
    m1, m2, s = words(w, h, args)
    n, bx, by = bounds(m1, m2)
    zero_axis = not any(bx) or not any(by)
    stride_past = s * (n * n - 1) >= 3072   # [post hoc]: between S = 128 and 256 at n = 4
    return 0x90004 if zero_axis or stride_past else 0x90100


def cases(commit):
    out = []
    for ds in SETS:
        rows = show(commit, f"{ds}/cases.tsv").splitlines()
        hdr = rows[0].split("\t")
        first, cur = {}, None
        for ln in show(commit, f"{ds}/kernel.log").splitlines():
            m = re.search(r"resgx545 case (\S+)", ln)
            if m:
                cur = m.group(1)
                continue
            m = re.search(r"sgxfive: BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", ln)
            if m and cur and cur not in first:
                first[cur] = (int(m.group(1), 16), int(m.group(2), 16))
        for r in rows[1:]:
            d = dict(zip(hdr, r.split("\t")))
            out.append((ds, d["name"], int(d["W"]), int(d["H"]), d.get("args", ""), first.get(d["name"])))
    return out


def self_sha():
    return hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()


# f3's two rows (never run: 384 x 256 is no size of E509's; B1 and B3 values none of its words
# at n = 2 had), each predicted under every form
F3 = (("f3-k4", 384, 256, "--kpoke-render 1:ta:143=0x00c00005"),     # B2 = 0: an empty x axis
      ("f3-k100", 384, 256, "--kpoke-render 1:ta:143=0x00406001"))   # fx 6: 2nd macrotile inside


def main(argv):
    commit = argv[1] if len(argv) > 1 else "45423fbc3"
    cs = cases(commit)
    faulted = [c for c in cs if c[5] is not None]
    print(f"O18-1 on data {commit}: {len(cs)} cases, {len(faulted)} faulting (first fault line each)")
    kinds = {}
    for c in faulted:
        kinds[c[5][0]] = kinds.get(c[5][0], 0) + 1
    print("observed kinds: " + ", ".join(f"{k:#x} x {v}" for k, v in sorted(kinds.items())))
    pages = sorted({(c[2], c[3], c[5][1] >> 12) for c in faulted if c[5][0] == 0x90004})
    print("0x90004 pages (W, H, page): " + ", ".join(f"{w}x{h} {p:#x}" for w, h, p in pages))
    best = None
    for f in FORMS:
        hit = sum(1 for c in faulted if kind(f, c[2], c[3], c[4]) == c[5][0])
        frac = hit / len(faulted)
        miss = [c[1] for c in faulted if kind(f, c[2], c[3], c[4]) != c[5][0]]
        print(f"{f}: {hit} of {len(faulted)} kinds ({100 * frac:.1f} %){' misses ' + ', '.join(miss[:8]) if miss else ''}")
        if frac >= RULE95 and (best is None or hit > best[1]):
            best = (f, hit)
    print(f"rule: a form fits at least 95 % of the faulting cases' kinds: "
          f"{'yes, ' + best[0] + ' (f3 is built)' if best else 'no (f3 is not built)'}")
    for name, w, h, args in F3:
        print(f"f3 {name} {w}x{h} {args}: " + ", ".join(f"{f} {kind(f, w, h, args):#x}" for f in FORMS))
    print(f"form file sha256 {self_sha()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
