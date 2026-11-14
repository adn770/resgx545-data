#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/make_vectors.py: the replay vectors of r16-usse (README "Replay vectors"), in the USSE
corpus format sgx545-vectors (tools/usse-asm/vectors.py's, version 1), one file a stage, one
vector a job, from the session's own files alone: the program words of bins/NAME.bin, the init
of a probe fill (`probe --temps 32`: one 64 x 32 fill, 2048 pixel instances, pa0 the fill's, the
16-page scratch at 0x3e003000 filled with 0xd0000000 | i, no register preset: each program sets
its own) and the readback the kept out/ATT/STAGE/NAME.txt.gz printed (o0, or `mixed` with o0 null
when the pixels differ, and the scratch dwords listed). A fold-local converter: closing_tables.py
has no kit kind for probe scratch dwords (reported to the round's tooling pass).

  python3 fold/make_vectors.py OUT_DIR    writes OUT_DIR/{uadd,utest,urpt}.vec.json"""
import datetime
import gzip
import hashlib
import json
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATT = "out/20261114-092913"
SESSION = "usse/closing-r16-usse"
QUESTION = {"uadd": "Q126: the value iaddu32 writes (source 1's extension) with immediates, c56, "
                    "i0 and sa0 (E1061)",
            "utest": "Q137: the class 9 test field's rule on the shifts, #7 forms, sums and lane "
                     "operations, both joins (E1062)",
            "urpt": "Q126: the write mask .xy / .xyzw on an iaddu32 test (E1061)"}
H = lambda v: "0x%08x" % v  # noqa: E731


def rows(stage):
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, _, _, _, args = ln.rstrip("\n").split("|", 5)
            yield name, st, args


def readback(text, name):
    if re.search(rf"^probe {re.escape(name)}: failed: (.*)$", text, re.M):
        return {"failed": re.search(rf"^probe {re.escape(name)}: failed: (.*)$", text, re.M)
                .group(1), "o0": None, "mixed": [], "scratch": {}, "pixels": None}
    m = re.search(rf"^probe {re.escape(name)}: o0 (.*)$", text, re.M).group(1)
    one = re.fullmatch(r"0x([0-9a-f]{8}) \((\d+) of \2\)", m)
    mixed = [] if one else [[H(int(v, 16)), int(c)] for v, c in
                            re.findall(r"0x([0-9a-f]{8}) x(\d+)", m)]
    scr = {f"0x{int(o, 16):03x}": H(int(v, 16)) for o, v in re.findall(
        rf"^probe {re.escape(name)}: scratch \+0x([0-9a-f]+) 0x([0-9a-f]{{8}})$", text, re.M)}
    return {"failed": None, "o0": H(int(one.group(1), 16)) if one else None, "mixed": mixed,
            "scratch": scr, "pixels": None}


def stage_file(stage):
    vecs, raw = [], hashlib.sha256()
    for case, (name, st, args) in enumerate(rows(stage)):
        b = open(os.path.join(KP, "bins", name + ".bin"), "rb").read()
        words = ["0x%016x" % int.from_bytes(b[i:i + 8], "little") for i in range(0, len(b), 8)]
        kept = os.path.join(KP, ATT, stage, name + ".txt.gz")
        text = gzip.open(kept, "rt").read()
        raw.update(gzip.open(kept, "rb").read())
        vecs.append({
            "id": f"r16-usse-{stage}-{name}",
            "program": {"isa": "usse", "entry": 0, "source": "recorded", "words": words},
            "init": {"task": "pixel", "instances": 2048, "temps": 32, "pa0": "fill",
                     "scratch": {"base": "0x3e003000", "bytes": 65536, "fill": "0xd0000000|i"},
                     "regs": {}, "job": {"pokes": [], "use_coeffs": {"load": False}}},
            "readback": readback(text, name),
            "provenance": {"probe": f"r16-usse-{name}", "case": case, "table": f"tables/{stage}.txt",
                           "template": f"bins/{name}.s", "set": st,
                           "template_sha256": hashlib.sha256(open(os.path.join(
                               KP, "bins", name + ".s"), "rb").read()).hexdigest(),
                           "inputs": {}, "params": {}, "options": args.split()[1:-1],
                           "question": QUESTION[stage]}})
    return {"format": "sgx545-vectors", "version": 1,
            "run": {"raw": f"{SESSION}/{ATT}/{stage}/", "raw_sha256": raw.hexdigest(),
                    "converted": datetime.datetime(2026, 11, 14, 12, 0).astimezone().isoformat(),
                    "tool": "closing-r16-usse fold/make_vectors.py 1"},
            "vectors": vecs, "orphans": []}


def main(argv):
    out = argv[1]
    os.makedirs(out, exist_ok=True)
    for st in ("uadd", "utest", "urpt"):
        with open(os.path.join(out, f"r16-usse-{st}.vec.json"), "w") as f:
            json.dump(stage_file(st), f, indent=1)
            f.write("\n")
        print(f"{st}: {len(stage_file(st)['vectors'])} vectors")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
