#!/usr/bin/env python3
"""post_1141ta.py: post-run analysis of the 157-job p1141/ta batch (draft, not frozen).

Reads out-hw/ (p1141ta-out, p1141ta-dumps, p1141ta-run.log) and the frozen files of the batch
(declared.tsv, predictions-declared.tsv, recompute/*.py, programs/o4-markers.tsv); writes nothing.
The frozen recompute_1141ta.py is NOT edited; where it cannot read the dumps of a table (it looks
for NAME.param.bin.gz, the tool wrote NAME.<program>.param.bin.gz; it reads o4 rows as `row N:`
at line start, the tool prints `probe pix_pa0: row N:`) the readers here replace it and say so.
Scoring follows predictions-declared.tsv unchanged; a prediction on a job that did not run is
reported as void, not as right.  Standard library only.
Usage: python3 post_1141ta.py TA_DIR [section ...]   sections: integrity vdm cap capr oom stack
hang eotstore eotglob o4
"""
import collections, glob, gzip, hashlib, os, random, re, struct, sys

TA = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else '.'
SECT = set(sys.argv[2:]) or {'integrity', 'vdm', 'cap', 'capr', 'oom', 'stack', 'hang', 'eotstore',
                             'eotglob', 'o4'}
sys.path.insert(0, os.path.join(TA, 'recompute'))
OUT = os.path.join(TA, 'out-hw')
TABLES = ['vdm-series-a', 'capacity', 'dpm-oom', 'dpm-stack', 'eot-globals', 'vdm-series-b',
          'o4-g25', 'dpm-hang', 'eot-store', 'capacity-rows']
FAIL = re.compile(r'failed|faulted|hung|rejected|FAILED')


def dumps(t): return f'{OUT}/p1141ta-dumps/{t}-all'
def gz(p): return gzip.open(p).read()
def txt(t, n): return gz(f'{dumps(t)}/{n}.txt.gz').decode('utf-8', 'replace')
def one(t, n, pat): return glob.glob(f'{dumps(t)}/{n}.{pat}')[0]


def cases(t):
    rows = [l.split('\t') for l in open(f'{dumps(t)}/cases.tsv').read().splitlines()]
    return [dict(zip(rows[0], r)) for r in rows[1:]]


def pred():
    p = collections.defaultdict(lambda: collections.defaultdict(dict))
    for l in open(f'{TA}/predictions-declared.tsv').read().splitlines()[1:]:
        c, q, v, m = l.split('\t'); p[c][m][q] = v
    return p
PRED = pred()
DECL = {r.split('\t')[0]: r.split('\t')[2] for r in open(f'{TA}/declared.tsv').read().splitlines()[1:]}


def kernel_sections(t):
    sec, cur = collections.defaultdict(list), None
    for l in open(f'{dumps(t)}/kernel.log', errors='replace'):
        m = re.search(r'resgx545 case (\S+)', l)
        if m: cur = m[1]; sec[cur] = []; continue
        if cur: sec[cur].append(l)
    return sec


def outinfo(t):
    info, cur = {}, None
    for l in open(f'{OUT}/p1141ta-out/{t}.out', errors='replace'):
        m = re.match(r'== (\S+) set=(\S+)', l)
        if m: cur = m[1]; info[cur] = {'rc': None, 'msg': ''}; continue
        m = re.match(r'  rc (\d+) ?(.*)', l)
        if m and cur: info[cur]['rc'] = int(m[1]); info[cur]['msg'] = m[2]
    return info


def score(table_rows, label):
    """table_rows: {case: {quantity: observed}}; scores PRED per model, '?' skipped."""
    sc = collections.defaultdict(lambda: [0, 0]); miss = collections.defaultdict(list)
    for c, obs in table_rows.items():
        for m, qs in PRED.get(c, {}).items():
            for q, v in qs.items():
                if v == '?' or q not in obs or obs[q] is None: continue
                sc[m][0] += 1; ok = str(obs[q]) == v; sc[m][1] += ok
                if not ok: miss[m].append(f'{c}({q} pred {v} obs {obs[q]})')
    for m in sorted(sc):
        print(f'  {label} model {m}: {sc[m][1]}/{sc[m][0]}' + ('  misses: ' + '; '.join(miss[m]) if miss[m] else ''))


