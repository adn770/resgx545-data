# SPDX-License-Identifier: MIT
"""mock/world.py: r14-dpm's fake laptop for kit/session.py mock (r13-dpm's, cut to stage pr3 over the
one register 0x0748). answer() sees the tool's name, the argv and the world's tokens, never a case
name. The wrapper (regtimeline, tool "rt") is answered here: the world runs the wrapped t10's
answer and appends regtimeline's block with a real-looking header (samples, start, end), so the
sampling period is the world's. The threshold is what the GPU sees: the debugfs knob
render_pb_pages as the kit wrote it (the fake debugfs, $FAKE_DBGREAL), never a row's name. The scene
is 3072x2048 (PL.THR0: thr0 -> partial renders, r8-ldpm's kept counts); the need there is 0x2e0
(above thr0 0x294, below 0x400).

The fake is as strict as the tool (sgxfive-test of resgx545 a581c06) on this session's rows: `probe`
takes only --tri pixel, --width, --height, --vertices 1500 and one program FILE that exists; any
other option is rc 2. regtimeline (rt) must be `0 0.3 0x0748 -- CMD...`.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     counts 0, 1, 4, 7, bit 2 never clears, 460 ns period: the stage runs, controls pass
  clear0    the PR 0 rows clear bit 2 once (the finding "none at 0" would refute): the stage runs
  perpr     one clear event per partial render at every row: the stage runs
  slow      a 7500 ns period (R-PULSE not testable): hook_check stops the stage (rc 24)
  noread    the captures have no timeline lines: no reading; the premise stops the session (rc 25)
  fault     the 4-PR rows fault: rc 4, the session stops
  rc3other  the 4-PR rows end rc 3 without the overflow line: not the expected end, rc 4
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import plan as PL  # noqa: E402

EXPECT = {"model": (0, {"pr3": 0}),
          "clear0": (0, {"pr3": 0}),
          "perpr": (0, {"pr3": 0}),
          "slow": (0, {"pr3": 24}),
          "noread": (25, {"pr3": 25}),
          "fault": (4, {"pr3": 4}),
          "rc3other": (4, {"pr3": 4})}
PROBE_OPTS = {"--width", "--height", "--vertices"}
NEED = 0x2E0
OVERFLOW = "probe p1139-green: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"
END_NS = 1_500_000_000
START_NS = 300_000_000


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


def prs(thr0):
    """The partial renders the world's GPU takes at thr0 (the kept counts, else 1 below the need)."""
    return {v: k for k, v in PL.THR0.items()}.get(thr0, 1 if thr0 < NEED else 0)


def inner(argv, world):
    sc, why = scene(argv)
    if sc is None:
        return usage(why)
    thr0 = knob() - PL.D_OFF
    out = f"probe p1139-green: tri {sc['w']}x{sc['h']} (1500 vertices), pixel replaced\n"
    rc = 0
    if thr0 < NEED:
        out += OVERFLOW
        rc = 3
    if "rc3other" in world and prs(thr0) == 4:
        out = out.replace(OVERFLOW, "") + "probe p1139-green: failed: render timed out\n"
        rc = 3
    a = dict(rc=rc, out=out, files={})
    if "fault" in world and prs(thr0) == 4:
        a["kmsg"] = ["SGX BIF fault: requestor 0x0 (mock)"]
        a["latch"] = (0x10, 0x10000011)
    return a


def lines(thr0, world):
    """(t_ns, 0x0748) per change: idle before the command, then a bit 2 clear in each partial render
    in the worlds that have one."""
    n = prs(thr0)
    ls = [(0, 0x1F)]
    t = START_NS + 50_000
    for _ in range(n):
        ls += [(t, 0x1D), (t + 2_000, 0x1B if "perpr" in world else 0x1D), (t + 2_900, 0x1F)]
        t += 100_000_000
    if "clear0" in world and n == 0:
        ls += [(t, 0x1B), (t + 900, 0x1F)]
    return ls


def answer(tool, argv, world):
    if tool == "rt":
        if argv[:4] != ["0", "0.3", PL.RT, "--"] or len(argv) < 6:
            return usage(f"regtimeline: not TOTAL 0, LEAD 0.3 and the register 0x0748: {argv[:4]}")
        a = inner(argv[5:], world)
        if a.get("rc") == 2 or a.get("out") is None:
            return a
        period = 7500 if "slow" in world else 460
        out = a["out"] + (f"timeline: regs {PL.RT} samples {END_NS // period} seconds 0 start {START_NS} "
                          f"end {END_NS} rc {a['rc']}\n")
        if "noread" not in world:
            out += "".join(f"tl {t} {v:08x}\n" for t, v in lines(knob() - PL.D_OFF, world))
        a["out"] = out
        return a
    if not argv or argv in (["fill"], ["tri"]):
        return None
    return inner(argv, world)
