#!/usr/bin/env python3
"""Q111: event-irq-matrix recomputed from the kept gz outputs only. python3 -B recompute_irq.py
DIR/event-irq-matrix. For each kind and each armed bit of CR_EVENT_HOST_ENABLE (0x0130 = 0x4000 | bit)
or CR_EVENT_HOST_ENABLE2 (0x0110 = bit): the host interrupts the kregnow counter shows after the job
(host_irqs, extra = interrupts with no SW_EVENT), the status words the ISR read (last). Compares with
predictions-declared.tsv (H111-fw, H111-ctl: extra_interrupt Y / N / ?)."""
import collections, gzip, pathlib, re, sys

d = pathlib.Path(sys.argv[1])
here = pathlib.Path(__file__).resolve().parent.parent
preds = {}
for line in (here / "predictions-declared.tsv").read_text().splitlines()[1:]:
    n, q, v, m = line.split("\t")
    if q == "extra_interrupt":
        preds[n] = (v, m)
rows = []
for f in sorted(d.glob("irq-*.txt.gz")):
    name = f.name[:-len(".txt.gz")]
    t = gzip.open(f).read().decode("utf-8", "replace")
    m = re.search(r"case \S+ kind (\S+) enable (\S+)=(\S+)", t)
    a = re.search(r"kregnow after: host_irqs (\d+) extra (\d+) last (0x\w+) (0x\w+)", t)
    b = re.search(r"kregnow before: host_irqs (\d+)", t)
    job = re.search(r"job: job: (\w+)", t)
    if not (m and a):
        print(name, "unparsed"); continue
    rows.append(dict(name=name, kind=m[1], reg=m[2], val=m[3], irqs=int(a[1]), extra=int(a[2]),
                     last=(a[3], a[4]), job=job[1] if job else "?", before=int(b[1]) if b else None))
score = collections.Counter()
for r in rows:
    p = preds.get(r["name"])
    got = "Y" if r["extra"] > 0 else "N"
    tag = ""
    if p and p[0] in "YN":
        ok = p[0] == got
        score[(p[1], ok)] += 1
        tag = "declared %s %s" % (p[0], "OK" if ok else "MISS")
    elif p:
        tag = "declared ? (exploration)"
    print("%-22s %-8s %s=%s job %s host_irqs %d extra %d last %s %s %s" % (
        r["name"], r["kind"], r["reg"], r["val"], r["job"], r["irqs"], r["extra"], r["last"][0], r["last"][1], tag))
for (m, ok), n in sorted(score.items()):
    print("SCORE %s %s: %d" % (m, "as declared" if ok else "not as declared", n))
