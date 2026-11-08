#!/usr/bin/env python3
"""Q111: the event-timelines outputs, recomputed from the kept gz files only. python3 -B
recompute_events.py DIR/event-timelines. Per kind (tri64, fill, tri256n3, copy, zstore, partial,
idle) and register set (r2: 0x0118 0x012c; r7: five more): over the jobs the bits of CR_EVENT_STATUS
(0x012c) and CR_EVENT_STATUS2 (0x0118) seen to change, in how many jobs, the width of each pulse
(time between a bit rising and falling, a sample interval at least), the number of pulses a job, and the
order of first rises."""
import collections, gzip, pathlib, re, statistics, sys

d = pathlib.Path(sys.argv[1])
BASE12C, BASE118 = 0x20000000, 0x400
names = {31: "MASTER_INTERRUPT", 29: "TIMER", 28: "TA_DPM_FAULT", 26: "MADD_CACHE_INVALCOMPLETE",
         25: "DPM_OUT_OF_MEMORY_ZLS", 24: "DPM_TA_MEM_FREE", 23: "ISP_END_TILE", 22: "DPM_INITEND",
         21: "ISP2_ZLS_CSW_FINISHED", 20: "OTPM_INV", 19: "OTPM_FLUSHED", 18: "PIXELBE_END_RENDER",
         16: "ISP_VISIBILITY_FAIL", 15: "BREAKPOINT", 14: "SW_EVENT", 13: "TA_FINISHED", 12: "TA_TERMINATE",
         11: "TPC_CLEAR", 10: "TPC_FLUSH", 9: "DPM_CONTROL_CLEAR", 8: "DPM_CONTROL_LOAD", 7: "DPM_CONTROL_STORE",
         6: "DPM_STATE_CLEAR", 5: "DPM_STATE_LOAD", 4: "DPM_STATE_STORE", 3: "DPM_REACHED_MEM_THRESH",
         2: "DPM_OUT_OF_MEMORY_GBL", 1: "DPM_OUT_OF_MEMORY_MT", 0: "DPM_3D_MEM_FREE"}
names2 = {0: "DPM_TA_FREE_LOAD", 1: "DPM_3D_FREE_LOAD", 2: "DPM_HOST_FREE_LOAD", 3: "DPM_DHOST_FREE_LOAD",
          5: "TRIG_DL", 6: "TRIG_3D", 7: "TRIG_TA", 8: "GSG_LOADED", 9: "GSG_FLUSHED", 10: "DCU_INVAL_COMPLETE",
          11: "OTPM_FLUSHED_INV", 12: "OTPM_MEM_CLEARED", 13: "VDM_TASK_KICKED", 14: "VDM_CONTEXT_LOAD",
          15: "MTE_STATE_FLUSHED"}
kinds = collections.defaultdict(list)
for f in sorted(d.glob("tl-*.txt.gz")):
    m = re.match(r"tl-([a-z0-9]+)-(r2|r7)-(\d+)", f.name)
    if not m:
        continue
    txt = gzip.open(f).read().decode("utf-8", "replace")
    hdr = next((l for l in txt.splitlines() if l.startswith("timeline:")), None)
    if not hdr:
        print(f.name, "no timeline"); continue
    regs = [t for t in hdr.split() if t.startswith("0x")]
    rows = [l.split()[1:] for l in txt.splitlines() if l.startswith("tl ")]
    h = hdr.split()
    smp = int(h[h.index("samples") + 1]); st = int(h[h.index("start") + 1]); en = int(h[h.index("end") + 1])
    dt = (en - st) / max(smp, 1)
    kinds[(m[1], m[2])].append(dict(name=f.name, regs=regs, rows=rows, dt=dt, start=st))

def ev(job, idx_reg, base, nm):
    """pulses of each bit of register idx_reg: list of (bit, t_rise, width)."""
    out = []
    reg = job["regs"].index(idx_reg)
    prev = base
    rise = {}
    for r in job["rows"]:
        t, vals = int(r[0]), [int(x, 16) for x in r[1:]]
        v = vals[reg]
        ch = v ^ prev
        for b in range(32):
            if ch >> b & 1:
                if v >> b & 1:
                    rise[b] = t
                elif b in rise:
                    out.append((b, rise.pop(b) - job["start"], t - rise_t(rise, b, t)))
        prev = v
    return out

def pulses(job, idx_reg, base):
    out, rise, prev = [], {}, base
    reg = job["regs"].index(idx_reg)
    for r in job["rows"]:
        t, v = int(r[0]), int(r[1 + reg], 16)
        ch = v ^ prev
        for b in range(32):
            if ch >> b & 1:
                if v >> b & 1:
                    rise[b] = t
                elif b in rise:
                    out.append((b, rise.pop(b), t - 0))
                    out[-1] = (b, out[-1][1] - job["start"], t - (out[-1][1]))
        prev = v
    for b, t in rise.items():
        out.append((b, t - job["start"], None))   # still set at the end of the timeline
    return out

for (kind, rs), jobs in sorted(kinds.items()):
    print("== %s %s: %d jobs, sample interval %.2f us" % (kind, rs, len(jobs), statistics.mean(j["dt"] for j in jobs) / 1000))
    for reg, base, nm in (("0x012c", BASE12C, names), ("0x0118", BASE118, names2)):
        seen = collections.defaultdict(list)
        npl = []
        order = collections.Counter()
        for j in jobs:
            p = pulses(j, reg, base)
            npl.append(len(p))
            for (b, t, w) in p:
                seen[b].append((t, w))
            first = []
            for (b, t, w) in sorted(p, key=lambda x: x[1]):
                if b not in first:
                    first.append(b)
            order[tuple(first)] += 1
        print("  %s: pulses a job min %d max %d" % (reg, min(npl), max(npl)))
        for b in sorted(seen, reverse=True):
            js = {i for i, j in enumerate(jobs) if any(x[0] == b for x in pulses(j, reg, base))}
            ws = [w for (_t, w) in seen[b] if w is not None]
            held = sum(1 for (_t, w) in seen[b] if w is None)
            print("    bit %2d %-26s in %2d of %2d jobs, %3d pulses, width us min %s median %s max %s%s" % (
                b, nm.get(b, "?"), len(js), len(jobs), len(seen[b]),
                "%.1f" % (min(ws) / 1000) if ws else "-", "%.1f" % (statistics.median(ws) / 1000) if ws else "-",
                "%.1f" % (max(ws) / 1000) if ws else "-", ", %d still set at the end" % held if held else ""))
        for o, n in order.most_common(4):
            print("    first-rise order x%d: %s" % (n, " ".join(str(b) for b in o)))
