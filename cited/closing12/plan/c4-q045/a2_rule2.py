#!/usr/bin/env python3
"""FROZEN rule A2 (v2: identical rule, only truncated timeline rows skipped; v1 crashed before output) (Q045 b), round 12 helper c4. Run: python -I a2_rule.py > a2_rule.out

Functions timeline/runs/ctl/state_page copied from
/Users/jtorra/src/resgx545-data/vdm/verification-1141ta/recompute/dpm_raise.py (file-name suffixes
adapted to the closing sessions: '<stem>.<probe>.tadata.bin.gz', timeline in '<stem>.txt.gz').

RULE A2: for a RAISED job (TA3DCtl dword 38 == 0x20 in <stem>.ta3d.1.bin.gz, else
<stem>.after.buf09.bin.gz, first 236 bytes as 59 LE dwords), with a state page at 0x42000
(tri width >= 4096, width from 'tri WxH' in <stem>.txt.gz) else 0x6000 (136 bytes, 34 dwords):
    S = sum(page[2*i] >> 16 for i in 0..15);  P = peaks[-1] (max status & 0xffff of the last TA run,
    runs() as in dpm_raise.py).   PREDICTION: S == P - 1.
RIVALS scored on the same rows: R1 S == P; R2 S == P - 2; R3 S == L where L = pages of the last TA
run = P - (status & 0xffff at the first non-partial-render sample of the last TA run).
PASS CRITERION: A2 holds on a row iff S == P - 1. Verdict on raised rows: HELD if every scored row
passes; REFUTED if any raised row with a state page misses; rows without width, timeline or state
page are 'cannot tell'. Unraised rows (dword 38 != 0x20) scored separately (E627's split), shown
for the same equation and rivals, not part of the verdict. Jobs w/o a ctl dump: cannot tell.
"""
import os, re, sys, glob, gzip, struct, collections
D = os.path.expanduser('~/src/resgx545-data/render')
SESS = ['closing-r5-dpm', 'closing-r6-dpm', 'closing-r7-dpm', 'closing-r8-dpm', 'closing-r9-dpm',
        'closing-r10-dpm', 'closing-r8-ldpm', 'closing-r9-ldpm',
        'closing-r1-pixgeo', 'closing-r2-geo', 'closing-r3-geo', 'closing-r3-geo-c']

def timeline(path):
    t = gzip.open(path, 'rt', errors='replace').read()
    m = re.search(r'^timeline: regs (.*?) samples', t, re.M)
    if not m: return None, t
    regs = m[1].split()
    rows = [[int(x, 0) if i == 0 else int(x, 16) for i, x in enumerate(l.split()[1:])]
            for l in t.splitlines() if l.startswith('tl ')]
    rows = [r for r in rows if len(r) == len(regs) + 1]  # drop truncated rows (v2 parser fix)
    return (regs, rows), t

def runs(regs, rows):
    ip, ist = regs.index('0x0658') + 1, regs.index('0x0724') + 1
    prs, peaks, cur, inpr = [], [], 0, False
    first = [None]  # status at first non-PR sample of each TA run
    for r in rows:
        if r[ip] & 1:
            if not inpr:
                prs.append(r[ist] & 0xffff); peaks.append(cur); cur = 0; inpr = True
                first.append(None)
            continue
        inpr = False
        if first[-1] is None: first[-1] = r[ist] & 0xffff
        cur = max(cur, r[ist] & 0xffff)
    peaks.append(cur)
    return prs, peaks, first

def ctl(d, n):
    for suf in ('.ta3d.1.bin.gz', '.after.buf09.bin.gz'):
        p = f'{d}/{n}{suf}'
        if os.path.exists(p):
            b = gzip.open(p).read()
            if len(b) >= 236: return struct.unpack('<59I', b[:236])
    return None

def state_page(p, width):
    b = gzip.open(p).read(); off = 0x42000 if width >= 4096 else 0x6000
    if off + 136 <= len(b): return struct.unpack('<34I', b[off:off + 136])
    return None

def main():
    res = {'raised': collections.Counter(), 'unraised': collections.Counter()}
    sess = collections.defaultdict(collections.Counter)
    miss = []; cant = collections.Counter()
    for s in SESS:
        base = f'{D}/{s}/out'
        if not os.path.isdir(base): cant[(s, 'no dir')] += 1; continue
        for p in sorted(glob.glob(base + '/**/*tadata.bin.gz', recursive=True)):
            d, f = os.path.dirname(p), os.path.basename(p); n = f.split('.')[0]
            tp = f'{d}/{n}.txt.gz'
            if not os.path.exists(tp): cant[(s, 'no txt')] += 1; continue
            tl, t = timeline(tp)
            if not tl: cant[(s, 'no timeline')] += 1; continue
            prs, peaks, first = runs(*tl)
            w = ctl(d, n)
            if w is None: cant[(s, 'no ctl')] += 1; continue
            m = re.search(r'tri (\d+)x\d+', t)
            if not m: cant[(s, 'no width')] += 1; continue
            sp = state_page(p, int(m[1]))
            if not sp: cant[(s, 'no state page')] += 1; continue
            raised = w[38] == 0x20; key = 'raised' if raised else 'unraised'
            S = sum(sp[2 * i] >> 16 for i in range(16)); P = peaks[-1]
            L = P - first[-1] if first[-1] is not None else None
            c = res[key]; c['n'] += 1
            c['A2 S==P-1'] += S == P - 1; c['R1 S==P'] += S == P; c['R2 S==P-2'] += S == P - 2
            c['R3 S==L'] += (L is not None and S == L)
            sess[(s, key)]['n'] += 1; sess[(s, key)]['A2'] += S == P - 1
            if raised and S != P - 1: miss.append((s, n, S, P, L))
    for k, c in res.items(): print(k, dict(c))
    for k, c in sorted(sess.items()): print(k, dict(c))
    print('cannot tell', dict(cant))
    print('raised misses (session, job, S, P, L):', len(miss))
    for m in miss[:40]: print('  ', m)
    r = res['raised']
    print('VERDICT', 'HELD' if r['n'] and r['n'] == r['A2 S==P-1'] else 'REFUTED' if r['n'] else 'NO DATA')

if __name__ == '__main__': main()
