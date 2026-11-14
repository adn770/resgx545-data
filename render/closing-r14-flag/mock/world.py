# SPDX-License-Identifier: MIT
"""mock/world.py: r14-flag's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name; it returns None (the health
pair) or dict(rc, out, err, files, kmsg, latch).

- f1 (t14, `probe --temps 32 --coords --pixels --scratch-pages 256 PROG`): t14 takes 16 to 256
  scratch pages (257 is a usage refusal); the program is named by its file (the generator's
  program of that name); an ok job prints the scratch line (1024 KiB) and the 32 rows of an image
  (the control's frozen image; a bit-14 row's H-TWP4096 image, or H-MOVE0's on f1-zero in the alt
  world); a fault prints the tool's `failed: job faulted` line, the kernel's `BIF fault S at A`
  line and latches the fault (the next reset clears it).
- f2 (t10, `tri --tri-full --pixels --width W --height H --max-width W --max-height H
  [--kpoke-render 1:ta:143=V] --wait-ms 20000 --keep-going --dump-render DIR`): r10-geo's fake
  (E1007's form): H-EVEN's surviving headers (gen/q139even.py) in a TA data dump at the header
  base of the kept baseline of the size (E1007's 0x4000 at 256 x 256, E959's 0x7000 at 768 x 640),
  the one flag bit 7 header on H-LASTBLOCK's slot (H-HIGHSLOT's in the alt world), a target tile
  drawn iff its header lies at or before the flag; DIR must exist.
Health pair (bare `fill`, `tri`): an exact draw, unless a wedged recovery left failing draws.

Worlds (EXPECT: the driver's status and each stage's runner status):
  model      f1 H-TWP4096 images (no fault), f2 H-COVER with H-EVEN and H-LASTBLOCK: 0, 0
  alt        f1-zero H-MOVE0's image, f2's flag H-HIGHSLOT: 0, 0
  faultany   every bit-14 row faults (BIF 0x90002 at scratch + 0x40000), every poked f2 row
             faults: each stage's #limit is used up on its last row: 0, 0
  unplanned  f1-ref-a faults (no expectfault): the runner stops (4) and the session with it
  ctlnopix   f1-ref-a prints no pixel rows: hook_check stops f1 (24), on_stop = end: driver 24
  f1hang     f1-tw32 hangs instead of faulting: hook_fault stops f1 (24), the session ends (24)
  recovfail  f1-tw32 faults and logs `SGX recovery failed: -110`: f1 24, the session ends (24)
  nobifline  f1-tw32 faults without the kernel's BIF line: f1 24, the session ends (24)
  ctl2fault  f2's first control faults (no expectfault): f2 4, the session 4
  f2hang     every poked f2 row hangs: hook_fault stops f2 (24) at the first; driver 0 (last stage)
  nohash     a poked f2 row draws without its target hash: hook_check stops f2 (24)
  nodump     a poked f2 row draws without its dump: hook_check stops f2 (24)
  wedge      as recovfail, and the first health draw after it fails (the retry draws): strict
             health stops the session (16)
"""
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import q139even as E  # noqa: E402
import q139model as Q  # noqa: E402

