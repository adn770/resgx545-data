# SPDX-License-Identifier: MIT
"""mock/world.py: r25-csc's fake laptop for kit/session.py mock. answer() sees the tool's name, the
argv and the world's tokens; it returns None (the health pair) or dict(rc, out, err). Each call
is its own process, so the colour-space set a job finds is read from the probe's NAME (its FILE's
base name yF-S: the row's place after its half's copy, gen/make.py), never from a case table.

As strict as t22 (3c68e8d) on this session's rows: `probe` with --temps N, --coords, --pixels,
--poke xfer:N[^]=V, one FILE; `copy` with --every-value, --pixels, --poke tex:/xfer:. Anything
else is refused as the tool's usage error (rc 2). t22 echoes each applied poke after the job.

Pixels: black is 0xff000000 at 2048 pixels; conv is E037's conversion of texel x mod 16 of the
16 x 1 texture (pattern 0 of gen_p1132's yuv_words), format 28 as Y0 U Y1 V, 29 as U Y0 V Y1:
r23-pk's measured fills (E1097; tests/test_plan.py checks the sha256 against the kept files).

EXPECT: {world: (the driver's status, {stage: the runner's status})}:
  model     H-FILLLOAD: a poked fill loads its words, an unpoked one keeps the set: all run (0)
  ignore    H-FILLIGNORE: the fills read the last copy's set: all run (0)
  clears    the set is cleared between jobs (unpoked fills black, d's control FAILS): runs (0)
  copynoop  the zeros copy does not load (zc reads E037's BT.601 hash, FAILS): runs (0)
  noecho    a tool without the echo (t10 to t20): y28-b echoes 0 of 6: hook_check stops csc (24; driver 0, the only stage)
"""
import re

EXPECT = {"model": (0, {"csc": 0}),
          "ignore": (0, {"csc": 0}),
          "clears": (0, {"csc": 0}),
          "copynoop": (0, {"csc": 0}),
          "noecho": (0, {"csc": 24})}
E037 = {"csc": "0xb6067a95fa98de2d", "none": "0xd3522437a14b6325"}
BUILT = {("xfer", 17): 0x00000000}      # the words as the library builds them (E1097's echo)
SPEC = re.compile(r"^(xfer|tex):(\d+)(\^?)=(0x[0-9a-fA-F]+|\d+)$")
BT601 = (0x00950095, 0x00000095, 0x010203ce, 0x039800cc, 0)
ORDER = {28: (0, 2, 1, 3), 29: (1, 3, 0, 2)}


def usage(why):
    return dict(rc=2, err=f"sgxfive-test: {why}\nusage: sgxfive-test COMMAND ...\n")


def parse(argv, vals, flags):
    opts, files, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a in vals:
            if i + 1 >= len(argv):
                return None, f"{a} needs a value"
            opts.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a in flags:
            opts.setdefault(a, []).append(True)
            i += 1
        elif a.startswith("-"):
            return None, f"unknown option {a}"
        else:
            files.append(a)
            i += 1
    return (opts, files), None


def pokes(specs, spaces):
    lines = []
    for s in specs:
        m = SPEC.match(s)
        if not m or m[1] not in spaces:
            return None, f"--poke {s}"
        old = BUILT.get((m[1], int(m[2])), 0)
        v = int(m[4], 0)
        lines.append((m[1], int(m[2]), old, old ^ v if m[3] else v))
    return lines, None


def loads(pk):
    """'bt601', 'zeros' or None: the set a job's pokes load (xfer:17 bit 0 and xfer:18-22)."""
    w = {(s, i): new for s, i, _, new in pk}
    if not w.get(("xfer", 17), 0) & 1:
        return None
    words = tuple(w.get(("xfer", i), 0) for i in range(18, 23))
    return "bt601" if words == BT601 else "zeros" if not any(words) else "other"


def words():
    return [(0x20 + 0x18 * j) | (0x70 + 0x0B * j) << 8 | (0x40 + 0x1C * j) << 16 |
            (0x90 + 0x07 * j) << 24 for j in range(8)]


