#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r32-misc's post-hoc readings (not frozen), from the kept files of an attempt.

  posthoc.py out/ATT    one line a row, then totals

Per row: snap0 and snap9 CR_CACHE_CTRL, the kept miscinfo answer (us), the served GETMISCINFO
answers the kernel logged after the last `SGX boot: kicking the EDM` before the row's snap0 mark
(score.kicks over the stage's kernel.log, the held rows too), every answer's us, and m2's
timeline: the first sample, the changes, the change's ms from the tool's start."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402

K = SC.K


def main(att):
    tot = {"rows": 0, "boots": 0, "answers": [], "word_us": []}
    for st in SC.STAGES:
        d = os.path.join(att, st)
        log = open(os.path.join(d, "kernel.log"), errors="replace").read()
        run = re.search(r"resgx545 r32m snap \S+ 0 \S+ \S+ (\S+)", log).group(1)
        tot["boots"] += log.count("SGX boot: kicking the EDM")
        tot["answers"] += [int(x) for x in re.findall(r"answered after ([0-9]+) us", log)]
        for r in K.table(KP, st):
            n = r["name"]
            mi = K.miscinfo(d, n)
            a = SC.analyse(K.text(d, n + ".txt"), K.text(d, n + ".snap0.regs"),
                           K.text(d, n + ".snap9.regs"), mi)
            k = SC.kicks(log, n, run=run)
            tot["rows"] += 1
            if mi:
                tot["word_us"].append(mi["us"])
            extra = " ".join(f"{q}={a[q]}" for q in ("ccfirst", "ccn", "ccword", "ccstart", "ivl")
                             if q in a)
            print(f"{st} {n} word={int('pre:miscinfo' in r['knobs'])} cache={a['cache']} "
                  f"cache9={a['cache9']} mi={a.get('mi')} mius={a.get('mius')} kicks={k} "
                  f"diff={a['diff']} {extra}".rstrip())
    us = tot["answers"]
    print(f"total: {tot['rows']} rows, {tot['boots']} boot kicks, {len(us)} logged answers "
          f"{min(us)} to {max(us)} us; the word's {len(tot['word_us'])} answers "
          f"{min(tot['word_us'])} to {max(tot['word_us'])} us")


if __name__ == "__main__":
    main(sys.argv[1])
