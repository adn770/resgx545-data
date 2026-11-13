# POST HOC (after a2_rule2 scored): split by whether the page at the rule's offset is all zero.
import sys, os, re, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a2_rule2 as R
c = collections.Counter(); rows = []
for s in R.SESS:
    for p in sorted(glob.glob(f'{R.D}/{s}/out/**/*tadata.bin.gz', recursive=True)):
        d, f = os.path.dirname(p), os.path.basename(p); n = f.split('.')[0]
        tp = f'{d}/{n}.txt.gz'
        if not os.path.exists(tp): continue
        tl, t = R.timeline(tp)
        if not tl: continue
        prs, peaks, first = R.runs(*tl); w = R.ctl(d, n); m = re.search(r'tri (\d+)x\d+', t)
        if w is None or not m: continue
        sp = R.state_page(p, int(m[1]))
        if not sp: continue
        key = ('raised' if w[38] == 0x20 else 'unraised', 'zero page' if not any(sp) else 'nonzero page')
        S = sum(sp[2*i] >> 16 for i in range(16)); P = peaks[-1]
        c[key + ('n',)] += 1; c[key + ('A2',)] += S == P - 1
        if key == ('raised', 'nonzero page'): rows.append((s, n, int(m[1]), S, P))
for k, v in sorted(c.items()): print(k, v)
for r in rows: print(r)
