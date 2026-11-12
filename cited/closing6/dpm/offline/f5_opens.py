#!/usr/bin/env python3
"""F5 check of its own premise (post hoc, fit side): f5lib's geometry against the stream blocks
F3 read in the dumps of completed jobs.  For 2048x2048 and 4096x2048, the regions with a stream
and the objects at which regions open blocks (with lag 3, F5's fit), against f3_streams.out's
lines for R2-geo c3-2048-cal and R3-geo c5a-cal."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import f5lib as F

kept, cur = {}, None
for l in open(os.path.join(HERE, 'f3_streams.out')):
    m = re.match(r'== (\S+) \((\d+x\d+)\): (\d+) regions', l)
    if m: cur = (m.group(1), m.group(2), int(m.group(3)))
    if cur and cur[0] in ('r2-geo/g-c3/c3-2048-cal', 'r3-geo/g-c5/c5a-cal') and 'opening blocks' in l:
        kept[cur[1]] = (cur[2], dict((int(a), int(b)) for a, b in re.findall(r'(\d+):(\d+)', l.split(':', 1)[1])))
for wh in ('2048x2048', '4096x2048'):
    w, h = (int(x) for x in wh.split('x'))
    ents = F.entries(w, h)
    S, opens, after = F.replay(w, h, ents, 3)
    model = {b: n for b, n in opens.items() if n}
    regs = len({(c, r) for v in ents.values() for c, r, dw in v})
    nk, ko = kept[wh]
    print(f'{wh}: regions with a stream model {regs} dump {nk}; block openings by object '
          f'{"identical" if model == ko else "DIFFER"} ({len(model)} objects, {sum(model.values())} blocks model, '
          f'{sum(ko.values())} dump)')
    if model != ko:
        print('   differ at', {b: (model.get(b), ko.get(b)) for b in sorted(set(model) | set(ko)) if model.get(b) != ko.get(b)})
