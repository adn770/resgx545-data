# SPDX-License-Identifier: MIT
"""mock/world.py: r29-kreg's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (the health
pair, or a refusal) or dict(rc, out, err, files={path: bytes}, kmsg=[lines], latch=(int, word)).
EXPECT: {world: (the driver's status, {stage: the runner's status})}.

t10's `tri` as the session runs it (`--width W --height H [-n N]`, nothing else): per render
`job: ok`, `target:`, `diff: 0 of W*H pixels`, `outside:`, the count line and `tri WxH #i: T us`,
then `tri: N renders ok` (E396's output and r19-flag's kept health). A 256x256 render takes about
67400 us, the first about 73400 (E396). Worlds: model; nodiff (no diff line: s0's first control
stops on it, rc 24, on_stop end); slow (the 12th timed job, k1's third row, renders three times slower:
the hook's wedge rule stops k1, rc 24, on_stop end); kregstuck (the fake kernel takes the write
and keeps 0x2c: the first k1 row stops before its job, rc 19)."""
import os

EXPECT = {"model": (0, {"s0": 0, "k1": 0}), "nodiff": (24, {"s0": 24}),
          "slow": (24, {"s0": 0, "k1": 24}), "kregstuck": (19, {"s0": 0, "k1": 19})}
ALLOWED = {"--width", "--height", "-n"}


def opt(a, name, cast=str, default=None):
    return cast(a[a.index(name) + 1]) if name in a else default


def timed_call():
    """The count of 256x256 jobs so far, this one included (a file in the fake laptop's state)."""
    p = os.path.join(os.environ["FAKE_DIR"], "timed")
    n = int(open(p).read()) + 1 if os.path.exists(p) else 1
    with open(p, "w") as f:
        f.write(str(n))
    return n


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] != "tri" or len(argv) % 2 != 1 or \
            any(a not in ALLOWED for a in argv[1::2]):
        return None             # a refusal: usage, rc 2
    w, h, n = opt(argv, "--width", int, 64), opt(argv, "--height", int, 64), opt(argv, "-n", int, 1)
    k = timed_call() if (w, h) == (256, 256) else 0
    out = f"tri: render context for targets up to {w}x{h}\n"
    for i in range(1, n + 1):
        t = (73400 if i == 1 else 67400 + 37 * ((i * 7 + k * 13) % 9 - 4)) * w * h // 65536
        if "slow" in world and k == 12:
            t *= 3
        out += "job: ok\ntarget: %dx%d hash 0x99385a04ee01c585\n" % (w, h)
        if "nodiff" not in world:
            out += "diff: 0 of %d pixels\n" % (w * h)
        out += ("outside: 0 dwords\nlayout: fb 0x3e001000\n"
                f"tri {w}x{h} #{i}: 1062 triangle, 3034 background, 0 other; wrong 0 inside, "
                f"0 outside, 0 at edges; 612 if flipped; guard 0\ntri {w}x{h} #{i}: {t} us\n")
    out += f"tri: {n} renders ok\n"
    return dict(out=out)