def integrity():
    print('## integrity: sha256 of every kept file against its raw line in p1141ta-out, markers, rc')
    nk = bad = 0; nmark = 0
    for t in TABLES:
        kept = set()
        for l in open(f'{OUT}/p1141ta-out/{t}.out', errors='replace'):
            m = re.match(r'\s+kept (\S+): (\d+) bytes raw, raw sha256 (\w+)', l)
            if m:
                n, sz, h = m.groups(); kept.add(n); nk += 1
                r = gz(f'{dumps(t)}/{n}.gz')
                if hashlib.sha256(r).hexdigest() != h or len(r) != int(sz): bad += 1; print('  BAD', t, n)
        files = {f[:-3] for f in os.listdir(dumps(t)) if f.endswith('.gz')}
        raw = {l.split()[0] for l in open(f'{dumps(t)}/raw.sha256')}
        assert files == kept == raw, (t, len(files), len(kept), len(raw))
        cs = cases(t); sec = kernel_sections(t); order = []
        for l in open(f'{dumps(t)}/kernel.log', errors='replace'):
            m = re.search(r'resgx545 case (\S+)', l)
            if m: order.append(m[1])
        assert order == [c['name'] for c in cs], t
        nmark += len(order)
        info = outinfo(t); hung = {n: sum('hung, recovering' in l for l in sec[n]) for n in sec}
        flt = {n: len(re.findall(r'BIF fault (0x\w+) at (0x\w+)', ''.join(sec[n]))) for n in sec}
        odd = [(n, i['rc'], i['msg'][:55]) for n, i in info.items()
               if (i['rc'] != 0) != (hung[n] > 0 or flt[n] > 0)]
        print(f'  {t}: {len(cs)} cases, {len(order)} markers in case order, rc!=0 '
              f'{sum(i["rc"] != 0 for i in info.values())}, hung lines {sum(hung.values())}, BIF fault '
              f'lines {sum(flt.values())}; rc!=0 without a hung or fault line: {len(odd)}')
        for o in odd: print('     ', o)
    print(f'  {nk} kept files, {bad} differ from their raw sha256 line; {nmark} markers')


def vdm():
    print('## vdm series (Q163, Q102): job outcomes against the frozen M0, M1, M2')
    rng = random.Random(1141)
    ser = {'A1': [(4, 2)] * 12, 'A2': [(3, 2)] * 12, 'A3': [(7, 2)] * 6,
           'A4': [(rng.choice([2, 2, 3, 4, 5, 6, 7]), rng.choice([2, 2, 3, 4, 5, 6, 7])) for _ in range(16)],
           'A5': [(5, 3)] * 6, 'B1': [(2, 1)] * 4,
           'B2': [(6, 2), (6, 2), (2, 1), (3, 2), (3, 2)], 'B3': [(6, 2), (6, 2), (2, 0), (3, 2), (3, 2)],
           'B4': [(6, 2), (1, 2), (1, 2), (1, 2), (6, 2), (6, 2)], 'B5': [(1, 2)] * 3,
           'B6': [(6, 2), (6, 2), (0, 2), (3, 2), (3, 2)]}
    pre = {'A1': 'vs-A1-v4x12', 'A2': 'vs-A2-v3x12', 'A3': 'vs-A3-v7x6', 'A4': 'vs-A4-rand16',
           'A5': 'vs-A5-v5v3x6', 'B1': 'vs-B1-b2v1x4', 'B2': 'vs-B2-v1-at-8', 'B3': 'vs-B3-v0-at-8',
           'B4': 'vs-B4-b1v1-at-4', 'B5': 'vs-B5-b1v1-at-0', 'B6': 'vs-B6-b1v0-at-8'}
    obs = {}
    for t in ('vdm-series-a', 'vdm-series-b'):
        for c in cases(t): obs[c['name']] = 'H' if FAIL.search(txt(t, c['name'])) else 'ok'
    for k, s in ser.items():
        names = [f'{pre[k]}-{i:02d}' for i in range(len(s))]
        sc = {m: sum(PRED[n][m]['job'] == obs[n] for n in names) for m in ('M0', 'M1', 'M2')}
        print(f'  {k} set={DECL[names[0]]} obs {"".join("H" if obs[n] == "H" else "." for n in names)}  '
              f'M0 {sc["M0"]}/{len(s)} M1 {sc["M1"]}/{len(s)} M2 {sc["M2"]}/{len(s)}')
        if k == 'A4': print('     A4 draws (v1, v2):', s)
        if k[0] == 'B':
            for i, n in enumerate(names):
                print(f'     job {i} v={s[i]} obs {obs[n]} pred M0/M1/M2 '
                      f'{PRED[n]["M0"]["job"]}/{PRED[n]["M1"]["job"]}/{PRED[n]["M2"]["job"]}')
    a = [(k, i, s) for k in ('A1', 'A2', 'A3', 'A4', 'A5') for i, s in enumerate(ser[k])]
    ho = lambda k, i: obs[f'{pre[k]}-{i:02d}'] == 'H'
    print(f'  A in all: {len(a)} jobs, {sum(ho(k, i) for k, i, s in a)} hangs; never-hang null '
          f'{sum(not ho(k, i) for k, i, s in a)}/{len(a)}; best stateless threshold on sum(v-2) '
          f'{max(sum(((s[0] - 2) + (s[1] - 2) >= T) == ho(k, i) for k, i, s in a) for T in range(12))}/{len(a)}')
    a4 = [(i, s) for i, s in enumerate(ser['A4'])]
    print(f'  A4 alone: 16 jobs, {sum(ho("A4", i) for i, s in a4)} hangs; never-hang '
          f'{sum(not ho("A4", i) for i, s in a4)}/16; best stateless threshold '
          f'{max(sum(((s[0] - 2) + (s[1] - 2) >= T) == ho("A4", i) for i, s in a4) for T in range(12))}/16')
    # post hoc M3 = M2 without the v=0 reset
    def m3(series):
        c, out = 0, []
        for v1, v2 in series:
            add, hn = 0, False
            for blk, v in ((1, v1), (2, v2)):
                if v >= 2: add += v - 2
                elif v == 1:
                    if blk == 2 and c == 0: hn = True
                    add -= 1
            h = hn or c + add > 8; out.append('H' if h else 'ok'); c = 0 if h else max(c + add, 0)
        return out
    r = sum(m3(ser[k])[i] == obs[f'{pre[k]}-{i:02d}'] for k in ser for i in range(len(ser[k])))
    print(f'  post hoc M3 (M2 without the v=0 reset): {r}/{sum(len(v) for v in ser.values())} over A and B')


