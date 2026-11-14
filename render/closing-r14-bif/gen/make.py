#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r14-bif's generator: tables/refill.txt and predictions/refill.tsv from gen/rf.py
(tool t14).

  python3 gen/make.py          write them
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import scorekit  # noqa: E402
import rf as R  # noqa: E402

STAGE = "refill"
HEADER = """# R14-4 (a), plan section 2 "r14-bif", Q108's stale-data clause (CACHECONSISTENT on data cached before the host's
# write): E1029's zb-c-id form (64 x 32, depth test never, the store holds the load) run twice on one context; render 1
# loads the index, the host refills the depth buffer with 0x3f400000 (--refill 2:depth=V, t14) and render 2 loads it
# again, with CACHECONSISTENT (vm_pte_flags 0x8) on the depth buffer's mapping and without. Frozen per refill row (store
# 2): H-CC-COHERENT / H-CC-STALE, H-NC-COHERENT / H-NC-STALE; H-CC-NOOP without a refill. Controls that can fail:
# rf-c-plain, rf-c-depth (both stores E1029's zb-c-id), rf-c-unread (render 1 never loads: store 2 must be V). Stop: any
# fault or hang (4); hook_check (24): a job line not ok, other buffer addresses, no kernel PTE line on a knob row, no
# refill line on a refill row."""


def build():
    import score as SC
    rows, controls = [], {}
    pred = ["case\tquantity\tvalue\tmodel\tset\tsource\n"]
    for name, sset, knobs, args, q in R.jobs():
        rows.append(f"{name}|{sset}|safe|{knobs}|t14|{args}")
        for quantity, mv in q.items():
            for m, v in mv.items():
                pred.append(f"{name}\t{quantity}\t{v}\t{m}\t{sset}\tgen/rf.py\n")
        if sset == "control":
            reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")][0]
            controls[name] = (tuple(reads), dict(name=name, args=args))
    scorekit.refuse_unreadable(controls, SC.producible)
    return {f"tables/{STAGE}.txt": (f"#stage {STAGE}\n#limit 0\n" + HEADER + "\n"
                                    + "\n".join(rows) + "\n").encode(),
            f"predictions/{STAGE}.tsv": "".join(pred).encode()}


def main(argv):
    files = build()
    bad = []
    for rel, b in files.items():
        p = os.path.join(KP, rel)
        if "--check" in argv:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                bad.append(rel)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(b)
    print("\n".join(f"differs: {b}" for b in bad) or f"ok: {len(files)} files")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
