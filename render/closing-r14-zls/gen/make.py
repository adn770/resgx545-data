#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r14-zls's generator: tables/STAGE.txt and predictions/STAGE.tsv for zgran, zodd,
zbits2 and zflat from gen/z14.py (tool t10).

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
import z14 as Z  # noqa: E402

STAGES = ("zgran", "zodd", "zbits2", "zflat")
HEADER = {
    "zgran": """# R14-1 (a), plan section 2 "zgran", Q243: E1029's zbase form (depth `index`, test never, 20 pages: depth 0x3e001000,
# store 0x3e015000) with rd:12 moved +8, +16, +32, +0x1008, +0x1020 (G8, G16, G32, G64, H-BYTE), formats 1 and 2 moved
# +0x1000 over a bit:10 fill (I-MOVED/UNMOVED-L32/L16, I-STOREBASE), and E988's stencil row (index) with rd:14 moved
# +0x1000 (S-MOVED, S-UNMOVED, S-STOREBASE). Controls that can fail: zg-c-ctl (E977's z243-ctl), zg-c-m4 and zg-c-m40
# (E1029's kept stores), zg-c-sid (rd:14 its own: the index stencil in E988's order). Stop: any fault or hang, other
# buffer addresses or no poke line (24).""",
    "zodd": """# R14-1 (a), plan section 2 "zodd", Q242: E996's plane at 63 x 31 (G 1) and 65 x 33 (G 2), formats 0 (reading rows,
# the references), 1 and 2 (INT-FLOOR-EXT, INT-ZERO-PAST, INT-EDGE-CLAMP past the target); overlapping stores at 65 x 33
# G 1 (edge tiles) and 640 x 480 G 2 (four macrotiles a side) from their full-pitch references (H-LATE/HDR, E996, and
# three rivals); E411's G 3 store base (rd:13 0xd000) with 20 pages, last (H-NEXTTILE, H-STRAY). Control that can
# fail: zo-c-ov (E996's zov-64x32-g0, byte for byte). Stop: any fault or hang, zo-g3's addresses (24).""",
    "zbits2": """# R14-1 (a), plan section 2 "zbits2", Q071: E988's stencil row with each set-half bit alone (15, 21-23, 27-31) and
# the groups 21-23, 27-31 (Z-ONE-k, Z-GRP, Z-GROUP, Z-ANY); bits 12 and 16 cleared at 96 x 32 and 64 x 32, G 2 (P-64,
# P-W, P-G); bit 12 cleared with a depth load (H-DEPTH-UNCH, H-DEPTH-LIN); bit 16 cleared on the 16-bit format (L16-*).
# Controls that can fail: zb2-c-base (1024), zb2-c-set (2048, every byte 0xff), zb2-c-r16 (E997's linear dump). Stop:
# any fault or hang, zb2-d12's addresses (24).""",
    "zflat": """# R14-1 (a), plan section 2 "zflat", Q120: format 6 on flat planes at 0.25, 0.75, 0.1234, 1.0, 0.0 (FL-HEAD,
# FL-CONST, FL-SHAPE: no rule of E1031's 44 dwords was fitted), format 7 under the index stencil on the flat 0.5
# (F7I-COMMON, F7I-COUNT), format 5 on it (F5-EQ-F6). Controls that can fail: zl-c-flat (E1031's zf-flat-f6) and
# zl-c-y6 (E986's z2y-f6), byte for byte. Stop: any fault or hang.""",
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
                pred[stage].append(f"{name}\t{quantity}\t{v}\t{m}\t{sset}\tgen/z14.py\n")
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
