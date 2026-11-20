# SPDX-License-Identifier: MIT
"""mock/world.py: the argv-driven fake laptop of the r41-n3f-* sessions (N3f rows C, X, Y, LC, T;
STEP below says the session). answer() refuses every tool (no stage runs one: every row is an
owntask row). own_res(cmd, params, world) gives the fake own task's stores for the kit's fake
fwtask_run.py ({dword: value}) by the armed line (FAKE_DIR/own) and the page so far
(FAKE_DIR/own_res.json, which the arm resets: the run id is the page's last one plus one, the
runner's count over the stage's jobs). Command 1: B11's (slot 1 M1, the run id, X0; S1; pa0-pa3,
sa0-sa3; M4 and the run id; the survey: pre sa0-sa31 = V and 0x5100 + k, post sa = pre for
form=fw14 (D0's sharing), else B11's shape (sa1 0x04400000, sa(12+k) = pa(k)), post pa = B11's
pa0-pa3 then 0). Command 6: the after-read in dwords 224-255 and M6 with the run id in slot 6:
form=fw14 after = pre (C-SAME), else after = post (X-REBASE, Y-REBASE, LC-REBASE). gate(world,
arm): the gate's texts by the armed line (the fake runner reads ok from them): form=fw14 draws;
every other arm faults its first tool (B11's fill fault and its devcoredump; row T's triangle at
0x01555000) unless the world draws it.
EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model      the predicted run: H1 c ok (C-SAME, gate exact) then x's planned gate failure (16,
             scored: the driver ends 0); H2 y, H3 lc (job 2 and 3 done: LC-REBASE's branch) and H4
             t likewise
  ownstop2   the second job never reports done: the runner's stop, rc 4 (C-NOKICK, X-NOKICK,
             LC-EARLY's shape)
  cdiff      H1: c's after-read differs from pre: the hooks stop c (C-DIFF, rc 24, on_stop end)
  cgatebad   H1: c's gate fails (rc 16; c has no on_gate_fail: the driver stops 16)
  nos1       H1: S1 absent though the job is done: the hooks stop c (rc 24)
  gateok     the last stage's gate draws: its hooks run, print the sa change, never stop (0)
  ownstop    H4: job 1 never reports done (rc 4); ownarmbad: the arm fails (rc 26)"""
import json
import os

STEP = "H3"
V = (0x32004000, 0x32005000, 0x32002000, 0x00000000)
M1, X0, M4, S1, M6 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306
SLOT1, SLOT_PA, SLOT_SA, SLOT4, SLOT5, SLOT6 = 0x44, 0x48, 0x4C, 0x50, 0x54, 0x58
PA = [0, 0x43000, 0x32002000, 0x01555620] + [0] * 12          # B11's post pa (attempt 1)
FIRST = {"H1": "c", "H2": "y", "H3": "lc", "H4": "t"}[STEP]
LAST = {"H1": "x", "H2": "y", "H3": "lc", "H4": "t"}[STEP]
EXPECT = {"H1": {"model": (0, {"c": 0, "x": 16}), "ownstop2": (4, {"c": 4}),
                 "cdiff": (24, {"c": 24}), "cgatebad": (16, {"c": 16}), "nos1": (24, {"c": 24}),
                 "gateok": (0, {"c": 0, "x": 0}), "ownarmbad": (26, {"c": 26})},
          "H2": {"model": (0, {"y": 16}), "ownstop2": (4, {"y": 4}), "gateok": (0, {"y": 0}),
                 "ownarmbad": (26, {"y": 26})},
          "H3": {"model": (0, {"lc": 16}), "ownstop2": (4, {"lc": 4}), "gateok": (0, {"lc": 0}),
                 "ownarmbad": (26, {"lc": 26})},
          "H4": {"model": (0, {"t": 16}), "ownstop": (4, {"t": 4}), "gateok": (0, {"t": 0}),
                 "ownarmbad": (26, {"t": 26})}}[STEP]
FILL_BAD = "programs asm\njob: ok\ndiff: 2048 of 2048 pixels, first (0, 0) 0xdeadbeef\n"
TRI_BAD = "tri: render context for targets up to 64x64\njob: faulted, context lost (Input/output error)\n"
DEVCD = ("**** sgxfive error state ****\ndetector: bif-fault\nrecovery: ok\n"
         "BIF_INT_STAT: 0x%08x\nBIF_FAULT: 0x%08x\n**** end ****\n")


def _fake(name):
    return os.path.join(os.environ.get("FAKE_DIR", "."), name)


def _arm():
    try:
        return open(_fake("own")).read().strip()
    except OSError:
        return ""


def _page():
    try:
        return json.load(open(_fake("own_res.json")))
    except (OSError, ValueError):
        return [0] * 1024


def _pre():
    return list(V) + [0x5100 + k for k in range(4, 32)]


def _post(arm):
    if "form=fw14" in arm:
        return _pre()
    floats = [0x3F800000, 0x3F400000, 0xBEC00000, 0, 0, 0, 0, 0, 0]
    return [V[0], 0x04400000, V[2]] + floats + PA[:16] + [0] * 4


def own_res(cmd, params, world):
    arm, p = _arm(), _page()
    r = p[3] + 1
    if cmd == 1:
        out = {SLOT1: M1, SLOT1 + 1: r, SLOT1 + 2: X0, 1: 0}
        if "nos1" not in world:
            out[SLOT5] = S1
        post = _post(arm)
        out.update({SLOT_PA + i: x for i, x in enumerate(PA[:4])})
        out.update({SLOT_SA + i: x for i, x in enumerate(post[:4])})
        out.update({SLOT4: M4, SLOT4 + 1: r})
        out.update({128 + k: x for k, x in enumerate(_pre())})
        out.update({160 + k: x for k, x in enumerate(post)})
        out.update({192 + k: x for k, x in enumerate(PA)})
        return out
    if cmd == 6:
        after = p[128:160] if "form=fw14" in arm else p[160:192]
        if "cdiff" in world:
            after = list(after)
            after[1] = 0x04400000
        out = {224 + k: x for k, x in enumerate(after)}
        out.update({SLOT6: M6, SLOT6 + 1: r, 1: 0})
        return out
    return {}


def gate(world, arm):
    if "form=fw14" in arm:
        return {"fill": FILL_BAD} if "cgatebad" in world else None
    if "gateok" in world:
        return None
    if STEP == "H4":
        return {"tri": TRI_BAD, "post": DEVCD % (0x00010400, 0x0155500F)}
    return {"fill": FILL_BAD, "post": DEVCD % (0x000D0400, 0x0004300F)}


def answer(tool, argv, world):
    return None
