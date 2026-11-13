"""Scores q036_rule.json (frozen). python -I q036_score.py > q036_score.out"""
import os, re, gzip, glob, math, collections
R = '/Users/jtorra/src/resgx545-data/render'
FIT = {'closing-r1-pixgeo', 'closing-r2-geo', 'closing-r3-geo', 'closing-r3-geo-c'}

def timelines(path):
    """yield (regs, rows) per 'timeline: regs' header (parse pattern from dpm_raise.py timeline())"""
    regs, rows = None, []
    with gzip.open(path, 'rt', errors='replace') as f:
        for l in f:
            if l.startswith('timeline: regs'):
                if regs: yield regs, rows
                regs = re.match(r'timeline: regs (.*?) samples', l)[1].split(); rows = []
            elif l.startswith('tl ') and regs:
                p = l.split()
                try:
                    row = [int(p[1])] + [int(x, 16) for x in p[2:]]
                    if len(row) == len(regs) + 1: rows.append(row)  # drop truncated lines
                except ValueError: pass
    if regs: yield regs, rows

def args_of(d):
    m = {}
    p = d + '/cases.tsv'
    if os.path.exists(p):
        h = None
        for l in open(p, errors='replace'):
            f = l.rstrip('\n').split('\t')
            if h is None: h = f; continue
            c = dict(zip(h, f)); m[c.get('name', '')] = l
    return m

jobs = []; hi710 = []; hi71c = []; after_n = 0; after71c = 0
sess_stat = collections.defaultdict(lambda: collections.Counter())
for sess in sorted(glob.glob(R + '/closing-r*') + glob.glob(R + '/closing-s*')):
    sn = os.path.basename(sess)
    for path in sorted(glob.glob(sess + '/out/**/*.txt.gz', recursive=True)):
        b = os.path.basename(path)
        if b.endswith('.after.regs.txt.gz'):
            after_n += 1; sess_stat[sn]['after'] += 1
            for l in gzip.open(path, 'rt', errors='replace'):
                if l.startswith('reg 0x071c '):
                    v = int(l.split()[2], 16); after71c += 1; sess_stat[sn]['after071c'] += 1
                    if v >> 16: hi71c.append((path, hex(v)))
            continue
        d = os.path.dirname(path); name = b[:-7]
        for regs, rows in timelines(path):
            if '0x0710' not in regs: continue
            i710 = regs.index('0x0710') + 1
            i748 = regs.index('0x0748') + 1 if '0x0748' in regs else None
            i72c = regs.index('0x072c') + 1 if '0x072c' in regs else None
            i658 = regs.index('0x0658') + 1 if '0x0658' in regs else None
            G = max((r[i72c] >> 16 for r in rows), default=None) if i72c else None
            sess_stat[sn]['jobs'] += 1; sess_stat[sn]['lines'] += len(rows)
            for r in rows:
                if r[i710] >> 16:
                    hi710.append((path, r[0], hex(r[i710]), G))
            if i748 is None: continue
            n = len(rows); c = sum(1 for r in rows if not (r[i748] >> 2) & 1)
            p = 0; inpr = False
            if i658:
                for r in rows:
                    x = r[i658] & 1
                    if x and not inpr: p += 1
                    inpr = bool(x)
            a = args_of(d).get(name, '')
            jobs.append(dict(s=sn, path=path, n=n, c=c, p=p, G=G, h100=('0x100' in a or '0x100' in name)))
print('== H0 ==')
print('tl lines total', sum(v['lines'] for v in sess_stat.values()), 'jobs with 0x0710', sum(v['jobs'] for v in sess_stat.values()))
print('after-reads', after_n, 'with 0x071c', after71c)
print('non-zero 0x0710 high halves:', len(hi710)); [print(' ', x) for x in hi710[:20]]
print('non-zero 0x071c high halves:', len(hi71c)); [print(' ', x) for x in hi71c[:20]]
print('per session (jobs, lines, after-reads, after 0x071c):')
for k, v in sess_stat.items(): print(f'  {k}: {v["jobs"]} jobs {v["lines"]} lines {v["after"]} after {v["after071c"]} w/071c')
Gs = [j['G'] for j in jobs if j['G'] is not None]
allG = collections.Counter()
for sn in sess_stat: pass
print('jobs with 0x0748:', len(jobs), 'G distribution (jobs with 0x0748):', sorted(collections.Counter(Gs).items()))
# H0 split by G over all jobs with 0x0710: recount G>=6 jobs
print('== bit 2 ==')
fit = [j for j in jobs if j['s'] in FIT]; held = [j for j in jobs if j['s'] not in FIT]
print('fit jobs', len(fit), 'lines', sum(j['n'] for j in fit), 'clear lines', sum(j['c'] for j in fit), 'jobs with clear', sum(j['c'] > 0 for j in fit))
print('held jobs', len(held), 'lines', sum(j['n'] for j in held), 'clear lines', sum(j['c'] for j in held), 'jobs with clear', sum(j['c'] > 0 for j in held))
for lab, f in (('G<=5', lambda j: j['G'] is not None and j['G'] <= 5), ('G>=6', lambda j: j['G'] is not None and j['G'] >= 6), ('G none', lambda j: j['G'] is None)):
    hh = [j for j in held if f(j)]
    print(f'held {lab}: jobs {len(hh)} with clear {sum(j["c"] > 0 for j in hh)} lines {sum(j["n"] for j in hh)} clear {sum(j["c"] for j in hh)} PR {sum(j["p"] for j in hh)}')
print('per held session: jobs, jobs with clear, lines, clear lines, PR')
for sn in sorted({j['s'] for j in held}):
    hh = [j for j in held if j['s'] == sn]
    print(f'  {sn}: {len(hh)} {sum(j["c"] > 0 for j in hh)} {sum(j["n"] for j in hh)} {sum(j["c"] for j in hh)} {sum(j["p"] for j in hh)}')
sn_ = sum(j['n'] for j in fit); sc = sum(j['c'] for j in fit)
q = sc / sn_ if sn_ else 0
fp = [j for j in fit if j['p'] > 0]; r = (sum(j['c'] for j in fp) / sum(j['p'] for j in fp)) if fp else 0
def frac(js): return sum(j['c'] > 0 for j in js) / len(js) if js else 0
f100 = frac([j for j in fit if j['h100']]); fo = frac([j for j in fit if not j['h100']]); f0 = frac(fit)
print(f'fit params q={q:.5f} r={r:.4f} f100={f100:.3f} fother={fo:.3f} const={f0:.3f}')
cl = lambda x: min(.99, max(.01, x))
rivals = {'R-LEN': lambda j: 1 - (1 - q) ** j['n'], 'R-PR': lambda j: 1 - math.exp(-r * j['p']),
          'R-0x100': lambda j: f100 if j['h100'] else fo, 'R-CONST': lambda j: f0}
for lab, f in (('G<=5', lambda j: j['G'] is not None and j['G'] <= 5), ('G>=6', lambda j: j['G'] is not None and j['G'] >= 6)):
    hh = [j for j in held if f(j)]
    print(f'-- held {lab}: {len(hh)} jobs')
    for k, fn in rivals.items():
        ll = bri = 0
        for j in hh:
            pr = cl(fn(j)); y = j['c'] > 0
            ll -= math.log(pr if y else 1 - pr); bri += (pr - y) ** 2
        print(f'  {k}: logloss {ll:.2f} brier {bri:.2f}')
