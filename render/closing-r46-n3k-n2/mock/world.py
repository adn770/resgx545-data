# SPDX-License-Identifier: MIT
"""mock/world.py: the argv-driven fake laptop of the r46-n3k-* sessions (N3k rows W, ZFF2, LFF2,
LFF3, LF3F, Q2, R, P, R2, P2, B5, B6; STEP below says the session). answer() draws the health fill
and triangle (the kit's default) and, in world fill2bad, fails a fill that follows a fill (K8: the
second draw of `fill,fill`); it refuses every other tool (no stage runs one: every row is an
owntask row). own_res(cmd, params, world) gives the fake own task's stores for the kit's fake
fwtask_run.py ({dword: value}) by the armed line (FAKE_DIR/own) and the page so far
(FAKE_DIR/own_res.json, which the arm resets; the run id is the one the fake runner posted in dword
3). Command 1: B11's slots (slot 1 M1, the run id, X0; S1; pa0-pa3, sa0-sa3; M4 and the run id)
and the survey: pre sa0-sa31 = V and 0x5100 + k; post sa X's post (round 41, E1174) with sa13 =
M13 and, for pds=mark and pds=land, sa1 = M1, for pds=crumbz sa1 = M1 and sa0 = 2, for pds=landq
sa0 = Q0 and sa1 = M1, for pds=landr sa0 = 0x04400000 and sa1 = M1, for pds=landp sa1 = Q0, for
pds=crumb3 (the B rows) post = pre; post pa = X's with pa1 = M13. Command 6: the after-read =
post and M6 with the run id in slot 6. bif(index, n, world): the K5 words as predicted: a land
image's job 2 faults at its predicted page from its pre on. gate(world, arm): the fill faults at
the page of the post sa13 with its devcoredump, unless the world draws it (gateok) or the arm is
crumb3's (the B rows: predicted exact).
EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  ownstop2   every job after job 1 not done: a two-job stage the planned stop (rc 4, the driver
             stops 4)
  model      every command job served: the land stage ends ok and its gate faults (rc 16, no
             on_gate_fail: the driver stops 16); the B rows' gate exact (0)
  gatebad    the B rows: the gate's fill faults (rc 16, on_gate_fail score: the driver ends 0)
  bifjob2    the model run with a fault after job 1 in every later job's K5 words (printed only)
  regbad     the register health fails at the first stage: recovery draws, rc 16
  fill2bad   N1, N2, N3: the begin draws `fill,fill`: the second fill fails: recovery draws, rc 16
  ownarmbad  the arm fails (rc 26)"""
import json
import os

STEP = "N2"
V = (0x32004000, 0x32005000, 0x32002000, 0x00000000)
M1, X0, M4, S1, M6 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304, 0x5A5A3306
MK13, MK1, EVT4, Q0, L4 = 0x005D3000, 0x005D1000, 0x04000010, 0x005D2000, 0x04400000
SLOT1, SLOT_PA, SLOT_SA, SLOT4, SLOT5, SLOT6 = 0x44, 0x48, 0x4C, 0x50, 0x54, 0x58
X_PA = [0x3, MK13, 0x32411000, 0x01555620, 0x32004000, 0, 0x32002000, 0x03C3CDAC, 0x32004000,
        0xDC531A54, 0x32002000, 0x5D50716F, 0x32004000, 0x82E151B5, 0x32002000, 0x11B5D77A]
X_LOW = [0x32004000, 0x04000010, 0x32002000, 0x3F800000, 0x3F400000, 0xBEC00000, 0, 0x3F800000,
         0xBEC00000, 0x3F400000, 0, 0]          # X's post sa0-sa11 (E1174)
X_HIGH = [0x32004000, 0x9ECC832E, 0x32002000, 0x4D21D720]   # X's post sa28-sa31
STAGES = {"B5": ("b5",), "B6": ("b6",), "N1": ("wa", "zff2", "wb", "lff2"), "N2": ("wc", "lff3"),
          "N3": ("wd", "lf3f"), "N4": ("we", "q2"), "N5": ("wf", "r"), "N6": ("wg", "p"),
          "N7": ("wh", "r2"), "N8": ("wi", "p2")}[STEP]
OK = {k: 0 for k in STAGES}
FIRST, LAST = STAGES[0], STAGES[-1]
if STEP in ("B5", "B6"):
    # no register health in a B row (the default begin and end draws), so no regbad world
    EXPECT = {"model": (0, OK), "ownstop2": (4, {FIRST: 4}), "gatebad": (0, {FIRST: 16}),
              "ownarmbad": (26, {FIRST: 26})}
else:
    EXPECT = {"ownstop2": (4, dict(OK, **{LAST: 4})), "model": (16, dict(OK, **{LAST: 16})),
              "bifjob2": (16, dict(OK, **{LAST: 16})),
              "regbad": (16, {FIRST: 16}), "ownarmbad": (26, {FIRST: 26})}
    if STEP in ("N1", "N2", "N3"):
        # the first stage with begin draws `fill,fill` (or fill,fill,fill) fails its second fill
        bad = STAGES[1]
        EXPECT["fill2bad"] = (16, dict({k: 0 for k in STAGES[:STAGES.index(bad)]}, **{bad: 16}))
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
    if "pds=crumb3" in arm:
        return _pre()                   # the B rows: post = pre (B-HID)
    low = list(X_LOW)
    if "pds=mark" in arm or "pds=land " in arm or arm.endswith("pds=land"):
        low[1] = MK1                    # W-SA1, LFF-KEEP
    if "pds=crumbz" in arm:
        low[0], low[1] = 2, MK1         # ZFF2-KEEP's sa0, sa1
    if "pds=landq" in arm:
        low[0], low[1] = Q0, MK1        # landq's Q0 to attribute 0, M1 to attribute 1
    if "pds=landr" in arm:
        low[0], low[1] = L4, MK1        # landr's L4 to attribute 0, M1 to attribute 1
    if "pds=landp" in arm:
        low[1] = Q0                     # landp's Q0 to attribute 1
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
    page = {"pds=landq": MK1, "pds=landr": MK1, "pds=landp": Q0, "pds=land ": 0}
    hit = next((v for k, v in page.items() if k in arm + " "), None)
    if hit is None:
        return None
    f = [FAULT_STAT, hit | 0xF]
    return {"pre": f, "post": list(f)}


def gate(world, arm):
    if "gateok" in world or ("pds=crumb3" in arm and "gatebad" not in world):
        return None
    page = _post(arm)[13] & ~0xFFF
    return {"fill": FILL_BAD, "post": DEVCD % (FAULT_STAT, page | 0xF)}


def answer(tool, argv, world):
    """The health draws, exact, except in world fill2bad a fill right after a fill (K8)."""
    if argv not in (["fill"], ["tri"]):
        return None
    f = _fake("lastdraw")
    last = open(f).read() if os.path.exists(f) else ""
    open(f, "w").write(argv[0])
    if argv == ["fill"] and last == "fill" and "fill2bad" in world:
        open(f, "w").write("failed")
        return {"out": "FAIL fill\n", "rc": 1}
    return {"out": "diff: 0 of %d pixels\n" % (2048 if argv == ["fill"] else 4096)}
