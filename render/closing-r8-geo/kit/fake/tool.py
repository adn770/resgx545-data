#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""tool.py PATH ARGS...: the fake tool of the kit's mock (fake/tool.sh execs it). The session's
mock/world.py (KIT_WORLD) answers from the tool's name and the argv only:

    answer(tool, argv, world) -> None or dict(rc=0, out="", err="", files={path: bytes},
                                              kmsg=[lines], latch=(int, word))

world is the set of FAKE_WORLD's comma separated tokens. None answers the health pair (bare
`fill` and `tri`: an exact draw) and refuses anything else (rc 2, "usage"). A file is written
only into a directory that exists, as the real tool does: a missing one prints "No such file or
directory" and the job ends rc 1. kmsg lines go to the fake kernel log, latch to the fake GPU
state (a fault the next reset clears)."""
import importlib.util
import os
import sys


def load(path):
    spec = importlib.util.spec_from_file_location("world", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv):
    path, args = argv[1], argv[2:]
    tools = dict(t.split("=", 1) for t in os.environ.get("KIT_TOOL_NAMES", "").split() if "=" in t)
    tool = tools.get(os.path.realpath(path), os.path.basename(path))
    world = set((os.environ.get("FAKE_WORLD") or "model").split(","))
    a = load(os.environ["KIT_WORLD"]).answer(tool, args, world)
    if a is None and args in (["fill"], ["tri"]) and "health-bad" not in world:
        a = dict(out="diff: 0 of %d pixels\n" % (2048 if args == ["fill"] else 4096))
    if a is None:
        sys.stderr.write("usage: sgxfive-test COMMAND ... (the mock world has no answer for %s)\n" % args)
        return 2
    rc = a.get("rc", 0)
    sys.stdout.write(a.get("out", ""))
    sys.stderr.write(a.get("err", ""))
    for p, data in a.get("files", {}).items():
        if not os.path.isdir(os.path.dirname(p) or "."):
            print("sgxfive-test: cannot open %s: No such file or directory" % p)
            rc = rc or 1
            continue
        with open(p, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode())
    if a.get("kmsg"):
        with open(os.environ["KIT_KMSG"], "a") as f:
            f.write("".join("gma500 0000:00:02.0: [drm] *ERROR* %s\n" % ln for ln in a["kmsg"]))
    if a.get("latch"):
        with open(os.path.join(os.environ["FAKE_DIR"], "state"), "w") as f:
            f.write("%d %d\n" % a["latch"])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
