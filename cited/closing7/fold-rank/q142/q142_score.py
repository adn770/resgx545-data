# SPDX-License-Identifier: MIT
# Q142, round 7 fold: score the frozen predictions (q142_grid.py predict) on the held-out job,
# te-m2-e0-128x128 of E504 (TA data and the stream blocks its parameter dump opens). Verdicts:
# a hypothesis is held when 0 of the 6144 TA-data dwords differ and its streams are exactly the
# opened blocks, FAILED otherwise. The control H-HALF must fail (it is refuted at 64 x 64 by the
# entry count): if it holds the scorer cannot tell. The input self-check (the 0x20000000 model
# gives the input back) is printed by the predict step and gates the headline here too.
import sys
from q142_grid import load, TADATA_LEN
from q142_fit import opened

data, prefix, job, selfcheck = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])


def read(path):
    words, ptrs = [0] * TADATA_LEN, []
    for line in open(path):
        if line.startswith('# pointers'):
            ptrs = [int(p, 16) for p in line.split()[2:]]
        else:
            i, v = line.split()
            words[int(i)] = int(v, 16)
    return words, ptrs


want, blocks = load(data, job, 'tadata'), opened(load(data, job, 'param'))
verdict = {}
for name, suffix in (('H-GRID', 'grid'), ('H-HALF', 'half')):
    pred, ptrs = read(f'{prefix}.{suffix}.txt')
    diff = [i for i in range(TADATA_LEN) if pred[i] != want[i]]
    held = not diff and ptrs == blocks
    verdict[name] = held
    print(f'{name}: {len(diff)} of {TADATA_LEN} TA-data dwords differ '
          f'(held-out job has {sum(1 for v in want if v)} non-zero); streams {len(ptrs)}, opened '
          f'blocks {len(blocks)}, same set {ptrs == blocks}: {"held" if held else "FAILED"}')
    for i in diff[:12]:
        print(f'  dword {i}: predicted {pred[i]:08x}, dumped {want[i]:08x}')
control = not verdict['H-HALF'] and selfcheck == 0
print(f'control H-HALF {"FAILED as required" if not verdict["H-HALF"] else "held: cannot tell"}; '
      f'input self-check {selfcheck} dwords off: {"pass" if control else "cannot tell"}')
if control:
    print(f'HEADLINE (1 held-out job decided): H-GRID {"held" if verdict["H-GRID"] else "FAILED"}')
else:
    print('HEADLINE: cannot tell (control)')