def decode(t, n):
    import q164_fate as Q
    pb = gz(one(t, n, '*.param.bin.gz')); td = gz(one(t, n, '*.tadata.bin.gz'))
    per, ws, O = Q.objects(pb, td); seen = collections.Counter(); unread = []; sizes = []
    for a, (nv, e) in sorted(O.items()):
        sizes.append(nv)
        for i, v in enumerate(Q.verts(ws, per, a, nv, e)):
            if v is None: unread.append((a, i))
            else: seen[v] += 1
    lost = sum(1 for i in range(126) if not seen[i]); dup = sum(1 for x in seen.values() if x > 1)
    return Q, per, ws, O, sizes, lost, dup, unread


def cap(t):
    print(f'## {t}: vertex fate of the 126 vertices per job (landed decoder recompute_p1131 via q164_fate)')
    rows = {}; ok_page = n_e = alt_ok = 0
    for c in cases(t):
        n = c['name']; hv = ('hung' in outinfo(t)[n]['msg'])
        if hv: print(f'  {n}: job hung, no dump'); continue
        Q, per, ws, O, sizes, lost, dup, unread = decode(t, n)
        rows[n] = {'lost>0': 'yes' if lost else 'no'}
        for a, (nv, e) in O.items():
            if e is None: continue
            n_e += 1; ok_page += all(v is not None for v in Q.verts(ws, per, a, nv, e))
            alt_ok += all(v is not None for v in Q.verts(ws, per, a, nv, e, True))
        v7 = re.search(r'--vdm 7\^=(\S+)', c['args'])
        print(f'  {n}: per {per} objects {len(O)} sizes {dict(collections.Counter(sizes))} lost {lost} '
              f'dup {dup} unreadable {len(unread)} vdm7^={v7[1] if v7 else "-"} '
              f'(set {DECL[n]})' + (f' unreadable at {unread}' if unread and lost < 10 else ''))
    score(rows, t)
    print(f'  objects with bit 21 whose vertices are all identified with the page claim: {ok_page} of '
          f'{n_e} (alternative page: {alt_ok}); jobs with lost vertices: '
          f'{sum(r["lost>0"] == "yes" for r in rows.values())} of {len(rows)}')


