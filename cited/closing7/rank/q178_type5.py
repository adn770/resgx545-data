# Q178, round 7 ranking (offline, data): what E567's three TEXTYPE 5 jobs (rt5-2d, rt5-3d-w5,
# rt5-3d-w15; 16 x 16 map texture, dword i = 0xD0000000 | i, 64 x 32 fill) stored per pixel.
# Read-only over resgx545-data/texture/p1132/tx-types-risky.
import gzip, re, collections
D = '/Users/jtorra/src/resgx545-data/texture/p1132/tx-types-risky/'
for n in ('rt5-2d', 'rt5-3d-w5', 'rt5-3d-w15', 'rt4-2d'):
    rows = [l.split(': ', 2)[2].split() for l in gzip.open(D + n + '.txt.gz').read().decode().splitlines()
            if re.search(r': row \d+: ', l)]
    distinct_rows = collections.Counter(' '.join(r) for r in rows)
    vals = collections.Counter(v for r in rows for v in r)
    by_col = {x % 16: {r[x] for r in rows} for x in range(len(rows[0]))}
    print(n, 'rows', len(rows), 'distinct rows', len(distinct_rows), 'values', dict(vals.most_common(3)))
    if n.startswith('rt5'):
        print('  value by x mod 16:', ' '.join(f'{k}:{"/".join(sorted(v))}' for k, v in sorted(by_col.items())))
