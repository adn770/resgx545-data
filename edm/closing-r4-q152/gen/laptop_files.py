#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""laptop_files.py: the files R4b's laptop directory ~/r4b holds, as paths relative to this tree (one a line; the landed
tools/fwtask/fwtask_run.py of resgx545 6421c1c is added as run/fwtask_run.py by the freeze and the staging).  One list, so that
what is frozen is what is copied."""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r4blayout as L  # noqa: E402


def files():
    out = [f"tables/{st}.json" for st in L.STAGES]
    out += [f"bins/{b}.blob" for b in L.BLOBS]
    out += ["bins/blobs.json", "gen/r3layout.py", "gen/r4blayout.py", "run/r4b_run.py", "run/r3common.py", "run/health_remote.sh",
            "TOOL.sha256"]
    return out


if __name__ == "__main__":
    print("\n".join(files()))
