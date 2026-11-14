#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r15-zls's generator: tables/STAGE.txt and predictions/STAGE.tsv for zpass, zbits3,
zflat2 and zovl from gen/z15.py (tool t10).

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
import z15 as Z  # noqa: E402

STAGES = ("zpass", "zbits3", "zflat2", "zovl")
HEADER = {
    "zpass": """# R15-1 (a), plan section 2 "zpass", Q297 (E1050): E1029's zbase form (load and store, 20 pages) over bit:K fills.
# 34 x 18 edge tiles (H-EDGE, H-EDGE-CLEAR, H-EDGE-SKIP), bit 19 under never and less (H-19-RENEG, H-19-ABS), formats 1
# and 2 at 0.375 (H-INT-PASS, H-INT-WORD), triangle depths 0, 0.125, 0.75, 1 (H-PASS-Z, H-PASS-LE). Controls that can
# fail: zp-c-id (E1029's zb-c-id), zp-c-467 (E467's pass at 256 x 128, 16384 drawn), zp-c-band (34 x 18 without a load,
# E831's band). The stencil edge row zp-e-st runs in zbits3. Stop: any fault or hang, zp-c-id's addresses (24).""",
    "zbits3": """# R15-1 (a), plan section 2 "zbits3", Q071 (E1053): E988's st1-b0 form with bit 15 alone at 96 x 32 G 2 and under
# the reference flipped (H15-FAIL, H15-READFF), bit 23 alone at 96 x 32 G 2 and over the index fill (H23-MOD16,
# H23-LOADED), bits 21 + 23 and 22 + 23 (H-PAIR-23, -ZERO, -BASE); E1050's stencil edge row zp-e-st last (34 x 18).
# Controls that can fail: zb3-c-base, zb3-c-set, zb3-c-b23 (E1042's kept stores), zb3-c-ref1 (E988 against reference
# 1). Stop: any fault or hang.""",
    "zflat2": """# R15-1 (a), plan section 2 "zflat2", Q120 (E1054): format 6 on flat planes at 0.375, 0.625, 0.9375, 0.0625
# (FL-REC0) and at 0.1, 0.3, 0.5 + 2^-20, each with its format-0 twin (H-LOW16, H-FLATPLANE). Controls that can fail:
# zl2-c-flat (E1031), zl2-c-y6 (E986), zl2-c-f5 (E1043), byte for byte. Stop: any fault or hang.""",
    "zovl": """# R15-1 (a), plan section 2 "zovl", Q298 (E1051): overlaps in format 2 (64 x 32 G 0, 160 x 48 G 2) and format 1
# (65 x 33 G 1, 640 x 480 G 2) from kept references (H-LATE/HDR and three rivals); integer depths at the z offsets
# 1.25 and -0.25 (H-INT-SAT, -WRAP, -SIGN); E411's bit-25 row and its pitches G 5, 9, 17 with the buffer sized, last in
# ascending extent (H-E465-EXT, H-STOP16; H-B25-FLOOR, H-B25-FF); zv-r-hi reads format 0 at 1.25. Controls that can
# fail: zv-c-ov (E996), zv-c-075 (format 1 at 0.75: 0x00c00000), zv-c-g3 (E1041's zo-g3). Stop: any fault or hang;
# addresses or poke line (24, on_stop end).""",
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
                pred[stage].append(f"{name}\t{quantity}\t{v}\t{m}\t{sset}\tgen/z15.py\n")
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
