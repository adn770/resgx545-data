#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""laptop_files.py: the files R4-events' laptop directory ~/r4e-run holds, as paths relative to this tree (one a line; the landed
tools/fwtask/fwtask_run.py of resgx545 5a13042 is added as run/fwtask_run.py by the freeze and the staging).  One list, so that what is
frozen is what is copied."""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r4layout as L  # noqa: E402


def files():
    out = [f"tables/{st}.json" for st in L.STAGES]
    out += [f"bins/{b}.blob" for b in L.BLOBS]
    out += ["bins/blobs.json", "gen/r3layout.py", "gen/r4layout.py", "run/r4e_run.py", "run/ops_kicker2.py", "run/ops_e3p.py", "run/r3common.py",
            "run/health_remote.sh", "TOOL.sha256"]
    return out


if __name__ == "__main__":
    print("\n".join(files()))
