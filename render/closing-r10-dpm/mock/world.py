# SPDX-License-Identifier: MIT
"""mock/world.py: r10-dpm's fake laptop for kit/session.py mock (r9-ldpm's, cut to this session's
rows). answer() sees the tool's name, the argv and the world's tokens, never a case name;
timeline() gives regtimeline's samples (the kit's fake regtimeline runs the wrapped tool's fake,
then prints them). The threshold is what the GPU sees: the debugfs knob render_pb_pages as the kit
wrote it (the fake debugfs, $FAKE_DBGREAL), never a row's name. The scene follows the frozen tables
(gen/plan.py: E874's step model; S_6 at the five targets as the kept reads, PL.KEPT), so in the
world `model` every control passes.

The fake is as strict as the tool (sgxfive-test of resgx545 4623753) on this session's rows:
`probe` takes only --tri pixel, --width, --height, --vertices 1500, --dump-render DIR and one
program FILE that exists; any other option is rc 2. regtimeline (rt) must be `0 0.3 REGS -- CMD...`
with R5-dpm's 16 registers.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     the stage runs, both controls pass
  ctloff    a0-cal-2048's job leaves 1 global page, not 2: hook_check stops the stage (rc 24)
  noread    a0-cal-2048's capture has no 0x0724 page count: no knob, no steps; the control has no
            reading, the premise stops the session (rc 25)
  fault     a 4096x1024 replicate faults: rc 4, the session stops
  rc3other  a 4096x1536 replicate ends rc 3 without the overflow line: not the expected end, rc 4
  needoff   a0-cal-2048f needs one page more: hook_check stops the stage (rc 24)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import plan as PL  # noqa: E402

EXPECT = {"model": (0, {"s6rep": 0}),
          "ctloff": (0, {"s6rep": 24}),
          "noread": (25, {"s6rep": 25}),
          "fault": (4, {"s6rep": 4}),
          "rc3other": (4, {"s6rep": 4}),
          "needoff": (0, {"s6rep": 24})}
REGS = PL.RT
PROBE_OPTS = {"--width", "--height", "--vertices", "--dump-render"}
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
    w, h = int(o["--width"][0]), int(o["--height"][0])
    S, A, U, after = PL.model(w, h)
    if (w, h) in PL.KEPT:
        S[6] = PL.KEPT[(w, h)]                     # the world reads S_6 as the kept runs did
    return dict(kind="probe", w=w, h=h, S=S, A=A, U=U, dump=o.get("--dump-render", [None])[0]), None


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
    files = {}
    out = f"probe p1139-green: tri {sc['w']}x{sc['h']} (1500 vertices), pixel replaced\n"
    rc = 0
    if thr0 < sc["U"]:
        out += OVERFLOW
        rc = 3
    if "rc3other" in world and (sc["w"], sc["h"]) == (4096, 1536):
        out = out.replace(OVERFLOW, "") + "probe p1139-green: failed: render timed out\n"
        rc = 3
    if sc["dump"]:
        for k in ("param", "tadata"):
            files[os.path.join(sc["dump"], f"p1139-green.{k}.bin")] = bytes(64)
    a = dict(rc=rc, out=out, files=files)
    if "fault" in world and (sc["w"], sc["h"]) == (4096, 1024):
        a["kmsg"] = ["SGX BIF fault: requestor 0x0 (mock)"]
        a["latch"] = (0x10, 0x10000011)
    return a


def timeline(tool, regs, argv, rc, world):
    """regtimeline's samples of the wrapped job (values per register of REGS, in order)."""
    sc, why = scene(argv)
    if sc is None:
        return None
    thr0 = knob() - PL.D_OFF
    S, U = sc["S"], sc["U"]
    if "needoff" in world and (sc["w"], sc["h"]) == (2048, 2048) and thr0 >= U:
        U += 1
    peak = U if thr0 >= U else thr0
    left = 1
    if S and 6 in S and S[6] < thr0 < S.get(7, 1 << 30):
        left = 1
    elif S:
        ks = [k for k in sorted(S) if S[k] < thr0]
        if ks and ks[-1] in sc["A"] and thr0 < sc["A"][ks[-1]]:
            left = 2
    if "ctloff" in world and (sc["w"], sc["h"], thr0) == (2048, 2048, 0x140):
        left = 1
    samples = [(0, 0, 0)]                          # (pages, global pages, partial render)
    g = 1
    for p in range(1, peak + 1):
        g = 1 + sum(1 for v in S.values() if v < p)
        samples.append((p, g, 0))
    if thr0 < U:                                   # the abort: one partial render, then a short run
        samples += [(peak, left, 1), (1, left, 1), (2, left, 0), (max(2, U - peak), left, 0)]
    if "noread" in world and thr0 == 0x140:
        samples = [(0, g, f) for p, g, f in samples]
    rows = []
    for p, g, f in samples:
        v = {0x624: thr0, 0x724: (p << 16) | p, 0x72C: (g << 16) | g, 0x658: f}
        rows.append([v.get(r, 0) for r in regs])
    return rows
