# SPDX-License-Identifier: MIT
"""mock/world.py: r19-flag's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv, the world's tokens and the fake laptop's state (the debugfs knobs the
runner wrote), never a case name; it returns None (the health pair) or dict(rc, out, err, files,
kmsg, latch). As strict as t18b's `tri` (ec50498): an option it does not take, a missing
argument, a --final-pb-pages without --geometry, a --dump-each without --dump-render, a geometry
or fill render outside its range, a bad --tadata-fill-render spec or an output directory that is
not there is refused (usage, rc 2).

What the fake draws (the mock's own rules, not measurements [infer]): the 1024x768 default
triangle in P pages (debugfs render_pb_pages, the runner's knob) overflows on its geometry kick iff
P < 0x40 (E625: P 0x28 does); the final render has N = --final-pb-pages pages, does not overflow
and reads 0x0624 = N - 0x22 (the module's threshold update, E1078's H-UPD); page 6 of the TA data
holds 18 non-zero dwords after the kick and, filled, the ramp 0xa5000000 + i.

Worlds (EXPECT: the driver's status and the stage's runner status):
  model       H-NOLOAD: both junk rows complete with the control's image: 0
  corrupt     H-LOAD-CORRUPT: both complete with a different image (rc 1, a diff line): 0
  faultjunk   H-LOAD-FAULT: both junk rows fault (BIF line), the limit used up on the last: 0
  hangjunk    H-LOAD-HANG: both junk rows hang, the kernel recovers: 0
  ctlfault    the control (no fill, no expectfault) faults: 4, the session stops
  ctlthr      the control's 0x0624 reads P - 0x22 (H-IGN): hook_check 24, no junk row runs
  ctlnoovf    the geometry kick does not overflow: 24
  nolists     page 6 holds no list after the kick: 24
  recovfail   a junk fault logs `SGX recovery failed: -110`: 24
  nobif       a junk fault without the kernel's BIF line: 24
  earlyfault  a junk row faults at render 1, before the fill: 24
  junkfail    a junk row fails without a fault or hang (job: failed: Invalid argument): 4
  wedge       a junk fault, then the health fails once (the retry draws): 16
"""
import os

