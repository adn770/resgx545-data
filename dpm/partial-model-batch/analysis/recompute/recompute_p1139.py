#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39 recompute: scores predictions-declared.tsv against the raw files the run kept, with its own
decoders (nothing is shared with run_table.sh, which keeps raw files and prints no reductions).

usage: recompute_p1139.py RUNDIR [--pred predictions-declared.tsv] [--declared declared.tsv]
       recompute_p1139.py --selftest

RUNDIR holds one directory per run of run_table.sh (free-safe, trig-safe, trig-risky, state-safe,
depth-safe, wide-safe, wide-risky, owner-safe, owner-risky): cases.tsv, NAME.txt.gz (the tool's
output), NAME.tri.N.param.bin.gz, NAME.tri.N.tadata.bin.gz (render_param, render_tadata after
render N), NAME.ta3d.N.bin.gz (the control block), NAME.depth.N.bin.gz (the depth buffer),
NAME.after.buf09.bin.gz, NAME.kept.bin.gz, NAME.held.*.gz.

Decoders (from the records, E309, E310, E465, E467, E468; written here again):
  page table  param dump at 0x423000, entry of page i at +4*i: previous page << 16 | next page, 0xffff
              at the ends; the free list is the walk from the entry whose previous page is 0xffff.
  state page  TA data at 0x3000 (context up to 64x64), 0x6000 (up to 1024x768) or 0x42000 (up to
              4096x4096): 17 lists of two dwords, (count << 16 | head page) and tail page, entry 16 the
              global list, entries 0 to 15 the macrotiles numbered down then across.
  ZLS store   tile (tx, ty) of 32x16 pixels at dword 512 * (ty * (G + 1) + tx), G = control bits 11:3,
              in-tile bits y0 x0 y1 x1 y2 x2 y3 x3 x4 from the lowest.
  timeline    regtimeline: "timeline: regs 0x.. ..." then "tl NS v0 v1 ..." (hex, no prefix).
