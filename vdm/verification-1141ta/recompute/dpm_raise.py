#!/usr/bin/env python3
"""p1141/ta dpm_raise.py: re-score 'the raise is the second out-of-memory event' on PMB timelines.

Rule R2: raised (control block dword 38 == 0x20) iff the TA run after the first partial render
reaches a page status >= thr0 (thr0 = status when the first partial render starts).
Own parser.  Groups: DEFAULT-TRI = scripts of E625's fit (trig, free, state, depth with the default
triangle, followup-a); others are scenes E625 did not fit (ramp, ov, wide, owner, poked).  Honest
status: R2 was formed after the author looked at tg-1024-n-0x28, so even the 'other' groups are held
out of E625's rule only, not of R2's form.  Also prints the state-page check (A2): sum of the 16
macrotile list counts == last-run peak - 1 for raised jobs.
Usage: python3 dpm_raise.py [-v]
"""
import os, re, sys, glob, gzip, struct, collections
D = os.path.expanduser(os.environ.get('DATA', '~/src/resgx545-data/dpm/partial-model-batch/dumps'))

def timeline(path):
    t = gzip.open(path, 'rt', errors='replace').read()
    m = re.search(r'^timeline: regs (.*?) samples', t, re.M)
    if not m: return None
    regs = m[1].split()
    rows = [[int(x, 0) if i == 0 else int(x, 16) for i, x in enumerate(l.split()[1:])]
            for l in t.splitlines() if l.startswith('tl ')]
    return regs, rows

def runs(regs, rows):
    """-> list of (start_status_of_each_PR, peak of each TA run between PRs)"""
    ip, ist = regs.index('0x0658') + 1, regs.index('0x0724') + 1
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

def ctl(d, n):
    for suf in ('.ta3d.1.bin.gz', '.after.buf09.bin.gz'):
        p = f'{d}/{n}{suf}'
        if os.path.exists(p):
            b = gzip.open(p).read()
            return struct.unpack('<59I', b[:236])
    return None

def state_page(d, n, width):
    for suf in ('.tri.1.tadata.bin.gz', '.tri.tadata.bin.gz'):
        p = f'{d}/{n}{suf}'
        if os.path.exists(p):
            b = gzip.open(p).read(); off = 0x42000 if width >= 4096 else 0x6000
            if off + 136 <= len(b): return struct.unpack('<34I', b[off:off + 136])
    return None

def main():
    verbose = '-v' in sys.argv
    tab = collections.defaultdict(lambda: [0, 0]); miss = []
    sp = [0, 0, collections.Counter()]
    for cs in sorted(glob.glob(D + '/*/cases.tsv')):
        d = os.path.dirname(cs); grp = os.path.basename(d).split('.')[0]
        hdr = None
        for l in open(cs):
            f = l.rstrip('\n').split('\t')
            if hdr is None: hdr = f; continue
            c = dict(zip(hdr, f)); n = c['name']; tp = f'{d}/{n}.txt.gz'
            if not os.path.exists(tp): continue
            tl = timeline(tp)
            if not tl: continue
            prs, peaks = runs(*tl)
            w = ctl(d, n)
            if not prs or w is None: continue
            thr0 = prs[0]; raised = w[38] == 0x20
            pred = len(peaks) > 1 and peaks[1] >= thr0
            scene = 'wide' if n.startswith('wd-') else 'ov' if n.startswith('ov-') else \
                    'ramp' if 'ramp' in n else 'owner' if grp.startswith('owner') else 'default-tri'
            key = (scene, 'E625-fit-script' if grp.split('-')[0] in ('trig', 'free', 'state', 'depth', 'followup') and scene == 'default-tri' else 'other-script')
            tab[key][0] += 1; tab[key][1] += pred == raised
            if pred != raised: miss.append((n, hex(thr0), [hex(p) for p in peaks[:3]], raised, hex(w[36])))
            m = re.search(r'--width (\d+)', c['args']); wd = int(m[1]) if m else 64
            s = state_page(d, n, wd)
            if s and raised:
                tot = sum(s[2 * i] >> 16 for i in range(16)); sp[0] += 1
                sp[1] += tot == peaks[-1] - 1; sp[2][tot - (peaks[-1] - 1)] += 1
    n = sum(v[0] for v in tab.values()); r = sum(v[1] for v in tab.values())
    print(f'R2 overall {r}/{n}')
    for k, v in sorted(tab.items()): print(f'  {k}: {v[1]}/{v[0]}')
    print('misses', miss)
    print(f'state page sum == last peak - 1 (raised jobs with a state page): {sp[1]}/{sp[0]}  diffs {dict(sp[2])}')

if __name__ == '__main__': main()
