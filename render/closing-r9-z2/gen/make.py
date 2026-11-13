#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r9-z2's generator: tables/z2.txt and predictions/z2.tsv from gen/z2.py.

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
import z2 as Z  # noqa: E402

HEADER = """# R9c-F / X-3, Q101: bit 19 with the integer stored formats at a negative depth. The depth is made negative by the
# viewport's z offset (--poke blk:10, after the MTE's clip, E287), not by --tri-z outside [0, 1] (clipped away).
# Ramps a (-0.25 to 0.25) and b (-0.75 to -0.25) at 256 x 128, G 7; frozen per dword from each ramp's format-0 dump:
# H-ABS / H-CLAMP / H-WRAP / H-B19 (gen/z2.py). Controls that can fail: the two format-0 jobs (every dword of the
# 64 tiles stored, E831). Stop: any fault or hang (none in E466/E490's format jobs)."""


def build():
    import score as SC
    rows, pred = [], ["case\tquantity\tvalue\tmodel\tset\tsource\n"]
    controls = {}
    for name, st, knobs, args, q in Z.jobs():
        rows.append(f"{name}|{st}|safe|{knobs}|t9|{args}")
        for quantity, mv in q.items():
            for m, v in mv.items():
                pred.append(f"{name}\t{quantity}\t{v}\t{m}\t{st}\tgen/z2.py\n")
        if st == "control":
            reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")][0]
            controls[name] = (tuple(reads), dict(name=name, args=args))
    scorekit.refuse_unreadable(controls, SC.producible)
    return {"tables/z2.txt": ("#stage z2\n#limit 0\n" + HEADER + "\n" + "\n".join(rows) + "\n").encode(),
            "predictions/z2.tsv": "".join(pred).encode()}


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