Quantities with no decoder here are printed as "not scored".
"""
from __future__ import annotations

import collections
import glob
import gzip
import os
import re
import struct
import sys

FILL = 0xDEADBEEF
ORDER = [("y", 0), ("x", 0), ("y", 1), ("x", 1), ("y", 2), ("x", 2), ("y", 3), ("x", 3), ("x", 4)]


def tile_index(lx: int, ly: int) -> int:
    v = 0
    for pos, (axis, bit) in enumerate(ORDER):
        v += (((lx if axis == "x" else ly) >> bit) & 1) << pos
    return v


def zls_addr(x: int, y: int, g: int) -> int:
    return 512 * ((y >> 4) * (g + 1) + (x >> 5)) + tile_index(x & 31, y & 15)


def rd(d: str, name: str, suffix: str = ".txt") -> bytes | None:
    p = os.path.join(d, name + suffix + ".gz")
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rb") as f:
        return f.read()


def dwords(b: bytes | None) -> list[int]:
    if not b:
        return []
    n = len(b) // 4
    return list(struct.unpack("<%dI" % n, b[: 4 * n]))


def load_cases(rundir: str):
    cases = {}
    for sub in sorted(os.listdir(rundir)):
        p = os.path.join(rundir, sub, "cases.tsv")
        if not os.path.exists(p):
            continue
        for line in open(p).read().splitlines()[1:]:
            f = line.split("\t")
            if len(f) >= 8:
                cases[f[0]] = dict(dir=os.path.join(rundir, sub), script=f[1], set=f[2], risk=f[3], P=f[4],
                                   knobs=f[5], rt=f[6], args=f[7])
    return cases


def arg(c, flag, default=None):
    m = re.search(re.escape(flag) + r"[ =](\S+)", c["args"])
    return m.group(1) if m else default


def ctx_size(c):
    w = int(arg(c, "--max-width", arg(c, "--width", 64)))
    h = int(arg(c, "--max-height", arg(c, "--height", 64)))
    return w, h


def state_off(c):
    w, h = ctx_size(c)
    return 0x3000 if w <= 64 and h <= 64 else 0x6000 if w <= 1024 and h <= 768 else 0x42000


# ------------------------------------------------------------------ decoders
def walk(param: bytes | None):
    """(free list as a page list, ok) from the page table at 0x423000."""
    t = dwords(param[0x423000:0x423000 + 4 * 0x424]) if param and len(param) >= 0x423000 + 4 * 0x424 else []
    if not t:
        return [], False
    heads = [i for i in range(1, len(t)) if (t[i] >> 16) == 0xffff and t[i] != 0]
    if len(heads) != 1:
        return [], False
    seq, i, seen = [], heads[0], set()
    while i != 0xffff and i not in seen and i < len(t):
        seen.add(i)
        seq.append(i)
        i = t[i] & 0xffff
    npages = sum(1 for i in range(1, len(t)) if t[i] != 0)
    return seq, len(seq) == npages


def state_lists(tadata: bytes | None, off: int):
    d = dwords(tadata[off:off + 0x88]) if tadata and len(tadata) >= off + 0x88 else []
    out = []
    for i in range(17):
        if len(d) < 2 * i + 2:
            break
        w0, w1 = d[2 * i], d[2 * i + 1]
        out.append((i, w0 >> 16, w0 & 0xffff, w1) if w0 or w1 else None)
    return out


def partials(tl: str | None):
    """number of stretches in which the register at 0x0658 reads 1 (None: no timeline)."""
    if not tl:
        return None
    m = re.search(r"^timeline: regs (.*?) samples", tl, re.M)
    if not m:
        return None
    regs = m.group(1).split()
    if "0x0658" not in regs:
        return None
    k = regs.index("0x0658")
    n, prev = 0, 0
    for line in tl.splitlines():
        if line.startswith("tl "):
            v = int(line.split()[2 + k], 16)
            if v == 1 and prev == 0:
                n += 1
            prev = v
    return n


def tl_values(tl: str | None, reg: str):
    if not tl:
        return []
    m = re.search(r"^timeline: regs (.*?) samples", tl, re.M)
    if not m or reg not in m.group(1).split():
        return []
    k = m.group(1).split().index(reg)
    return [int(l.split()[2 + k], 16) for l in tl.splitlines() if l.startswith("tl ")]


def render_lines(out: str):
    return re.findall(r"^tri (\d+)x(\d+) #(\d+): (overflowed, )?(\d+) triangle, (\d+) background", out, re.M)


def job1_status(out: str) -> str:
    if re.search(r"faulted|hung|rejected|FAILED after", out) and not re.search(r"overflowed", out):
        return "fail"
    rl = render_lines(out)
    if rl:
        return "overflow" if rl[0][3] else "ok"
    if "scene overflowed" in out:
        return "overflow"
    return "ok" if re.search(r"o0 ", out) else "fail"


def fill_of(c) -> int:
    """the job's own marker: the fill of the buffer that is read back (the store buffer with --depth-store)."""
    key = "--depth-store-fill" if "--depth-store" in c["args"] else "--depth-fill"
    v = arg(c, key, "0xdeadbeef")
    return int(v, 0) if v.lower().startswith("0x") else FILL


def stored(depth: list[int], fill: int = FILL):
    return [(i, v) for i, v in enumerate(depth) if v != fill]


