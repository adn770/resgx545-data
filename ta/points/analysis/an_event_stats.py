"""Q111 numbers for E547: per kind (r2 and r7 merged, 10 jobs a kind) the jobs of ten in which each bit rose and fell and
its pulse widths, and the jobs with SW_EVENT that also show MASTER_INTERRUPT. Reads only data/event-timelines."""
import collections, gzip, pathlib, re
d = pathlib.Path("data/event-timelines")
kinds = collections.defaultdict(list)
for f in sorted(d.glob("tl-*.txt.gz")):
    m = re.match(r"tl-([a-z0-9]+)-(r2|r7)-(\d+)", f.name)
    t = gzip.open(f).read().decode()
    hdr = next(l for l in t.splitlines() if l.startswith("timeline:")).split()
    regs = [x for x in hdr if x.startswith("0x")]
    rows = [l.split()[1:] for l in t.splitlines() if l.startswith("tl ")]
    kinds[m[1]].append((regs, rows))
def pulses(regs, rows, reg, base):
    out, rise, prev = [], {}, base
    i = regs.index(reg)
    for r in rows:
        t, v = int(r[0]), int(r[1 + i], 16)
        for b in range(32):
            if (v ^ prev) >> b & 1:
                if v >> b & 1: rise[b] = t
                elif b in rise: out.append((b, t - rise.pop(b)))
        prev = v
    return out
S12C = {0: "DPM_3D_MEM_FREE", 1: "DPM_OUT_OF_MEMORY_MT", 5: "DPM_STATE_LOAD", 6: "DPM_STATE_CLEAR", 9: "DPM_CONTROL_CLEAR", 10: "TPC_FLUSH",
        12: "TA_TERMINATE", 13: "TA_FINISHED", 14: "SW_EVENT", 18: "PIXELBE_END_RENDER", 26: "MADD_CACHE_INVALCOMPLETE", 31: "MASTER_INTERRUPT"}
S118 = {0: "DPM_TA_FREE_LOAD", 12: "OTPM_MEM_CLEARED"}
for kind in ("idle", "fill", "copy", "tri64", "tri256n3", "zstore", "partial"):
    for reg, base, nm in (("0x012c", 0x20000000, S12C), ("0x0118", 0x400, S118)):
        inj = collections.Counter(); w = collections.defaultdict(list); npl = []
        for regs, rows in kinds[kind]:
            p = pulses(regs, rows, reg, base); npl.append(len(p))
            for b in {x[0] for x in p}: inj[b] += 1
            for b, ww in p: w[b].append(ww / 1000)
        print(kind, reg, "jobs", len(kinds[kind]), "pulses a job", min(npl), "to", max(npl), "; " + ", ".join(
            "%s %d (%.1f-%.1f us)" % (nm.get(b, b), inj[b], min(w[b]), max(w[b])) for b in sorted(inj, reverse=True)))
tot = both = 0
for kind, js in kinds.items():
    for regs, rows in js:
        a = {b for b, _ in pulses(regs, rows, "0x012c", 0x20000000)}
        if 14 in a: tot += 1; both += (31 in a)
print("jobs with SW_EVENT", tot, "of which with MASTER_INTERRUPT", both)