def a7_row():
    Q, per, ws, O, sizes, lost, dup, unread = decode('capacity', 'cap-n8-f10-a7')
    for a, i in unread:
        nv, e = O[a]; f = a - 0x400; pg = f & ~0x3ff; tot = per * nv; have = f - pg
        seq = (ws[((e >> 10) * 0x400 - (tot - have)):(e >> 10) * 0x400] + ws[pg:f]) if e is not None and tot > have else ws[f - tot:f]
        print(f'  cap-n8-f10-a7 object {a:#x} vertex {i}: ' + ' '.join(f'{x:#x}' for x in seq[i * per:(i + 1) * per]))


def dpm():
    import dpm_raise as R
    return R


def oom():
    R = dpm(); print('## dpm-oom: timeline, control block dwords 34..40, outcome of the tool')
    info = outinfo('dpm-oom'); rows = {}
    for c in cases('dpm-oom'):
        n = c['name']; i = info[n]; ran = 'overflowed' in i['msg']
        tl = R.timeline(f'{dumps("dpm-oom")}/{n}.txt.gz'); prs, peaks = R.runs(*tl) if ran else ([], [])
        w = R.ctl(dumps('dpm-oom'), n) if ran else None
        raised = ('yes' if w[38] == 0x20 else 'no') if ran else None
        rows[n] = {'raised': raised}
        print(f'  {n} (set {DECL[n]}): rc {i["rc"]} {"ran: overflowed" if ran else "DID NOT RUN (usage text)"}'
              + (f' thr0 {[hex(x) for x in prs]} peaks {[hex(x) for x in peaks]} dw34..40 {[hex(x) for x in w[34:41]]}' if ran else ''))
    score(rows, 'dpm-oom (void jobs excluded)')


def stack():
    R = dpm(); print('## dpm-stack: the tool runs -n renders one after the other (one triangle each)')
    d = dumps('dpm-stack'); import dpm_raise
    for c in cases('dpm-stack'):
        n = c['name']; t = txt('dpm-stack', n)
        res = re.findall(r'^tri 1024x768 #(\d+): (overflowed, )?(\d+) triangle', t, re.M)
        regs, rows = R.timeline(f'{d}/{n}.txt.gz'); ist = regs.index('0x0724') + 1
        segs, cur, last = [], None, None
        for r in rows:
            s = r[ist] & 0xffff
            if s:
                if cur is None or r[0] - last > 50_000_000:
                    if cur: segs.append(cur)
                    cur = [r[0], r[0], s]
                cur[1] = r[0]; cur[2] = max(cur[2], s); last = r[0]
        if cur: segs.append(cur)
        dw = []
        for k in range(1, 5):
            p = f'{d}/{n}.ta3d.{k}.bin.gz'
            if os.path.exists(p):
                w = struct.unpack('<59I', gz(p)[:236]); dw.append((hex(w[37]), hex(w[38])))
        print(f'  {n}: renders {[(a, "overflowed" if b else "ok", int(p)) for a, b, p in res]} '
              f'peaks of status runs {[hex(m) for a, b, m in segs] if "0x422" in n else "-"} dw37/38 {dw}')


def hang():
    R = dpm(); print('## dpm-hang: kernel hung lines, partial renders, span of the timeline')
    info = outinfo('dpm-hang'); sec = kernel_sections('dpm-hang'); rows = {}
    for c in cases('dpm-hang'):
        n = c['name']; regs, tl = R.timeline(f'{dumps("dpm-hang")}/{n}.txt.gz')
        ip, ist = regs.index('0x0658') + 1, regs.index('0x0724') + 1; prs, peaks = R.runs(regs, tl)
        nz = next(r[0] for r in tl if r[ist] & 0xffff); prev = None; lastc = 0
        for r in tl:
            if prev is not None and tuple(r[1:]) != prev: lastc = r[0]
            prev = tuple(r[1:])
        hl = sum('hung, recovering' in l for l in sec[n]); held = any('recovery held' in l for l in sec[n])
        rows[n] = {'hung_line': 'yes' if hl else 'no'}
        print(f'  {n} (set {DECL[n]}): hung lines {hl}, recovery held {held}, rc {info[n]["rc"]} '
              f'{info[n]["msg"][21:80]}; partial renders {len(prs)}, thr0 {prs[0]:#x}, span first status '
              f'to last change {(lastc - nz) / 1e9:.3f} s')
    score(rows, 'dpm-hang')


def eotstore():
    print('## eot-store: tool outcome, BIF fault word and address per job, scratch words')
    info = outinfo('eot-store'); sec = kernel_sections('eot-store'); rows = {}
    for c in cases('eot-store'):
        n = c['name']; f = re.findall(r'BIF fault (0x\w+) at (0x\w+)', ''.join(sec[n]))
        t = txt('eot-store', n); rows[n] = {'fault': 'yes' if info[n]['rc'] != 0 else 'no'}
        sc = re.findall(r'scratch \+0x(\w+) 0x(\w+)', t)
        print(f'  {n} (set {DECL[n]}): rc {info[n]["rc"]} fault lines {f} scratch words {sc}')
    score(rows, 'eot-store')