EXPECT = {
    "model": (0, {"f1": 0, "f2": 0}),
    "alt": (0, {"f1": 0, "f2": 0}),
    "faultany": (0, {"f1": 0, "f2": 0}),
    "unplanned": (4, {"f1": 4}),
    "ctlnopix": (24, {"f1": 24}),
    "f1hang": (24, {"f1": 24}),
    "recovfail": (24, {"f1": 24}),
    "nobifline": (24, {"f1": 24}),
    "ctl2fault": (4, {"f1": 0, "f2": 4}),
    "f2hang": (0, {"f1": 0, "f2": 24}),
    "nohash": (0, {"f1": 0, "f2": 24}),
    "nodump": (0, {"f1": 0, "f2": 24}),
    "wedge": (16, {"f1": 16}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
SCRATCH = 0x3E003000
R110 = "SGX recovery failed: -110"
GREEN, SENT = 0xFF00FF00, 0xDEADBEEF
T10_TRI = {"--tri-full": 0, "--pixels": 0, "--keep-going": 0, "--wait-ms": 1, "--width": 1,
           "--height": 1, "--max-width": 1, "--max-height": 1, "--kpoke-render": 1,
           "--dump-render": 1}


def state(name, default="0"):
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, name) if d else None
    return open(p).read().strip() if p and os.path.exists(p) else default


def put(name, value):
    d = os.environ.get("FAKE_DIR")
    if d:
        with open(os.path.join(d, name), "w") as f:
            f.write(str(value))


def frozen(name, model):
    return open(os.path.join(KP, "predictions/f1", f"{name}.{model}.txt")).read().split()


def fault(head, stat, addr, world, hung=False):
    kmsg = [f"sgxfive: job 12 hung, recovering"] if hung else \
        [f"sgxfive: BIF fault {stat} at {addr:#010x} (PD 0x5736000) stalls job 7, recovering"]
    if "nobifline" in world:
        kmsg = []
    if world & {"recovfail", "wedge"}:
        kmsg.append(R110)
    if "wedge" in world:
        put("r14f_wedge", 1)
    what = "job hung, context lost (Connection timed out)" if hung else \
        "job faulted, context lost (Input/output error)"
    return dict(rc=3, out=head + f"failed: {what}\n", kmsg=kmsg,
                latch=None if hung else (int(stat, 16) & 0xFFFF or 0x1000, addr))


# ---- f1: t14 probe ---------------------------------------------------------------------------
def f1(argv, world):
    if argv[:5] != ["probe", "--temps", "32", "--coords", "--pixels"] or len(argv) != 8 or \
            argv[5] != "--scratch-pages":
        return USAGE
    try:
        pages = int(argv[6])
    except ValueError:
        return USAGE
    if not 16 <= pages <= 256:
        return USAGE
    if not os.path.exists(argv[7]):
        return dict(rc=1, err=f"sgxfive-test: {argv[7]}: No such file or directory\n")
    prog = os.path.basename(argv[7])[:-4]
    head = f"probe {prog}: scratch at {SCRATCH:#010x} ({pages * 4} KiB)\n"
    if prog == "f1-ref-a" and "unplanned" in world:
        return fault(head + f"probe {prog}: ", "0x90002", SCRATCH + 0x21, set())
    ref = {"f1-ref-a": "H-E566", "f1-ref-b": "H-E561"}
    if prog in ref:
        if prog == "f1-ref-a" and "ctlnopix" in world:
            return dict(out=head)
        toks = frozen(prog, ref[prog])
    else:
        if prog == "f1-tw32" and "f1hang" in world:
            return fault(head + f"probe {prog}: ", "", 0, world, hung=True)
        if "faultany" in world or (prog == "f1-tw32" and world & {"recovfail", "nobifline", "wedge"}):
            return fault(head + f"probe {prog}: ", "0x90002", SCRATCH + 0x40000 + 0x1,
                         world if prog == "f1-tw32" else set())
        toks = frozen(prog, "H-MOVE0" if prog == "f1-zero" and "alt" in world else "H-TWP4096")
    rows = "".join(f"probe {prog}: row {y}: {' '.join(toks[y * 64:(y + 1) * 64])}\n" for y in range(32))
    return dict(out=head + rows + f"probe {prog}: scratch unchanged\n")


# ---- f2: t10 tri --tri-full ------------------------------------------------------------------
def parse(argv, table):
    opts, i = {}, 1
    while i < len(argv):
        a = argv[i]
        if a not in table or i + table[a] >= len(argv):
            return None
        opts.setdefault(a, []).append(argv[i + 1] if table[a] else True)
        i += 1 + table[a]
    return opts


def f2(argv, world):
    o = parse(argv, T10_TRI)
    if o is None or "--width" not in o or "--height" not in o or "--dump-render" not in o:
        return USAGE
    w, h = int(o["--width"][0]), int(o["--height"][0])
    pokes = o.get("--kpoke-render", [])
    if any(not p.startswith("1:ta:143=") for p in pokes):
        return USAGE
    d = o["--dump-render"][0]
    if not os.path.isdir(d):
        return dict(rc=1, err="sgxfive-test: %s: No such file or directory\n" % d)
    head = "tri: render context for targets up to %dx%d\n" % (w, h)
    if not pokes and "ctl2fault" in world and w == 256:
        return fault(head + "job: ", "0x90020", 0x3e10000c, set())
    if pokes and "faultany" in world:
        return fault(head + "job: ", "0x90020", 0x3e10000c, set())
    if pokes and "f2hang" in world:
        return fault(head + "job: ", "", 0, set(), hung=True)
    args = " ".join("--kpoke-render " + p for p in pokes)
    own = E.headers(w, h, args, "H-EVEN")
    tx, ty = -(-w // 32), -(-h // 16)
    n = E.geometry(w, h, args)[0]
    key = Q.KEYS["blkrow"]
    tgt = {sl: t for sl, t in own.items() if t[0] < tx and t[1] < ty}
    last = max(tgt) if "alt" in world else max(tgt, key=lambda sl: key(tgt[sl][1], tgt[sl][0], 0, 0, n))
    drawn = {t for sl, t in tgt.items() if sl <= last}
    base, top = (0x4000 if w * h < 640 * 480 else 0x7000), max(own) + 1   # E1007's, E959's bases
    td = bytearray(base + 12 * top + 0x1000)
    par = bytearray(0x2000 + 0x80 * top + 0x1000)
    for sl, (c, r) in own.items():
        stream = 0x2000 + 0x80 * sl
        flag = 0x80 if sl == last else 0
        struct.pack_into("<3I", td, base + 12 * sl, flag << 24 | (2 * c) << 16 | (2 * r), stream, 0)
        struct.pack_into("<3I", par, stream - 0x1000, 0x88000000 | sl, 0x00001000, 0xC0000000)
    g, b = "0x%08x" % GREEN, "0x%08x" % SENT
    rows, bad = [], 0
    for y in range(h):
        px = [g if (x // 32, y // 16) in drawn else b for x in range(w)]
        bad += px.count(b)
        rows.append("row %d: %s" % (y, " ".join(px)))
    out = [head.rstrip("\n")]
    out += ["tri: kpoke before render 1: %s" % p.split(":", 1)[1] for p in pokes]
    out += ["job: ok"]
    if not ("nohash" in world and pokes):
        out.append("target: %dx%d hash 0x%016x" % (w, h, len(drawn) * 0x9E3779B97F4A7C15 & (2 ** 64 - 1)))
    out += ["diff: %d of %d pixels" % (bad, w * h), "outside: 0 dwords", "layout: fb 0x3e001000",
            "tri %dx%d #1: %d triangle, 0 background, %d other" % (w, h, w * h - bad, bad)] + rows
    files = {}
    if not ("nodump" in world and pokes):
        files = {os.path.join(d, "tri.param.bin"): bytes(par), os.path.join(d, "tri.tadata.bin"): bytes(td)}
        out.append("probe tri: render memory to %s/tri.{param,tadata}.bin (%d, %d bytes)" % (d, len(par), len(td)))
    out.append("tri: 0 of 1 renders ok" if bad else "tri: 1 renders ok")
    return dict(rc=1 if bad else 0, out="\n".join(out) + "\n", files=files)


def health(argv):
    if int(state("r14f_wedge", "0")) > 0:
        put("r14f_wedge", int(state("r14f_wedge")) - 1)
        return dict(rc=1, out="job: failed: job hung, context lost (Connection timed out)\n"
                    "diff: 4096 of 4096 pixels\n")
    return None


def answer(tool, argv, world):
    if argv in (["fill"], ["tri"]):
        return health(argv)
    if tool == "t14" and argv[:1] == ["probe"]:
        return f1(argv, world)
    if tool == "t10" and argv[:1] == ["tri"]:
        return f2(argv, world)
    return USAGE
