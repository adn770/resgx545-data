# SPDX-License-Identifier: MIT
"""mock/world.py: r9-ldpm's fake laptop for kit/session.py mock (r8-ldpm's, cut to this session's
rows). answer() sees the tool's name, the argv and the world's tokens, never a case name;
timeline() gives regtimeline's samples (the kit's fake regtimeline runs the wrapped tool's fake,
then prints them). The threshold is what the GPU sees: the debugfs knob render_pb_pages as the kit
wrote it (the fake debugfs, $FAKE_DBGREAL), never a row's name. The scene follows the frozen tables
(gen/plan.py: E874's step model, OD-2's H-NEXT1 end of band 6, F9), so in the world `model` every
control passes.

The fake is as strict as the tool (sgxfive-test of resgx545 4623753) on this session's rows:
`probe` takes only --tri pixel, --width, --height, --vertices 1500, --dump-render DIR and one
program FILE that exists; `tri` only --width, --height, -n, --keep-overflow, --wait-ms, --words,
--regs; any other option is rc 2. regtimeline (rt) must be `0 0.3 REGS -- CMD...` with R5-dpm's 16
registers.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     every stage runs, every control passes
  ctloff    a0-c4-b5's job leaves 1 global page, not 2: hook_check stops a0 (rc 24) and the gate
            keeps every later stage from running
  noread    a0-cal-2048's capture has no 0x0724 page count: no knob, no steps; the control has no
            reading, the premise stops the session (rc 25)
  fault     a 2304x2304 band 6 job of m6b faults: rc 4, the session stops
  rc3other  a w job ends rc 3 without the overflow line: not the expected end, rc 4
  m6boff    an E936 replicate of m6b leaves 1 page where 2 are frozen: no stop (the scorer gates
            the stage's verdicts), every stage runs
  f9boff    f9b's 1280x1280 calibration needs one page more: hook_check stops f9b (rc 24)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import plan as PL  # noqa: E402

EXPECT = {"model": (0, {"a0": 0, "m6b": 0, "w": 0, "f9b": 0}),
          "ctloff": (0, {"a0": 24}),
          "noread": (25, {"a0": 25}),
          "fault": (4, {"a0": 0, "m6b": 4}),
          "rc3other": (4, {"a0": 0, "m6b": 0, "w": 4}),
          "m6boff": (0, {"a0": 0, "m6b": 0, "w": 0, "f9b": 0}),
          "f9boff": (0, {"a0": 0, "m6b": 0, "w": 0, "f9b": 24})}
REGS = PL.RT
PROBE_OPTS = {"--width", "--height", "--vertices", "--dump-render"}
TRI_OPTS = {"--width", "--height", "-n", "--wait-ms", "--words", "--regs"}
TRI_FLAGS = {"--keep-overflow"}
OVERFLOW = "probe p1139-green: failed: scene overflowed the parameter buffer, context kept (No space left on device)\n"


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def knob():
    p = os.path.join(os.environ.get("FAKE_DBGREAL", ""), "render_pb_pages")
    try:
        return int(open(p).read().strip(), 0)
    except (OSError, ValueError):
        return 0x422


def parse(argv, opts, flags=()):
    got, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in flags:
            got.setdefault(a, []).append(True)
            i += 1
        elif a in opts:
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


def end6(w, h):
    """The world's band 6 end: OD-2's H-NEXT1 (after[b_6 + 1]); A_6 where no m6b row names one."""
    S, A, U, after = PL.model(w, h)
    return after[1] if after else A[6]


def scene(argv):
    if argv[:3] == ["probe", "--tri", "pixel"]:
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
        return dict(kind="probe", w=w, h=h, S=S, A=A, U=U, E6=end6(w, h),
                    dump=o.get("--dump-render", [None])[0]), None
    if argv[:1] == ["tri"]:
        p, why = parse(argv[1:], TRI_OPTS, TRI_FLAGS)
        if p is None:
            return None, why
        o, pos = p
        if pos:
            return None, f"tri takes no FILE ({pos})"
        w, h = int(o["--width"][0]), int(o["--height"][0])
        if (w, h) != (4096, 4096) or o.get("-n") != ["1"]:
            return None, "the only tri row is a0's g-qf (4096x4096, -n 1)"
        return dict(kind="tri", w=w, h=h, S={}, A={}, U=287, E6=None,
                    dump=None, words=o.get("--words", [None])[0]), None
    return None, f"no such command {argv[:1]}"


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
    if sc["kind"] == "probe":
        out = f"probe p1139-green: tri {sc['w']}x{sc['h']} (1500 vertices), pixel replaced\n"
        rc = 0
        if thr0 < sc["U"]:
            out += OVERFLOW
            rc = 3
            if "rc3other" in world and (sc["w"], sc["h"]) == (4096, 1024):
                out = out.replace("scene overflowed the parameter buffer", "render timed out")
        if sc["dump"]:
            for k in ("param", "tadata"):
                files[os.path.join(sc["dump"], f"p1139-green.{k}.bin")] = bytes(64)
        a = dict(rc=rc, out=out, files=files)
    else:
        over = thr0 < sc["U"]
        out = f"tri: render context for targets up to {sc['w']}x{sc['h']}\n"
        out += "job: failed: scene overflowed the parameter buffer, context kept\n" if over else "job: ok\n"
        out += f"target: {sc['w']}x{sc['h']} hash 0x0\ndiff: 0 of {sc['w'] * sc['h']} pixels\n"
        if sc["words"]:
            files[os.path.join(sc["words"], "words.0.txt")] = "reg 0x0700 0x00000000\n"
        a = dict(rc=0, out=out, files=files)
    if "fault" in world and sc["kind"] == "probe" and (sc["w"], sc["h"]) == (2304, 2304) and thr0 < sc["U"]:
        a["kmsg"] = ["SGX BIF fault: requestor 0x0 (mock)"]
        a["latch"] = (0x10, 0x10000011)
    return a


def runpeaks(sc, thr0):
    """The runs' peaks of the frozen tables where they have them, else one partial render."""
    w, h, U = sc["w"], sc["h"], sc["U"]
    if thr0 >= U:
        return [U]
    if sc["kind"] == "probe":
        for x in PL.T["w"]:
            if (x["w"], x["h"]) == (w, h) and int(x["thr0"], 16) == thr0:
                return [int(v, 16) for v in x["F9"][1]]
        for x in PL.T["f9b"]:
            if (x["w"], x["h"]) == (w, h):
                for c in x["cells"]:
                    if int(c["thr0"], 16) == thr0:
                        return [int(v, 16) for v in c["F9"][1]]
        return [thr0, max(2, min(U - thr0 + 1, thr0 + 0x20))]
    return list(PL.QF_PEAKS)


