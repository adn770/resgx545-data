#!/usr/bin/env python3
"""Q111: the three repeats of the irq matrix against H111-rep (predictions-followup8.tsv): python3 -B
recompute_irq_repeat.py DIR (holding event-irq-repeat1..3). Reads only the kept gz outputs."""
import collections, gzip, pathlib, re, sys
root = pathlib.Path(sys.argv[1]); here = pathlib.Path(__file__).resolve().parent.parent
pred = {}
for line in (here / "predictions-followup8.tsv").read_text().splitlines()[1:]:
    n, q, v, m = line.split("\t"); pred[n] = v
tot = collections.Counter(); rows = collections.defaultdict(dict)
for i in (1, 2, 3):
    d = root / ("event-irq-repeat%d" % i)
    for f in sorted(d.glob("irq-*.txt.gz")):
        name = f.name[:-7]
        t = gzip.open(f).read().decode("utf-8", "replace")
        a = re.search(r"kregnow after: host_irqs (\d+) extra (\d+)", t)
        if not a: continue
        ex = int(a[2])
        rows[name][i] = ex
        if name in pred:
            ok = ("Y" if ex else "N") == pred[name]
            tot[ok] += 1
        elif "none" in name:
            tot[("control", ex == 0)] += 1
for n in sorted(rows):
    print("%-22s declared %-2s extra per repeat %s" % (n, pred.get(n, "none"), [rows[n].get(i) for i in (1, 2, 3)]))
print("H111-rep: as declared %d of %d case-runs; controls with no extra %d of %d" % (tot[True], tot[True] + tot[False], tot[("control", True)], tot[("control", True)] + tot[("control", False)]))
