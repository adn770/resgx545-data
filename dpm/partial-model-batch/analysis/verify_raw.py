#!/usr/bin/env python3
"""verify every NAME.gz of a run directory against raw.sha256 (raw sha256 of the gunzipped file); prints a count."""
import gzip, hashlib, os, sys
bad = n = 0
for d in sorted(os.listdir(sys.argv[1])):
    p = os.path.join(sys.argv[1], d, "raw.sha256")
    if not os.path.exists(p):
        continue
    for line in open(p):
        f = line.split()
        if len(f) != 3:
            continue
        g = os.path.join(sys.argv[1], d, f[0] + ".gz")
        n += 1
        if not os.path.exists(g) or hashlib.sha256(gzip.open(g).read()).hexdigest() != f[2]:
            bad += 1
            print("BAD", d, f[0])
print(f"{n} files checked, {bad} bad")
