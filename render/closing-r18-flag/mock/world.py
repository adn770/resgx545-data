# SPDX-License-Identifier: MIT
"""mock/world.py: r18-flag's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv, the world's tokens and the fake laptop's state (the debugfs knobs the
runner wrote, its reset count), never a case name; it returns None (the health pair) or dict(rc,
out, err, files, kmsg, latch). As strict as the tools: an option a command does not take, a
missing argument or a program file that is not there is refused (usage, rc 2).

- t10/t14 `tri`: the library triangle, E1051's zv- form, r14-bif's rf-c-depth (t14 only: -n),
  E998's ramp, E1048's --tri-full --dump-render form. Buffers in the GENERAL heap's bump order
  (sgxfive-test.c and render.c at a581c06): the depth buffer at 0x3e001000 (pages from
  --depth-pages, else W x H dwords + 16), the depth store after it, then the colour buffer (W x H
  dwords and a guard page, whole pages). The s0 references answer with their kept dumps
  (mock/kept/) and kept hashes; a store past the depth buffer lands in the colour buffer while it
  is mapped and faults at the first unmapped page (H-PAST-FAULT) in the model world.
- t14 `probe --temps 32 --coords --pixels --scratch-pages N PROG` (16 to 256 pages): the scratch
  at 0x3e003000, E1047's kept image of f1-ref-a.
- t10 `probe --tri pixel ...`: E756's index rows (o0 line, the 32-bit echo) and the h2 streams,
  whose hangs follow a counter kept in the fake state (M1: c = 0 after a reset, + 4 a job with
  block 1 at v = 6, a hang iff c + 4 > 8).
- f2's rows read the knobs the runner wrote (vm_pte_addr, vm_pte_flags) from the fake debugfs.

Worlds (EXPECT: the driver's status and each stage's runner status; a stage whose gate closed
is skipped, so absent):
  model      every frozen hypothesis (f1 H-PAST-FAULT, f2 H-WO-ALL + H-EDM-READ, f3 H-KIND, f4
             H-FAULT-ANY, h1 H-B24-HANG, h2 M1-SHAPE): 0 everywhere
  alt        the rivals (f1 H-PAST-ANY, f2 H-EDM-ZLS + H-EDM-TEX, f3 H-ONE-KIND, f4 H-NEEDS-BUF,
             h1 H-B24-W32, h2 H-SCALE): 0 everywhere
  faultmax   every expectfault row of f1 to f4 faults and h1 hangs (h2 as M1: a hang after a
             hang is not reachable without a reset): each fault #limit used up on its last row: 0
  s0diff     x-ctl's hash differs: s0 0, f4's gate closed (skipped), the rest run: 0
  s0fault    zv-c-g3 faults (no expectfault): s0 4, the session stops (4)
  s0noread   ix32-n's o0 line has no background pixel (no bg reading): the premise stops s0
             (25), the session with it
  recovline  an ok s0 row's kernel slice holds `SGX recovery failed`: every flagged gate closes: 0
  recovfail  q299-g5 faults and logs `SGX recovery failed: -110`: f1 24, the session ends (24)
  f2hang     q108-edm-load hangs: hook_fault stops f2 (24), the session ends (24)
  nobifline  f3-k4 faults without the kernel's BIF line: f3 24, the session ends (24)
  h1fault    b24-w32 faults instead of hanging: h1 24, the session ends (24)
  h2ctlhang  E413's alternation: h2's control (second row) hangs, no expectfault: h2 4, session 4
  wedge      b18-lib's fault leaves the first health draw failing (the retry draws): strict
             health stops f4 (16), the session with it
"""
import gzip
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECT = {
    "model": (0, {s: 0 for s in ("s0", "f1", "f2", "f3", "f4", "h1", "h2")}),
    "alt": (0, {s: 0 for s in ("s0", "f1", "f2", "f3", "f4", "h1", "h2")}),
    "faultmax": (0, {s: 0 for s in ("s0", "f1", "f2", "f3", "f4", "h1", "h2")}),
    "s0diff": (0, {s: 0 for s in ("s0", "f1", "f2", "f3", "h1", "h2")}),
    "s0fault": (4, {"s0": 4}),
    "s0noread": (25, {"s0": 25}),
    "recovline": (0, {"s0": 0}),
    "recovfail": (24, {"s0": 0, "f1": 24}),
    "f2hang": (24, {"s0": 0, "f1": 0, "f2": 24}),
    "nobifline": (24, {"s0": 0, "f1": 0, "f2": 0, "f3": 24}),
    "h1fault": (24, {"s0": 0, "f1": 0, "f2": 0, "f3": 0, "f4": 0, "h1": 24}),
    "h2ctlhang": (4, {"s0": 0, "f1": 0, "f2": 0, "f3": 0, "f4": 0, "h1": 0, "h2": 4}),
    "wedge": (16, {"s0": 0, "f1": 0, "f2": 0, "f3": 0, "f4": 16}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
R110 = "SGX recovery failed: -110"
PAGE = 4096
GREEN, BG = "ff00ff00", "ff203040"
TRI = {"--keep-going": 0, "--wait-ms": 1, "--width": 1, "--height": 1, "--max-width": 1,
       "--max-height": 1, "--tri-full": 0, "--tri-z": 1, "--tri-v": 1, "--depth": 0,
       "--depth-ctl": 1, "--depth-fill": 1, "--depth-pages": 1, "--depth-dump": 1, "--poke": 1,
       "--kpoke-render": 1, "--pixels": 0, "--dump-render": 1, "--depth-store": 0,
       "--depth-store-fill": 1}
PROBE_TRI = {"--tri": 1, "--vertices": 1, "--copy-depth": 0, "--dump-render": 1, "--pixels": 0,
             "--index-width": 1, "--vdm": 1, "--temps": 1, "--width": 1, "--height": 1,
             "--obj2": 1, "--obj2-blk": 1, "--obj2-pixel": 1}
HASH = {"f2-ctl-256": "0x66648495c9ea2325", "x-ctl": "0xafb12e5a2a9a6725"}


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
    what = "job hung, context lost (Connection timed out)" if hung else \
        "job faulted, context lost (Input/output error)"
    return dict(rc=3, out=head + f"failed: {what}\n", kmsg=kmsg,
                latch=None if hung else (stat & 0xFFFF or 0x1000, addr))


# ---- tri ------------------------------------------------------------------------------------
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
    pokes = o.get("--poke", [])
    kp = o.get("--kpoke-render", [])
    for d in (g("--depth-dump"), g("--dump-render")):
        if d is not None and not os.path.isdir(d):
            return dict(rc=1, err=f"sgxfive-test: {d}: No such file or directory\n")
    out, files, kmsg = [f"tri: render context for targets up to {w}x{h}"], {}, []
    addr = 0x3E001000
    depth = pages = None
    ctl = g("--depth-ctl")
    if "--depth" in o:
        pages = int(g("--depth-pages", (w * h * 4 + PAGE - 1) // PAGE + 16))
        if pages < (w * h * 4 + PAGE - 1) // PAGE:
            return USAGE
        depth = addr
        out.append(f"depth: {depth:#010x} {pages} pages, fill {g('--depth-fill')}, base 0x3e000000, control {ctl}")
        addr += pages * PAGE
        if "--depth-store" in o:
            out.append(f"depth store: {addr:#010x} {pages} pages, fill {g('--depth-store-fill')}")
            addr += pages * PAGE
    fb, fbsize = addr, ((w * h * 4 + 2 * PAGE - 1) // PAGE) * PAGE
    head = "\n".join(out) + "\n"
    knob_flags, knob_addr = knob("vm_pte_flags"), knob("vm_pte_addr")
    # which job: by its argv
    zv = ctl in ("0x0017101c", "0x0017102c") and w == 64 and h == 64
    rf = "--depth-store" in o
    ramp = w == 80 and h == 40
    lib = not o or set(o) == {"--poke"}
    poked_ta = any(p.startswith("1:ta:143=") for p in kp)
    if zv and pages == 20 and "s0fault" in world:
        return fault(head + "job: ", 0x90200, 0x3e011000 | 0x91, world)
    if zv and pages == 16:                                 # f1 (Q299)
        store = (16, 18) if ctl == "0x0017101c" else (18, 21)
        if "alt" in world or "faultmax" in world:          # H-PAST-ANY: the first page past it
            return fault(head + "job: ", 0x90200, depth + store[0] * PAGE + 0x91, world)
        for p in store:                                    # H-PAST-FAULT: the first unmapped
            if not fb <= depth + p * PAGE < fb + fbsize:
                extra = [R110] if "recovfail" in world else []
                return fault(head + "job: ", 0x90200, depth + p * PAGE + 0x91, world, extra=extra)
    if rf and knob_addr == depth and knob_flags:            # f2 (Q108), the ZLS load
        if "f2hang" in world and knob_flags == 0x10:
            return fault(head + "job: ", 0, 0, world, hung=True)
        if knob_flags == 0x2 or "alt" in world or "faultmax" in world:
            return fault(head + "job: ", 0x80200 if knob_flags == 0x2 else 0xA0200, depth | 0x91, world)
    if poked_ta:                                           # f3 (Q139)
        v = int(kp[0].split("=")[1], 16)
        empty = (v >> 12) & 0xFF == 0
        nb = "nobifline" in world
        if empty and "alt" not in world:
            return fault(head + "job: ", 0x90004, 0x20006021, world, nobif=nb)
        return fault(head + "job: ", 0x90100, 0x10000012, world, nobif=nb)
    if lib and pokes == ["blk:1^=0x00040000"]:             # f4 (Q241 bit 18)
        if "wedge" in world:
            put("r18f_wedge", 1)
        return fault(head + "job: ", 0x91000, 0x3e002011, world)
    if ramp and pokes == ["blk:1=0x00440200"] and "alt" not in world:
        return fault(head + "job: ", 0x91000, 0x3e002011, world)
    # a job that completes
    lines = out[:]
    tri_line = f"tri: triangle (0,0) ({3 * w},0) (0,{3 * h}), depth 0.5 0.5 0.5"
    for k in range(1, n + 1):
        lines.append(tri_line)
        lines += [f"tri: kpoke before render {k}: {p.split(':', 1)[1]}" for p in kp]
        lines.append("job: ok")
        if depth is not None:
            if "--depth-dump" in o:
                if zv and pages == 20:
                    b = kept("zv-c-g3.depth.1.bin.gz")
                elif zv and pages == 24:
                    b = kept("zv-g5.depth.1.bin.gz")
                elif ramp:
                    b = kept("x-ctl.depth.1.bin.gz")
                else:
                    b = bytes(pages * PAGE)
                files[os.path.join(g("--depth-dump"), f"depth.{k}.bin")] = b
                if rf:
                    files[os.path.join(g("--depth-dump"), f"depth-store.{k}.bin")] = kept("rf-c-depth.depth-store.1.bin.gz")
            lines.append(f"depth #{k}: {pages * 1024} dwords, 4096 changed, 2 distinct; 0xdeadbeef x 1, 0x3f000000 x 1")
            if rf:
                lines.append(f"depth store #{k}: {pages * 1024} dwords, 2048 changed, 2049 distinct; 0x3e800000 x 1")
        hsh = "0x%016x" % (w * 0x9E3779B97F4A7C15 + h & (2 ** 64 - 1))
        if w == 256 and h == 256 and not poked_ta and "--dump-render" in o:
            hsh = HASH["f2-ctl-256"]
        if ramp and pokes == ["blk:1=0x00400200"]:
            hsh = HASH["x-ctl"] if "s0diff" not in world else "0x0123456789abcdef"
        lines += [f"target: {w}x{h} hash {hsh}", f"diff: 0 of {w * h} pixels", "outside: 0 dwords",
                  f"layout: fb {fb:#010x}"]
        if "--pixels" in o:
            lines += [f"row {y}: " + " ".join(["0x" + GREEN] * w) for y in range(min(h, 2))]
    if "--dump-render" in o:
        d = g("--dump-render")
        files[os.path.join(d, "tri.param.bin")] = bytes(64)
        files[os.path.join(d, "tri.tadata.bin")] = bytes(64)
        lines.append(f"probe tri: render memory to {d}/tri.{{param,tadata}}.bin (4603904, 24576 bytes)")
    lines.append(f"tri: {n} renders ok")
    return dict(rc=0, out="\n".join(lines) + "\n", files=files, kmsg=kmsg)


# ---- probe ----------------------------------------------------------------------------------
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
    head = f"probe {prog}: scratch at 0x3e003000 ({pages * 4} KiB)\n"
    flags, at = knob("vm_pte_flags"), knob("vm_pte_addr")
    if at == 0x3E003000 and flags:
        if flags == 0x2 or "alt" in world or "faultmax" in world:
            return fault(head + f"probe {prog}: ", 0x80002 if flags == 0x2 else 0xA0002, 0x3E003012, world)
    text = kept("f1-ref-a.txt.gz").decode()
    rows = [ln for ln in text.splitlines() if ": row " in ln]
    kmsg = [R110 + " (an earlier recovery)"] if "recovline" in world else []
    return dict(out=head + "\n".join(rows) + "\n", kmsg=kmsg)


def probe_tri(argv, world):
    if not argv or not os.path.exists(argv[-1]):
        return USAGE
    o = parse(argv, PROBE_TRI, first=1, trailing=1)
    if o is None or o.get("--tri") != ["pixel"]:
        return USAGE
    for k in ("--obj2-pixel",):
        if k in o and not os.path.exists(o[k][0]):
            return USAGE
    if "--dump-render" in o and not os.path.isdir(o["--dump-render"][0]):
        return dict(rc=1, err="sgxfive-test: No such file or directory\n")
    prog = os.path.basename(argv[-1])[:-4]
    vdm = o.get("--vdm", [])
    head = f"probe {prog}: scratch at 0x3e00e000 (64 KiB)\n"
    files = {}
    if "--dump-render" in o:
        d = o["--dump-render"][0]
        files = {os.path.join(d, f"{prog}.param.bin"): bytes(64), os.path.join(d, f"{prog}.tadata.bin"): bytes(64)}
    tail = f"probe {prog}: render memory to {o.get('--dump-render', ['.'])[0]}/{prog}.{{param,tadata}}.bin (4603904, 24576 bytes)\n" \
        if files else ""
    if o.get("--index-width") == ["32"]:                    # E756's index rows (s0 ix32-n, h1)
        desc = f"probe {prog}: tri 64x64 (15 vertices, at depths, 32-bit indices) (VDM words ^2), pixel replaced\n"
        if vdm == ["2^=0x03000000"]:                        # h1: bit 24 alone
            if "h1fault" in world:
                return fault(head + desc + f"probe {prog}: ", 0xD0008, 0x1, world)
            if "alt" not in world:
                return fault(head + desc + f"probe {prog}: ", 0, 0, world, hung=True)
            return dict(out=head + desc + f"probe {prog}: o0 mixed 0x{BG} x2998 0x{GREEN} x1098\n" + tail, files=files)
        if "s0noread" in world:                             # an o0 line without the background
            return dict(out=head + desc + f"probe {prog}: o0 0x{GREEN} (4096 of 4096)\n" + tail, files=files)
        return dict(out=head + desc + f"probe {prog}: o0 0x{BG} (4096 of 4096)\n" + tail, files=files)
    if vdm != ["1^=0x00000800"]:
        return USAGE
    # h2: the counter (M1), kept in the fake state; a reset since the last job clears it
    r = resets()
    last_r, c = (int(x) for x in state("r18f_counter", "-1 0").split())
    if r != last_r:
        c = 0
    if "h2ctlhang" in world:
        hang = c > 0                                        # E413's alternation
    elif "alt" in world:
        hang = False                                        # H-SCALE
    else:
        hang = c + 4 > 8                                    # M1
    if hang:
        put("r18f_counter", f"{r + 1} 0")                   # the runner resets after a hang
        return fault(head + f"probe {prog}: ", 0, 0, world, hung=True)
    put("r18f_counter", f"{r} {c + 4}")
    return dict(out=head + f"probe {prog}: o0 mixed 0xff0000ff x1024 0x{BG} x3072\n", files=files)


def health(argv):
    if int(state("r18f_wedge", "0")) > 0:
        put("r18f_wedge", int(state("r18f_wedge")) - 1)
        return dict(rc=1, out="job: failed: job hung, context lost (Connection timed out)\n"
                    "diff: 4096 of 4096 pixels\n")
    return None


def answer(tool, argv, world):
    if argv in (["fill"], ["tri"]):
        return health(argv)
    if tool not in ("t10", "t14") or not argv:
        return USAGE
    if argv[0] == "tri":
        return tri(tool, argv, world)
    if argv[0] == "probe" and tool == "t14":
        return probe_tex(argv, world)
    if argv[0] == "probe" and tool == "t10" and "--tri" in argv:
        return probe_tri(argv, world)
    return USAGE
