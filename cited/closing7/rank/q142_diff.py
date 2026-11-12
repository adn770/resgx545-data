# Q142, round 7 ranking: where do the dwords that CR_TE_AA bits 30/31 change sit (E504's dumps)?
# Read-only over resgx545-data/isp/msaa-te-dumps/dumps (raw binary, gzip). Prints runs of changed
# dword indices and old -> new values against the 0x20000000 job of the same size and mode.
import gzip, struct, sys
D = '/Users/jtorra/src/resgx545-data/isp/msaa-te-dumps/dumps/'
def load(n, kind):
    b = gzip.open(D + f'{n}.{kind}.txt.gz').read()
    return struct.unpack(f'<{len(b)//4}I', b[:len(b)//4*4])
pairs = [('te-m2-20-64x64', 'te-m2-60-64x64'), ('te-m2-20-64x64', 'te-m2-a0-64x64'),
         ('te-m0-60-64x64', 'te-m2-60-64x64'), ('te-m2-20-64x64', 'te-m2-e0-64x64'),
         ('te-m2-20-128x128', 'te-m2-e0-128x128')]
for a, b in pairs:
    for kind in ('param', 'tadata'):
        A, B = load(a, kind), load(b, kind)
        d = [i for i in range(min(len(A), len(B))) if A[i] != B[i]]
        print(f'== {a} -> {b} {kind}: {len(d)} differ (len {len(A)})')
        runs = []
        for i in d:
            if runs and i - runs[-1][1] <= 8: runs[-1][1] = i
            else: runs.append([i, i])
        for s, e in runs[:40]:
            ch = [f'{i}:{A[i]:08x}>{B[i]:08x}' for i in d if s <= i <= e]
            print(f'  [{s}..{e}] n={len(ch)} ' + ' '.join(ch[:8]) + (' ...' if len(ch) > 8 else ''))
