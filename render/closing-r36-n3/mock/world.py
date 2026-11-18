# SPDX-License-Identifier: MIT
"""mock/world.py: r36-n3's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (a refusal) or
dict(rc, out, err). own_res(cmd, params, world) is the fake own task's stores for the kit's fake
fwtask_run.py ({dword: value}): emitsa's entry 0 (slot 1) and entry 1 (slots 2-4), the run id
from the task's own count of commands since the arm (FAKE_DIR/n3.runs: the run id is the row's
place in the stage, kit/session.py prepare). V0-V3: TA3DCtl dwords 0-3 as r35-sa's snap0 (E1144),
the hooks' fallback (the fake regs has no ta3dctl lines).
EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     H-PA: pa0 = V0, pa2 = V2 (every row decided)
  sa        H-SA: pa0, pa2 = 0 (not V0, V2), sa unchanged
  sabad     sa0 is not V0 from the first job: hooks stop own (rc 24), on_stop end ends the run
  nomark4   entry 1's marker absent but the job done: hooks stop own (rc 24)
  ownstop   entry 1 never sets state 2 (the runner's stop: no done, rc 1): unexplained failure,
            rc 4, the session ends (H-NONE's own end)
  owngatebad  the gate after a job fails (rc 16); ownarmbad the arm fails (rc 26)
  postbad   post's triangle drew (the health pair passes) without `job: ok`: hooks stop post
            (rc 24, the last stage: the driver ends 0)"""
import os

EXPECT = {"model": (0, {"own": 0, "post": 0}), "sa": (0, {"own": 0, "post": 0}),
          "sabad": (24, {"own": 24}), "nomark4": (24, {"own": 24}), "ownstop": (4, {"own": 4}),
          "owngatebad": (16, {"own": 16}), "ownarmbad": (26, {"own": 26}),
          "postbad": (0, {"own": 0, "post": 24})}
V = (0x32004000, 0x32005000, 0x32002000, 0x00000000)
M1, M4 = 0x5A5A3301, 0x5A5A3302
SLOT1, SLOT_PA, SLOT_SA, SLOT4 = 0x44, 0x48, 0x4C, 0x50
# t30's texts for the health pair's argv (the shape of E1134's kept begin.health1/fill1)
TRI = ("tri: render context for targets up to 64x64\njob: ok\n"
       "target: 64x64 hash 0x99385a04ee01c585\ndiff: 0 of 4096 pixels\noutside: 0 dwords\n"
       "tri: 1 renders ok\n")
FILL = ("programs asm\njob: ok\njob time: 470 us\ntarget: 64x32 hash 0xb60c6095080bd325\n"
        "diff: 0 of 2048 pixels\noutside: 0 dwords\n"
        "fill: ok, 64x32 at (0, 0), stride 256, colour 0xff336699\n")


def runid():
    p = os.path.join(os.environ.get("FAKE_DIR", "."), "n3.runs")
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
    pa = [0x00000000, 0x00000007, 0x00000000, 0x00000000]
    if "sa" not in world:
        pa[0], pa[2] = V[0], V[2]
    sa = list(V)
    if "sabad" in world:
        sa[0] = 0x12345678
    out.update({SLOT_PA + i: x for i, x in enumerate(pa)})
    out.update({SLOT_SA + i: x for i, x in enumerate(sa)})
    if "nomark4" not in world:
        out.update({SLOT4: M4, SLOT4 + 1: r})
    return out


def answer(tool, argv, world):
    if tool != "t30":
        return None
    if argv == ["tri"]:
        return dict(out=TRI.replace("job: ok\n", "") if "postbad" in world else TRI)
    if argv == ["fill"]:
        return dict(out=FILL)
    return None
