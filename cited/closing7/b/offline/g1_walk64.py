#!/usr/bin/env python3
"""G1 (round 7 dpm offline stage, H-WALK64, Q211).  The TA takes a region's stream block (128
bytes, 32 a page) walking the target in strips of 64 pixel rows, each strip in 64 x 64-pixel
blocks left to right, a block's regions (32 x 16 pixels) row by row; a macrotile's blocks fill
its current page and it takes a new page when the next block does not fit.  The test needs no
model of the scene: the regions that the dump itself shows with a stream are replayed in that
order (olib.place, the planner's q211_walk64.py logic unchanged) and every region's (page rank,
slot) is compared with the address in its header.

Dumps scored (rule fixed here, before any held-out dump is opened): every PB dump under
render/closing-*/out of a job whose cases.tsv args draw one object of the tool's triangle in one
kick and complete it: tri or --tri (default, moved, --tri-full, --tri-v, --coords, --vtx-coords...),
no --vertices other than 3, no --geometry, no -n above 1, no --obj2*, no --aa4 (4x layout), no
--poke, --kpoke or --kpoke-render (words changed by hand), no --vdm, --fault, --cmd or
--tadata-fill-render; exactly one param dump of the last render (--dump-each's per-render
copies tri.N.* left out: with -n 1 they repeat it) with its tadata; and a timeline
(<name>.txt.gz) sampling 0x0658 with no partial render, or, without one, a target whose every
region taking a block could not reach the first threshold (1 + n * n * ceil(mx * my / 32) pages
at most, the macrotile grid of dpm_words.mtile_grid, against P - 0x22 with P the cases.tsv P
column or the tool's default 0x422).  A job with --max-width/--max-height is
scored with the context's layout, as its own class.  A job that meets the args rule but whose
completion cannot be read is listed and not scored.  A missing tadata file stops the script.

Labels: u-2048 (closing-r1-pixgeo) is the fit dump; SEMI are the dumps the planner's q211_walk.py
and q211_walk64.py printed or scored (FIT_SEEN below); every other dump is HELD OUT.
Verdict: H-WALK64 HELD iff every region of every scored dump is placed exactly, else REFUTED.
Row and column order are printed beside it as a tally.  `--seen` scores only the fit and SEMI
dumps (the dry run before the freeze).  Read-only, public data; standard library only."""
import collections, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import olib as O

