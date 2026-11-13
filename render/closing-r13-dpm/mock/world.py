# SPDX-License-Identifier: MIT
"""mock/world.py: r13-dpm's fake laptop for kit/session.py mock (r10-dpm's, cut to stage pr2).
answer() sees the tool's name, the argv and the world's tokens, never a case name; timeline() gives
regtimeline's samples (the kit's fake regtimeline runs the wrapped tool's fake, then prints them).
The threshold is what the GPU sees: the debugfs knob render_pb_pages as the kit wrote it (the fake
debugfs, $FAKE_DBGREAL), never a row's name. The scene is 3072x2048 (PL.THR0: thr0 -> partial
renders, r8-ldpm's kept counts); the need there is 0x2e0 (above thr0 0x294, below 0x400).

The fake is as strict as the tool (sgxfive-test of resgx545 a581c06) on this session's rows: `probe`
takes only --tri pixel, --width, --height, --vertices 1500 and one program FILE that exists; any
other option is rc 2. regtimeline (rt) must be `0 0.3 REGS -- CMD...` with R5-dpm's 16 registers.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     counts 0, 1, 2, 4, bit 2 never clears: the stage runs, both controls pass
  clear0    the PR 0 rows clear bit 2 once (the finding R-PR would refute): the stage runs
  perpr     one clear line per partial render at every row: the stage runs
  ctloff    a PR 0 row reads one partial render: hook_check stops the stage (rc 24)
  noread    the captures have no 0x0724 page count: no knob, no reading; the premise stops the
            session (rc 25)
  fault     the 2-PR rows fault: rc 4, the session stops
  rc3other  the 4-PR rows end rc 3 without the overflow line: not the expected end, rc 4
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import plan as PL  # noqa: E402

EXPECT = {"model": (0, {"pr2": 0}),
          "clear0": (0, {"pr2": 0}),
          "perpr": (0, {"pr2": 0}),
          "ctloff": (0, {"pr2": 24}),
          "noread": (25, {"pr2": 25}),
          "fault": (4, {"pr2": 4}),
          "rc3other": (4, {"pr2": 4})}
REGS = PL.RT
PROBE_OPTS = {"--width", "--height", "--vertices"}
NEED = 0x2E0
OVERFLOW = "probe p1139-green: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def knob():
    p = os.path.join(os.environ.get("FAKE_DBGREAL", ""), "render_pb_pages")
    try:
        return int(open(p).read().strip(), 0)
    except (OSError, ValueError):
        return 0x422


def parse(argv, opts):
    got, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in opts:
            if i + 1 >= len(argv):
                return None, f"{a} without its value"
            got.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a.startswith("-"):
            return None, f"unknown option {a}"
        else:
            pos.append(a)
            i += 1
    return (got, pos), None


def scene(argv):
    if argv[:3] != ["probe", "--tri", "pixel"]:
        return None, f"no such command {argv[:1]}"
    p, why = parse(argv[3:], PROBE_OPTS)
    if p is None:
        return None, why
    o, pos = p
    if len(pos) != 1 or not os.path.exists(pos[0]):
        return None, "probe: one program FILE that exists"
    if o.get("--vertices") != ["1500"]:
        return None, "the DPM rows run --vertices 1500"
    return dict(w=int(o["--width"][0]), h=int(o["--height"][0])), None


def prs(thr0, world):
    """The partial renders the world's GPU takes at thr0."""
    n = {v: k for k, v in PL.THR0.items()}.get(thr0, 1 if thr0 < NEED else 0)
    if "ctloff" in world and thr0 == 0x400:
        n = 1
    return n


def answer(tool, argv, world):
    if tool == "rt":
        if argv[:3] != ["0", "0.3", REGS] or argv[3:4] != ["--"]:
            return usage(f"regtimeline: not TOTAL 0, LEAD 0.3 and R5-dpm's registers: {argv[:4]}")
        return None
    if not argv or argv in (["fill"], ["tri"]):
        return None
    sc, why = scene(argv)
    if sc is None:
        return usage(why)
    thr0 = knob() - PL.D_OFF
    out = f"probe p1139-green: tri {sc['w']}x{sc['h']} (1500 vertices), pixel replaced\n"
    rc = 0
    if thr0 < NEED:
        out += OVERFLOW
        rc = 3
    if "rc3other" in world and prs(thr0, world) == 4:
        out = out.replace(OVERFLOW, "") + "probe p1139-green: failed: render timed out\n"
        rc = 3
    a = dict(rc=rc, out=out, files={})
    if "fault" in world and prs(thr0, world) == 2:
        a["kmsg"] = ["SGX BIF fault: requestor 0x0 (mock)"]
        a["latch"] = (0x10, 0x10000011)
    return a


def timeline(tool, regs, argv, rc, world):
    """regtimeline's samples of the wrapped job (values per register of REGS, in order)."""
    sc, why = scene(argv)
    if sc is None:
        return None
    thr0 = knob() - PL.D_OFF
    n = prs(thr0, world)
    samples = []                                   # (pages, global pages, partial render, 0x0748)
    peak = min(thr0, NEED)
    for p in range(0, peak + 1, 16):
        samples.append((p, 1, 0, 0x1F))
    clear = "perpr" in world            # bit 2 clears once in each partial render (0x1b)
    for k in range(n):
        samples += [(peak, 1, 1, 0x1D), (peak, 1, 1, 0x1B if clear else 0x1D), (2, 1, 0, 0x1F)]
    if "clear0" in world and n == 0:
        samples.append((peak, 1, 0, 0x1B))
    if "noread" in world:
        samples = [(0, g, f, m) for p, g, f, m in samples]
    rows = []
    for p, g, f, m in samples:
        v = {0x624: thr0, 0x724: (p << 16) | p, 0x72C: (g << 16) | g, 0x658: f, 0x748: m}
        rows.append([v.get(r, 0) for r in regs])
    return rows
