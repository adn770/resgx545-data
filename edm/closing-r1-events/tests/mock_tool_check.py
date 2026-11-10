#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""mock_tool_check.py: every client command of every table (k, t, d0, d1) run against the landed tool's in-process mock
(`sgxfive-test --mock`, built on the Mac from the landed tree: userspace/libsgxfive/build/sgxfive-test).  No GPU, no laptop.
An option the tool does not know, a bad value or a missing program shows up as rc 2 or a usage message.  What this proves:
the commands parse and run in the mock: loop programs through `probe` (fill and `--tri pixel` targets down to 8x8), the vertex
program through `--tri vtxuse` (the offline premise of Q082's T5), the 4096x4096 job with --vertices 1500 and --dump-render.
It does not prove any hardware behaviour (the mock does not run the programs: o0 is the program's first immediate).

    PYTHONDONTWRITEBYTECODE=1 ../../closing/pixel-faults/.venv/bin/python tests/mock_tool_check.py
Exit 0 when every command is accepted."""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
R1 = pathlib.Path(__file__).resolve().parent.parent
TOOL = pathlib.Path.home() / "src/resgx545/userspace/libsgxfive/build/sgxfive-test"


def main():
    if not TOOL.exists():
        print(f"SKIPPED, NOT PASSED: no {TOOL}")
        return 2
    bad, n = [], 0
    lines = []
    for st in ("k", "t", "d0", "d1"):
        t = json.loads((R1 / "tables" / f"{st}.json").read_text())
        for j in t["jobs"]:
            args = j.get("tool_args")
            if not args:
                continue
            with tempfile.TemporaryDirectory() as w:
                a = [x.replace("$B", str(R1 / "bins")).replace("$W", w) for x in args]
                if j["op"] == "ringtool" and j.get("rt"):
                    pass
                cmd = [str(TOOL), "--mock"] + a
                if "--wait-ms" in a:                                  # the held fault: the mock needs no 20 s wait
                    cmd = [str(TOOL), "--mock"] + [x if x != "20000" else "100" for x in a]
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    rc, txt = r.returncode, r.stdout + r.stderr
                except subprocess.TimeoutExpired:
                    rc, txt = 124, "timeout"
            n += 1
            usage = rc in (2, 124) or "usage" in txt.lower() or "bad option" in txt or "unknown option" in txt
            o0 = re.search(r"o0 .*$", txt, re.M)
            lines.append(f"{st}/{j['name']}: rc {rc} {o0[0][:70] if o0 else ''}")
            if usage:
                bad.append((st, j["name"], rc, txt.strip().splitlines()[-1][:120] if txt.strip() else ""))
    for ln in lines[:6] + ["..."] + lines[-4:]:
        print(ln)
    print(f"{n - len(bad)} of {n} commands accepted by the tool's mock" + (f"; refused: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
