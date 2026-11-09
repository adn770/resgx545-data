#!/usr/bin/env python3
"""recompute_1141ta.py DIR TABLE [--pred predictions-declared.tsv]: score one run directory, independent of the
run scripts (run_table_ta.sh only keeps raw files).  DIR holds cases.tsv, NAME.txt.gz, NAME.after.buf09.bin.gz,
NAME.param.bin.gz, NAME.tadata.bin.gz, kernel.log (as run_table_ta.sh writes them).  Prints, per model of
predictions-declared.tsv, right/total over the cases whose prediction is not '?'.  Imports the sibling
scratch modules vdm_counter (not needed), dpm_raise (timeline), q164_fate (vertex fate), o4_parity (decode)
only for parsers.  TABLE: vdm-series-a, vdm-series-b, capacity, capacity-rows, dpm-oom, dpm-stack, dpm-hang,
eot-store, eot-globals, o4-g25.   numpy not needed.
"""
import collections, gzip, os, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FAIL = re.compile(r'failed|faulted|hung|rejected|FAILED')
def cases(d):
    hdr, out = None, []
    cand = [os.path.join(d, 'cases.tsv'), os.path.join(d, '..', 'cases.tsv'), os.path.join(d, '..', '..', 'cases.tsv')]
    path = next(p for p in cand if os.path.exists(p))     # landed datasets keep cases.tsv above the dumps
    for l in open(path):
        f = l.rstrip('\n').split('\t')
        if hdr is None: hdr = f; continue
        row = dict(zip(hdr, f))
        if os.path.exists(os.path.join(d, row['name'] + '.txt.gz')): out.append(row)
    return out
def raw(d, n, suf='.txt'):
    p = os.path.join(d, n + suf + '.gz')
    return gzip.open(p).read() if os.path.exists(p) else None
def text(d, n): r = raw(d, n); return r.decode('utf-8', 'replace') if r is not None else ''
def kernel_section(d, n):
    p = os.path.join(d, 'kernel.log'); cur, out = None, []
    if not os.path.exists(p): return ''
    for l in open(p, errors='replace'):
        m = re.search(r'resgx545 case (\S+)', l)
        if m: cur = m[1]
        elif cur == n: out.append(l)
    return ''.join(out)
def load_pred(path):
    pr = collections.defaultdict(dict)   # case -> model -> {quantity: value}
    for l in open(path).read().splitlines()[1:]:
        c, q, v, m = l.split('\t'); pr[c].setdefault(m, {})[q] = v
    return pr
def observe(d, table, c):
    n = c['name']; o = {}
    if table.startswith('vdm-series'):
        o['job'] = 'H' if FAIL.search(text(d, n)) else 'ok'
    elif table in ('capacity', 'capacity-rows'):
        import q164_fate as Q
        p, td = raw(d, n, '.param.bin'), raw(d, n, '.tadata.bin')
        if p is None or td is None: return {'lost>0': 'nodump'}
        per, ws, O = Q.objects(p, td); seen = collections.Counter()
        for a, (nv, e) in O.items():
            for v in Q.verts(ws, per, a, nv, e):
                if v is not None: seen[v] += 1
        o['lost>0'] = 'yes' if any(not seen[i] for i in range(126)) else 'no'
    elif table in ('dpm-oom', 'dpm-stack', 'dpm-hang'):
        import dpm_raise as R
        tp = os.path.join(d, n + '.txt.gz'); tl = R.timeline(tp) if os.path.exists(tp) else None
        if tl:
            prs, peaks = R.runs(*tl); o['prs'] = len(prs); o['peaks'] = [hex(x) for x in peaks]
            o['pages_max'] = max(peaks)
            if 'raised' in o or table == 'dpm-oom':
                w = R.ctl(d, n); o['raised'] = 'yes' if w and w[38] == 0x20 else 'no'; o['dw36'] = w[36] if w else None
        o['hung_line'] = 'yes' if 'hung, recovering' in kernel_section(d, n) else 'no'
    elif table == 'eot-store':
        t = text(d, n); o['fault'] = 'yes' if FAIL.search(t) else 'no'
        o['fault_word'] = re.findall(r'BIF[_ ]FAULT\s+(0x[0-9a-f]+)', kernel_section(d, n))[:1]
    elif table == 'eot-globals':
        t = text(d, n); o['completes'] = 'no' if FAIL.search(t) else 'yes'; o['scratch_lines'] = len(re.findall(r'scratch \+0x', t))
    elif table == 'o4-g25':
        o['tag5_pairs'] = 'see o4_pairs()'   # needs the x/y partner: done in main()
    return o
def o4_pairs(d, cs):
    import o4_parity as O
    mk = {l.split('\t')[0]: int(l.split('\t')[1]) for l in (HERE.parent / 'programs/o4-markers.tsv').read_text().splitlines()}
    res = {}
    for c in cs:
        n = c['name']
        if not n.endswith('-x'): continue
        base = n[:-2]
        def grid(nn):
            rows = {}
            for l in text(d, nn).splitlines():
                m = re.match(r'row (\d+): (.*)$', l)
                if m: rows[int(m[1])] = [int(v, 16) for v in m[2].split()]
            return [rows[i] for i in sorted(rows)]
        gx, gy = grid(base + '-x'), grid(base + '-y')
        if not gx or not gy: res[base] = None; continue
        H, W = len(gx), len(gx[0]); cnt = collections.Counter()
        for y in range(H):
            for x in range(W):
                vx, vy = gx[y][x], gy[y][x]
                if vx == O.BG or vy == O.BG or (vx & 15) != 5 or (vy & 15) != 5: continue
                if (vx & 0xffff) >> 4 != mk[base + '-x'] or (vy & 0xffff) >> 4 != mk[base + '-y']: continue
                sx = round(O.f32(vx & 0xffff0000) * W / 2 + W / 2 - .5); sy = round(O.f32(vy & 0xffff0000) * H / 2 + H / 2 - .5)
                if 0 <= sx < W and 0 <= sy < H: cnt[(sx & 1, sy & 1)] += 1
        res[base] = cnt
    return res
def main():
    a = sys.argv[1:]; d, table = a[0], a[1]
    pf = a[a.index('--pred') + 1] if '--pred' in a else str(HERE.parent / 'predictions-declared.tsv')
    cs = cases(d); pr = load_pred(pf); score = collections.defaultdict(lambda: [0, 0])
    if table == 'o4-g25':
        for base, cnt in o4_pairs(d, cs).items():
            n5 = sum(cnt.values()) if cnt else None
            print(f'{base}: tag5 pairs {n5} by parity {dict(cnt) if cnt else None}')
            for m, qs in pr.get(base + '-x', {}).items():
                v = qs.get('tag5_pairs')
                if v in (None, '?') or n5 is None: continue
                ok = (n5 > 0) if v == '>0' else (n5 == 0)
                score[m][0] += 1; score[m][1] += ok
    else:
        for c in cs:
            o = observe(d, table, c); n = c['name']
            print(n, {k: v for k, v in o.items()})
            for m, qs in pr.get(n, {}).items():
                for q, v in qs.items():
                    if v == '?' or q not in o: continue
                    score[m][0] += 1; score[m][1] += str(o[q]) == v
    if table.startswith('vdm-series'):   # per-series pattern line
        ser = collections.defaultdict(str)
        for c in cs:
            ser[c['name'].rsplit('-', 1)[0]] += 'H' if FAIL.search(text(d, c['name'])) else '.'
        for k, v in ser.items(): print(k, v)
    for m, (n, r) in sorted(score.items()): print(f'model {m}: {r}/{n}')
if __name__ == '__main__': main()
