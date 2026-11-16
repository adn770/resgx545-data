# SPDX-License-Identifier: MIT
"""mock/world.py: r29-flag's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv, the world's tokens and the fake laptop's state (the debugfs knobs the
runner wrote, its reset count, and this world's own state files in FAKE_DIR), never a case name;
it returns None (the health pair) or dict(rc, out, err, files, kmsg, latch). As strict as the
tools: an option a command does not take, a missing argument or a program file that is not there
is refused (usage, rc 2).

- t14 `tri -n 2 ...` (r14-bif's rf-c-depth: the depth buffer at 0x3e001000, its kept store) and
  `probe --temps 32 --coords --pixels --scratch-pages N PROG` (the scratch at 0x3e003000, E1047's
  kept image); f1 reads the knobs the runner wrote (vm_pte_addr, vm_pte_flags 0x12).
- t10 `tri --tri-full ... --dump-render DIR` (E1048's form at 256 x 256 and 512 x 512: the TA
  data bytes are the kernel's layout, 24576 and 32768; a CR_TE_MTILE1/2 poke faults 0x90004), the
  E737 bit-24 index row (`probe --tri pixel --vertices 15 ... --vdm 2^=0x01000000`) and E700's
  stream (`probe --tri pixel ... --obj2 6 ...`), whose hangs follow E700's counter M1 and the
  world's block-2 v = 1 decider, kept in FAKE_DIR (a reset since the last job clears both).
- t22 `copy --every-value --pixels --poke tex:/xfer:...`: the colour-space set, kept in FAKE_DIR:
  a copy whose xfer:17 bit 0 is set loads its words; without it the set is the last loaded one.

r29-flag2: the stages are s0 (the four copies), h1 and h2 (r29-flag's); the tri and t14 paths
stay for r29-flag's rows and are not reached.

Worlds (EXPECT: the driver's status and each stage's runner status; a stage whose gate closed
is skipped, so absent):
  model      every frozen hypothesis (h1 H-KEEP, h2 H-PREV16): h1 2, h2 2 hangs; 0 everywhere
  alt        the rivals (h1 H-RECOV-CLR: a recovery loads zeros, h2 D-PREVADD: no hang): 0
  always     h2 H-ALWAYS (the three block-2 v = 1 rows hang: #limit 3 used on the last row): 0
  s0diff     the BT.601 load does not hold (c10-bn reads black): h1's gate closes (skipped): 0
  s0fault    a copy loading zeros faults (no expectfault): s0 4, the session stops (4)
  s0noread   a copy without its target line (no hash reading): hook_check stops s0 (24) before
             the premise would (25); s0's on_stop = end ends the session
  recovline  an ok s0 copy's kernel slice holds `SGX recovery failed`: every flagged gate closes: 0
  recovfail  q010-h1 hangs and logs `SGX recovery failed: -110`: h1 24, the session ends (24)
  h1fault    q010-h1 faults instead of hanging: h1 24, the session ends (24)
  h2ctlhang  h2's control h2-c-b hangs (no expectfault): h2 4, the session (4)
  wedge      q010-h1's hang leaves the first health draw failing (the retry draws): strict health
             stops h1 (16), the session with it
"""
import gzip
import os
import re

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALL = ("s0", "h1", "h2")
EXPECT = {
    "model": (0, {s: 0 for s in ALL}),
    "alt": (0, {s: 0 for s in ALL}),
    "always": (0, {s: 0 for s in ALL}),
    "s0diff": (0, {"s0": 0, "h2": 0}),
    "s0fault": (4, {"s0": 4}),
    "s0noread": (24, {"s0": 24}),
    "recovline": (0, {"s0": 0}),
    "recovfail": (24, {"s0": 0, "h1": 24}),
    "h1fault": (24, {"s0": 0, "h1": 24}),
    "h2ctlhang": (4, {"s0": 0, "h1": 0, "h2": 4}),
    "wedge": (16, {"s0": 0, "h1": 16}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
R110 = "SGX recovery failed: -110"
PAGE = 4096
GREEN, BG = "ff00ff00", "ff203040"
TRI = {"--keep-going": 0, "--wait-ms": 1, "--width": 1, "--height": 1, "--max-width": 1,
       "--max-height": 1, "--tri-full": 0, "--tri-z": 1, "--depth": 0, "--depth-ctl": 1,
       "--depth-fill": 1, "--depth-pages": 1, "--depth-dump": 1, "--poke": 1, "--kpoke-render": 1,
       "--pixels": 0, "--dump-render": 1, "--depth-store": 0, "--depth-store-fill": 1}
PROBE_TRI = {"--tri": 1, "--vertices": 1, "--copy-depth": 0, "--pixels": 0, "--vdm": 1, "--temps": 1,
             "--width": 1, "--height": 1, "--obj2": 1, "--obj2-blk": 1, "--obj2-pixel": 1}
HASH256 = "0x66648495c9ea2325"                         # E1048's f2-ctl-256
TADATA = {(256, 256): 24576, (512, 512): 32768}         # the kernel's layout (gen/make.py)
COPYHASH = {"bt601": "0xb6067a95fa98de2d", "zeros": "0xd3522437a14b6325"}
BT601 = (0x00950095, 0x00000095, 0x010203CE, 0x039800CC, 0)
SPEC = re.compile(r"^(xfer|tex):(\d+)(\^?)=(0x[0-9a-fA-F]+|\d+)$")


def kept(name):
    with open(os.path.join(KP, "mock", "kept", name), "rb") as f:
        return gzip.decompress(f.read())


def state(name, default="0"):
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, name) if d else None
    return open(p).read().strip() if p and os.path.exists(p) else default


def put(name, value):
    d = os.environ.get("FAKE_DIR")
    if d:
        with open(os.path.join(d, name), "w") as f:
            f.write(str(value))


def knob(name):
    d = os.environ.get("FAKE_DBGREAL")
    p = os.path.join(d, name) if d else None
    return int(open(p).read().strip() or "0", 0) if p and os.path.exists(p) else 0


def resets():
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, "writes") if d else None
    return sum(1 for ln in open(p) if ln.startswith("reset")) if p and os.path.exists(p) else 0


