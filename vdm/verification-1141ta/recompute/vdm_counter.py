#!/usr/bin/env python3
"""p1141/ta vdm_counter.py: re-score the E413 hidden-counter hypothesis for VDM_STATE1 bits 11:9.

Own parser, not Opus's.  Reads ~/src/resgx545-data/vdm (override with DATA=...).
Model C(T=8): counter c (0 after reset/hang); each job adds sum(v-2) over its state blocks
(v = field bits 11:9, baseline 2); hang iff c+add > T; a completed job keeps c+add.
Sets: FIT = the 130 jobs E413 was fitted on (state1-hang, state1-hang-seq).
'LATE' = every other set; NOT truly held out (see plan.md section 1): the grid's v6 period
was seen first by the model's author.  Jobs with a bit other than 11:9 forced (15:13, 17, closed
word forms) are listed, not scored.  v<2 jobs: variant g0 (add 0), variant gneg (v=1 -> -1).
Usage: python3 vdm_counter.py [--null]
"""
import os, re, sys, pathlib, gzip
D = pathlib.Path(os.environ.get('DATA', os.path.expanduser('~/src/resgx545-data/vdm')))
CLOSED = {0x0800e105, 0x08002505}

def vfield(word): return (word >> 9) & 7

def jobs_tri(path):
    """output.txt of state1-*: '== name: tri ARGS' then 'job: ok|failed'."""
    out, cur = [], None
    for l in (path / 'output.txt').read_text().splitlines():
        m = re.match(r'== (\S+): tri ?(.*)', l)
        if m: cur = (m[1], m[2]); continue
        m = re.match(r'job: (\S+)', l)
        if m and cur:
            x = re.search(r'vdm:1\^=(0x[0-9a-f]+)', cur[1])
            v = 2 ^ vfield(int(x[1], 16)) if x else 2
            out.append(dict(name=cur[0], vs=[v], fail=m[1] != 'ok', forced=False, script=str(path)))
            cur = None
    return out

def jobs_units():
    """state-units/output.txt: '## script S', '== name', '  cmd: ...--vdm N[^]=0x..', '  rc R'."""
    out, script, cur = [], None, None
    for l in (D / 'state-units' / 'output.txt').read_text().splitlines():
        m = re.match(r'## script (\S+)', l)
        if m: script = m[1]; continue
        m = re.match(r'== (\S+) ', l)
        if m: cur = dict(name=m[1], script=script, vb={1: 2, 9: 2}, forced=False); continue
        if cur is None: continue
        if l.strip().startswith('cmd:'):
            for blk, op, val in re.findall(r'--vdm (\d+)(\^?=)(0x[0-9a-f]+)', l):
                val = int(val, 16); blk = int(blk)
                if op == '=':
                    if val in CLOSED: cur['forced'] = True
                    cur['vb'][blk] = vfield(val)
                else:
                    if val & 0x2e000: cur['forced'] = True
                    cur['vb'][blk] = 2 ^ vfield(val)
        m = re.match(r'\s*rc (\d+)', l)
        if m:
            raw = gzip.open(D / 'state-units' / 'dumps' / cur['script'] / (cur['name'] + '.txt.gz')).read().decode()
            failed = m[1] != '0' or bool(re.search(r'failed|faulted|hung|rejected|overflowed', raw))
            out.append(dict(name=cur['name'], vs=[cur['vb'][1], cur['vb'][9]], fail=failed,
                            forced=cur['forced'], script=cur['script']))
            cur = None
    return out

def jobs_probe(sub, pat):
    """state2-*: raw.txt 'probe X__N: ...failed|hung' lines; description from report.txt."""
    desc = {}
    for l in (D / sub / pat / 'report.txt').read_text().splitlines():
        m = re.match(r'\s*\[(\d+)\] (.*?), run \d+:', l)
        if m: desc[int(m[1])] = m[2]
    order, fails = [], set()
    for l in (D / sub / pat / 'raw.txt').read_text().splitlines():
        m = re.match(r'probe \S+?__(\d+): (.*)', l)
        if m:
            i = int(m[1])
            if i not in order: order.append(i)
            if re.search('failed|hung', m[2]): fails.add(i)
    out = []
    for i in order:
        s = desc.get(i, '?'); vb = [2, 2]; forced = False
        m = re.search(r'block ?([12]) bits 11:9 = (\d)', s)
        if m: vb[int(m[1]) - 1] = int(m[2])
        if re.search(r'bits? (15:13|17|18)', s): forced = True
        out.append(dict(name=f'{i}:{s}', vs=vb, fail=i in fails, forced=forced, script=sub))
    return out

