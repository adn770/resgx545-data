#!/usr/bin/env python3
"""Job outcomes per script from the kept outputs only: python3 -B recompute_counts.py DIR. A job is
'completed' unless its output says failed (job faulted / job hung / overflowed / rejected)."""
import collections, gzip, pathlib, re, sys
root = pathlib.Path(sys.argv[1])
tot = collections.Counter()
for d in sorted(p for p in root.iterdir() if p.is_dir()):
    cf = d / "cases.tsv"
    if not cf.exists():
        continue
    n = collections.Counter()
    sets = collections.Counter()
    for line in cf.read_text().splitlines()[1:]:
        name, script, sset = line.split("\t")[:3]
        f = d / (name + ".txt.gz")
        if not f.exists():
            n["not kept"] += 1; continue
        t = gzip.open(f).read().decode("utf-8", "replace")
        m = re.search(r"failed: (job [a-z]+|[^\n(]+)", t)
        n[("failed: " + m[1].strip()) if m else "completed"] += 1
        sets[sset] += 1
    print("%-22s jobs %3d  %s  sets %s" % (d.name, sum(n.values()), dict(n), dict(sets)))
    tot.update(n)
print("TOTAL jobs %d %s" % (sum(tot.values()), dict(tot)))
