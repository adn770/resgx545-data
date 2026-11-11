#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""guard_blob_r4b.py [--root DIR]: the blob and the table of R4b.  (1) asm/ring_exit.s, bins/ring_exit.blob and bins/blobs.json have
the sha256 of R3k-events' published freeze (edm/closing-r3k-events FROZEN.sha256, E817's run); (2) the landed tools/fwtask (resgx545,
RESGX545 or ~/src/resgx545) assembles the source to the blob and its verifier accepts the blob; (3) blobs.json says cont4, no str, no
sa or pa write for ring_exit; (4) tables/fr.json is exactly gen/gen_r4b.py's table.  Exit 1 with the problems."""
import hashlib
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PUBLISHED = {"asm/ring_exit.s": "e0be17c15cd2664a0df64f317ac9a8262ca62f57763a720cbdb8003157951865",
             "bins/ring_exit.blob": "3c031d998489f1699d53b469d5aae6403dd0beec2fc51e35ddb29556955a19cb",
             "bins/blobs.json": "2627a09d184d67670a82246b138c16f3475a7e6542daf4c3131648428bb534d1"}


def problems(root):
    root = pathlib.Path(root)
    out = []
    for f, h in PUBLISHED.items():
        if hashlib.sha256((root / f).read_bytes()).hexdigest() != h:
            out.append(f"{f} is not R3k-events' frozen file ({h[:16]}...)")
    R = pathlib.Path(os.environ.get("RESGX545", str(pathlib.Path.home() / "src/resgx545")))
    sys.path.insert(0, str(R / "tools" / "fwtask"))
    import fwtask as fw  # the landed tree
    regs = fw.load_regs()
    text = (root / "asm" / "ring_exit.s").read_text()
    blob = (root / "bins" / "ring_exit.blob").read_bytes()
    try:
        if fw.build_blob_text(text, regs) != blob:
            out.append("ring_exit: the blob is not what its source assembles to with the landed tools/fwtask")
    except fw.VerifyError as e:
        out.append(f"ring_exit: the landed verifier refuses the source: {e}")
    try:
        bad = fw.verify_blob(blob, regs)
    except Exception as e:
        bad = [repr(e)]
    if bad:
        out.append(f"ring_exit: the landed verifier refuses the blob: {bad[:2]}")
    info = json.loads((root / "bins" / "blobs.json").read_text())["ring_exit"]
    if not info.get("cont4") or info.get("str") or info.get("sa_writes") or info.get("pa_writes"):
        out.append("ring_exit: blobs.json does not say cont4 with no str, sa or pa write")
    sys.path.insert(0, str(root / "gen"))
    import gen_r4b as G
    if json.loads((root / "tables" / "fr.json").read_text()) != json.loads(json.dumps(G.table())):
        out.append("tables/fr.json is not gen/gen_r4b.py's table")
    return out


def main(argv):
    root = pathlib.Path(argv[argv.index("--root") + 1]) if "--root" in argv else HERE.parent
    p = problems(root)
    for x in p:
        print("GUARD: " + x)
    if not p:
        print("guard_blob_r4b: clean (ring_exit, table fr)")
    return 1 if p else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
