#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fake_o4.py ARGS...: the p5-o4 branch of the fake tool (tests/fake_tool.sh).  It answers by the command's argv: the command must be
R4's C_BASE shape exactly (--tri pixel, 64x64, --vtx-coords 2, --blk 4=0x00030001, the pixpds and vtxuse slots; anything else, e.g. the
default triangle of R4's o2 slip, draws a plain image no o4 scorer can read), and the staged program named by the LAST argument is run
in sgx-sim (debug/target/debug/simcheck, --tri-pixel 0,0: the lane-0 instance every tag-5 pair comes from) with pa0 = 0x11110000 and
pa1 = 0x22220000, so its output words, marker, tags, axis and predicate come from the program's bytes.  The world: FAKE_O4_MODEL (one
of the nine, "none", or any OR/AND/XOR/MUX of o5model's syntax; default OR(o0,o3)).  Prints the probe's rows."""
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import o4world as WD  # noqa: E402

HARNESS = HERE.parent / "debug/target/debug/simcheck"
SHAPE = re.compile(r"^probe --tri pixel --temps 32 --pixels --dump-render \S+ --width 64 --height 64 --vtx-coords 2 "
                   r"--blk 4=0x00030001 --slot pixpds=\S+/pds_iter_xy\.bin:12 --slot vtxuse=\S+/vtx_coords\.bin \S+\.bin$")


def sim_words(binf, lane=(0, 0)):
    r = subprocess.run([str(HARNESS), str(binf), "0x20", "--tri-pixel", f"{lane[0]},{lane[1]}", "--set", "pa0=0x11110000",
                        "--set", "pa1=0x22220000"], capture_output=True, text=True)
    lines = r.stdout.splitlines()
    o = {int(m[1]): int(m[2], 16) for ln in lines if (m := re.fullmatch(r"o(\d+) = (0x[0-9a-f]+)", ln))}
    ax = "x" if (o.get(0, 0) >> 16) == 0x1111 else "y"
    return (lines[0] if lines else "no output"), ax, {j: (o[j] & 0xffff) if j in o else None for j in range(8)}


def instance_words(binf):
    """(status, axis, words) of the landing instance: lane 0's words; an output lane 0 does not write takes the word of the lane-3
    instance (E709's o4g-3 writes o4 under p1 = (g25 == 3) only, yet R4's c-e709 read 0xcf5 at lane-0 sources, 39 of 39: the mock
    copies the image, why it does is open [infer]); an output no lane writes stays None."""
    st, ax, w = sim_words(binf)
    _, _, w3 = sim_words(binf, (1, 1))
    return st, ax, {j: (w[j] if w[j] is not None else w3[j]) for j in range(8)}


def main(argv):
    name = pathlib.Path(argv[-1]).stem
    if not SHAPE.match(" ".join(argv)):
        g = [[WD.BG] * 64 for _ in range(64)]
        sys.stdout.write(WD.text(name, g))
        return 0
    st, ax, w = instance_words(argv[-1])
    if not st.startswith("ended"):
        print(f"probe {name}: failed: the program did not end in the simulator ({st})")
        return 1
    sys.stdout.write(WD.text(name, WD.image(ax, w, os.environ.get("FAKE_O4_MODEL", "OR(o0,o3)"))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
