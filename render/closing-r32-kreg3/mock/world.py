# SPDX-License-Identifier: MIT
"""mock/world.py: r32-kreg3's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (the health
pair, or a refusal) or dict(rc, out, err, files={path: bytes}, kmsg=[lines], latch=(int, word)).
EXPECT: {world: (the driver's status, {stage: the runner's status})}.

t10's `tri` as the session runs it (`--width 64 --height 64`, nothing else; the health pair):
`job: ok`, `target:`, `diff: 0 of 4096 pixels`, the count line, `tri: 1 renders ok`. t30's
`probe --tri pixel --width W --height H --vertices 1500 F...` (W x H 64x64 or 1024x768, N files,
N 10, 20 or 40, F the staged bins/p1139-green.bin; nothing else; t30 only): per file the scratch
line, the tri line, `tri WxH #1: T us` and the o0 line, as t30's library mock printed them
(debug/probe). T made up: about 2000 us at 64x64 and 9000 us at 1024x768, each render a few us
apart; in a NOISY form every job's renders also move together by up to 5 percent (E1125's job to
job spread), so its eight references spread over the 0.8 percent pick bound.

Worlds: model (64x64 steady: s0 picks form 10, k10 runs, every other k gate shut); large (64x64
noisy, 1024x768 steady: s0 picks l10, kl10 runs); noisy (every form noisy: no pick, no flagged
stage runs, the driver ends 0 after s0); nodiff (c0-tri has no diff line: s0 stops, rc 24, end);
slowprobe (k10's third row, the 11th job of form 10, three times slower: the hook's wedge rule
stops k10, rc 24, end); probebad (the same job's last render fails and the tool ends rc 3: the
runner's unexplained-failure stop, rc 4); kregstuck (the fake kernel takes the write and keeps
0x2c: k10's first row stops before its job, rc 19)."""
import os

EXPECT = {"model": (0, {"s0": 0, "k10": 0}), "large": (0, {"s0": 0, "kl10": 0}),
          "noisy": (0, {"s0": 0}), "nodiff": (24, {"s0": 24}),
          "slowprobe": (24, {"s0": 0, "k10": 24}), "probebad": (4, {"s0": 0, "k10": 4}),
          "kregstuck": (19, {"s0": 0, "k10": 19})}
TARGETS = {(64, 64): (2000, "o0 mixed 0xff203040 x2961 0xff00ff00 x1135"),
           (1024, 768): (9000, "o0 mixed 0xff203040 x577967 0xff00ff00 x208465")}
PROG = "/bins/p1139-green.bin"


def opt(a, name, cast=str, default=None):
    return cast(a[a.index(name) + 1]) if name in a else default


def count(key):
    """The count of KEY's jobs so far, this one included (a file in the fake laptop's state)."""
    p = os.path.join(os.environ["FAKE_DIR"], key)
    n = int(open(p).read()) + 1 if os.path.exists(p) else 1
    with open(p, "w") as f:
        f.write(str(n))
    return n


def tokens(world):
    return set(world.split(",")) if isinstance(world, str) else set(world)


def probe(argv, world):
    head = argv[:9]
    if len(head) < 9 or head[:3] != ["probe", "--tri", "pixel"] or head[3] != "--width" or \
            head[5] != "--height" or head[7:9] != ["--vertices", "1500"]:
        return None
    try:
        w, h = int(head[4]), int(head[6])
    except ValueError:
        return None
    files = argv[9:]
    if (w, h) not in TARGETS or len(files) not in (10, 20, 40) or \
            any(not f.endswith(PROG) or not os.path.isfile(f) for f in files):
        return None
    tk = tokens(world)
    n = len(files)
    k = count(f"probe-{w}x{h}-{n}")
    base, o0 = TARGETS[(w, h)]
    noisy = "noisy" in tk or ("large" in tk and (w, h) == (64, 64))
    job = 1.0 + (0.025 * ((k * 7) % 5 - 2) if noisy else 0.0)
    out, rc = "programs asm\n", 0
    for i in range(1, n + 1):
        t = int((base * 1.2 if i == 1 else base + 7 * ((i * 5 + k * 11) % 9 - 4)) * job)
        if "slowprobe" in tk and (w, h, n) == (64, 64, 10) and k == 11:
            t *= 3
        out += ("probe p1139-green: scratch at 0x3e00e000 (64 KiB)\n"
                f"probe p1139-green: tri {w}x{h} (1500 vertices), pixel replaced\n")
        if "probebad" in tk and (w, h, n) == (64, 64, 10) and k == 11 and i == n:
            out += "probe p1139-green: failed: job timed out\n"
            rc = 3
            continue
        out += f"tri {w}x{h} #1: {t} us\nprobe p1139-green: {o0}\n"
    return dict(out=out, rc=rc)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world) if tool == "t30" else None
    if tool != "t10" or argv != ["tri", "--width", "64", "--height", "64"]:
        return None             # a refusal: usage, rc 2
    out = "tri: render context for targets up to 64x64\njob: ok\n"
    out += "target: 64x64 hash 0x99385a04ee01c585\n"
    if "nodiff" not in tokens(world):
        out += "diff: 0 of 4096 pixels\n"
    out += ("outside: 0 dwords\nlayout: fb 0x3e001000\ntri 64x64 #1: 1062 triangle, 3034 "
            "background, 0 other; wrong 0 inside, 0 outside, 0 at edges; 612 if flipped; guard 0\n"
            "tri: 1 renders ok\n")
    return dict(out=out)
