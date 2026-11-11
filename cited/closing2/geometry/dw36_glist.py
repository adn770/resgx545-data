#!/usr/bin/env python3
"""Offline test of "TA3DCtl dword 36 = global-list pages - 2" on every 4096x4096 job with a kept
control block and TA-data dump (S1 g-e1, S1b g-e1, E630 wd-glist, E704 dpm-oom).  Read-only.

Per job: dwords 34..40 of buf09, the state page's 17 lists (count, head, tail) at TA-data offset
0x42000 (E627's 4096x4096 offset), the sum of the macrotile counts, the global list's count, and
the partial-render count / run peaks from the kept timeline when there is one.
"""
import sys, pathlib, gzip, struct, re, collections
sys.dont_write_bytecode = True

STATE_OFF = 0x42000  # 4096x4096 (E627); 0x6000 at 1024x768


def gz(p):
    return gzip.open(p).read() if p.exists() else None


def dwords(b):
    return list(struct.unpack("<%dI" % (len(b) // 4), b[: len(b) // 4 * 4]))


def state_lists(tadata, off=STATE_OFF):
    d = dwords(tadata[off:off + 0x88]) if tadata and len(tadata) >= off + 0x88 else []
    out = []
    for i in range(17):
        w0, w1 = d[2 * i], d[2 * i + 1]
        out.append((i, w0 >> 16, w0 & 0xffff, w1) if (w0 or w1) else None)
    return out


def timeline(text):
    m = re.search(r"^timeline: regs (.*?) samples", text or "", re.M)
    if not m:
        return None
    regs = m[1].split()
    rows = [[int(x, 0) if i == 0 else int(x, 16) for i, x in enumerate(ln.split()[1:])]
            for ln in text.splitlines() if ln.startswith("tl ")]
    return regs, rows


def runs(tl):
    regs, rows = tl
    if "0x0658" not in regs or "0x0724" not in regs:
        return None, None
    ip, ist = regs.index("0x0658") + 1, regs.index("0x0724") + 1
    prs, peaks, cur, inpr = [], [], 0, False
    for r in rows:
        if r[ip] & 1:
            if not inpr:
                prs.append(r[ist] & 0xffff); peaks.append(cur); cur = 0; inpr = True
            continue
        inpr = False
        cur = max(cur, r[ist] & 0xffff)
    peaks.append(cur)
    return prs, peaks


def jobs(d, pat):
    d = pathlib.Path(d)
    names = sorted({p.name.split(".")[0] for p in d.glob("*.after.buf09.bin.gz") if re.match(pat, p.name)})
    for n in names:
        b = gz(d / f"{n}.after.buf09.bin.gz")
        if not b or len(b) < 236:
            continue
        cb = list(struct.unpack("<59I", b[:236]))
        td = next((gz(p) for p in d.glob(f"{n}.*tadata.bin.gz")), None)
        txt = gz(d / f"{n}.txt.gz")
        txt = txt.decode(errors="replace") if txt else ""
        yield n, cb, td, txt


def main():
    srcs = [
        ("S1", pathlib.Path.home() / "src/resgx545-data/render/closing-s1/out/g-e1", r".*"),
        ("S1b", pathlib.Path.home() / "src/resgx545-data/render/closing-s1b/out/g-e1", r".*"),
        ("E630", pathlib.Path.home() / "src/resgx545-data/dpm/partial-model-batch/dumps/wide-safe.c1", r"wd-glist.*"),
        ("E704", pathlib.Path.home() / "src/resgx545-data/vdm/verification-1141ta/out-hw/p1141ta-dumps/dpm-oom-all", r"oom-.*"),
    ]
    rows = []
    for tag, d, pat in srcs:
        for n, cb, td, txt in jobs(d, pat):
            ls = state_lists(td) if td else None
            g = ls[16] if ls else None
            msum = sum(l[1] for l in ls[:16] if l) if ls else None
            nlists = sum(1 for l in ls[:16] if l) if ls else None
            tl = timeline(txt)
            prs, peaks = runs(tl) if tl else (None, None)
            m = re.search(r"--vertices (\d+)", txt)
            V = int(m[1]) if m else None
            rows.append(dict(tag=tag, n=n, V=V, dw=cb[34:41], g=g, msum=msum, nlists=nlists, prs=prs, peaks=peaks, ls=ls))
    print(f"{'src':5} {'job':18} {'V':>5} {'dw35':>5} {'dw36':>4} {'dw37':>7} {'dw38':>4} {'dw39':>4} | glist(cnt,head,tail) {'msum':>5} {'nl':>3} | parts peaks")
    hits = collections.Counter()
    for r in rows:
        dw = r["dw"]
        g = r["g"]
        gs = f"({g[1]},{g[2]:#x},{g[3]:#x})" if g else ("-" if r["ls"] is not None else "no dump")
        parts = len(r["prs"]) if r["prs"] is not None else "-"
        peaks = [hex(p) for p in r["peaks"]] if r["peaks"] else "-"
        print(f"{r['tag']:5} {r['n']:18} {str(r['V']):>5} {dw[1]:#5x} {dw[2]:4d} {dw[3]:#7x} {dw[4]:#4x} {dw[5]:4d} | {gs:>18} {str(r['msum']):>5} {str(r['nlists']):>3} | {parts} {peaks}")
        if g:
            hits["dw36 == gcount-2"] += dw[2] == g[1] - 2
            hits["dw36 == gcount-1"] += dw[2] == g[1] - 1
            hits["dw36 == gcount"] += dw[2] == g[1]
            hits["dw36 == nlists"] += dw[2] == r["nlists"]
            hits["dw36 == parts"] += (r["prs"] is not None and dw[2] == len(r["prs"]))
            hits["dw36 == parts+1"] += (r["prs"] is not None and dw[2] == len(r["prs"]) + 1)
            hits["jobs with a global list"] += 1
    print()
    for k, v in hits.items():
        print(f"{k}: {v}")
    print("\nglobal lists in full (idx 16) and the macrotile lists per job:")
    for r in rows:
        if r["ls"]:
            print(r["tag"], r["n"], "dw36", r["dw"][2], "lists:", [(l[0], l[1]) for l in r["ls"] if l])


if __name__ == "__main__":
    main()
