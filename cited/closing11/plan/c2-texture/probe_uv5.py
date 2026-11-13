"""Exploratory (post hoc, after the freeze): what the mode 5 jobs read by region."""
import sys, collections
sys.argv = ["x"]
exec(open("score_a.py").read().split('print("job;')[0])
for name, w, h, um, vm, st in jobs:
    if um != 5 or vm != 5: continue
    reg = collections.defaultdict(collections.Counter)
    for s, t, got in st:
        a = "s<0" if s < 0 else ("s>=W" if s >= w else "s in")
        b = "t<0" if t < 0 else ("t>=H" if t >= h else "t in")
        pm = R.predict("H-MAX", w, h, um, vm, s, t)
        reg[(a, b)][(got, pm)] += 1
    print(name, w, h)
    for k, c in sorted(reg.items()):
        print("  ", k, sum(c.values()), "distinct (read, H-MAX pred):", len(c), sorted(c.items())[:4])
