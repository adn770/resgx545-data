# SPDX-License-Identifier: MIT
"""mock/world.py: the argv-driven fake laptop of the r42-n3g-* sessions (N3g rows C, M, S, Q, LV;
STEP below says the session). answer() refuses every tool (no stage runs one: every row is an
owntask row). own_res(cmd, params, world) gives the fake own task's stores for the kit's fake
fwtask_run.py ({dword: value}) by the armed line (FAKE_DIR/own) and the page so far
(FAKE_DIR/own_res.json, which the arm resets; the run id is the one the fake runner posted in
dword 3). Command 1: B11's slots (slot 1 M1, the run id, X0; S1; pa0-pa3, sa0-sa3; M4 and the run
id) and the survey: pre sa0-sa31 = V and 0x5100 + k; post sa = pre for form=fw14 (C and S: D0's
sharing), else the frozen predictions' shape (H-BLOCK): X's post (round 41, E1174) with, for
pds=mark, sa1 = M1 and sa13 = M13 (row M), for form=sb402 V0/V2 in every fourth word from sa4
(row Q) and for pds=landv sa0 = V0, sa2 = V2 (row LV); post pa = X's with pa1 = M13 after row M
(rows M, S, Q, LV: S-KEEP) and 0x00043000 before it (row C: R-BOOT as in nine kept rows).
Command 6: the after-read in dwords 224-255 and M6 with the run id in slot 6: form=fw14 after =
pre (C-SAME), else after = post (M-REBASE, Q-REBASE, LV-REBASE; LV's job 3 no heal). gate(world,
arm): the gate's texts by the armed line (the fake runner reads ok from them): form=fw14 draws;
every other arm faults its fill at the page of the post sa13 with its devcoredump, unless the
world draws it.
EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model      the predicted run: G1 c ok (C-SAME, gate exact) then m's planned gate failure (16,
             scored: the driver ends 0); G2 s then q likewise; G3 lv's planned gate failure
  ownstop2   the second job never reports done: the runner's stop, rc 4 (C-NOKICK, M-NOKICK,
             LV-EARLY's shape); its cmd word 6 stays posted on the page (E0 reads job 1's record)
  bifjob2    the model run with a fault after job 1 in every later job's K5 words (printed only)
  cdiff      G1, G2: the control's after-read differs from pre: the hooks stop it (C-DIFF, rc 24)
  cgatebad   G1, G2: the control's gate fails (rc 16; no on_gate_fail: the driver stops 16)
  nos1       G1, G2: S1 absent though the job is done: the hooks stop the control (rc 24)
  gateok     the last stage's gate draws: its hooks run, print the sa change, never stop (0)
  ownarmbad  the arm fails (rc 26)"""
import json
import os

STEP = "G1"
V = (0x32004000, 0x32005000, 0x32002000, 0x00000000)
M1, X0, M4, S1, M6 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306
MK13, MK1 = 0x005D3000, 0x005D1000
SLOT1, SLOT_PA, SLOT_SA, SLOT4, SLOT5, SLOT6 = 0x44, 0x48, 0x4C, 0x50, 0x54, 0x58
# X's post pa (round 41, E1174); pa1 is M13 once row M ran (S-KEEP), 0x00043000 before it
X_PA = [0x3, 0x43000, 0x32411000, 0x01555620, 0x32004000, 0, 0x32002000, 0x03C3CDAC, 0x32004000,
        0xDC531A54, 0x32002000, 0x5D50716F, 0x32004000, 0x82E151B5, 0x32002000, 0x11B5D77A]
X_LOW = [0x32004000, 0x04000010, 0x32002000, 0x3F800000, 0x3F400000, 0xBEC00000, 0, 0x3F800000,
         0xBEC00000, 0x3F400000, 0, 0]          # X's post sa0-sa11 (E1174)
X_HIGH = [0x32004000, 0x9ECC832E, 0x32002000, 0x4D21D720]   # X's post sa28-sa31
FIRST = {"G1": "c", "G2": "s", "G3": "lv"}[STEP]
LAST = {"G1": "m", "G2": "q", "G3": "lv"}[STEP]
EXPECT = {"G1": {"model": (0, {"c": 0, "m": 16}), "ownstop2": (4, {"c": 4}),
                 "bifjob2": (0, {"c": 0, "m": 16}), "cdiff": (24, {"c": 24}),
                 "cgatebad": (16, {"c": 16}), "nos1": (24, {"c": 24}),
                 "gateok": (0, {"c": 0, "m": 0}), "ownarmbad": (26, {"c": 26})},
          "G2": {"model": (0, {"s": 0, "q": 16}), "ownstop2": (4, {"s": 4}),
                 "bifjob2": (0, {"s": 0, "q": 16}), "cdiff": (24, {"s": 24}),
                 "cgatebad": (16, {"s": 16}), "nos1": (24, {"s": 24}),
                 "gateok": (0, {"s": 0, "q": 0}), "ownarmbad": (26, {"s": 26})},
          "G3": {"model": (0, {"lv": 16}), "ownstop2": (4, {"lv": 4}),
                 "bifjob2": (0, {"lv": 16}), "gateok": (0, {"lv": 0}),
                 "ownarmbad": (26, {"lv": 26})}}[STEP]
FILL_BAD = "programs asm\njob: ok\ndiff: 2048 of 2048 pixels, first (0, 0) 0xdeadbeef\n"
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


def _pa(arm):
    pa = list(X_PA)
    if STEP != "G1" or "pds=mark" in arm:
        pa[1] = MK13                    # S-KEEP: M's marker kept in attribute 13 (pa1)
    if "form=sb402" in arm:
        pa[0], pa[2] = V[0], V[2]       # attributes 12 and 14: sa12 = V0, sa14 = V2 (Q-REP)
    return pa


def _post(arm):
    if "form=fw14" in arm:
        return _pre()
    low = list(X_LOW)
    if "pds=mark" in arm:
        low[1] = MK1                    # M-SA1 (H-BLOCK)
    if "form=sb402" in arm:
        for k in (4, 8):
            low[k] = V[0]
        for k in (6, 10):
            low[k] = V[2]               # Q-REP
    return low + _pa(arm) + X_HIGH


def own_res(cmd, params, world):
    arm, p = _arm(), _page()
    r = p[3]
    if cmd == 1:
        out = {SLOT1: M1, SLOT1 + 1: r, SLOT1 + 2: X0, 1: 0}
        if "nos1" not in world:
            out[SLOT5] = S1
        post = _post(arm)
        pa = _pa(arm)
        out.update({SLOT_PA + i: x for i, x in enumerate(pa[:4])})
        out.update({SLOT_SA + i: x for i, x in enumerate(post[:4])})
        out.update({SLOT4: M4, SLOT4 + 1: r})
        out.update({128 + k: x for k, x in enumerate(_pre())})
        out.update({160 + k: x for k, x in enumerate(post)})
        out.update({192 + k: x for k, x in enumerate(pa)})
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
    page = _post(arm)[13] & ~0xFFF
    return {"fill": FILL_BAD, "post": DEVCD % (0x000D0400, page | 0xF)}


def answer(tool, argv, world):
    return None
