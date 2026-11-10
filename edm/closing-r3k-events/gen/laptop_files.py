#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""laptop_files.py SESSION: the files a session's laptop directory holds, as paths relative to this tree (one a line; the landed
run/fwtask_run.py is added by the freeze and the staging).  Used by run/freeze_r3.sh and run/stage_r3.sh; one list, so that what is
frozen is what is copied."""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3layout as L  # noqa: E402


def files(session):
    stages = L.SESSIONS[session]
    out = [f"tables/{st}.json" for st in stages]
    blobs = sorted({L.BLOB_OF[st] for st in stages if L.BLOB_OF[st]})
    out += [f"bins/{b}.blob" for b in blobs] + ["bins/blobs.json", "gen/r3layout.py", "run/r3_run.py", "run/ops_kicker.py", "run/ops_e2b.py",
                                              "run/ops_e3.py", "run/ops_k0.py", "run/r3common.py", "run/health_remote.sh", "TOOL.sha256"]
    if "k0t" in stages:
        out += ["TOOLR1.sha256", "bins/progs/dd-p1__0.bin", "bins/progs/pix_green.bin"]
    if any(st in stages for st in ("e3h", "e3a", "e3b")):
        out += [f"bins/progs/{L.LOOP_PROG}.bin"]
    return out


if __name__ == "__main__":
    print("\n".join(files(sys.argv[1])))