def timeline(tool, regs, argv, rc, world):
    """regtimeline's samples of the wrapped job (values per register of REGS, in order)."""
    sc, why = scene(argv)
    if sc is None:
        return None
    thr0 = knob() - PL.D_OFF
    S = sc["S"]
    peaks = runpeaks(sc, thr0)
    left = 1
    if S and 6 in S and S[6] < thr0 < S.get(7, 1 << 30):
        left = PL.left_by(thr0, S, sc["E6"]) or 1
    elif S:
        ks = [k for k in sorted(S) if S[k] < thr0]
        if ks and ks[-1] in sc["A"] and thr0 < sc["A"][ks[-1]] and ks[-1] != 6:
            left = 2
    if "ctloff" in world and (sc["w"], sc["h"], thr0) == (2048, 2048, 0xE2):
        left = 1
    if "m6boff" in world and (sc["w"], sc["h"], thr0) == (1536, 1536, 0x109):
        left = 1
    if "f9boff" in world and (sc["w"], sc["h"]) == (1280, 1280) and thr0 >= sc["U"]:
        peaks = [sc["U"] + 1]
    samples = [(0, 0, 0)]                          # (pages, global pages, partial render)
    g = 1
    for i, pk in enumerate(peaks):
        start = 1 if i == 0 else 2
        for p in range(start, pk + 1):
            if i == 0:
                g = 1 + sum(1 for v in S.values() if v < p)
            samples.append((p, g, 0))
        if i < len(peaks) - 1:
            g = left if i == 0 else 1
            samples += [(pk, g, 1), (1, g, 1)]
    if "noread" in world and sc["kind"] == "probe" and thr0 == 0x140:
        samples = [(0, g, f) for p, g, f in samples]
    rows = []
    for p, g, f in samples:
        v = {0x624: thr0, 0x724: (p << 16) | p, 0x72C: (g << 16) | g, 0x658: f}
        rows.append([v.get(r, 0) for r in regs])
    return rows
