#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r16-zls's generator: tables/STAGE.txt and predictions/STAGE.tsv for zpass2, zbits4,
zovp and zoff from gen/z16.py (tool t10), and gen/oq069.out (the offline gate OQ069).

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
import z16 as Z  # noqa: E402

STAGES = ("zpass2", "zbits4", "zovp", "zoff")
HEADER = {
    "zpass2": """# R16-1 (a), R16-3 (a), plan section 2 "zpass2", Q297 (E1059): E1050's zpass form (64 x 32, bit:9 load, less) at
# 0.125, 0.0625, 0.1, 0.3, 0.375, 0.625 and 0.5 + 2^-20, each pass row followed by its no-load twin (0x0017100c):
# H-PASS-TWIN against H-PASS-OWN, H-PASS-EXACT at the one-float depths. Controls that can fail: zp2-c-467 (E1050's
# zp-c-467) and zp2-c-z125 (E1050's zp-z125), their kept stores byte for byte. Stop: any fault or hang.""",
    "zbits4": """# R16-1 (a), plan section 2 "zbits4", Q071 (E1063): bit 0 on E988's st1, E1031's flat format 6 and F7K and E1030's
# bit-16-cleared rows (H-B0, H-B0-NOSTORE); bit 20 cleared on the format 6 and 7 rows (H-INERT20); E1064's stencil pass
# at G 0 and G 2 over overlapping tiles (H-OVL-PASS, H-OVL-SKIP); bit 23 with the reference 0x80, the compare mask 0xff
# and the background stencil 0x5a (rd:17), last (H23-FIXED, H23-REF, H23-MASK, H23-BG). Controls that can fail:
# zb4-c-base, zb4-c-b23, zb4-c-f6 (kept dumps byte for byte). Stop: any fault or hang; zb4-23-bg's poke line (24).""",
    "zovp": """# R16-1 (a), plan section 2 "zovp", Q299 (E1064): the depth load pass over overlapping tiles (E996's plane, 64 x 32
# G 0, 160 x 48 G 2, load 0.2: H-OVL-PASS, H-OVL-FIRST, H-OVL-SKIP); kept NaN loads into formats 1 and 2 under never
# (H-NAN-SAT, H-NAN-ZERO, H-NAN-LOW); E1063's bit 20 on E1042's zb2-d12 (H-INERT20). Controls that can fail: zo-c-64
# (the no-load twin, E996's owner rule) and zo-c-f1 (E1050's zp-f1, kept). Stop: any fault or hang; zb4-20-d12's
# addresses or poke line (24).""",
    "zoff": """# R16-1 (a), R16-8 (a), plan sections 2 and 5 "zoff", Q069 (E1066): E987's zw form with the z offset w = 7/16,
# 3/8, 5/16, 3/16, 1/16 and 0 (s 0.5) and w 0.25 at the z scale 0.25 and 0.75 (OQ069: H-LIN [fitted] outside BEND,
# H-LIN-S, H-POLYCLIP); E1063's bit 20 at 640 x 480 (H-INERT20). Control that can fail: zw2-c-0125 (E987's zw-0125,
# kept). Stop: any fault or hang (the session ends: on_stop "end").""",
}


def build():
    import oq069
    import score as SC
    files = {}
    rows = {s: [] for s in STAGES}
    pred = {s: ["case\tquantity\tvalue\tmodel\tset\tsource\n"] for s in STAGES}
    controls = {s: {} for s in STAGES}
    for stage, name, sset, knobs, args, q in Z.jobs():
        rows[stage].append(f"{name}|{sset}|safe|{knobs}|t10|{args}")
        for quantity, mv in q.items():
            for m, v in mv.items():
                pred[stage].append(f"{name}\t{quantity}\t{v}\t{m}\t{sset}\tgen/z16.py\n")
        if sset == "control":
            reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")][0]
            controls[stage][name] = (tuple(reads), dict(name=name, args=args))
    for s in STAGES:
        scorekit.refuse_unreadable(controls[s], SC.producible)
        files[f"tables/{s}.txt"] = (f"#stage {s}\n#limit 0\n" + HEADER[s] + "\n"
                                    + "\n".join(rows[s]) + "\n").encode()
        files[f"predictions/{s}.tsv"] = "".join(pred[s]).encode()
    files["gen/oq069.out"] = oq069.report().encode()
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