def eotglob():
    print('## eot-globals: per-tile stores of g16-g31 (ga) and g39-g43, sa0-sa10 (gb), slot = dword // 16')
    info = outinfo('eot-globals')
    for c in cases('eot-globals'):
        n = c['name']; w = {}
        for m in re.finditer(r'scratch \+0x(\w+) 0x(\w+)', txt('eot-globals', n)): w[int(m[1], 16) // 4] = int(m[2], 16)
        slots = collections.defaultdict(dict)
        for k, v in w.items(): slots[k // 16][k % 16] = v
        full = [s for s in slots if s < 64]
        print(f'  {n}: rc {info[n]["rc"]}, dwords listed {len(w)}, slots with data {len(slots)} '
              f'(slot < 64: {len(full)}), slots above 63: {sorted(s for s in slots if s >= 64)}')
        if n in ('eotg-ga', 'eotg-gb', 'eotg-ga-256', 'eotg-gb-256'):
            cols = range(16)
            for k in cols:
                vals = collections.Counter(slots[s].get(k, 0) for s in full)
                print(f'     dword {k:2d}: ' + ' '.join(f'{v:#x}x{c}' for v, c in sorted(vals.items())[:6]))


def o4():
    print('## o4-g25: tag counts per job and x/y pairs (tag 5 = o4)')
    BG = 0xff203040
    mk = {l.split('\t')[0]: int(l.split('\t')[1]) for l in open(f'{TA}/programs/o4-markers.tsv').read().splitlines()}
    f32 = lambda w: struct.unpack('<f', struct.pack('<I', w & 0xffffffff))[0]
    def grid(n):
        r = {}
        for l in txt('o4-g25', n).splitlines():
            m = re.search(r'row (\d+): (.*)$', l)
            if m: r[int(m[1])] = [int(v, 16) for v in m[2].split()]
        return [r[i] for i in sorted(r)]
    sc = collections.defaultdict(lambda: [0, 0])
    for k in ('0', '1', '2', '3', 'u'):
        gx, gy = grid(f'o4g-{k}-x'), grid(f'o4g-{k}-y'); H, W = len(gx), len(gx[0]); cnt = collections.Counter()
        tags = {}
        for ax, g in (('x', gx), ('y', gy)):
            tags[ax] = collections.Counter(v & 15 for row in g for v in row
                                           if v != BG and ((v & 0xffff) >> 4) == mk[f'o4g-{k}-{ax}'])
        for y in range(H):
            for x in range(W):
                vx, vy = gx[y][x], gy[y][x]
                if vx == BG or vy == BG or (vx & 15) != 5 or (vy & 15) != 5: continue
                if (vx & 0xffff) >> 4 != mk[f'o4g-{k}-x'] or (vy & 0xffff) >> 4 != mk[f'o4g-{k}-y']: continue
                sx = round(f32(vx & 0xffff0000) * W / 2 + W / 2 - .5); sy = round(f32(vy & 0xffff0000) * H / 2 + H / 2 - .5)
                if 0 <= sx < W and 0 <= sy < H: cnt[(sx & 1, sy & 1)] += 1
        n5 = sum(cnt.values())
        print(f'  g25 == {k}: tag 5 pixels x {tags["x"][5]} y {tags["y"][5]}; pairs {n5} by parity {dict(cnt)}')
        for ax in 'xy':
            for m, qs in PRED.get(f'o4g-{k}-{ax}', {}).items():
                v = qs.get('tag5_pairs')
                if v in (None, '?'): continue
                sc[m][0] += 1; sc[m][1] += (n5 > 0) if v == '>0' else (n5 == 0)
    for m, (n, r) in sorted(sc.items()): print(f'  o4-g25 model {m}: {r}/{n} (x and y jobs counted separately)')


for name, fn in (('integrity', integrity), ('vdm', vdm), ('cap', lambda: (cap('capacity'), a7_row())),
                 ('capr', lambda: cap('capacity-rows')), ('oom', oom), ('stack', stack),
                 ('hang', hang), ('eotstore', eotstore), ('eotglob', eotglob), ('o4', o4)):
    if name in SECT: fn()
