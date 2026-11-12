#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fake_o4.py ARGS...: the pixel branch of the fake tool (tests/fake_tool.sh), R6-pixel.  It answers by the command's ARGV and the
staged program's BYTES, never by a case name:
  - the command must be R5's C_BASE shape exactly, or C_BASE with E406's setup (`--blk 4=0x00030001 --blk 1=0x05d00200 --kpoke
    rd:9=1`) or the restore options (`--blk 4=0x00030001 --kpoke rd:9=0`) in its place; anything else (e.g. the default triangle of
    R4's o2 slip) draws a plain image no scorer can read;
  - the staged program named by the LAST argument runs in sgx-sim (debug/target/debug/simcheck --tri-pixel, pa0 = 0x11110000, pa1 =
    0x22220000) at the four lanes of a quad.  A program that reads an output register (`mov ..., oJ`) is ALSO interpreted here from
    the simulator's own decode (`simcheck --list`), instruction by instruction, under the world's rules; with the default world
    (H-STORE, gated) the interpretation must equal the simulator's run at every lane, else the fake fails the job (rc 1): the
    program's premise is checked on every mock run.  Programs without a read take R5's path (lane 0's words, an output lane 0 does
    not write from lane 3; FAKE_Y_O3_LANE: the y job's o3 from that lane, the L3 worlds).
Worlds (environment):
  FAKE_O4_MODEL   the tag-5 word's model (o5model syntax; default OR(o0,o3))
  FAKE_RD_MODEL   H-STORE (default), H-FOUR (a read of o4..o7 returns a leftover word of another job), H-O0 (every read returns o0),
                  H-MOD4 (o_j reads o_(j-4)), FIFTH (o0..o3 read o0, o4..o7 as stored: a vector no model has), DEAD (every read
                  returns the leftover: c-rd-0 dead)
  FAKE_PRED       gated (default: the simulator's), ignored (a predicated write always runs), never (a p1 write never runs), both
                  on o1..o7 only (o0's predicated write, c-prd-0's, stays gated: the control passes in every predicate world)
  FAKE_OW         last (default) or first (an output keeps its first write: c-ow fails)
  FAKE_S_MODEL    the setup's world: OR(o0,o3) (default), MUX(o4;o4) (o4's own word), plain (the setup changes nothing)
Prints the probe's rows."""
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import o4world as WD  # noqa: E402

HARNESS = HERE.parent / "debug/target/debug/simcheck"
BASE = (r"probe --tri pixel --temps 32 --pixels --dump-render \S+ --width 64 --height 64 --vtx-coords 2 {opts} "
        r"--slot pixpds=\S+/pds_iter_xy\.bin:12 --slot vtxuse=\S+/vtx_coords\.bin \S+\.bin$")
SHAPES = {"plain": re.compile("^" + BASE.format(opts=r"--blk 4=0x00030001")),
          "setup": re.compile("^" + BASE.format(opts=r"--blk 4=0x00030001 --blk 1=0x05d00200 --kpoke rd:9=1")),
          "restore": re.compile("^" + BASE.format(opts=r"--blk 4=0x00030001 --kpoke rd:9=0"))}
PA = {0: 0x11110000, 1: 0x22220000}
LEFT = 0x7fc9                          # a leftover word: marker 0x1ff (no job of this session), tag 9
LANES = {0: (0, 0), 1: (1, 0), 2: (0, 1), 3: (1, 1)}


def sim(binf, lane, listing=False):
    x, y = LANES[lane]
    a = [str(HARNESS), str(binf), "0x20", "--tri-pixel", f"{x},{y}", "--set", f"pa0={PA[0]:#x}", "--set", f"pa1={PA[1]:#x}"]
    out = subprocess.run(a + (["--list"] if listing else []), capture_output=True, text=True).stdout.splitlines()
    ins = [ln.split(" ", 2)[2] for ln in out if ln.startswith("insn ")]
    rest = [ln for ln in out if not ln.startswith("insn ")]
    o = {int(m[1]): int(m[2], 16) for ln in rest if (m := re.fullmatch(r"o(\d+) = (0x[0-9a-f]+)", ln))}
    return (rest[0] if rest else "no output"), o, ins


OR_RE = re.compile(r"^(?:(!?p\d) )?or(\.[\w.]+)? o(\d+), pa(\d+), #(0x[0-9A-Fa-f]+)$")
XOR_RE = re.compile(r"^xor\.testtaz\.chan0 !c0, p1, g25, #(\d+)$")
RD_RE = re.compile(r"^mov(\.[\w.]+)? r10, o(\d+)$")
WB_RE = re.compile(r"^mov(\.[\w.]+)? o0, r10$")


def interpret(ins, lane, w):
    """Run the decoded program at one lane under the world w: {o register: 32-bit word}; raises ValueError on an instruction the
    interpreter does not know."""
    o, r10, p1 = {}, None, None
    for t in ins:
        if t.startswith("phas "):
            continue
        if m := OR_RE.match(t):
            pred, j, val = m[1], int(m[3]), PA[int(m[4])] | int(m[5], 16)
            if pred:
                if p1 is None:
                    raise ValueError("p1 read before it is set")
                run = p1 if pred == "p1" else not p1
                if j and w["pred"] == "ignored":              # the predicate worlds act on o1..o7: o0's (c-prd-0) stays gated
                    run = True
                elif j and w["pred"] == "never" and pred == "p1":
                    run = False
                if not run:
                    continue
            if w["ow"] == "first" and j in o:
                continue
            o[j] = val
        elif m := XOR_RE.match(t):
            p1 = lane == int(m[1])
        elif m := RD_RE.match(t):
            j = int(m[2])
            r10 = read(o, j, w["rd"], lane)
        elif WB_RE.match(t):
            o[0] = r10
        else:
            raise ValueError(f"not interpreted: {t}")
    return o


def read(o, j, model, lane):
    hi = PA[0] & 0xffff0000
    left = (o.get(0, hi) & 0xffff0000) | LEFT
    if model == "DEAD":
        return left
    if model == "H-O0" or (model == "FIFTH" and j < 4):
        return o.get(0, left)
    if model == "H-FOUR" and j >= 4:
        return left
    if model == "H-MOD4" and j >= 4:
        return o.get(j - 4, left)
    return o.get(j, left)                                    # H-STORE (an unwritten register: a leftover, E373)


def lane_words(binf, w):
    """{lane: words16} of a program interpreted under the world w; the default world must equal the simulator at every lane."""
    _, _, ins = sim(binf, 0, listing=True)
    out = {}
    for lane in range(4):
        st, so, _ = sim(binf, lane)
        mine = interpret(ins, lane, dict(rd="H-STORE", pred="gated", ow="last"))
        if st.startswith("stopped") and "before the program writes it" in st:
            # the simulator refuses to read an unwritten output (E373: it holds a leftover); the state before the read must agree
            mine, so = {j: v for j, v in mine.items() if j}, {j: v for j, v in so.items() if j}
        elif not st.startswith("ended"):
            raise ValueError(f"the program did not end in the simulator ({st})")
        if mine != so:
            raise ValueError(f"lane {lane}: the interpretation {mine} is not the simulator's {so}")
        got = interpret(ins, lane, w)
        out[lane] = {j: (got[j] & 0xffff) if j in got else None for j in range(8)}
    axis = {int(m[4]) for t in ins if (m := OR_RE.match(t))}
    return out, ("x" if axis == {0} else "y")


def interpretable(ins):
    try:
        interpret(ins, 0, dict(rd="H-STORE", pred="gated", ow="last"))
        return True
    except ValueError:
        return False


def instance_words(binf, y_o3_lane):
    """R5's landing instance: lane 0's words, an output lane 0 does not write from lane 3 (E709's o4g-3); FAKE_Y_O3_LANE: o3 from it."""
    st, w, _ = sim(binf, 0)
    _, w3, _ = sim(binf, 3)
    words = {j: (w[j] if j in w else w3.get(j)) for j in range(8)}
    if y_o3_lane is not None:
        _, wl, _ = sim(binf, y_o3_lane)
        if 3 in wl:
            words[3] = wl[3]
    return st, {j: (v & 0xffff if v is not None else None) for j, v in words.items()}, w


def main(argv):
    name = pathlib.Path(argv[-1]).stem
    cmd = " ".join(argv)
    shape = next((k for k, r in SHAPES.items() if r.match(cmd)), None)
    if shape is None:
        g = [[WD.BG] * 64 for _ in range(64)]
        sys.stdout.write(WD.text(name, g))
        return 0
    w = dict(rd=os.environ.get("FAKE_RD_MODEL", "H-STORE"), pred=os.environ.get("FAKE_PRED", "gated"),
             ow=os.environ.get("FAKE_OW", "last"))
    model = os.environ.get("FAKE_O4_MODEL", "OR(o0,o3)")
    setup = False
    if shape == "setup" and os.environ.get("FAKE_S_MODEL", "OR(o0,o3)") != "plain":
        setup, model = True, os.environ.get("FAKE_S_MODEL", "OR(o0,o3)")
    _, _, ins = sim(argv[-1], 0, listing=True)
    reads = any(RD_RE.match(t) for t in ins)
    # o0 differs by lane when the program reads an output into o0 or writes o0 under a predicate (c-prd-0): those take the lanes
    reads = reads or any((m := OR_RE.match(t)) and m[1] and m[3] == "0" for t in ins)
    try:
        if reads or (w != dict(rd="H-STORE", pred="gated", ow="last") and interpretable(ins)):
            lw, ax = lane_words(argv[-1], w)
            img = WD.image(ax, dict(lw[0]), model, lanes=lw if reads else None, setup=setup)
        else:
            yl = os.environ.get("FAKE_Y_O3_LANE")
            st, words, raw = instance_words(argv[-1], None)
            ax = "x" if (raw.get(0, 0) >> 16) == 0x1111 else "y"
            if ax == "y" and yl:
                st, words, raw = instance_words(argv[-1], int(yl))
            if not st.startswith("ended"):
                print(f"probe {name}: failed: the program did not end in the simulator ({st})")
                return 1
            img = WD.image(ax, words, model, setup=setup)
    except ValueError as e:
        print(f"probe {name}: failed: {e}")
        return 1
    sys.stdout.write(WD.text(name, img))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
