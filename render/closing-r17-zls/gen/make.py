#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r17-zls's generator: tables/STAGE.txt and predictions/STAGE.tsv for zovp2, zovs2 and
zb20 from gen/z17.py (tool t10).

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
import z17 as Z  # noqa: E402

STAGES = ("zovp2", "zovs2", "zb20")
HEADER = {
    "zovp2": """# R17-1 (a), R17-5 (a), plan section 2 "zovp2", Q299 (E1068): the depth load pass over overlapping tiles WITH
# EDGE TILES (E996's plane over a 0.2 load, 65 x 33 G 1 and 63 x 31 G 0: H-OVL-PASS-EDGE, H-OVL-FIRST, H-EDGE-SKIP,
# H-EDGE-EXT). Controls that can fail: zo2-c-160 (E1064's zo-p-160, kept store byte for byte), zo2-c-65 and zo2-c-63
# (the no-load stores of the two shapes: E996's owner rule, the first also E1041's kept zo-65-ov). Stop: any fault or
# hang; a row without job: ok or without its --depth-pages (24).""",
    "zovs2": """# R17-1 (a), R17-5 (a), plan section 2 "zovp2", Q299 (E1068): the stencil load pass over overlapping tiles with edge
# tiles (E988's st1 form at 65 x 33 G 1 and 63 x 31 G 0: H-OVL-PASS-EDGE, H-EDGE-SKIP, H-EDGE-EXT, H-EDGE-CLIP).
# Control that can fail: zo2-c-s160 (E1064's zo-s-160, kept stencil store byte for byte). Stop: any fault or hang; a
# row without job: ok or without its --depth-pages (24).""",
    "zb20": """# R17-1 (a), plan section 2 "zb20", Q071 (E1069): bit 20 cleared on formats 6 and 7 at 96 x 48 G 2 and 128 x 64 G 3,
# each beside its bit-20-set twin (the records of the row's expected content): H-PACK2048, H-PACK-AFTER, H-PACK-SCALE.
# Control that can fail: zb20-c-f6 (E1063's zb4-c-f6, E1031's zf-flat-f6, kept dumps byte for byte). The 128 x 64 pair
# runs last (never run: the 32-page buffers, records up to dword 8192); the stage's stop ends the session. Stop: any
# fault or hang; a row without job: ok or without its --depth-pages (24).""",
}


def build():
    import score as SC
    files = {}
    rows = {s: [] for s in STAGES}
    pred = {s: ["case\tquantity\tvalue\tmodel\tset\tsource\n"] for s in STAGES}
    controls = {s: {} for s in STAGES}
    for stage, name, sset, knobs, args, q in Z.jobs():
        rows[stage].append(f"{name}|{sset}|safe|{knobs}|t10|{args}")
        for quantity, mv in q.items():
            for m, v in mv.items():
                pred[stage].append(f"{name}\t{quantity}\t{v}\t{m}\t{sset}\tgen/z17.py\n")
        if sset == "control":
            reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")][0]
            controls[stage][name] = (tuple(reads), dict(name=name, args=args))
    for s in STAGES:
        scorekit.refuse_unreadable(controls[s], SC.producible)
        files[f"tables/{s}.txt"] = (f"#stage {s}\n#limit 0\n" + HEADER[s] + "\n"
                                    + "\n".join(rows[s]) + "\n").encode()
        files[f"predictions/{s}.tsv"] = "".join(pred[s]).encode()
    return files


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