ORDERS = {'walk64': lambda c, r: (r // 8, c // 4, r, c),
          'row': lambda c, r: (r, c),
          'col': lambda c, r: (c, r)}
FIT = {('closing-r1-pixgeo', 'u-2048')}
SEEN = {('closing-r1-pixgeo', n) for n in ('u-2048-1536', 'u-1280', 'u-640', 'u-512-m128',
                                           'u-4096-m1024', 'u-m32', 'u-m384-288', 'u-ctl-1',
                                           'u-m-128-96', 'u-m0-96')}
SEEN |= {('closing-r4-render4x', 'o8-1x-4096x4096-p422')}
SEEN |= {('closing-r6-dpm', 'v-cal-c4'), ('closing-r6-dpm', 'v-cal-c8')}   # PB page 1 read
BAD = ('--geometry', '--aa4', '--poke', '--kpoke', '--kpoke-render', '--vdm',
       '--fault', '--cmd', '--tadata-fill-render', '--obj2', '--obj2-blk', '--obj2-pixel')


def eligible():
    seen = set()
    for ds, stg, d, name, args, prow in O.cases():
        toks = args.split()
        if not toks or not (toks[0] == 'tri' or '--tri' in toks) or any(b in toks for b in BAD):
            continue
        v, n = O.opt(args, '--vertices'), O.opt(args, '-n')
        if (v and int(v) != 3) or (n and int(n) != 1):
            continue
        pres = [p for p in O.dumps(d, name) if not O.re.search(r'\.\d+\.$', p)]
        if len(pres) != 1 or (d, name) in seen:
            continue
        seen.add((d, name))
        w, h = int(O.opt(args, '--width')), int(O.opt(args, '--height'))
        mw, mh = O.opt(args, '--max-width'), O.opt(args, '--max-height')
        lw, lh = (int(mw or w), int(mh or h))
        tl = os.path.join(d, name + '.txt.gz')
        rows = O.load(tl)[1] if os.path.exists(tl) else []
        if rows and 0x658 in rows[0][1]:
            if O.stretches(rows):
                continue
        else:
            P = int(prow.get('P') if (prow.get('P') or '-') != '-' else '0x422', 0)
            n, mx, my = O.D.mtile_grid(lw, lh)
            bound = 1 + n * n * -(-(mx * my) // 32)
            if bound > P - 0x22:
                yield ds, stg, name, pres[0], (w, h), (lw, lh), 'no completion reading'
                continue
        yield ds, stg, name, pres[0], (w, h), (lw, lh), None


def main():
    only_seen = '--seen' in sys.argv
    tal = collections.defaultdict(lambda: collections.Counter())
    fails, skipped = [], []
    for ds, stg, name, pre, (w, h), (lw, lh), why in eligible():
        lab = 'fit' if (ds, name) in FIT else 'SEMI' if (ds, name) in SEEN else 'held'
        if only_seen and lab == 'held':
            continue
        if why:
            skipped.append('%s/%s/%s (%s)' % (ds[8:], stg, name, why))
            continue
        if not os.path.exists(pre + 'tadata.bin.gz'):
            raise SystemExit('missing ' + pre + 'tadata.bin.gz')
        regs = O.regions_of(pre, lw, lh)
        cls = (lab, 'context' if (lw, lh) != (w, h) else 'target')
        t = tal[cls]
        t['dumps'] += 1
        res = {}
        for o, key in ORDERS.items():
            ok, tot, real, npg = O.place(regs, key)
            res[o] = (ok, tot, real, npg)
            t[o] += ok
            t[o + ' dumps exact'] += ok == tot and real == npg
        t['blocks'] += len(regs)
        ok, tot, real, npg = res['walk64']
        line = '%-5s %-22s %-34s %4dx%-4d ctx %4dx%-4d blocks %5d pages %3d | walk64 %5d (pages %3d) row %5d col %5d' % (
            lab, ds[8:], stg + '/' + name, w, h, lw, lh, tot, real, ok, npg, res['row'][0], res['col'][0])
        print(line)
        if not (ok == tot and real == npg):
            fails.append(line)
    print()
    for s in skipped:
        print('not scored:', s)
    print('\nlabel   class    dumps  blocks  walk64 (dumps exact)  row (dumps exact)  col (dumps exact)')
    allb = allok = 0
    for cls in sorted(tal):
        t = tal[cls]
        allb += t['blocks']; allok += t['walk64']
        print('%-7s %-8s %5d %7d  %7d (%d)  %7d (%d)  %7d (%d)' % (cls[0], cls[1], t['dumps'], t['blocks'], t['walk64'],
              t['walk64 dumps exact'], t['row'], t['row dumps exact'], t['col'], t['col dumps exact']))
    held = [c for c in tal if c[0] == 'held']
    hb = sum(tal[c]['blocks'] for c in held); hok = sum(tal[c]['walk64'] for c in held)
    print('\nall: walk64 %d of %d blocks; held out: %d of %d blocks in %d dumps; not scored %d' % (
        allok, allb, hok, hb, sum(tal[c]['dumps'] for c in held), len(skipped)))
    if only_seen:
        print('DRY RUN (fit and SEMI dumps only): no verdict')
    else:
        print('VERDICT H-WALK64:', 'HELD' if not fails and allb else 'REFUTED', '(%d dumps off)' % len(fails))


if __name__ == '__main__':
    main()