def simulate(L, g0='zero', closed=False, T=8):
    """returns (scored, right, misses).  Resets c at script change and at any observed failure."""
    c, last, sc, ok, miss = 0, None, 0, 0, []
    for j in L:
        if j['script'] != last: c, last = 0, j['script']
        add = 0
        for v in j['vs']:
            if v >= 2: add += v - 2
            elif v == 1 and g0 == 'neg': add -= 1
        pred = c + add > T
        if not j['forced']:
            sc += 1
            if pred == j['fail']: ok += 1
            else: miss.append(j['name'])
        hang = pred if (closed and not j['forced']) else j['fail']
        c = 0 if hang else max(c + add, 0)
    return sc, ok, miss

def clean_subset(L):
    """jobs whose counter history since the last reset/hang holds only v>=2 jobs (c known without
    any v<2 convention); scored one-step.  Returns (n, right, hangs, n_v3, right_v3, misses)."""
    c, last, tainted = 0, None, False
    n = r = h = n3 = r3 = 0
    miss = []
    for j in L:
        if j['script'] != last: c, last, tainted = 0, j['script'], False
        low = any(v < 2 for v in j['vs'])
        add = sum(v - 2 for v in j['vs'] if v >= 2)
        pred = c + add > 8
        if not j['forced'] and not low and not tainted:
            n += 1; h += j['fail']; r += pred == j['fail']
            if pred != j['fail']: miss.append(j['name'])
            if max(j['vs']) >= 3: n3 += 1; r3 += pred == j['fail']
        if j['fail'] or j['forced'] and j['fail']: c, tainted = 0, False
        else:
            c += add
            if low: tainted = True
    return n, r, h, n3, r3, miss

def main():
    fit = jobs_tri(D / 'state1-hang') + jobs_tri(D / 'state1-hang-seq')
    units = jobs_units()
    by = {}
    for j in units: by.setdefault(j['script'], []).append(j)
    late = [('state1-split', jobs_tri(D / 'state1-split')),
            ('state-units', by['vdm-state-units']), ('state-risky', by['vdm-state-risky']),
            ('state-grid', by['vdm-state-grid']),
            ('state2-fields', jobs_probe('state2-fields', 'vdm-state2-fields-blocks')),
            ('state2-consts', jobs_probe('state2-consts', 'vdm-state2-consts-loaded'))]
    sets = [('FIT state1-hang', jobs_tri(D / 'state1-hang')), ('FIT state1-hang-seq', jobs_tri(D / 'state1-hang-seq'))] + late
    for mode in ('zero', 'neg'):
        print(f'== variant v<2 adds: {mode}')
        for name, L in sets:
            r = simulate(L, mode); rc = simulate(L, mode, closed=True)
            print(f'{name:22s} n={len(L):3d} hangs={sum(j["fail"] for j in L):3d} one-step {r[1]}/{r[0]}'
                  f' closed-loop {rc[1]}/{rc[0]} miss {r[2][:6]}')
    # v>=2-only subset of the late sets (variant independent)
    n = right = n3 = right3 = h3 = 0
    for name, L in late:
        sc, ok, miss = simulate(L, 'zero')
        mset = set(miss)
        for j in L:
            if j['forced'] or any(v < 2 for v in j['vs']): continue
            n += 1; right += j['name'] not in mset
            if max(j['vs']) >= 3:
                n3 += 1; right3 += j['name'] not in mset; h3 += j['fail']
    print(f'LATE jobs with all v>=2, unforced: {right}/{n}; of them v>=3: {right3}/{n3} (hangs {h3})')
    tot = [0, 0, 0, 0, 0]
    for name, L in late:
        n, r, h, n3, r3, miss = clean_subset(L)
        print(f'CLEAN {name:14s} {r}/{n} (hangs {h}); v>=3 {r3}/{n3}; miss {miss}')
        for k, x in enumerate((n, r, h, n3, r3)): tot[k] += x
    print(f'CLEAN total {tot[1]}/{tot[0]} hangs {tot[2]}; v>=3 {tot[4]}/{tot[3]}')
    nfit = sum(simulate(L)[0] for _, L in sets[:2]); okfit = sum(simulate(L)[1] for _, L in sets[:2])
    print(f'FIT total {okfit}/{nfit}')
    if '--null' in sys.argv:
        print('== nulls on all unforced v>=2 LATE jobs (base rates)')
        allj = [j for _, L in late for j in L if not j['forced'] and all(v >= 2 for v in j['vs'])]
        print('hang rate', sum(j['fail'] for j in allj), '/', len(allj))
        for thr in (3, 4, 5, 6, 7):  # stateless: hang iff sum(v-2) >= thr
            ok = sum((sum(v - 2 for v in j['vs']) >= thr) == j['fail'] for j in allj)
            print(f'stateless add>={thr}: {ok}/{len(allj)}')
        ok = sum(not j['fail'] for j in allj); print(f'never hang: {ok}/{len(allj)}')

if __name__ == '__main__': main()
