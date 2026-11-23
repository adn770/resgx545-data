# SPDX-License-Identifier: MIT
"""mock/world.py: the argv-driven fake laptop of the r43-n3h-* sessions (N3h rows W, V, W2, F;
STEP below says the session). answer() refuses every tool (no stage runs one: every row is an
owntask row). own_res(cmd, params, world) gives the fake own task's stores for the kit's fake
fwtask_run.py ({dword: value}) by the armed line (FAKE_DIR/own) and the page so far
(FAKE_DIR/own_res.json, which the arm resets; the run id is the one the fake runner posted in
dword 3). Command 1: B11's slots (slot 1 M1, the run id, X0; S1; pa0-pa3, sa0-sa3; M4 and the run
id) and the survey: pre sa0-sa31 = V and 0x5100 + k; post sa the frozen predictions' shape: X's
post (round 41, E1174) with sa13 = M13 and, for pds=mark, sa1 = M1 (W-SA1), for pds=landv sa0 =
V0, sa2 = V2, sa1 = M1 (V-KEEP), for pds=crumb3 sa1 = 0x04000010 (F-FILL4); post pa = X's with
pa1 = M13. Command 6: the after-read = post (K-SERVE's shape) and M6 with the run id in slot 6.
bif(index, n, world): the K5 words as predicted: landv's job 2 faults at M1's page from its pre
on (V-EARLY1); crumb3's kick-only job 2 reads 0 before its kick and M13's page in mid and post
(K-QUIET, K-KICK), job 3 the same throughout. gate(world, arm): the fill faults at the page of
the post sa13 with its devcoredump, unless the world draws it (gateok).
EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  ownstop2   the design's run: every job after job 1 not done (the kick-only job's expected end):
             N1 w ok (no gate, no end draws), v's planned stop (V-EARLY1: rc 4, the driver
             stops 4); N2 w2 ok, f's K-STALL stop (rc 4)
  model      every command job served: N1 v ends ok (V-SERVE's shape), its gate faults (rc 16,
             no on_gate_fail: the driver stops 16); N2 f's gate faults, its planned end (16,
             scored: the driver ends 0)
  gateok     N2: f's gate draws (0)
  bifjob2    the model run with a fault after job 1 in every later job's K5 words (printed only)
  regbad     the register health fails at w's (w2's) end: recovery draws, rc 16
  ownarmbad  the arm fails (rc 26)"""
import json
import os

STEP = "N1"
V = (0x32004000, 0x32005000, 0x32002000, 0x00000000)
M1, X0, M4, S1, M6 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306
MK13, MK1, EVT4 = 0x005D3000, 0x005D1000, 0x04000010
SLOT1, SLOT_PA, SLOT_SA, SLOT4, SLOT5, SLOT6 = 0x44, 0x48, 0x4C, 0x50, 0x54, 0x58
X_PA = [0x3, MK13, 0x32411000, 0x01555620, 0x32004000, 0, 0x32002000, 0x03C3CDAC, 0x32004000,
        0xDC531A54, 0x32002000, 0x5D50716F, 0x32004000, 0x82E151B5, 0x32002000, 0x11B5D77A]
X_LOW = [0x32004000, 0x04000010, 0x32002000, 0x3F800000, 0x3F400000, 0xBEC00000, 0, 0x3F800000,
         0xBEC00000, 0x3F400000, 0, 0]          # X's post sa0-sa11 (E1174)
X_HIGH = [0x32004000, 0x9ECC832E, 0x32002000, 0x4D21D720]   # X's post sa28-sa31
EXPECT = {"N1": {"ownstop2": (4, {"w": 0, "v": 4}), "model": (16, {"w": 0, "v": 16}),
                 "bifjob2": (16, {"w": 0, "v": 16}), "regbad": (16, {"w": 16}),
                 "ownarmbad": (26, {"w": 26})},
          "N2": {"ownstop2": (4, {"w2": 0, "f": 4}), "model": (0, {"w2": 0, "f": 16}),
                 "gateok": (0, {"w2": 0, "f": 0}), "bifjob2": (0, {"w2": 0, "f": 16}),
                 "regbad": (16, {"w2": 16}), "ownarmbad": (26, {"w2": 26})}}[STEP]
FILL_BAD = "programs asm\njob: ok\ndiff: 2048 of 2048 pixels, first (0, 0) 0xdeadbeef\n"
DEVCD = ("**** sgxfive error state ****\ndetector: bif-fault\nrecovery: ok\n"
         "BIF_INT_STAT: 0x%08x\nBIF_FAULT: 0x%08x\n**** end ****\n")
FAULT_STAT = 0x000D0400


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
    low = list(X_LOW)
    if "pds=mark" in arm or "pds=landv" in arm:
        low[1] = MK1                    # W-SA1, V-KEEP
    if "pds=crumb3" in arm:
        low[1] = EVT4                   # F-FILL4
    return low + list(X_PA) + X_HIGH    # sa13 = X_PA[1] = M13


def own_res(cmd, params, world):
    arm, p = _arm(), _page()
    r = p[3]
    if cmd == 1:
        post = _post(arm)
        out = {SLOT1: M1, SLOT1 + 1: r, SLOT1 + 2: X0, 1: 0, SLOT5: S1}
        out.update({SLOT_PA + i: x for i, x in enumerate(X_PA[:4])})
        out.update({SLOT_SA + i: x for i, x in enumerate(post[:4])})
        out.update({SLOT4: M4, SLOT4 + 1: r})
        out.update({128 + k: x for k, x in enumerate(_pre())})
        out.update({160 + k: x for k, x in enumerate(post)})
        out.update({192 + k: x for k, x in enumerate(X_PA)})
        return out
    if cmd == 6:
        out = {224 + k: x for k, x in enumerate(p[160:192])}
        out.update({SLOT6: M6, SLOT6 + 1: r, 1: 0})
        return out
    return {}


def bif(i, n, world):
    if "bifjob2" in world or i == 0:
        return None
    arm = _arm()
    if "pds=landv" in arm:
        f = [FAULT_STAT, MK1 | 0xF]
        return {"pre": f, "post": list(f)}
    if "pds=crumb3" in arm:
        f = [FAULT_STAT, MK13 | 0xF]
        if n == 0:
            return {"pre": [0, 0], "mid": f, "post": list(f)}
        return {"pre": f, "mid": list(f), "post": list(f)}
    return None


def gate(world, arm):
    if "gateok" in world:
        return None
    page = _post(arm)[13] & ~0xFFF
    return {"fill": FILL_BAD, "post": DEVCD % (FAULT_STAT, page | 0xF)}


def answer(tool, argv, world):
    return None
