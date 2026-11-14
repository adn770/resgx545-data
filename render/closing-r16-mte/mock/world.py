# SPDX-License-Identifier: MIT
"""mock/world.py: r16-mte's argv-driven fake laptop for kit/session.py mock. answer(tool, argv,
world) sees the tool's name, the argv and the world's tokens, never a case name; it returns None
(the health pair) or dict(rc, out, err, files, kmsg, latch).

As strict as t10 (sgxfive-test at a581c06) on the options the rows use: `probe --tri pixel --temps
N --pixels --width W --height H [--tri-full] [--blk-add BIT=V[,V]] FILE` (FILE must exist). Any
other option, a missing value or a second FILE is a usage refusal (rc 2). `--blk-add` is parsed
as the tool parses it (sgxfive-test.c, strtoul base 0): BIT 2 to 5 takes exactly one word, 7
exactly two, comma-separated, each a whole number to 0xffffffff with nothing after it; anything
else is the tool's usage refusal. Stricter than the tool in three ways no row needs: a sign or a
blank before a number, a second --blk-add of one bit (the tool keeps the last), and any bit but 7
(this session adds only the clip) are refused too. Every row is also replayed on t10's library
mock by the kit first (built from the same source).

The image: gen/model.py's prediction under the world's truth (default H-TILECLIP + H-BG + H-EN; an
edge pixel of the default triangle drawn), printed as the tool prints a probe (o0, `row N:`).

Worlds (EXPECT: the driver's status, {stage: the runner's status}):
  model      the frozen truth: rclip 0
  flip       H-FLIP: 0 (the scorer's FAILED, not a stop)
  untouched  H-UNTOUCHED: 0
  always     H-ALWAYS: 0
  gatebad    H-EXCL: the gate row reads half its target: hook_check stops rclip at its first row
             (24) and on_stop = "end" ends the session (24)
  nopix      no row prints its pixels: hook_check stops rclip at the gate row (24; before the
             premise's 25 for the control's missing `pixels` reading), the session ends
  stray      a partial row prints a value none of the three: hook_check (24), the session ends
  short      a 256 x 256 row prints 255 rows: hook_check (24), the session ends
  clipfault  every row with --blk-add faults: the gate row's unexpected fault stops it (4)
  emptyhang  the last row (the empty clip) hangs: 4, 4
Tokens for the scorer's tests only (tests/test_score.py): excl, pixel, noclip, offdrop."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
sys.dont_write_bytecode = True
import model as M  # noqa: E402

EXPECT = {
    "model": (0, {"rclip": 0}),
    "flip": (0, {"rclip": 0}),
    "untouched": (0, {"rclip": 0}),
    "always": (0, {"rclip": 0}),
    "gatebad": (24, {"rclip": 24}),
    "nopix": (24, {"rclip": 24}),
    "stray": (24, {"rclip": 24}),
    "short": (24, {"rclip": 24}),
    "clipfault": (4, {"rclip": 4}),
    "emptyhang": (4, {"rclip": 4}),
}
USAGE = "usage: sgxfive-test [--mock[=rev1|harness|none]] ... (mock world: %s)\n"
PROBE_OPTS = {"--tri": 1, "--temps": 1, "--pixels": 0, "--width": 1, "--height": 1,
              "--tri-full": 0, "--blk-add": 1}
UINT32_MAX = 0xFFFFFFFF
FAULT_ADDR = 0x3E10000C


def usage(why):
    return dict(rc=2, err=USAGE % why)


def strtoul0(s):
    """C's strtoul(s, &end, 0) for an unsigned digit run (no blank, no sign: refused here):
    (value, rest), rest == s when no digit was read"""
    if s[:2] in ("0x", "0X") and len(s) > 2 and s[2] in "0123456789abcdefABCDEF":
        i = 2
        while i < len(s) and s[i] in "0123456789abcdefABCDEF":
            i += 1
        return int(s[2:i], 16), s[i:]
    if s[:1] == "0":
        i = 1
        while i < len(s) and s[i] in "01234567":
            i += 1
        return int(s[:i], 8), s[i:]
    i = 0
    while i < len(s) and s[i].isdigit() and s[i].isascii():
        i += 1
    return (int(s[:i]), s[i:]) if i else (None, s)


def blk_add(arg):
    """(bit, [words]) as t10 takes `--blk-add arg`, or None for its usage refusal"""
    bit, rest = strtoul0(arg)
    if bit is None or not rest.startswith("=") or not (2 <= bit <= 5 or bit == 7):
        return None
    want, words, p = (2 if bit == 7 else 1), [], rest[1:]
    for n in range(want):
        v, after = strtoul0(p)
        if v is None or v > UINT32_MAX:
            return None
        if n + 1 < want:
            if not after.startswith(","):
                return None
            p = after[1:]
        elif after:
            return None
        words.append(v)
    return bit, words


def parse(argv):
    """(opts {name: [values]}, positionals) or a usage dict"""
    opts, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if not a.startswith("--"):
            pos.append(a)
            i += 1
            continue
        if a not in PROBE_OPTS or i + PROBE_OPTS[a] >= len(argv):
            return usage("probe: %s is an option t10 does not take here, or its value is missing" % a)
        if PROBE_OPTS[a] == 0 and a in opts:
            return usage("probe: %s twice" % a)
        opts.setdefault(a, []).append(argv[i + 1] if PROBE_OPTS[a] else True)
        i += 1 + PROBE_OPTS[a]
    return opts, pos


def truth(world):
    form = ("H-EXCL" if "excl" in world or "gatebad" in world else "H-FLIP" if "flip" in world else
            "H-PIXEL" if "pixel" in world else "H-NOCLIP" if "noclip" in world else "H-TILECLIP")
    return (form, "H-UNTOUCHED" if "untouched" in world else "H-BG",
            "H-ALWAYS" if "always" in world else "H-OFFDROP" if "offdrop" in world else "H-EN")


def fault(head, hung=False):
    if hung:
        return dict(rc=3, out=head + "failed: job hung, context lost (Connection timed out)\n",
                    kmsg=["sgxfive: job 12 hung, recovering"], latch=None)
    return dict(rc=3, out=head + "failed: job faulted, context lost (Input/output error)\n",
                kmsg=["sgxfive: BIF fault 0x90020 at %#010x (PD 0x5736000) stalls job 7, recovering"
                      % FAULT_ADDR], latch=(0x0020, FAULT_ADDR))


def probe(argv, world):
    p = parse(argv)
    if isinstance(p, dict):
        return p
    o, pos = p
    for k in ("--tri", "--temps", "--width", "--height"):
        if len(o.get(k, [])) != 1:
            return usage("probe: %s once" % k)
    if o["--tri"] != ["pixel"] or "--pixels" not in o or len(pos) != 1:
        return usage("probe --tri pixel --pixels FILE")
    try:
        w, h, temps = int(o["--width"][0]), int(o["--height"][0]), int(o["--temps"][0])
    except ValueError:
        return usage("probe: --width, --height, --temps take numbers")
    if not (1 <= w <= 4096 and 1 <= h <= 4096 and 1 <= temps <= 128):
        return usage("probe: a size or temps out of range")
    clip, bits = None, set()
    for a in o.get("--blk-add", []):
        b = blk_add(a)
        if b is None:
            return usage("probe: bad option --blk-add %s (bits 2-5 one word, 7 two)" % a)
        if b[0] != 7 or b[0] in bits:
            return usage("probe: --blk-add %s: only bit 7, once, in this session" % a)
        bits.add(b[0])
        clip = tuple(b[1])
    if not os.path.isfile(pos[0]):
        return dict(rc=1, out="sgxfive-test: cannot open %s: No such file or directory\n" % pos[0])
    name = os.path.splitext(os.path.basename(pos[0]))[0]
    head = "programs asm\nprobe %s: scratch at 0x3e01a000 (64 KiB)\n" % name
    head += "probe %s: tri %dx%d%s, pixel replaced\n" % (name, w, h, " (blk-add 0x80)" if clip else "")
    if "--tri-full" in o:
        head += "probe %s: triangle (0,0) (%d,0) (0,%d)\n" % (name, 3 * w, 3 * h)
    if clip and "clipfault" in world:
        return fault(head + "probe %s: " % name)
    r = dict(name="mock", set="heldout", w=w, h=h, full="--tri-full" in o, clip=clip, why="")
    if clip and not ("--tri-full" in o) and clip[1] == 0x00040007 and "emptyhang" in world:
        return fault(head + "probe %s: " % name, hung=True)
    pred = M.predict(r, truth(world))
    val = {"G": M.GREEN, "g": M.GREEN, "B": M.BG, "S": M.SENTINEL}
    px = [val[c] for c in pred]
    if "stray" in world and clip and "B" in pred and "G" in pred:
        px[pred.index("B")] = 0x12345678
    counts = {}
    for v in px:
        counts[v] = counts.get(v, 0) + 1
    if len(counts) == 1:
        out = head + "probe %s: o0 0x%08x (%d of %d)\n" % (name, px[0], w * h, w * h)
    else:
        top = sorted(counts.items(), key=lambda kv: -kv[1])
        out = head + "probe %s: o0 mixed" % name + "".join(" 0x%08x x%d" % kv for kv in top) + "\n"
    nrows = h - 1 if "short" in world and w == 256 and clip else h
    if "nopix" not in world:
        out += "".join("probe %s: row %d: %s\n" % (name, y, " ".join("%08x" % v for v in px[y * w:(y + 1) * w]))
                       for y in range(nrows))
    return dict(rc=0, out=out)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if tool != "t10":
        return usage("tool %s" % tool)
    if argv[0] == "probe":
        return probe(argv, world)
    return usage(argv[0])
