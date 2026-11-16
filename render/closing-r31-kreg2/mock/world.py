# SPDX-License-Identifier: MIT
"""mock/world.py: r31-kreg2's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (the health
pair, or a refusal) or dict(rc, out, err, files={path: bytes}, kmsg=[lines], latch=(int, word)).
EXPECT: {world: (the driver's status, {stage: the runner's status})}.

t10's `tri` as the session runs it (`--width W --height H [-n N]`, nothing else): per render
`job: ok`, `target:`, `diff: 0 of W*H pixels`, `outside:`, the count line and `tri WxH #i: T us`,
then `tri: N renders ok` (E396's and E1114's output). A 256x256 render about 67400 us, the first
about 73400 (E1114). t30's `probe --tri pixel --width 64 --height 64 --vertices 1500 F F F F F F`
(nothing else; t30 only): per file the scratch line, the tri line, `tri 64x64 #1: T us` and the
o0 line, as the library mock of t30 printed them (debug/, r31-kreg2's builder; T about 2000 us
here, made up: L2 was never timed on the laptop).

Worlds: model; nodiff (no diff line: s0's first control stops on it, rc 24, on_stop end); slow
(the 12th 256x256 job, k1's third row, renders three times slower: the hook's wedge rule stops
k1, rc 24, end); slowprobe (the 11th probe job, k2's third row, three times slower: k2 stops,
rc 24); probebad (the 11th probe job's sixth render fails and the tool ends rc 3: the runner's
unexplained-failure stop, rc 4); kregstuck (the fake kernel takes the write and keeps 0x2c: k1's first row stops before its job,
rc 19)."""
import os

EXPECT = {"model": (0, {"s0": 0, "k1": 0, "k2": 0}), "nodiff": (24, {"s0": 24}),
          "slow": (24, {"s0": 0, "k1": 24}), "slowprobe": (24, {"s0": 0, "k1": 0, "k2": 24}),
          "probebad": (4, {"s0": 0, "k1": 0, "k2": 4}),
          "kregstuck": (19, {"s0": 0, "k1": 19})}
TRI_ALLOWED = {"--width", "--height", "-n"}
PROBE_HEAD = ["probe", "--tri", "pixel", "--width", "64", "--height", "64", "--vertices", "1500"]


def opt(a, name, cast=str, default=None):
    return cast(a[a.index(name) + 1]) if name in a else default


def count(key):
    """The count of KEY's jobs so far, this one included (a file in the fake laptop's state)."""
    p = os.path.join(os.environ["FAKE_DIR"], key)
    n = int(open(p).read()) + 1 if os.path.exists(p) else 1
    with open(p, "w") as f:
        f.write(str(n))
    return n


def probe(argv, world):
    files = argv[len(PROBE_HEAD):]
    if argv[:len(PROBE_HEAD)] != PROBE_HEAD or len(files) != 6 or \
            any(not f.endswith("/bins/p1139-green.bin") or not os.path.isfile(f) for f in files):
        return None
    k = count("probe")
    out, rc = "programs asm\n", 0
    for i in range(1, 7):
        t = 2400 if i == 1 else 2000 + 7 * ((i * 5 + k * 11) % 9 - 4)
        if "slowprobe" in world and k == 11:
            t *= 3
        out += ("probe p1139-green: scratch at 0x3e00e000 (64 KiB)\n"
                "probe p1139-green: tri 64x64 (1500 vertices), pixel replaced\n")
        if "probebad" in world and k == 11 and i == 6:
            out += "probe p1139-green: failed: job timed out\n"
            rc = 3
            continue
        out += (f"tri 64x64 #1: {t} us\n"
                "probe p1139-green: o0 mixed 0xff203040 x2961 0xff00ff00 x1135\n")
    return dict(out=out, rc=rc)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world) if tool == "t30" else None
    if tool != "t10" or argv[0] != "tri" or len(argv) % 2 != 1 or \
            any(a not in TRI_ALLOWED for a in argv[1::2]):
        return None             # a refusal: usage, rc 2
    w, h, n = opt(argv, "--width", int, 64), opt(argv, "--height", int, 64), opt(argv, "-n", int, 1)
    k = count("timed") if (w, h) == (256, 256) else 0
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