def depth_facts(c, d: list[int]):
    g = (int(arg(c, "--depth-ctl", "0x0017100c"), 0) >> 3) & 0x1ff
    st = stored(d, fill_of(c))
    zero = sum(1 for _, v in st if v == 0)
    nz = [v for _, v in st if v != 0]
    sign = sum(1 for v in nz if v >> 31)
    slots = collections.defaultdict(list)
    for i, v in st:
        slots[i // 512].append(v)
    whole = sum(1 for s, vs in slots.items() if len(vs) == 512 and all(v == 0 for v in vs))
    return dict(g=g, window=len(st), zero=zero, nonzero=len(nz), signed=sign, whole_zero_tiles=whole)


def plane(v):
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = v
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    a = ((z1 - z0) * (y2 - y0) - (z2 - z0) * (y1 - y0)) / det
    b = ((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / det
    return lambda x, y: z0 + a * (x - x0) + b * (y - y0)


def inside(v, x, y):
    s = []
    for k in range(3):
        (xa, ya, _), (xb, yb, _) = v[k], v[(k + 1) % 3]
        s.append((xb - xa) * (y - ya) - (yb - ya) * (x - xa))
    return all(e >= 0 for e in s) or all(e <= 0 for e in s)


def overlap_value(c, d: list[int]):
    w, h = int(arg(c, "--width", 1024)), int(arg(c, "--height", 768))
    zs = [float(z) for z in arg(c, "--tri-z", "0.25,0.75,0.25").split(",")]
    base = [(8 * w / 64, 8 * h / 64), (56 * w / 64, 20 * h / 64), (20 * w / 64, 56 * h / 64)]
    mv = re.search(r"--move 2:(-?\d+),(-?\d+)", c["args"])
    dx, dy = (int(mv.group(1)), int(mv.group(2))) if mv else (0, 0)
    va = [(x, y, z) for (x, y), z in zip(base, zs)]
    vb = [(x + dx, y + dy, z) for (x, y), z in zip(base, zs)]
    pa, pb = plane(va), plane(vb)
    g = (int(arg(c, "--depth-ctl", "0x0017100c"), 0) >> 3) & 0x1ff
    n = collections.Counter()
    for y in range(h):
        for x in range(w):
            if not (inside(va, x + .5, y + .5) and inside(vb, x + .5, y + .5)):
                continue
            a = zls_addr(x, y, g)
            if a >= len(d) or d[a] in (fill_of(c), 0):
                n["unwritten"] += 1
                continue
            z = struct.unpack("<f", struct.pack("<I", d[a] & 0x7fffffff))[0]
            za, zb = pa(x + .5, y + .5), pb(x + .5, y + .5)
            n["A" if abs(z - za) < 2e-4 and abs(z - zb) >= 2e-4 else "B" if abs(z - zb) < 2e-4 and
              abs(z - za) >= 2e-4 else "both" if abs(z - za) < 2e-4 else "other"] += 1
    tot = n["A"] + n["B"]
    if not tot:
        return "none", n
    return ("A" if n["A"] >= .95 * tot else "B" if n["B"] >= .95 * tot else "mixed"), n


def index_rows(c, d: list[int]):
    g = (int(arg(c, "--depth-ctl", "0x0017100c"), 0) >> 3) & 0x1ff
    hit = tot = 0
    for i, v in stored(d, fill_of(c)):
        if (i // 512) // (g + 1) < 12:
            continue
        tot += 1
        hit += (v & 0x7fffffff) == i
    return ("yes" if tot and hit >= .5 * tot else "no" if tot else "none"), hit, tot


# ------------------------------------------------------------------ observed value of a quantity
class Case:
    def __init__(self, name, c):
        self.name, self.c, self.d = name, c, c["dir"]
        raw = rd(self.d, name)
        self.out = raw.decode("latin-1") if raw else ""
        self.tl = self.out if "timeline: regs" in self.out else None

    def files(self, pat):
        return sorted(glob.glob(os.path.join(self.d, self.name + pat + ".gz")))

    def dump(self, kind, n):
        return rd(self.d, self.name, f".tri.{n}.{kind}.bin") or next(
            (open_gz(p) for p in self.files(f".*.{kind}.bin")), None)

    def ta3d(self, n=None):
        b = rd(self.d, self.name, f".ta3d.{n}.bin") if n else None
        return dwords(b or rd(self.d, self.name, ".after.buf09.bin"))

    def depth(self, n=1):
        """the buffer read back: the store buffer's dump when the job has one, else the depth buffer's."""
        which = "depth-store" if "--depth-store" in self.c["args"] else "depth"
        return dwords(rd(self.d, self.name, f".{which}.{n}.bin"))


def open_gz(p):
    with gzip.open(p, "rb") as f:
        return f.read()


def observe(cs: dict, k: Case, q: str, pred: str):
    c = k.c
    if q == "job1_status":
        return job1_status(k.out)
    if q == "outcome":
        return "hang" if re.search(r"hung", k.out) else "overflow" if "overflow" in k.out else "ok"
    if q == "partials":
        return partials(k.tl)
    if q == "dword35":
        t = k.ta3d(1) or k.ta3d()
        return "0x%x" % t[35] if len(t) > 35 else None
    if q == "dword36":
        t = k.ta3d()
        return t[36] if len(t) > 36 else None
    if q == "status2_high":
        v = tl_values(k.tl, "0x0710") + tl_values(k.tl, "0x071c")
        return 0 if v and all(x >> 16 == 0 for x in v) else (None if not v else "nonzero")
    if q == "bit2_cleared":
        v = tl_values(k.tl, "0x0748")
        return ("yes" if any(x & 4 == 0 for x in v) else "no") if v else None
    if q in ("walk_ok", "job2_is_head_prefix", "job3_is_head_prefix", "job1_pages", "tail_has_state_order"):
        w = [walk(k.dump("param", n)) for n in (1, 2, 3)]
        if q == "walk_ok":
            ws = [x for x in w if x[0]]
            return "yes" if ws and all(ok for _, ok in ws) else ("no" if ws else None)
        pg = [dwords(k.dump("param", n)) for n in (1, 2, 3)]
        if q in ("job2_is_head_prefix", "job3_is_head_prefix"):
            n = 2 if q[3] == "2" else 3
            a, b = k.dump("param", n - 1), k.dump("param", n)
            if not a or not b or not w[n - 2][0]:
                return None
            changed = [p for p in range(1, 0x423) if a[p * 4096:(p + 1) * 4096] != b[p * 4096:(p + 1) * 4096]]
            seq = w[n - 2][0]
            return "yes" if changed and sorted(changed) == sorted(seq[:len(changed)]) else "no"
        if q == "job1_pages":
            a = k.dump("param", 1)
            used = [p for p in range(1, 0x423) if a and any(a[p * 4096:(p + 1) * 4096])]
            return "%d-%d" % (min(used), max(used)) if used else None
        if q == "tail_has_state_order":
            seq = w[0][0]
            ls = [l for l in state_lists(k.dump("tadata", 1), state_off(c))[:16] if l]
            if not seq or not ls:
                return None
            exp = [l[2] for l in ls]            # list heads in macrotile order
            pos = [seq.index(p) for p in exp if p in seq]
            return "yes" if len(pos) == len(exp) and pos == sorted(pos) else "no"
    if q in ("global_list", "lists_disjoint", "state_sum", "state_sum_ge", "state_sum_acc", "global_list_pages"):
        ls = state_lists(rd(k.d, k.name, ".tri.1.tadata.bin") or next((open_gz(p) for p in k.files(".*.tadata.bin")), None),
                         state_off(c))
        if not any(ls):
            return None
        if q in ("global_list", "global_list_pages"):
            g = ls[16] if len(ls) > 16 else None
            return None if not g else ("%d:page%d" % (g[1], g[2]) if q == "global_list" else g[1])
        if q == "lists_disjoint":
            # a list's pages are known only at its ends (head, tail): the ends are distinct
            ends = [p for l in ls[:16] if l for p in {l[2], l[3]}]
            return "yes" if len(ends) == len(set(ends)) else "no"
        s = sum(l[1] for l in ls[:16] if l)
        return s if q != "state_sum_acc" else ("no" if s <= int(pred if pred.isdigit() else 0) + 1 else "yes")
    if q in ("window_dwords", "zero_dwords", "zero_whole_tiles", "sign", "zero_dwords_between"):
        d = k.depth()
        if not d:
            return None
        f = depth_facts(c, d)
        if q == "window_dwords":
            return f["window"]
        if q == "zero_dwords":
            return f["zero"]
        if q == "zero_whole_tiles":
            return f["whole_zero_tiles"]
        if q == "zero_dwords_between":
            return f["zero"]
        if f["nonzero"] == 0:
            return "no"
        r = f["signed"] / f["nonzero"]
        return "yes" if r >= .95 else "no" if r == 0 else "mixed"
    if q in ("stored_index_based_rows_ge12", "stored_equals_index"):
        d = k.depth()
        if not d:
            return None
        r = index_rows(c, d)
        return r[0] if q.startswith("stored_index") else ("all_loaded_tiles" if r[0] == "yes" else r[0])
    if q == "overlap_value":
        d = k.depth()
        return overlap_value(c, d)[0] if d else None
    if q.startswith("kept_page"):
        kb = rd(k.d, k.name, ".kept.bin")
        if not kb:
            return None
        dw = dwords(kb)
        at = lambda off, n=0: dw[off // 4 + n] if len(dw) > off // 4 + n else 0
        if q == "kept_page1_w0":
            return "0x%08x" % at(0x1000)
        if q == "kept_page2_w0":
            return "0x%08x" % at(0x2000)
        if q == "kept_page3_w01":
            return "0x%08x,%d" % (at(0x3000), at(0x3004))
        if q == "kept_page3_w0_is_count_head":
            w0, w1 = at(0x3000), at(0x3004)
            return "yes" if w0 >> 16 == w1 and w0 & 0xffff == 1 else "no"
        if q == "kept_page2_w0_high":
            return "0x%04x" % (at(0x2000) >> 16)
    if q == "kept_at_render_end_has_store":
        a, b = rd(k.d, k.name, ".kept.1.bin"), rd(k.d, k.name, ".kept.bin")
        if not a or not b:
            return None
        return "yes" if a[0x3000:0x3008] == b[0x3000:0x3008] and any(b[0x3000:0x3008]) else "no"
    if q == "held_pages_exhausted":
        h = rd(k.d, k.name, ".held.regs.bin")
        if not h:
            return None
        regs = dict(re.findall(r"reg (0x[0-9a-f]{4}) (0x[0-9a-f]{8})", h.decode("latin-1")))
        return " ".join(f"{r}={regs.get(r)}" for r in ("0x0700", "0x0710", "0x0720", "0x0724", "0x0658", "0x0748"))
    if q == "kept_state_replaced":
        solo = cs.get("ow-part-solo")       # the kept owner's pages with no second context rendered
        a, b = rd(k.d, k.name, ".kept.bin"), rd(solo["dir"], "ow-part-solo", ".kept.bin") if solo else None
        if not a or not b:
            return None
        return "yes" if a[0x6000:0x7000] != b[0x6000:0x7000] else "no"
    if q in ("walk_same_as_control", "image_same_as_control"):
        ctl = cs.get("ow-fill-control-" + k.name.rsplit("-", 1)[1])
        if not ctl:
            return None
        ck = Case(ctl and "ow-fill-control-" + k.name.rsplit("-", 1)[1], ctl)
        if q == "walk_same_as_control":
            a, b = walk(k.dump("param", 2))[0], walk(ck.dump("param", 2))[0]
            return None if not a or not b else ("yes" if a == b else "no")
        a, b = render_lines(k.out), render_lines(ck.out)
        return None if not a or not b else ("yes" if a == b else "no")
    if q == "same_lists_as":
        o = cs.get(pred)
        if not o:
            return None
        la = state_lists(k.dump("tadata", 1), state_off(c))
        lb = state_lists(Case(pred, o).dump("tadata", 1), state_off(o))
        if not any(la) or not any(lb):
            return None
        cnt = lambda ls: [l[1] if l else 0 for l in ls]          # the structure: pages per list
        return pred if cnt(la) == cnt(lb) else "differs"
    if q == "lists_pages_differ_from":
        o = cs.get(pred)
        if not o:
            return None
        la = state_lists(k.dump("tadata", 1), state_off(c))
        lb = state_lists(Case(pred, o).dump("tadata", 1), state_off(o))
        return None if not any(la) or not any(lb) else ("yes" if la != lb else "no")
    return "not scored"


def hit(q, pred, obs):
    if obs is None:
        return "no data"
    if obs == "not scored":
        return "not scored"
    if pred == "?":
        return "explore"
    if q == "zero_dwords_between":
        lo, hi = map(int, pred.split("-"))
        return "hit" if lo <= obs <= hi else "miss"
    if q in ("state_sum_ge",):
        return "hit" if obs >= int(pred) else "miss"
    return "hit" if str(obs) == str(pred) else "miss"


def main(argv):
    if "--selftest" in argv:
        return selftest()
    rundir = argv[0]
    here = os.path.dirname(os.path.abspath(__file__))
    pred_path = argv[argv.index("--pred") + 1] if "--pred" in argv else os.path.join(here, "..", "predictions-declared.tsv")
    cs = load_cases(rundir)
    preds = [l.split("\t") for l in open(pred_path).read().splitlines()[1:]]
    tally = collections.defaultdict(lambda: collections.Counter())
    print("case\tset\tquantity\tpredicted\tobserved\tmodel\tresult")
    for case, q, v, model in preds:
        c = cs.get(case)
        if not c:
            continue
        k = Case(case, c)
        want, ref = (v.split("@", 1) + [v])[:2] if "@" in v else (v, v)
        try:
            obs = observe(cs, k, q, ref)
        except Exception as e:      # a malformed dump: reported, not fatal
            obs = None
            print(f"# {case} {q}: decoder error {type(e).__name__}: {e}", file=sys.stderr)
        res = hit(q, want, obs)
        tally[(model, c["set"])][res] += 1
        print("\t".join([case, c["set"], q, v, str(obs), model, res]))
    print("\n## tally by model and set (hit / miss / other)")
    for (model, st), cnt in sorted(tally.items()):
        print(f"{model}\t{st}\thit {cnt['hit']}\tmiss {cnt['miss']}\tother {sum(cnt.values()) - cnt['hit'] - cnt['miss']}")
    print("\n## depth cases: partial renders, sign, zero dwords, window (the table that settles Q107's sign)")
    for n, c in cs.items():
        if n.startswith(("dp-", "w4096")):
            k = Case(n, c)
            d = k.depth()
            if d:
                f = depth_facts(c, d)
                print(f"{n}\tP {c['P']}\tpartials {partials(k.tl)}\tzero {f['zero']}\twindow {f['window']}\tsigned {f['signed']}/{f['nonzero']}")
    # repeatability: cases named X-r1 / X-r2 (or X, X-rep): every observed quantity equal, else NR
    print("\n## repeatability (R: identical in the kept observables, NR: differs)")
    groups = collections.defaultdict(list)
    for n in cs:
        groups[re.sub(r"(-r\d+|-rep|-[ab])$", "", n)].append(n)
    for g, names in sorted(groups.items()):
        if len(names) < 2:
            continue
        sig = {}
        for n in names:
            k = Case(n, cs[n])
            sig[n] = (job1_status(k.out), partials(k.tl), tuple(k.ta3d(1)[35:40]) if k.ta3d(1) else None,
                      depth_facts(cs[n], k.depth())["zero"] if k.depth() else None)
        print(("R" if len(set(sig.values())) == 1 else "NR"), g, len(names), "runs", sig if len(set(sig.values())) > 1 else "")
    return 0


# ------------------------------------------------------------------ selftest
def selftest():
    # state list decode, page table walk, ZLS address rule against E465's window arithmetic, plane/overlap
    param = bytearray(0x424000 + 0x1000)
    pages = [3, 4, 5, 1, 2]            # free list order after a toy job on 5 pages
    for i, p in enumerate(pages):
        prev = pages[i - 1] if i else 0xffff
        nxt = pages[i + 1] if i + 1 < len(pages) else 0xffff
        struct.pack_into("<I", param, 0x423000 + 4 * p, prev << 16 | nxt)
    seq, ok = walk(bytes(param))
    assert seq == pages and ok, (seq, ok)
    ta = bytearray(0x7000)
    struct.pack_into("<II", ta, 0x6000 + 8 * 1, 2 << 16 | 9, 0xa)
    struct.pack_into("<II", ta, 0x6000 + 8 * 16, 1 << 16 | 1, 1)
    ls = state_lists(bytes(ta), 0x6000)
    assert ls[1] == (1, 2, 9, 0xa) and ls[16] == (16, 1, 1, 1) and ls[0] is None
    assert zls_addr(0, 0, 1) == 0 and zls_addr(32, 0, 1) == 512 and zls_addr(0, 16, 1) == 1024
    assert sorted(tile_index(x, y) for y in range(16) for x in range(32)) == list(range(512))
    tl = "timeline: regs 0x0654 0x0658 0x0660 samples 5 seconds 1 start 0 end 9 rc 0\ntl 0 0 0 0\ntl 5 0 1 0\ntl 6 0 0 0\ntl 7 0 1 0\ntl 8 0 0 0\n"
    assert partials(tl) == 2
    v = [(0.0, 0.0, 0.25), (10.0, 0.0, 0.75), (0.0, 10.0, 0.25)]
    assert abs(plane(v)(5, 0) - 0.5) < 1e-9 and inside(v, 2, 2) and not inside(v, 9, 9)
    c = dict(args="tri --width 64 --height 64 --depth --depth-ctl 0x0017100c", dir=".")
    assert depth_facts(c, [FILL] * 10 + [0, 0, 0x80000001, 5])["zero"] == 2
    # a synthetic run: two renders on 5 pages, job 2 takes the head pages of the list job 1 left
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, "free-safe")
        os.makedirs(d)
        name = "toy"
        open(os.path.join(d, "cases.tsv"), "w").write(
            "name\tscript\tset\trisk\tP\tknobs\trt\targs\n"
            f"{name}\tfree-safe\tfit\tsafe\t0x422\t\t-\ttri --width 64 --height 64 -n 2 --depth --depth-ctl 0x0017100c\n")
        def put(suffix, data):
            with gzip.open(os.path.join(d, name + suffix + ".gz"), "wb") as f:
                f.write(data)
        p1 = bytearray(0x464000)
        for pg in (1, 2):                       # job 1 wrote pages 1 and 2 (non-zero content)
            p1[pg * 4096] = 7
        def table(pb, order):
            for i, pg in enumerate(order):
                prev = order[i - 1] if i else 0xffff
                nxt = order[i + 1] if i + 1 < len(order) else 0xffff
                struct.pack_into("<I", pb, 0x423000 + 4 * pg, prev << 16 | nxt)
        table(p1, [3, 4, 5, 1, 2])
        p2 = bytearray(p1)
        for pg in (3, 4):                       # job 2 wrote the head pages 3 and 4
            p2[pg * 4096] = 9
        table(p2, [5, 1, 2, 3, 4])
        put(".tri.1.param.bin", bytes(p1))
        put(".tri.2.param.bin", bytes(p2))
        put(".txt", b"job: ok\ntri 64x64 #1: 1062 triangle, 3034 background, 0 other; x\n")
        dep = [FILL] * 4096
        dep[0:3] = [0, 0, 0x80000000 | 0x3f000000]
        put(".depth.1.bin", struct.pack("<4096I", *dep))
        cs = load_cases(td)
        k = Case(name, cs[name])
        assert observe(cs, k, "walk_ok", "yes") == "yes"
        assert observe(cs, k, "job2_is_head_prefix", "yes") == "yes"
        assert observe(cs, k, "job1_pages", "") == "1-2"
        assert observe(cs, k, "zero_dwords", "") == 2 and observe(cs, k, "sign", "") == "yes"
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
