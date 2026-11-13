#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r10-zls's generator: tables/STAGE.txt and predictions/STAGE.tsv of zst2 (gen/zst2.py,
tool t4), zbgc, zbg and zw (gen/zbg.py, tool t9).

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
import zbg as B  # noqa: E402
import zst2 as Z  # noqa: E402

HEADERS = {
    "zst2": """# R10-4 (a), seeds plan section 5, Q120: E978's stored formats 3 to 7 with a loaded stencil, four depth planes (x: E978's
# ramp, y, d: 0 to 1, e: 40 x 20 edge tiles), stencil fills index, 0x00000000, 0xffffffff, 0xa5a5a5a5. Frozen per byte:
# E985's layouts (f3, f5, f4, f6; H-DEPTHORD stencil order) from each plane's format-0 reference; f7 a reading.
# Controls that can fail: the four format-0 references (E831's and E467's counts) and z2x-f4 (E978's 640). Stop: any fault.""",
    "zbgc": """# R10-4 (a), seeds plan section 6, Q101: the background depth (render details dword 16) at its default 1.0 and at 0.25,
# format 0. Controls that can fail (zbg's gate): every background pixel stores the poked word. Stop: any fault.""",
    "zbg": """# R10-4 (a), Q101: background depth -0.25 in formats 0, 1, 2 without and with bit 19, and -0.0 in format 1. Frozen per
# background dword: H-RAW, H-CLAMP0, H-CLAMP0P, H-ABS, H-B19-INT (gen/zbg.py). Runs only when zbgc's two controls pass.""",
    "zw": """# R10-4 (a), Q101: state-block word 10 at 0.75, 1.0, 0.125 on r9-z2's ramp a (format 0). Frozen per dword where
# x/512 + y/256 <= 0.5: H-LIN (1.6 w + 0.2) t, H-HYP 0.375 t / (0.875 - w), H-OFF t + w - 0.5. Control that can fail:
# zw-c50 (word 10 = 0.5 explicit) byte for byte E977's kept z242-a-f0. Stop: any fault.""",
}
TOOLS = {"zst2": "t4", "zbgc": "t9", "zbg": "t9", "zw": "t9"}
SOURCES = {"zst2": "gen/zst2.py", "zbgc": "gen/zbg.py", "zbg": "gen/zbg.py", "zw": "gen/zbg.py"}


def stage_jobs(st):
    return Z.jobs() if st == "zst2" else B.jobs(st)


def build():
    import score as SC
    files = {}
    for st in HEADERS:
        rows, pred = [], ["case\tquantity\tvalue\tmodel\tset\tsource\n"]
        controls = {}
        for name, sset, knobs, args, q in stage_jobs(st):
            rows.append(f"{name}|{sset}|safe|{knobs}|{TOOLS[st]}|{args}")
            for quantity, mv in q.items():
                for m, v in mv.items():
                    pred.append(f"{name}\t{quantity}\t{v}\t{m}\t{sset}\t{SOURCES[st]}\n")
            if sset == "control":
                reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")][0]
                controls[name] = (tuple(reads), dict(name=name, args=args))
        scorekit.refuse_unreadable(controls, SC.producible)
        files[f"tables/{st}.txt"] = (f"#stage {st}\n#limit 0\n" + HEADERS[st] + "\n" + "\n".join(rows)
                                     + "\n").encode()
        files[f"predictions/{st}.tsv"] = "".join(pred).encode()
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
