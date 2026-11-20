# SPDX-License-Identifier: MIT
"""mock/world.py: the argv-driven fake laptop of the r40-n3e-* sessions (N3e rows B0, L, B1-B11;
r40-d0-survey's, r40-s-*'s: emitsb14d and every emitsb_<form> store what emitsb stores; STEP below
says the row: in L the model world's post sa24 and sa26 hold land's markers, L-SA's shape). answer() sees the tool's
name, the argv and the world's tokens, never a case name; it returns None (a refusal) or dict(rc,
out, err). own_res(cmd, params, world) is the fake own task's stores for the kit's fake
fwtask_run.py ({dword: value}), the ones of a job that ends ok: the blob's entry 0 (slot 1: M1, the
run id, X0) and entry 1 (S1 in slot 5, pa0-pa3, sa0-sa3, M4 and the run id in slot 4), the run
id from the task's own count of commands since the arm (FAKE_DIR/n3c.runs: the row's place in
the stage, kit/session.py prepare). V0-V3: TA3DCtl dwords 0-3 as r35-sa's snap0 (E1144), the
hooks' fallback (the fake regs has no ta3dctl lines). The fake runner stores nothing for a job
that is not done, so the stop outcomes (NEVER, T1-T3, E1) are the scorer's
tests' (tests/attempt.py), not the mock's; the model world's ok end is the M, P and W tables'
DONE (K-DONE, Z-DONE).
EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     DONE: every store, the job done (SB, S2: the kick answered); own ends ok, post runs
  nox0      X0 absent but the job done: hooks stop own (rc 24), on_stop end ends the run
  nos1      S1 absent but the job done: hooks stop own (rc 24)
  nomark4   entry 1's marker absent but the job done: hooks stop own (rc 24)
  sabad     sa0 is not V0: hooks stop own (rc 24)
  ownstop   the job never reports done (the runner's stop, rc 1): unexplained failure, rc 4, the
            session ends (every stop outcome of the table)
  ownhang   the same with the tick frozen: the runner's "firmware hung" stop, rc 4
  owngatebad  the gate after the job fails (rc 16); ownarmbad the arm fails (rc 26)
  postbad   post's triangle drew (the health pair passes) without `job: ok`: hooks stop post
            (rc 24, the last stage: the driver ends 0)"""
import os

STEP = "B11"
MA, MB = 0x5A5A3A18, 0x5A5A3A1A

EXPECT = {"model": (0, {"own": 0, "post": 0}), "nox0": (24, {"own": 24}),
          "nos1": (24, {"own": 24}), "nomark4": (24, {"own": 24}), "sabad": (24, {"own": 24}),
          "ownstop": (4, {"own": 4}), "ownhang": (4, {"own": 4}),
          "owngatebad": (16, {"own": 16}), "ownarmbad": (26, {"own": 26}),
          "postbad": (0, {"own": 0, "post": 24})}
V = (0x32004000, 0x32005000, 0x32002000, 0x00000000)
M1, X0, M4, S1 = 0x5A5A3301, 0x5A5A3303, 0x5A5A3302, 0x5A5A3304
SLOT1, SLOT_PA, SLOT_SA, SLOT4, SLOT5 = 0x44, 0x48, 0x4C, 0x50, 0x54
# t30's texts for the health pair's argv (the shape of E1134's kept begin.health1/fill1)
TRI = ("tri: render context for targets up to 64x64\njob: ok\n"
       "target: 64x64 hash 0x99385a04ee01c585\ndiff: 0 of 4096 pixels\noutside: 0 dwords\n"
       "tri: 1 renders ok\n")
FILL = ("programs asm\njob: ok\njob time: 470 us\ntarget: 64x32 hash 0xb60c6095080bd325\n"
        "diff: 0 of 2048 pixels\noutside: 0 dwords\n"
        "fill: ok, 64x32 at (0, 0), stride 256, colour 0xff336699\n")


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
    if "nos1" not in world:
        out[SLOT5] = S1
    pa = [V[0], 0x00000007, V[2], 0x00000000]
    sa = list(V)
    if "sabad" in world:
        sa[0] = 0x12345678
    out.update({SLOT_PA + i: x for i, x in enumerate(pa)})
    out.update({SLOT_SA + i: x for i, x in enumerate(sa)})
    if "nomark4" not in world:
        out.update({SLOT4: M4, SLOT4 + 1: r})
    # D0's survey (emitsb14d): pre sa0-sa31 (dwords 128-159), post sa0-sa31 (160-191) the same,
    # post pa0-pa15 (192-207): the predicted D0-HID shape
    pre = list(V) + [0x5100 + k for k in range(4, 32)]
    out.update({128 + k: x for k, x in enumerate(pre)})
    post = list(pre)
    if STEP == "L":
        post[24], post[26] = MA, MB
    out.update({160 + k: x for k, x in enumerate(post)})
    out.update({192 + k: x for k, x in enumerate(pa + [0] * 12)})
    return out


def answer(tool, argv, world):
    if tool != "t30":
        return None
    if argv == ["tri"]:
        return dict(out=TRI.replace("job: ok\n", "") if "postbad" in world else TRI)
    if argv == ["fill"]:
        return dict(out=FILL)
    return None
