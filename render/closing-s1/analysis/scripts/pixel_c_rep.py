"""POST HOC: where c-k7-x-rep differs from c-k7-x (dwords, tag nibble, position)."""
import pathlib, sys
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score"))
from s1lib import Kept, rows_of
k = Kept(S1 / "out" / "p-c")
a, b = np.array(rows_of(k.out("c-k7-x"))), np.array(rows_of(k.out("c-k7-x-rep")))
print("shape", a.shape, b.shape)
d = np.argwhere(a != b)
print("differing dwords", len(d))
for y, x in d[:40]:
    print(f"  ({x},{y}) {a[y,x]:#010x} -> {b[y,x]:#010x}  tag {a[y,x]&15} -> {b[y,x]&15}")
