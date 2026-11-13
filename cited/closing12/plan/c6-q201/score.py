import re, sys
sys.path.insert(0, '.')
import sample0_rule as r
RAW = '/Users/jtorra/src/resgx545-data/isp/sample-positions/raw.txt'
cases = {}
cur = None
for line in open(RAW):
    m = re.match(r'=== case (.*)', line)
    if m:
        cur = m.group(1); cases[cur] = {}; continue
    m = re.match(r'target: 64x64 hash (0x[0-9a-f]+)', line)
    if m and cur: cases[cur]['hash'] = m.group(1)
    m = re.match(r'tri 64x64 #1: (\d+) triangle', line)
    if m and cur: cases[cur]['count'] = int(m.group(1))
    m = re.match(r'diff: (\d+) of 4096', line)
    if m and cur: cases[cur]['diff'] = int(m.group(1))
obs = {}
for k, d in cases.items():
    if k == 'baseline': n = 0x88
    else:
        m = re.match(r'cmd:16\^=(0x[0-9a-f]+)$', k)
        n = 0x88 ^ int(m.group(1), 16)
    obs[n] = d
print('cases', len(cases), 'distinct values', len(obs), 'complete',
      sum(1 for d in obs.values() if 'hash' in d and 'count' in d))
print('observed distinct hashes', len({d['hash'] for d in obs.values()}), 'diff all 0:',
      all(d['diff'] == 0 for d in obs.values()))
one = {n for n in range(256) if (n & 15) == 8 or (n >> 4) == 8}
for rule in ['SAMPLE0', 'SWAPPED', 'FIXED', 'HALF']:
    img = {n: r.image(rule, n) for n in range(256)}
    cnt_ok = [n for n in range(256) if len(img[n]) == obs[n]['count']]
    # partition: pairs of values agree on equal-image <=> equal-hash
    pbad = 0
    classes_pred = {}
    classes_obs = {}
    for n in range(256):
        classes_pred.setdefault(img[n], []).append(n)
        classes_obs.setdefault(obs[n]['hash'], []).append(n)
    ps = {frozenset(v) for v in classes_pred.values()}
    os_ = {frozenset(v) for v in classes_obs.values()}
    exact_classes = len(ps & os_)
    # per value: its predicted class equals its observed class
    pv = {n: frozenset(classes_pred[img[n]]) for n in range(256)}
    ov = {n: frozenset(classes_obs[obs[n]['hash']]) for n in range(256)}
    part_ok = [n for n in range(256) if pv[n] == ov[n]]
    def split(s): return (len([n for n in s if n in one]), len([n for n in s if n not in one]))
    print(f'{rule}: count held {len(cnt_ok)}/256 (one-nibble {split(cnt_ok)[0]}/{len(one)}, '
          f'two-nibble {split(cnt_ok)[1]}/{256-len(one)}); '
          f'predicted classes {len(ps)}, observed {len(os_)}, identical classes {exact_classes}; '
          f'values with identical class {len(part_ok)}/256 '
          f'(one {split(part_ok)[0]}, two {split(part_ok)[1]}); '
          f'PASS={len(cnt_ok)==256 and ps==os_}')
    bad = [n for n in range(256) if n not in cnt_ok]
    print('  first count failures (n, pred, obs):', [(hex(n), len(img[n]), obs[n]['count']) for n in bad[:8]])
