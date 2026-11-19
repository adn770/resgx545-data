# SPDX-License-Identifier: MIT
"""mock/world.py: r38-n3c-s1's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (a refusal, the
health pair, or the wrapper whose wrapped tool the kit's fake runs) or dict(rc, out, err).
own_res(cmd, params, world) is the fake own task's stores for the kit's fake fwtask_run.py
({dword: value}) of a job that ends ok: emitsn's (slot 1: M1, the run id, X0; slot 4: M4 and the
run id), the run id from the task's own count of commands since the arm (FAKE_DIR/n3c.runs).
timeline() gives regtimeline's stored samples of 0x0acc for th: a running count, then 0x00abcde0
held (the kit's fake prints them 1 us apart; interval_ns gives E1133's t1d TOTAL / samples). The kit's
fake snapshots have no 0x0acc, so T0 and snap9 read cannot tell in the mock's scores.
The fake runner stores nothing for a job that is not done, so N0-STOP is the scorer's tests'
(tests/attempt.py), not the mock's.

t30's forms as the session runs them: the health pair's bare `tri` and `fill` (E1134's texts) and
th's `probe --temps 32 --pds 36 --use .../bins/sa_dump.bin .../bins/pds-timer-tim-host__0.bin`
(the recorded run's text, resgx545-data pds/timer/pds-timer-tim-host/raw.txt); any other argv is
a refusal.

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     N0-OK and V0-HOLDS: every stage ends ok
  v0not     th's timeline runs throughout (V0-NOT's shape): no stop, every stage ok
  nox0      X0 absent but the job done: hooks stop own (rc 24), on_stop end ends the run
  nomark4   done's marker absent but the job done: hooks stop own (rc 24)
  fillbad   a store in slot 5 (dword 84) though the job is done: hooks stop own (rc 24)
  ownstop   the job never reports done (the runner's stop, rc 1): unexplained failure, rc 4, the
            session ends (N0-STOP)
  ownhang   the same with the tick frozen: the runner's "firmware hung" stop, rc 4
  owngatebad  the gate after the job fails (rc 16); ownarmbad the arm fails (rc 26)
  probefail th's probe fails (rc 1, a `failed:` line): unexplained failure, rc 4, the session
            ends before post
  postbad   post's triangle drew without `job: ok`: hooks stop post (rc 24, the last stage: the
            driver ends 0)"""
import os

EXPECT = {"model": (0, {"own": 0, "tim": 0, "post": 0}),
          "v0not": (0, {"own": 0, "tim": 0, "post": 0}),
          "nox0": (24, {"own": 24}), "nomark4": (24, {"own": 24}), "fillbad": (24, {"own": 24}),
          "ownstop": (4, {"own": 4}), "ownhang": (4, {"own": 4}),
          "owngatebad": (16, {"own": 16}), "ownarmbad": (26, {"own": 26}),
          "probefail": (4, {"own": 0, "tim": 4}),
          "postbad": (0, {"own": 0, "tim": 0, "post": 24})}
M1, X0, M4 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302
SLOT1, SLOT4 = 0x44, 0x50
TIM = 0x00ABCDE0
N_RUN = 2000
# t30's texts for the health pair's argv (the shape of E1134's kept begin.health1/fill1)
TRI = ("tri: render context for targets up to 64x64\njob: ok\n"
       "target: 64x64 hash 0x99385a04ee01c585\ndiff: 0 of 4096 pixels\noutside: 0 dwords\n"
       "tri: 1 renders ok\n")
FILL = ("programs asm\njob: ok\njob time: 470 us\ntarget: 64x32 hash 0xb60c6095080bd325\n"
        "diff: 0 of 2048 pixels\noutside: 0 dwords\n"
        "fill: ok, 64x32 at (0, 0), stride 256, colour 0xff336699\n")
# the recorded run's scratch (raw.txt): input A at +0x000, tim at +0x008-0x014 and +0x028-0x034
SCRATCH = [TIM, 0, TIM, TIM, TIM, TIM, 0, 0, 0, 0, TIM, TIM, TIM, TIM, 0, 0]
PROBE_HEAD = ["probe", "--temps", "32", "--pds", "36", "--use"]


def probe_out(name):
    out = ["programs asm", f"probe {name}: scratch at 0x3e003000 (64 KiB)",
           f"probe {name}: o0 0x0da7a000 (2048 of 2048)"]
    out += [f"probe {name}: scratch +0x{4 * i:03x} 0x{v:08x}" for i, v in enumerate(SCRATCH)]
    return "\n".join(out) + "\n"


def runid():
    p = os.path.join(os.environ.get("FAKE_DIR", "."), "n3c.runs")
    try:
        n = int(open(p).read()) + 1
    except (OSError, ValueError):
        n = 1
    open(p, "w").write(str(n))
    return n


def own_res(cmd, params, world):
    if cmd != 1:
        return {}
    r = runid()
    out = {SLOT1: M1, SLOT1 + 1: r, 1: 0}
    if "nox0" not in world:
        out[SLOT1 + 2] = X0
    if "nomark4" not in world:
        out.update({SLOT4: M4, SLOT4 + 1: r})
    if "fillbad" in world:
        out[0x54] = 0x5A5A3304
    return out


def is_probe(argv):
    return (len(argv) == 8 and argv[:6] == PROBE_HEAD and argv[6].endswith("/bins/sa_dump.bin")
            and argv[7].endswith("/bins/pds-timer-tim-host__0.bin")
            and all(os.path.isfile(a) for a in argv[6:]))


def answer(tool, argv, world):
    if tool == "rt":
        return None             # the kit's fake runs the wrapped tool, then timeline()
    if tool != "t30":
        return None
    if argv == ["tri"]:
        return dict(out=TRI.replace("job: ok\n", "") if "postbad" in world else TRI)
    if argv == ["fill"]:
        return dict(out=FILL)
    if is_probe(argv):
        name = os.path.basename(argv[7])[:-4]
        if "probefail" in world:
            return dict(rc=1, out=f"probe {name}: failed: job faulted, context lost "
                                  "(Input/output error)\n")
        return dict(out=probe_out(name))
    return None


def timeline(tool, regs, argv, rc, world):
    if regs != [0x0ACC] or not is_probe(argv):
        return None
    rows = [[0x01000000 | ((0x40000 - 399 * i) % 400000)] for i in range(N_RUN)]
    if "v0not" not in world:
        rows.append([TIM])
    return rows


def interval_ns(tool, regs, argv, rc, world):
    """E1133's t1d reading (3018 to 3126 ns: TOTAL / samples), so th's ivl passes in the mock."""
    return 3100
