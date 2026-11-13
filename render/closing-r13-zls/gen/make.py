#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r13-zls's generator: tables/STAGE.txt and predictions/STAGE.tsv for zbase, zbits and
zfmt from gen/z13.py (tool t10).

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
import z13 as Z  # noqa: E402

STAGES = ("zbase", "zbits", "zfmt")
HEADER = {
    "zbase": """# R13-1 (a), plan section 2 "zbase", Q243: the ZLS depth load base (render details dword 12) moved by --kpoke-render
# 1:rd:12 after depth_arm's own pokes: +0x1000, +0x4000, +0x10000, onto the store's base, +0x800, +0x40, +4 (depth `index`,
# test never, 20 pages: depth 0x3e001000, store 0x3e015000, hook_check). Frozen per stored dword: H-MOVED, H-ALIGN4K,
# H-ALIGNTILE, H-STOREBASE, H-UNMOVED. Controls that can fail: zb-c-ctl (E977's z243-ctl, rd:12 its own), zb-c-eq0 (E995's
# eq-m0), zb-c-id (identity), zb-c-off (load bits off: 1.0). Stop: any fault or hang, other buffer addresses (24).""",
    "zbits": """# R13-1 (a), plan section 2 "zbits", Q071: the ZLS control's bits 12, 16, 20 cleared alone and in pairs under E988's
# stencil test (st1-b0, 0x0017300e) and on E977's ramp store (z242-c-f0, 0x00171014), and the set half alone under the
# test. Frozen: per clause (Z: the test reads 0, 2048 drawn; L: E997's linear store) c-BIT-k, c-PAIR-a+b, c-ALL, c-ANY,
# Z-SET. Controls that can fail: zbs-base (1024), zbs-q071 (2048), zbr-ctl (E977's dump). Stop: any fault or hang.""",
    "zfmt": """# R13-1 (a), plan section 2 "zfmt", Q120: E1015's F7K at the stencil fills 0x3f and 0x1f (the markers) and F6C on a
# 48 x 32 y ramp of another origin (its rows from zf-y48-f0, a reading) and on a flat 0.5 (every tile). Frozen: F7K and
# F7K-FIX, F6C and F6RAW (c7_rule.py, pinned). Control that can fail: zf-y6-ctl (E986's z2y-f6, byte for byte). Stop:
# any fault or hang.""",
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
                pred[stage].append(f"{name}\t{quantity}\t{v}\t{m}\t{sset}\tgen/z13.py\n")
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
