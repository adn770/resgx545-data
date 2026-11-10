"""Post hoc: histogram of the stored depth dump of g-e8 jobs (values as float32)."""
import sys, gzip, glob, collections, numpy as np
for p in sys.argv[1:]:
    b = gzip.open(p).read()
    a = np.frombuffer(b[: len(b) // 4 * 4], dtype="<u4")
    c = collections.Counter(a.tolist())
    top = c.most_common(6)
    print(p.split("/")[-1], len(a), "dwords; distinct", len(c), "top",
          [(hex(v), float(np.array([v], dtype="<u4").view("<f4")[0]), n) for v, n in top])
