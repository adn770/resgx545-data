# SPDX-License-Identifier: MIT
# Q142, round 7 fold: H-GRID and H-HALF on the fit set, E504's 64 x 64 jobs (seen by the round 7
# ranking): each job's TA data predicted from its 0x20000000 twin of the same mode, dword for dword
# over the 6144 dumped, and the streams against the blocks opened in its parameter dump. Read-only.
import sys
from q142_grid import load, h_grid, h_half, TADATA_LEN

FIT = [('te-m0-20-64x64', 'te-m0-60-64x64', 0x60000000), ('te-m0-20-64x64', 'te-m0-a0-64x64', 0xa0000000),
       ('te-m2-20-64x64', 'te-m2-60-64x64', 0x60000000), ('te-m2-20-64x64', 'te-m2-a0-64x64', 0xa0000000),
       ('te-m2-20-64x64', 'te-m2-e0-64x64', 0xe0000000), ('te-m2-20-64x64-r2', 'te-m2-e0-64x64-r2', 0xe0000000),
       ('te-m2-20-64x64', 'te-m2-20-64x64-r2', 0x20000000), ('te-m2-20-64x64', 'te-m2-00-64x64', 0x20000000),
       ('te-m0-20-64x64', 'te-m0-00-64x64', 0x20000000)]


def opened(param):
    """0x80-byte stream blocks in [0x2000, 0x100000) of the slot with a non-zero dword (the dump's
    dword 0 is slot byte 0x1000)."""
    return sorted({(0x1000 + 4 * i) & ~0x7f for i, v in enumerate(param)
                   if v and 0x2000 <= 0x1000 + 4 * i < 0x100000})


def main():
    data = sys.argv[1]
    for base, job, aa in FIT:
        t, want, param = load(data, base, 'tadata'), load(data, job, 'tadata'), load(data, job, 'param')
        blocks = opened(param)
        for name, f in (('H-GRID', h_grid), ('H-HALF', h_half)):
            pred, ptrs = f(t, 64, 64, aa)
            bad = sum(1 for i in range(TADATA_LEN) if pred[i] != want[i])
            print(f'{job:20s} {aa:#010x} {name}: {bad:4d} of {TADATA_LEN} TA-data dwords differ; '
                  f'streams {len(ptrs)} vs opened blocks {len(blocks)}, same set {ptrs == blocks}')


if __name__ == '__main__':
    main()
