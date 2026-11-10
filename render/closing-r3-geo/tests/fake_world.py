#!/usr/bin/env python3
"""fake_world.py MODE ARGS...: the DPM readings of a synthetic world (tests/world_r3.py) for the bash runner's mock.
  buf09 ARGS   write the control block (dword 38 = 0x20 on a raise, dword 36) to $SGXFIVE_DEBUGFS/buf09 for the job ARGS describe, at
               the knob in $SGXFIVE_DEBUGFS/render_pb_pages (P - 0x22 = thr0); prints the tool's overflow line when the job aborts
  timeline     print the regtimeline block (stdin unused): fake_rt.py calls it
Environment FAKE_WORLD = the spec string of world_r3.named_world."""
import os
import pathlib
import struct
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import world_r3 as W  # noqa: E402

mode, argv = sys.argv[1], sys.argv[2:]
world = W.named_world(os.environ.get("FAKE_WORLD", ""))
dbg = pathlib.Path(os.environ["SGXFIVE_DEBUGFS"])
P = int(open(dbg / "render_pb_pages").read().split()[0], 0)
thr0 = P - 0x22
args = " ".join(argv)
text, buf = W.job_reading(world, args, thr0)
if mode == "buf09":
    (dbg / "buf09").write_bytes(struct.pack("<59I", *buf))
    j = W.parse_args(args)
    if world.need(j) > thr0:
        print("probe x: failed: scene overflowed the parameter buffer, context kept (No space left on device)")
        sys.exit(3)
else:
    sys.stdout.write(text.replace("rc 3", "rc 3"))
