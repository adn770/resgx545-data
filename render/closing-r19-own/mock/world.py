# SPDX-License-Identifier: MIT
"""mock/world.py: r19-own's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv, the world's tokens and the debugfs knobs the runner wrote (FAKE_DBGREAL),
never a case name; it returns None (the health pair) or dict(rc, out, err, files, kmsg, latch).
As strict as t18b for the one form the tables use: an option it does not take, a missing argument,
--kept-copy or --close-first-early without --ctx2, or a directory that is not there is refused.

t18b `tri --width W --height H -n 1 --keep-overflow --wait-ms MS --ctx2 --close-first-early
--kept-copy DIR --words DIR --kpoke-render 1:ta:7^=F` (sgxfive-test.c at ec50498, cmd_tri): the
first render (overflowing when W x H > 64 x 64 and render_pb_pages < 0x100), the words 101, the
close, kept.closed.1.bin, the second render, kept.1.bin, the words 1, the counts. The TA data is
the fork's layout (score.layout); the state page holds 18 non-zero dwords after a partial render at
0x28 (E464), 24 at another P, and the owner words are E631's for flag 0xc. Without render_keep
armed the second render faults (E631's close without keep: BIF 0x90400).

Worlds (EXPECT: the driver's status and each stage's runner status):
  model     own2 H-RSTORE (closed: lists, after: 0), own1 H-RENDER and H-COUNT (U 0x13): 0, 0
  alt       own2 H-LATE (both copies hold the lists), own1 H-CLOSE and H-CONST: 0, 0
  early     own2 H-EARLY (both copies 0), own1 H-NONE: 0, 0
  nokeep    render_kept unreadable after the close (that copy fails, 0 bytes): a file the scorer
            reads was not kept, the runner stops own2 (23), the session with it
  noovf     no first render overflows (a P the module ignored): hook_check stops own2 after its
            first row (24); own1 runs (0); the driver ends 0 (on_stop "next")
  fault     the second context's render faults in own2's second row: own2 4, the session stops
"""
import os
import struct
import sys

EXPECT = {
    "model": (0, {"own2": 0, "own1": 0}),
    "alt": (0, {"own2": 0, "own1": 0}),
    "early": (0, {"own2": 0, "own1": 0}),
    "nokeep": (23, {"own2": 23}),
    "noovf": (0, {"own2": 24, "own1": 0}),
    "fault": (4, {"own2": 4}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
PAGE = 4096
TRI = {"--width": 1, "--height": 1, "-n": 1, "--keep-overflow": 0, "--wait-ms": 1, "--ctx2": 0,
       "--close-first-early": 0, "--kept-copy": 1, "--words": 1, "--kpoke-render": 1}


def layout(w, h):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "score"))
    import score
    return score.layout(w, h)


def knob(name, default="0"):
    d = os.environ.get("FAKE_DBGREAL")
    p = os.path.join(d, name) if d else None
    return open(p).read().strip() if p and os.path.exists(p) else default


def put(name, value):
    d = os.environ.get("FAKE_DIR")
    if d:
        with open(os.path.join(d, name), "w") as f:
            f.write(str(value))


def got(name):
    d = os.environ.get("FAKE_DIR")
    p = os.path.join(d, name) if d else None
    return open(p).read().strip() if p and os.path.exists(p) else ""


def parse(argv):
    opts, i = {}, 1
    while i < len(argv):
        a = argv[i]
        if a not in TRI or i + TRI[a] >= len(argv) + (0 if TRI[a] else 1):
            return None
        opts.setdefault(a, []).append(argv[i + 1] if TRI[a] else True)
        i += 1 + TRI[a]
    return opts


def td(w, h, state=(), words=None):
    c, o, s, size = layout(w, h)
    b = bytearray(size)
    for k, v in enumerate(state):
        struct.pack_into("<I", b, s + 4 * k, v)
    if words:
        struct.pack_into("<I", b, c, words[0])
        struct.pack_into("<I", b, o, words[1])
        struct.pack_into("<2I", b, s, words[2], words[3])
    for k in range(64):                     # region headers: the owner's own TA writes
        struct.pack_into("<I", b, s + PAGE + 4 * k, 0x10000 + k)
    return bytes(b)


