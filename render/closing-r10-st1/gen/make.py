#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r10-st1's generator: tables/st1.txt and predictions/st1.tsv from gen/st1.py (tool t10).

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
import st1 as S  # noqa: E402

HEADER = """# R10-4 (a) / R10-6 (a), seeds plan section 5 "Stage st1", Q121 (and the ranking plan's R10-4 Q071 stencil rows): the
# stencil test (ISP word 2, --isp2) against the loaded stencil (E467's control 0x0017300e), EQUAL with reference 0, SOP3
# invert, fills bytes[:S] and 0x03020100, 64 x 32 and 40 x 20. Frozen per pixel and per stored stencil byte: H-DEPTHORD,
# H-RASTER, H-F2ORD, H-NOLOAD; q071-*: H-INERT (byte for byte their base rows). Controls that can fail: st1-always (2048
# drawn), st1-never (0), st1-noisp (2048). Stop: any fault."""


def build():
    import score as SC
    rows, pred = [], ["case\tquantity\tvalue\tmodel\tset\tsource\n"]
    controls = {}
    for name, sset, knobs, args, q in S.jobs():
        rows.append(f"{name}|{sset}|safe|{knobs}|t10|{args}")
        for quantity, mv in q.items():
            for m, v in mv.items():
                pred.append(f"{name}\t{quantity}\t{v}\t{m}\t{sset}\tgen/st1.py\n")
        if sset == "control":
            reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")][0]
            controls[name] = (tuple(reads), dict(name=name, args=args))
    scorekit.refuse_unreadable(controls, SC.producible)
    return {"tables/st1.txt": ("#stage st1\n#limit 0\n" + HEADER + "\n" + "\n".join(rows) + "\n").encode(),
            "predictions/st1.tsv": "".join(pred).encode()}


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