def parse(argv, table, first=1, trailing=0):
    opts, i = {}, first
    end = len(argv) - trailing
    while i < end:
        a = argv[i]
        if a not in table or i + table[a] >= end + (0 if table[a] else 1):
            return None
        opts.setdefault(a, []).append(argv[i + 1] if table[a] else True)
        i += 1 + table[a]
    return opts


def fault(head, stat, addr, world, hung=False, extra=(), nobif=False):
    kmsg = ["sgxfive: job 12 hung, recovering"] if hung else \
        [f"sgxfive: BIF fault {stat:#x} at {addr:#010x} (PD 0x5736000) stalls job 7, recovering"]
    if nobif and not hung:
        kmsg = []
    kmsg += list(extra)
    if "alt" in world:                                   # H-RECOV-CLR: a recovery loads zeros
        put("r29f_csc", "zeros")
    what = "job hung, context lost (Connection timed out)" if hung else \
        "job faulted, context lost (Input/output error)"
    return dict(rc=3, out=head + f"failed: {what}\n", kmsg=kmsg,
                latch=None if hung else (stat & 0xFFFF or 0x1000, addr))


# ---- tri (t10, t14) ---------------------------------------------------------------------------
def tri(tool, argv, world):
    a = argv[1:]
    n = 1
    if a[:1] == ["-n"]:
        if tool != "t14" or len(a) < 2 or a[1] != "2":
            return USAGE
        n, a = 2, a[2:]
    o = parse(["tri"] + a, TRI)
    if o is None:
        return USAGE
    g = lambda k, d=None: o[k][0] if k in o else d  # noqa: E731
    w, h = int(g("--width", 64)), int(g("--height", 64))
    kp = o.get("--kpoke-render", [])
    for d in (g("--depth-dump"), g("--dump-render")):
        if d is not None and not os.path.isdir(d):
            return dict(rc=1, err=f"sgxfive-test: {d}: No such file or directory\n")
    out, files = [f"tri: render context for targets up to {w}x{h}"], {}
    addr = 0x3E001000
    depth = pages = None
    if "--depth" in o:
        pages = int(g("--depth-pages", (w * h * 4 + PAGE - 1) // PAGE + 16))
        depth = addr
        out.append(f"depth: {depth:#010x} {pages} pages, fill {g('--depth-fill')}, base 0x3e000000, "
                   f"control {g('--depth-ctl')}")
        addr += pages * PAGE
        if "--depth-store" in o:
            out.append(f"depth store: {addr:#010x} {pages} pages, fill {g('--depth-store-fill')}")
            addr += pages * PAGE
    head = "\n".join(out) + "\n"
    rf = "--depth-store" in o
    if rf and "s0fault" in world and not knob("vm_pte_flags"):
        return fault(head + "job: ", 0x90200, 0x3E011091, world)
    if rf and knob("vm_pte_addr") == depth and knob("vm_pte_flags") == 0x12 and "pass" not in world:   # f1
        extra = [R110] if "recovfail" in world else []
        return fault(head + "job: ", 0xA0200 if "alt" in world else 0x80200, depth | 0x1, world, extra=extra)
    if kp:                                                 # f2 (Q139): an empty-axis word
        m = re.fullmatch(r"1:ta:(143|144)=(0x[0-9a-f]+)", kp[0])
        if not m or (w, h) != (512, 512):
            return USAGE
        if "f2hang" in world and m.group(1) == "143":
            return fault(head + "job: ", 0, 0, world, hung=True)
        if "wedge" in world and m.group(1) == "143":
            put("r29f_wedge", 1)
        end = 0x20000000 + TADATA[(w, h)]
        page = (0x20008000 if m.group(1) == "143" else 0x20010000) if "alt" not in world else \
            end + (0x2000 if m.group(1) == "143" else 0xA000)
        return fault(head + "job: ", 0x90004, page | 0x21, world, nobif="nobifline" in world)
    lines = out[:]
    for k in range(1, n + 1):
        lines.append(f"tri: triangle (0,0) ({3 * w},0) (0,{3 * h}), depth 0.5 0.5 0.5")
        lines.append("job: ok")
        if depth is not None and "--depth-dump" in o:
            files[os.path.join(g("--depth-dump"), f"depth.{k}.bin")] = bytes(pages * PAGE)
            if rf:
                files[os.path.join(g("--depth-dump"), f"depth-store.{k}.bin")] = \
                    kept("rf-c-depth.depth-store.1.bin.gz")
        hsh = HASH256 if (w, h) == (256, 256) else "0x%016x" % (w * 0x9E3779B97F4A7C15 + h & (2 ** 64 - 1))
        lines += [f"target: {w}x{h} hash {hsh}", f"diff: 0 of {w * h} pixels", "outside: 0 dwords",
                  f"layout: fb {addr:#010x}"]
        if "--pixels" in o:
            lines += [f"row {y}: " + " ".join(["0x" + GREEN] * 4) for y in range(2)]
    if "--dump-render" in o:
        d = g("--dump-render")
        files[os.path.join(d, "tri.param.bin")] = bytes(64)
        files[os.path.join(d, "tri.tadata.bin")] = bytes(64)
        lines.append(f"probe tri: render memory to {d}/tri.{{param,tadata}}.bin (4603904, {TADATA[(w, h)]} bytes)")
    lines.append(f"tri: {n} renders ok")
    kmsg = [R110 + " (an earlier recovery)"] if "recovline" in world and rf else []
    return dict(rc=1 if rf else 0, out="\n".join(lines) + "\n", files=files, kmsg=kmsg)


# ---- probe (t14 texture, t10 index and stream rows) --------------------------------------------
def probe_tex(argv, world):
    if argv[:5] != ["probe", "--temps", "32", "--coords", "--pixels"] or len(argv) != 8 or \
            argv[5] != "--scratch-pages":
        return USAGE
    try:
        pages = int(argv[6])
    except ValueError:
        return USAGE
    if not 16 <= pages <= 256 or not os.path.exists(argv[7]):
        return USAGE
    prog = os.path.basename(argv[7])[:-4]
    head = "" if "s0noread" in world else f"probe {prog}: scratch at 0x3e003000 ({pages * 4} KiB)\n"
    if knob("vm_pte_addr") == 0x3E003000 and knob("vm_pte_flags") == 0x12 and "pass" not in world:
        return fault(head + f"probe {prog}: ", 0xA0002 if "alt" in world else 0x80002, 0x3E003001, world)
    rows = [ln for ln in kept("f1-ref-a.txt.gz").decode().splitlines() if ": row " in ln]
    return dict(out=head + "\n".join(rows) + "\n")


def e700_inputs(vdm):
    v = {1: 2, 9: 2}
    for s in vdm:
        m = re.fullmatch(r"(1|9)\^=(0x[0-9a-f]+)", s)
        if not m:
            return None
        v[int(m.group(1))] = (2 ^ (int(m.group(2), 16) >> 9)) & 7
    return v[1], v[9]


def probe_tri(argv, world):
    if not argv or not os.path.exists(argv[-1]):
        return USAGE
    o = parse(argv, PROBE_TRI, first=1, trailing=1)
    if o is None or o.get("--tri") != ["pixel"]:
        return USAGE
    if "--obj2-pixel" in o and not os.path.exists(o["--obj2-pixel"][0]):
        return USAGE
    prog = os.path.basename(argv[-1])[:-4]
    vdm = o.get("--vdm", [])
    head = f"probe {prog}: scratch at 0x3e00e000 (64 KiB)\n"
    if o.get("--vertices") == ["15"]:                       # h1: E737's bit 24 alone
        if vdm != ["2^=0x01000000"]:
            return USAGE
        if "h1fault" in world:
            return fault(head + f"probe {prog}: ", 0xD0008, 0x1, world)
        if "wedge" in world and state("r29g_wedged", "0") == "0":
            put("r29g_wedged", 1)
            put("r29f_wedge", 1)
        return fault(head + f"probe {prog}: ", 0, 0, world, hung=True,
                     extra=[R110] if "recovfail" in world else [])
    vv = e700_inputs(vdm)
    if vv is None or o.get("--obj2") != ["6"]:
        return USAGE
    v1, v2 = vv
    # E700's counter (M1) and the job before, since the last reset
    r = resets()
    last_r, c, p1, p2 = (int(x) for x in state("r29f_e700", "-1 0 0 0").split())
    if r != last_r:
        c, p1, p2 = 0, 0, 0                                  # 0 0: no job since the reset
    add = sum({0: 0, 1: -1}.get(v, v - 2) for v in (v1, v2))
    if v2 == 1 and v1 == 2:
        if "always" in world:
            hang = True
        elif "alt" in world:
            hang = False                                     # D-PREVADD (and D-C) on these rows
        else:
            hang = not ({1, 6} & {p1, p2})                   # H-PREV16
    elif "h2ctlhang" in world and c > 0:
        hang = True
    else:
        hang = c + add > 8
    if hang:
        put("r29f_e700", f"{r + 1} 0 0 0")                  # the runner resets after a hang
        return fault(head + f"probe {prog}: ", 0, 0, world, hung=True)
    put("r29f_e700", f"{r} {max(c + add, 0)} {v1} {v2}")
    return dict(out=head + f"probe {prog}: o0 mixed 0xff0000ff x1024 0x{BG} x3072\n")


# ---- copy (t22) -------------------------------------------------------------------------------
def copy(argv, world):
    o, i = {}, 1
    while i < len(argv):
        a = argv[i]
        if a in ("--every-value", "--pixels"):
            o.setdefault(a, True)
            i += 1
        elif a == "--poke" and i + 1 < len(argv) and SPEC.match(argv[i + 1]):
            o.setdefault("--poke", []).append(argv[i + 1])
            i += 2
        else:
            return USAGE
    if "--every-value" not in o:
        return USAGE
    w = {}
    for s in o.get("--poke", []):
        m = SPEC.match(s)
        w[(m[1], int(m[2]))] = (0 ^ int(m[4], 0)) if m[3] else int(m[4], 0)
    cur = state("r29f_csc", "zeros")
    if w.get(("xfer", 17), 0) & 1:
        words = tuple(w.get(("xfer", k), 0) for k in range(18, 23))
        if "s0fault" in world and not any(words):
            return fault("job: ", 0x80020, 0x3E002001, world)
        cur = "bt601" if words == BT601 else "zeros" if not any(words) else "other"
        put("r29f_csc", "zeros" if "s0diff" in world else cur)
    out = ["job: ok", "job time: 536 us", f"target: 64x32 hash {COPYHASH.get(cur, '0x0')}",
           "diff: 2048 of 2048 pixels, first (0, 0) 0xff000000 expected 0x000d6539", "outside: 0 dwords"]
    if "s0noread" in world:
        out.pop(2)
    kmsg = [R110 + " (an earlier recovery)"] if "recovline" in world else []
    return dict(rc=1, out="\n".join(out) + "\n", kmsg=kmsg)


def health(argv):
    if int(state("r29f_wedge", "0")) > 0:
        put("r29f_wedge", int(state("r29f_wedge")) - 1)
        return dict(rc=1, out="job: failed: job hung, context lost (Connection timed out)\n"
                    "diff: 4096 of 4096 pixels\n")
    return None


def answer(tool, argv, world):
    if argv in (["fill"], ["tri"]):
        return health(argv)
    if not argv:
        return USAGE
    if argv[0] == "tri" and tool in ("t10", "t14"):
        return tri(tool, argv, world)
    if argv[0] == "probe" and tool == "t14":
        return probe_tex(argv, world)
    if argv[0] == "probe" and tool == "t10" and "--tri" in argv:
        return probe_tri(argv, world)
    if argv[0] == "copy" and tool == "t22":
        return copy(argv, world)
    return USAGE