EXPECT = {
    "model": (0, {"fl": 0}),
    "corrupt": (0, {"fl": 0}),
    "faultjunk": (0, {"fl": 0}),
    "hangjunk": (0, {"fl": 0}),
    "ctlfault": (4, {"fl": 4}),
    "ctlthr": (24, {"fl": 24}),
    "ctlnoovf": (24, {"fl": 24}),
    "nolists": (24, {"fl": 24}),
    "recovfail": (24, {"fl": 24}),
    "nobif": (24, {"fl": 24}),
    "earlyfault": (24, {"fl": 24}),
    "junkfail": (4, {"fl": 4}),
    "wedge": (16, {"fl": 16}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PAGE = 4096
TRI = {"--width": 1, "--height": 1, "-n": 1, "--geometry": 1, "--final-pb-pages": 1,
       "--keep-going": 0, "--keep-overflow": 0, "--wait-ms": 1, "--dump-render": 1,
       "--dump-each": 0, "--words": 1, "--regs": 1, "--tadata-fill-render": 1}
FAULTING = ("faultjunk", "recovfail", "nobif", "wedge")


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


def num(s):
    try:
        return int(s, 0)
    except ValueError:
        return None


def parse(argv):
    """{option: [values]} of tri's argv, or None when the real tool would refuse it."""
    opts, i = {}, 1
    while i < len(argv):
        a = argv[i]
        if a not in TRI or i + TRI[a] >= len(argv) + (0 if TRI[a] else 1):
            return None
        opts.setdefault(a, []).append(argv[i + 1] if TRI[a] else True)
        i += 1 + TRI[a]
    return opts


def fault(head, hung=False, bif=True, extra=()):
    """A job that ended in a fault or a hang: the tool's job line, rc 1, the kernel's lines."""
    kmsg = ["sgxfive: job 12 hung, recovering"] if hung else \
        ["sgxfive: BIF fault 0x90200 at 0x30011a40 (PD 0x5736000) stalls job 7, recovering"] \
        if bif else []
    kmsg += list(extra)
    what = "job hung, context lost (Connection timed out)" if hung else \
        "job faulted, context lost (Input/output error)"
    if "wedge" in os.environ.get("FAKE_WORLD", ""):
        put("r19f_wedge", 1)
    return dict(rc=1, out=head + f"job: failed: {what}\n", err=f"sgxfive-test: render: {what}\n",
                kmsg=kmsg, latch=None if hung else (0x1000, 0x30011a40))


def regs_block(lo, hi, thr):
    lines = [f"regs: 0x{lo:04x}-0x{hi:04x} at 0x80080000"]
    for off in range(lo, hi + 1, 4):
        lines.append(f"reg 0x{off:04x} 0x{thr if off == 0x0624 else 0:08x}")
    return lines


def tadata(filled, world):
    pg = [bytearray(PAGE) for _ in range(8)]
    if not filled and "nolists" not in world:
        for i in range(18):
            pg[6][4 * i:4 * i + 4] = (0x10006 + i).to_bytes(4, "little")
    if filled:
        for i in range(1024):
            pg[6][4 * i:4 * i + 4] = (0xa5000000 + i).to_bytes(4, "little")
    return b"".join(bytes(p) for p in pg)


def tri(tool, argv, world):
    if tool != "t18b":
        return USAGE
    o = parse(argv)
    if o is None:
        return USAGE
    g = lambda k, d=None: o[k][0] if k in o else d  # noqa: E731
    w, h, n = num(g("--width", "64")), num(g("--height", "64")), num(g("-n", "1"))
    if not (w and h and n):
        return USAGE
    geo = [num(x) for x in o.get("--geometry", [])]
    final = num(g("--final-pb-pages", "0")) if "--final-pb-pages" in o else None
    if "--final-pb-pages" in o and (not geo or final is None or not 0x23 <= final <= 0x422):
        return USAGE
    if any(x is None or not 1 <= x < n for x in geo):
        return USAGE
    if "--dump-each" in o and "--dump-render" not in o:
        return USAGE
    fills = []
    for spec in o.get("--tadata-fill-render", []):
        f = spec.split(":")
        k = num(f[0]) if len(f) in (3, 4) else None
        if k is None or not 1 <= k <= n or num(f[1]) is None or num(f[2]) is None or \
                (len(f) == 4 and f[3] != "ramp"):
            return USAGE
        fills.append((k, " ".join(f[1:])))
    lo = hi = 0
    if "--regs" in o:
        r = o["--regs"][0].split("-")
        lo, hi = num(r[0]), num(r[1]) if len(r) == 2 else None
        if lo is None or hi is None or lo > hi:
            return USAGE
    for k in ("--dump-render", "--words"):
        if k in o and not os.path.isdir(o[k][0]):
            return dict(rc=1, err=f"sgxfive-test: {o[k][0]}: No such file or directory\n")
    P = knob("render_pb_pages") or 0x422
    overflow = P < 0x40 and "ctlnoovf" not in world
    junk = bool(fills)
    out = [f"tri: render context for targets up to {w}x{h}"]
    if final:
        out.append(f"tri: final renders' PB 0x{final:x} pages (debugfs render_final_pb_pages)")
    files, wd, dd = {}, g("--words"), g("--dump-render")

    def words(k, thr):
        if wd:
            files[os.path.join(wd, f"words.{k}.txt")] = b"words\n"
            files[os.path.join(wd, f"ta3d.{k}.bin")] = bytes(64)
            out.append(f"tri: words {k} to {wd}/words.{k}.txt (6 bytes), {wd}/ta3d.{k}.bin (64 bytes)")
            if "--regs" in o:
                out.append(f"tri: registers at snapshot {k}")
                out.extend(regs_block(lo, hi, thr))

    def dump(name, filled):
        if dd:
            files[os.path.join(dd, f"{name}.param.bin")] = bytes(64)
            files[os.path.join(dd, f"{name}.tadata.bin")] = tadata(filled, world)

    words(0, 0)
    thr_final = (P if "ctlthr" in world else (final or P)) - 0x22
    base = (w * 0x9E3779B97F4A7C15 + h) & (2 ** 64 - 1)
    ok_count = overflowed = rc = 0
    for k in range(1, n + 1):
        for f in fills:
            if f[0] == k:
                out.append(f"tri: tadata_fill before render {k}: {f[1]}")
        head = "\n".join(out) + "\n"
        if k == 1 and junk and "earlyfault" in world:
            return fault(head)
        if k in geo and overflow:
            out.append("job: failed: scene overflowed the parameter buffer, context kept "
                       "(No space left on device)")
            words(k, P - 0x22 + 0x20)
            out += [f"target: {w}x{h} hash 0x{base ^ 0xff:016x}",
                    f"diff: 1000 of {w * h} pixels, first (0, 0) 0xff000000 expected 0xff203040",
                    "outside: 0 dwords", "layout: fb 0x3e500000",
                    f"tri {w}x{h} #{k}: overflowed, 300 triangle, 3 background, 0 other; "
                    "wrong 0 inside, 0 outside, 0 at edges; 0 if flipped; guard 0"]
            if "--dump-each" in o:
                dump(f"tri.{k}", False)
            overflowed += 1
            continue
        if k in geo:
            out.append("job: ok")
            words(k, P - 0x22)
            out.append(f"tri {w}x{h} #{k}: geometry only, the scene left open")
            ok_count += 1
            continue
        if junk:
            if any(t in world for t in FAULTING):
                extra = ["SGX recovery failed: -110"] if "recovfail" in world else []
                return fault(head, bif="nobif" not in world, extra=extra)
            if "hangjunk" in world:
                return fault(head, hung=True)
            if "junkfail" in world:
                return dict(rc=1, out=head + "job: failed: Invalid argument\n")
        elif "ctlfault" in world:
            return fault(head)
        out.append("job: ok")
        words(k, thr_final)
        if "--regs" in o:
            out.extend(regs_block(lo, hi, thr_final))
        bad = 1000 if junk and "corrupt" in world else 0
        out.append(f"target: {w}x{h} hash 0x{base ^ (0x77 if bad else 0):016x}")
        out.append(f"diff: {bad} of {w * h} pixels" +
                   (", first (5, 5) 0x00000000 expected 0xff00ff00" if bad else ""))
        out += ["outside: 0 dwords", "layout: fb 0x3e500000",
                f"tri {w}x{h} #{k}: 3000 triangle, 0 background, 0 other; wrong {bad} inside, "
                "0 outside, 0 at edges; 0 if flipped; guard 0"]
        if bad:
            rc = 1
        else:
            out.append(f"tri {w}x{h} #{k}: 5000 us")
            ok_count += 1
        if "--dump-each" in o:
            dump(f"tri.{k}", junk)
    if dd and not rc:
        dump("tri", junk)
        out.append(f"probe tri: render memory to {dd}/tri.{{param,tadata}}.bin (4603904, {8 * PAGE} bytes)")
    if rc:
        out.append(f"tri: {ok_count} of {n} renders ok")
    elif overflowed:
        out.append(f"tri: {ok_count} of {n} renders ok, {overflowed} overflowed")
    else:
        out.append(f"tri: {ok_count} renders ok")
    return dict(rc=rc, out="\n".join(out) + "\n", files=files)


def answer(tool, argv, world):
    if argv in (["fill"], ["tri"]):
        if int(state("r19f_wedge", "0")) > 0:
            put("r19f_wedge", int(state("r19f_wedge")) - 1)
            return dict(rc=1, out="job: failed: job hung, context lost (Connection timed out)\n"
                        "diff: 4096 of 4096 pixels\n")
        return None
    if not argv or argv[0] != "tri":
        return USAGE
    return tri(tool, argv, world)