def tri(tool, argv, world):
    o = parse(argv)
    if o is None or tool != "t18b":
        return USAGE
    g = lambda k, d=None: o[k][0] if k in o else d  # noqa: E731
    if "--ctx2" not in o or "--close-first-early" not in o or g("-n") != "1":
        return USAGE
    w, h = int(g("--width")), int(g("--height"))
    kp = g("--kpoke-render", "")
    if not kp.startswith("1:ta:7^=") or kp[8:] not in ("0xc", "0x4"):
        return USAGE
    flag = int(kp[8:], 16)
    kdir, wdir = g("--kept-copy"), g("--words")
    for d in (kdir, wdir):
        if not os.path.isdir(d):
            return dict(rc=1, err=f"sgxfive-test: {d}: No such file or directory\n")
    P = int(knob("render_pb_pages", "0x422"), 0)
    keep = knob("render_keep") in ("1", "Y", "y")
    ovf = w * h > 64 * 64 and P < 0x100 and "noovf" not in world
    n = int(got("r19o_rows") or 0) + 1
    put("r19o_rows", n)
    out = [f"tri: render context for targets up to {w}x{h}", "tri: second render context",
           f"tri: words 0 to {wdir}/words.0.txt (3079 bytes), {wdir}/ta3d.0.bin (236 bytes)",
           f"tri: kpoke before render 1: ta:7^={kp[8:]}"]
    files = {f"{wdir}/words.0.txt": "words 0\n", f"{wdir}/ta3d.0.bin": bytes(236),
             f"{wdir}/words.101.txt": "words 101\n", f"{wdir}/ta3d.101.bin": bytes(236),
             f"{wdir}/words.201.txt": "words 201\n", f"{wdir}/ta3d.201.bin": bytes(236)}
    out.append("job: failed: scene overflowed the parameter buffer, context kept (No space left "
               "on device)" if ovf else "job: ok")
    out += [f"tri: words 101 to {wdir}/words.101.txt (3079 bytes), {wdir}/ta3d.101.bin (236 bytes)",
            "tri: closed the first context before the second context's render 1"]
    lists = [((0x14 - k) << 16) | (9 + k) for k in range(9)] * 2 if P == 0x28 else \
        [((0x30 - k) << 16) | (9 + k) for k in range(12)] * 2
    lists = lists[:18] if P == 0x28 and w == 1024 else lists
    U = 0x13 if w == 1024 else 2
    words = (0x00200047, 0x04000417, (U << 16) | 1, U)
    big = w * h > 64 * 64
    if "alt" in world:
        words = (0x00200047, 0x04000417, 0x00020001, 2)
    closed_state = lists if ovf and "early" not in world else ()
    closed_words = words if flag == 0xC and "alt" in world and not big else None
    after_state = closed_state if "alt" in world else ()
    after_words = None if flag != 0xC or ovf or ("early" in world and big) else words
    closed = td(w, h, closed_state, closed_words)
    after = td(w, h, after_state, after_words)
    if "nokeep" in world:
        out.append("tri: render_kept after closing the first context, before the second "
                   "context's render 1: No such device (0 bytes)")
    else:
        p = f"{kdir}/kept.closed.1.bin"
        files[p] = closed
        out.append("tri: render_kept after closing the first context, before the second "
                   f"context's render 1: {p} ({len(closed)} bytes)")
    out += [f"tri: words 201 to {wdir}/words.201.txt (3079 bytes), {wdir}/ta3d.201.bin (236 bytes)"]
    if not keep or ("fault" in world and n == 2):
        out.append("job: failed: job faulted, context lost (Input/output error)")
        out.append("sgxfive-test: second context render: job faulted, context lost")
        return dict(rc=1, out="\n".join(out) + "\n", files=files,
                    kmsg=["sgxfive: BIF fault 0x90400 at 0x3241100f (PD 0x0) stalls job 9, "
                          "recovering"], latch=(0x90400, 0x3241100F))
    out.append("job: failed: scene overflowed the parameter buffer, context kept (No space left "
               "on device)" if ovf else "job: ok")
    if ovf:
        out.append(f"tri2 {w}x{h} #1: overflowed")
    else:
        out.append(f"tri2 {w}x{h} #1: 1062 triangle, 3034 background, 0 other; wrong 0 inside, "
                   "0 outside, 0 at edges; 612 if flipped; guard 0")
    p = f"{kdir}/kept.1.bin"
    files[p] = after
    out.append(f"tri: render_kept after the second context's render 1: {p} ({len(after)} bytes)")
    out += [f"tri: words 1 to {wdir}/words.1.txt (3079 bytes), {wdir}/ta3d.1.bin (236 bytes)",
            f"target: {w}x{h} hash 0x1a1e80e565302a05"]
    files[f"{wdir}/words.1.txt"] = "words 1\n"
    files[f"{wdir}/ta3d.1.bin"] = bytes(236)
    if ovf:
        out += [f"tri {w}x{h} #1: overflowed, 162544 triangle, 623888 background, 0 other; wrong "
                "44191 inside, 0 outside, 0 at edges; 136225 if flipped; guard 0",
                "tri: 0 of 1 renders ok, 1 overflowed"]
    else:
        out += [f"tri {w}x{h} #1: 1062 triangle, 3034 background, 0 other; wrong 0 inside, "
                "0 outside, 0 at edges; 612 if flipped; guard 0", f"tri {w}x{h} #1: 19972 us",
                "tri: 1 renders ok"]
    out.append("tri: closing the second context")
    return dict(out="\n".join(out) + "\n", files=files)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "tri":
        return tri(tool, argv, world)
    return USAGE
