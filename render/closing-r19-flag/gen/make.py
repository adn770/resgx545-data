#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/make.py: r19-flag's table and predictions (closing19/plan/rank-round19.md section 5, S4;
closing19/DECISIONS-R19.md: the user OK'd fl-junk, R19-3 a). Standard library only; no repository
file is read (the rows are our own argv, the predictions come from the kernel's arithmetic and the
records named in their source column).

  python3 gen/make.py          write tables/fl.txt and predictions/fl.tsv
  python3 gen/make.py --check  exit 1 when a written file is not what the generator writes

One stage, fl: the control first (fl-ctl, safe, no fill: ld's base form on the final-PB knob),
then the two planned rows (fl-junk-a and fl-junk-b: the same job with page 6 of the TA data,
the state page of a 1024x768 context, filled with E631's ramp 0xa5000000 + i before the closing
render). #limit counts exactly the expectfault rows that are not controls (E946): 2."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ld's form (plan section 3a, E631 Part B): a 1024x768 default triangle, two renders, the first a
# geometry kick that overflows at P 0x28 (one partial render, E625) and leaves the scene open, the
# second closes it on N = 0x100 pages (--final-pb-pages: the free list max(P, N), the final's
# 0x0624 = N - 0x22 = 0xde, so no overflow). --dump-each writes tri.1 (after the kick, before the
# fill), --words the kernel's command words, --regs the thresholds and counts after each render.
BASE = ('tri --width 1024 --height 768 -n 2 --geometry 1 --final-pb-pages 0x100 --keep-going '
        '--keep-overflow --wait-ms 20000 --dump-render "$W" --dump-each --words "$W" '
        '--regs 0x0600-0x0750')
FILL = ' --tadata-fill-render 2:6:0xa5000000:ramp'      # E631's junk: page 6, 1024 dwords, ramp
P = "dbg:render_pb_pages=0x28"


def rows():
    return [
        ("fl-ctl", "control", "safe", f"{P} expectdiff after reads:job,ovf,thr,lists", "t18b", BASE),
        ("fl-junk-a", "fit", "risky", f"{P} expectfault expectdiff after", "t18b", BASE + FILL),
        ("fl-junk-b", "heldout", "risky", f"{P} expectfault expectdiff after", "t18b", BASE + FILL),
    ]


HEAD = [
    "r19-flag fl, Q045 (E1086): does a load task read the lists a partial render stored in the state "
    "page? ld's form (E631 Part B on the final-PB knob: a geometry kick that overflows at P 0x28, "
    "the closing render on N 0x100 pages, which does not overflow, so it no longer stores over page 6 "
    "before any read), with page 6 filled with E631's junk ramp 0xa5000000 + i between the two renders. "
    "FLAGGED (the user OK'd it, DECISIONS-R19 R19-3 a): a planned fault or a recovered hang is possible.",
    "fl-ctl is the stage's control (safe, no fill, no expectfault): hook_check stops the stage (24, "
    "the session ends) unless the kick overflowed once, the final read 0x0624 = 0xde (N - 0x22) and "
    "page 6 held lists before any fill. fl-junk-a (fit) and fl-junk-b (held out, a replicate) are the "
    "planned rows: #limit 2 counts them, a fault or hang there is a reading, the strict health "
    "follows each; a junk row that completes must show the kick's overflow and the lists (its own "
    "threshold is a reading); any SGX recovery failed line, an end that is neither a BIF fault nor a "
    "recovered hang, or a fault before the fill was armed (hook_fault) stops the session.",
]


# (case, quantity, value, model, set, source); quantities: the control's reading keys (job, ovf,
# thr, lists), end (ok, fault, hang) and same (1 when the final's last target hash equals
# fl-ctl's) for the junk rows
def predictions():
    p = []
    src = "E625 (one partial render at P 0x28); E1078 H-UPD, N - 0x22 [infer: the update is unmeasured]; E627, E631"
    for k, v in (("job", "ok"), ("ovf", "1"), ("thr", "0xde"), ("lists", "yes")):
        p.append(("fl-ctl", k, v, "H-REF", "control", src))
    s = "E631 (junk in page 6 changed no render, but the next kick stored over its first 34 dwords); plan S4 [infer]"
    models = (("H-NOLOAD", "ok", "1"), ("H-LOAD-FAULT", "fault", None), ("H-LOAD-HANG", "hang", None),
              ("H-LOAD-CORRUPT", "ok", "0"))
    for n, sset in (("fl-junk-a", "fit"), ("fl-junk-b", "heldout")):
        for m, end, same in models:
            p.append((n, "end", end, m, sset, s))
            if same is not None:
                p.append((n, "same", same, m, sset, s))
    return p


def outputs():
    t = rows()
    planned = [r for r in t if "expectfault" in r[3].split() and r[1] != "control"]
    body = ["#stage fl", f"#limit {len(planned)}"] + [f"# {ln}" for ln in HEAD]
    body += ["|".join(r) for r in t]
    pred = ["case\tquantity\tvalue\tmodel\tset\tsource"] + ["\t".join(r) for r in predictions()]
    return {"tables/fl.txt": ("\n".join(body) + "\n").encode(),
            "predictions/fl.tsv": ("\n".join(pred) + "\n").encode()}


def main(argv):
    out = outputs()
    bad = []
    for rel, b in sorted(out.items()):
        p = os.path.join(KP, rel)
        if "--check" in argv:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                bad.append(rel)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b)
    if "--check" in argv:
        print("gen: current" if not bad else "gen: NOT current: " + ", ".join(bad))
        return 1 if bad else 0
    print("gen: wrote " + ", ".join(sorted(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
