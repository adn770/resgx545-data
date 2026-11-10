"""POST HOC: which image has E722's A4 hash 9568c92a... (shared by three different cases)?  Candidates: constant
images, the observed images with the index wrapped modulo the 64 KiB scratch.  Not frozen."""
import hashlib, pathlib, sys
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score"))
from s1lib import Kept, rows_of, pixel_sha
k = Kept(S1 / "out" / "p-d")
T = "9568c92ac5f00beed9d33d0e7fe80caa853d546bd0b6d850981337aa84233f21"
def sha(a): return hashlib.sha256(",".join(f"{int(v) & 0xffffffff:08x}" for v in a.ravel()).encode()).hexdigest()
for shape in ((32, 64), (64, 64), (64, 32)):
    for c in (0, 0xD0000000, 0xFFFFFFFF, 0xDEADBEEF):
        if sha(np.full(shape, c)) == T: print("A4 hash = constant", hex(c), shape)
for n in ("d-L2e2-64", "d-L3e3-64", "d-st-L3e2-64"):
    a = np.array(rows_of(k.out(n)), dtype=np.int64)
    for mod in (0x4000, 0x8000, 0x10000):
        b = 0xD0000000 | ((a & 0x0FFFFFFF) % mod)
        if sha(b) == T: print(n, "wrapped modulo", hex(mod), "gives A4")
print("done")
