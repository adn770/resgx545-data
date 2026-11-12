#!/usr/bin/env python3
"""F9 (round 6 dpm offline stage, exploratory, no verdict): F5's replay of the 1500-vertex scene
with partial renders, against the kept counts and run peaks at 2048x2048 (R3-geo g-c4 the fit
side named by the plan, g-d36 and R5-dpm d-t the rest; all seen before, so nothing is held out).
Rules tried, written before the comparison: a page request (a stream block's page or a global
page) above the threshold is refused and starts a partial render; the render keeps the global
pages that hold objects the TA has written and not yet tiled, the object under way included
(objects t .. t + lag, lag 3 from F5), and frees every other page; the streams restart (each
region opens a new block at its next entry); the threshold after the first render is thr0 +
0x20 when the kept job's dword 38 reads the raise, else thr0 (the job's own reading, not a
model).  Read-only, public data."""
import gzip, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import f5lib as F
from r6lib import jobs, scene_of, load, stretches, hi

LAG = 3
STAGES = {('closing-r3-geo', 'g-c4'), ('closing-r3-geo', 'g-d36'), ('closing-r5-dpm', 'a2/d-t'),
          ('closing-r5-dpm', 'a2/d-a1'), ('closing-r5-dpm', 'a2/d-a2'), ('closing-r2-geo', 'g-c3')}


def run(ents, thr0, raised, w=2048, h=2048):
    gk = {F.bk(k): k for k in range(2, 12)}
    writes = {}
    for b in range(F.OBJS):
        writes.setdefault(max(0, b - LAG), []).append(b)
    used, mtb = {}, {}
    pages, gpages, written = 1, [0], 0      # gpages: first object index of each global page
    thr, peaks, parts = thr0, [], 0
    def render(t):
        nonlocal pages, used, mtb, thr, parts
        peaks.append(pages); parts += 1
        last = written - 1
        keep = sum(1 for i, g0 in enumerate(gpages)
                   if (gpages[i + 1] if i + 1 < len(gpages) else F.OBJS) > t and g0 <= last)
        pages = max(1, keep); used, mtb = {}, {}
        if parts == 1 and raised:
            thr = thr0 + 0x20
        return parts < 40
    for t in range(F.OBJS):
        for b in writes.get(t, []):
            if b in gk:
                if pages + 1 > thr and not render(t):
                    return None
                pages += 1; gpages.append(b)
            written = b + 1
        for c, r, dw in ents[t]:
            dw += 1 if t in gk else 0
            if (c, r) not in used or used[(c, r)] + dw > F.CAP:
                used[(c, r)] = 0
                m = F.mtile(w, h, c, r); nb = mtb.get(m, 0)
                if nb % F.BPP == 0:
                    if pages + 1 > thr:
                        if not render(t):
                            return None
                        used[(c, r)] = 0; nb = 0
                    pages += 1
                mtb[m] = nb + 1
            used[(c, r)] += dw
    peaks.append(pages)
    return parts, peaks


def main():
    ents = F.entries(2048, 2048)
    n_ok = p_ok = last_ok = tot = 0
    for ds, stg, name, d, m in jobs():
        if (ds, stg) not in STAGES:
            continue
        args = m.get('args', ''); wh, sc = scene_of(args)
        if wh != '2048x2048' or sc != 'tri1500':
            continue
        cols, tl = load(f'{d}/{name}.txt.gz')
        if not tl or any(r not in tl[0][1] for r in (0x724, 0x658, 0x624)):
            continue
        st = stretches(tl)
        if not st:
            continue
        thr0 = tl[st[0][0]][1][0x624] & 0xffff
        bp = f'{d}/{name}.after.buf09.bin.gz'
        if not os.path.exists(bp):
            continue
        raised = struct.unpack_from('<I', gzip.open(bp).read(), 152)[0] == 0x20
        bounds = [(1, st[0][0])] + [(st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(tl)) for k in range(len(st))]
        peaks = [max(hi(tl[i][1], 0x724) for i in range(a, e)) for a, e in bounds if e > a]
        rp = run(ents, thr0, raised)
        tot += 1
        okn = rp is not None and rp[0] == len(st)
        n_ok += okn; p_ok += okn and rp[1] == peaks; last_ok += okn and rp[1][-1] == peaks[-1]
        print('%-34s thr0 %#x %s read %d %s | replay %s %s' % (f'{ds[8:]}/{stg}/{name}', thr0, 'R' if raised else 'N', len(st),
              ' '.join('%x' % p for p in peaks), rp[0] if rp else None, ' '.join('%x' % p for p in rp[1]) if rp else ''))
    print('exploratory: count %d of %d, every run peak %d, last run peak %d' % (n_ok, tot, p_ok, last_ok))


if __name__ == '__main__':
    main()
