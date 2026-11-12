#!/usr/bin/env python3
"""Round 7 dpm offline stage (G1 to G7), shared paths and readers.  Read-only, public data,
standard library only.  The round 6 offline library is imported from its published twin
(resgx545-data cited/closing6/dpm/offline/), the repo's tools/usse-asm from RESGX545_TREE."""
import csv, gzip, os, re, struct, sys
DATA = os.environ.get('RESGX545_DATA', '/Users/jtorra/src/resgx545-data')
TREE = os.environ.get('RESGX545_TREE', '/Users/jtorra/src/resgx545')
R6 = os.path.join(DATA, 'cited', 'closing6', 'dpm', 'offline')
for p in (R6, os.path.join(TREE, 'tools', 'usse-asm'), os.path.join(DATA, 'render', 'closing-r5-dpm', 'gen')):
    if not os.path.isdir(p):
        raise SystemExit('missing directory: ' + p)
    sys.path.insert(0, p)
import dpm_words as D            # noqa: E402
from r6lib import load, stretches, hi   # noqa: E402,F401
RENDER = os.path.join(DATA, 'render')


def cases():
    """every row of every cases.tsv under render/closing-*/out (tests/ fixtures left out):
    (session, stage dir relative to out/, dir, name, args, the row)"""
    for ds in sorted(os.listdir(RENDER)):
        base = os.path.join(RENDER, ds, 'out')
        if not ds.startswith('closing-') or not os.path.isdir(base):
            continue
        for d, _, fs in sorted(os.walk(base)):
            if 'cases.tsv' not in fs:
                continue
            with open(os.path.join(d, 'cases.tsv')) as f:
                for r in csv.DictReader(f, delimiter='\t'):
                    if r.get('name'):
                        yield ds, os.path.relpath(d, base), d, r['name'], r.get('args') or '', r


def dumps(d, name):
    """the job's PB dumps: prefixes p with p + 'param.bin.gz' in d (sorted)"""
    return sorted(os.path.join(d, f[:-len('param.bin.gz')]) for f in os.listdir(d)
                  if f.startswith(name + '.') and f.endswith('.param.bin.gz'))


def opt(args, flag):
    m = re.search(r'(?:^|\s)' + re.escape(flag) + r'\s+(\S+)', args)
    return m.group(1) if m else None


def regions_of(pre, w, h):
    """region headers with a stream (not outside, not empty): dicts addr, c, r, m, i"""
    tad = gzip.open(pre + 'tadata.bin.gz').read()
    lay = D.tadata_layout(w, h)
    ws = struct.unpack_from('<%dI' % ((lay['zls'] - lay['rgn']) // 4), tad, lay['rgn'])
    regs = []
    for i in range(len(ws) // 3):
        w0, w1 = ws[3 * i], ws[3 * i + 1]
        if w1 and not (w0 >> 24) & 0x0a:
            regs.append(dict(addr=w1, c=(w0 >> 16) & 0xff, r=w0 & 0xfff, m=(w0 >> 12) & 0xf, i=i))
    return regs


def place(regs, key):
    """replay the allocation in the order key(c, r): a macrotile's blocks fill its current
    page, 32 a page, a new page when the next block does not fit; pages ranked by address.
    Returns (exact, total, real pages, replayed pages)."""
    pages = sorted({x['addr'] >> 12 for x in regs})
    rank = {p: i for i, p in enumerate(pages)}
    cur, npg, ok = {}, 0, 0
    for x in sorted(regs, key=lambda x: key(x['c'], x['r'])):
        m = x['m']
        if m not in cur or cur[m][1] == 32:
            cur[m] = [npg, 0]
            npg += 1
        pg, slot = cur[m]
        cur[m][1] += 1
        ok += (rank[x['addr'] >> 12], (x['addr'] & 0xfff) // 128) == (pg, slot)
    return ok, len(regs), len(pages), npg
