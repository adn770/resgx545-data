"""Exploratory (post hoc, after the freeze): distinct reads of the mode 5 jobs where s is inside and t outside."""
import sys, collections
exec(open("score_a.py").read().split('print("job;')[0])
for name, w, h, um, vm, st in jobs:
    if um != 5 or vm != 5: continue
    for lab, cond in (("t<0", lambda s, t: 0 <= s < w and t < 0), ("t>=H", lambda s, t: 0 <= s < w and t >= h)):
        c = collections.Counter(got for s, t, got in st if cond(s, t))
        print(name, w, h, lab, dict(c))