def conv(yy, u, v):
    def sat(t):
        return min(max(t, 0), 255)
    r = sat((149 * (yy - 16) + 204 * (v - 128)) >> 7)
    g = sat((149 * (yy - 16) - 50 * (u - 128) - 104 * (v - 128)) >> 7)
    b = sat((149 * (yy - 16) + 258 * (u - 128)) >> 7)
    return 0xFF000000 | r << 16 | g << 8 | b


def texels(fmt):
    o, w, out = ORDER[fmt], words(), []
    for x in range(16):
        b = [w[x // 2] >> (8 * k) & 255 for k in range(4)]
        out.append(conv(b[o[0] if x % 2 == 0 else o[1]], b[o[2]], b[o[3]]))
    return out


def pixel_rows(name, fmt, state):
    t = texels(fmt) if state == "conv" else [0xFF000000] * 16
    return [f"probe {name}: row {y}: " + " ".join(f"{t[x % 16]:08x}" for x in range(64))
            for y in range(32)]


def fill_state(suffix, load, world):
    """the set a fill reads in this world: 'conv' or 'black'."""
    half = "zeros" if suffix in ("a", "b", "c") else "bt601"       # the half's copy
    copied = "bt601" if "copynoop" in world and half == "zeros" else half
    if "ignore" in world:
        cur = copied
    elif "clears" in world:
        cur = load or "zeros"
    else:                                                           # model: H-FILLLOAD
        cur = load or {"a": copied, "b": "bt601", "c": "bt601", "d": copied,
                       "e": "zeros", "f": "zeros"}[suffix]
    return "conv" if cur == "bt601" else "black"


def probe(argv, world):
    p, why = parse(argv, {"--temps", "--poke"}, {"--coords", "--pixels"})
    if why:
        return usage(why)
    o, files = p
    if len(files) != 1:
        return usage("probe takes one FILE here")
    pk, why = pokes(o.get("--poke", []), ("xfer",))
    if why:
        return usage(why)
    name = files[0].rsplit("/", 1)[-1][:-len(".bin")]
    m = re.match(r"y(28|29)-([a-f])$", name)
    if not m:
        return usage(f"{name} is not this session's program")
    state = fill_state(m[2], loads(pk), world)
    out = [f"probe {name}: scratch at 0x3e003000 (64 KiB)"]
    if pk:
        out.append(f"probe {name}: pokes " + " ".join(o["--poke"]))
    if "noecho" not in world:
        out += [f"probe {name}: poked {s}:{i} 0x{a:08x} -> 0x{b:08x}" for s, i, a, b in pk]
    out.append(f"probe {name}: job time: 700 us")
    out.append(f"probe {name}: o0 0xff000000 (2048 of 2048)" if state == "black" else
               f"probe {name}: o0 mixed other x2048")
    if "--pixels" in o:
        out += pixel_rows(name, int(m[1]), state)
    return dict(rc=0, out="\n".join(out) + "\n")


def copy(argv, world):
    p, why = parse(argv, {"--poke"}, {"--every-value", "--pixels"})
    if why:
        return usage(why)
    o, files = p
    if files or "--every-value" not in o:
        return usage("copy here: --every-value")
    pk, why = pokes(o.get("--poke", []), ("xfer", "tex"))
    if why:
        return usage(why)
    ld = loads(pk)
    if "copynoop" in world and ld == "zeros":
        ld = "bt601"
    h = E037["csc"] if ld == "bt601" else E037["none"]
    out = ["job: ok", f"target: 64x32 hash {h}", "diff: 2048 of 2048 pixels, first (0, 0) "
           "0xff000000 expected 0xff102030"]
    return dict(rc=1, out="\n".join(out) + "\n")


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "probe":
        return probe(argv, world)
    if argv[0] == "copy":
        return copy(argv, world)
    return usage(f"{argv[0]} is not this session's")
