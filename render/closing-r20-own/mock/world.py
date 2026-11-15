# SPDX-License-Identifier: MIT
"""mock/world.py: r20-own's argv-driven fake laptop for kit/session.py mock (r19-own1b's, with
--move and regtimeline). answer() sees the tool's name, the argv, the world's tokens and the
debugfs knobs the runner wrote (FAKE_DBGREAL), never a case name; it returns None (the health pair,
or regtimeline's own words, checked) or dict(rc, out, err, files, kmsg, latch). As strict as t18b
for the one form the tables use: an option it does not take, a missing argument, --move other than
1:DX,DY, --kept-copy or --close-first-early without --ctx2, or a directory not there is refused.
regtimeline (rt) must be `0 0.3 REGS -- CMD...` with one of the plan's two register lists.

The pages are the frozen references (predictions/ow.tsv and owp.tsv, gen/make.py's E1087 and E1084
pages): the owner overflows below P 0x100, is raised at P 0x2c and below (ta3d.101.bin dword 38
0x20), its closed copy is zero at 0x422 and holds lists below. Without render_keep armed the second
render faults (E631).

Worlds (EXPECT: the driver's status and each stage's runner status):
  model     H-SECOND (E1087's pages whatever the move; E1084's at 0x30), H-REGIME, H-TA: 0
  alt       H-OWNER (the moved cover's lists), H-END: 0
  oneempty  the copy right after the close reads 0 bytes in the second row of a stage only: that
            row is cannot tell, the stage goes on: 0
  twoempty  it reads 0 bytes in the second and third rows of ow: hook_check stops ow (24), owt and
            owp run (driver 0)
  nokeep    render_kept unreadable after the close: the runner stops (23)
  fault     the second context's render faults in ow's second row: 4
"""
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECT = {
    "model": (0, {"ow": 0, "owt": 0, "owp": 0}),
    "alt": (0, {"ow": 0, "owt": 0, "owp": 0}),
    "oneempty": (0, {"ow": 0, "owt": 0, "owp": 0}),
    "twoempty": (0, {"ow": 24, "owt": 0, "owp": 0}),
    "nokeep": (23, {"ow": 23}),
    "fault": (4, {"ow": 4}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
RT = ("0x0620-0x0634,0x0658,0x065c,0x0674,0x0694,0x0698,0x0700-0x0728",
      "0x062c,0x0634,0x0694,0x0698")
PAGE, SIZE = 4096, 0x11000
TRI = {"--width": 1, "--height": 1, "-n": 1, "--keep-overflow": 0, "--wait-ms": 1, "--ctx2": 0,
       "--close-first-early": 0, "--kept-copy": 1, "--words": 1, "--kpoke-render": 1, "--move": 1}
O_BASE, S_BASE = 0x20406000, 0x20806000
MOVED = {"-112,-80": [0, 1, 2, 3, 4, 5, 6, 8, 9, 12], "64,64": [0, 1, 4, 5, 6, 7, 9, 10, 11, 13, 14]}


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


def ref(stage, name, q):
    """a frozen value of predictions/STAGE.tsv (the first row of that case and quantity)"""
    for ln in open(os.path.join(KP, "predictions", f"{stage}.tsv")).read().splitlines()[1:]:
        c = ln.split("\t")
        if c[0] == name and c[1] == q:
            return c[2]
    raise KeyError((stage, name, q))


def fill(b, spec):
    for part in spec.split(";"):
        p, _, ws = part.partition(":")
        for w in filter(None, ws.split(",")):
            i, v = w.split("=")
            struct.pack_into("<I", b, int(p[1:]) * PAGE + 4 * int(i), int(v, 16))


def lists(b, mts, first=9):
    for k, m in enumerate(mts):
        struct.pack_into("<2I", b, 6 * PAGE + 8 * m, (1 << 16) | (first + k), first + k)
    struct.pack_into("<2I", b, 6 * PAGE + 8 * 16, 0x00010001, 1)


def parse(argv):
    opts, i = {}, 1
    while i < len(argv):
        a = argv[i]
        if a not in TRI or i + TRI[a] >= len(argv) + (0 if TRI[a] else 1):
            return None
        opts.setdefault(a, []).append(argv[i + 1] if TRI[a] else True)
        i += 1 + TRI[a]
    return opts


def tri(tool, argv, world):
    o = parse(argv)
    if o is None or tool != "t18b":
        return USAGE
    g = lambda k, d=None: o[k][0] if k in o else d  # noqa: E731
    if "--ctx2" not in o or "--close-first-early" not in o or g("-n") != "1":
        return USAGE
    w, h = int(g("--width")), int(g("--height"))
    if (w, h) != (1024, 768) or g("--kpoke-render") != "1:ta:7^=0xc":
        return USAGE
    mv = g("--move")
    if mv is not None and (not mv.startswith("1:") or mv[2:] not in MOVED or len(o["--move"]) > 1):
        return dict(rc=255, err=f"sgxfive-test: bad --move {mv} (N:DX,DY)\n")
    kdir, wdir = g("--kept-copy"), g("--words")
    for d in (kdir, wdir):
        if not os.path.isdir(d):
            return dict(rc=1, err=f"sgxfive-test: {d}: No such file or directory\n")
    P = int(knob("render_pb_pages", "0x422"), 0)
    keep = knob("render_keep") in ("1", "Y", "y")
    ovf, raised = P < 0x100, P <= 0x2c
    n = int(got("r20o_rows") or 0) + 1
    put("r20o_rows", n)
    words = "".join(f"rtds:{i}=0x{v:08x}\n" for i, v in enumerate(
        [0x3242320c, 0, 8, 0, 0, 1, 0x32423000, 0, 1, 0xc0, 0x10c64000, O_BASE, O_BASE - 0x2000,
         O_BASE - 0x1000, O_BASE - 0x6000]))
    ta = bytearray(236)
    struct.pack_into("<I", ta, 38 * 4, 0x20 if raised else 0)
    out = ["tri: render context for targets up to 1024x768", "tri: second render context",
           f"tri: words 0 to {wdir}/words.0.txt (3079 bytes), {wdir}/ta3d.0.bin (236 bytes)",
           "tri: kpoke before render 1: ta:7^=0xc"]
    if mv:
        out.append(f"tri: render 1 moved by {mv[2:]}")
    files = {f"{wdir}/words.0.txt": words, f"{wdir}/ta3d.0.bin": bytes(236),
             f"{wdir}/words.101.txt": words, f"{wdir}/ta3d.101.bin": bytes(ta),
             f"{wdir}/words.201.txt": words, f"{wdir}/ta3d.201.bin": bytes(ta)}
    out.append("job: failed: scene overflowed the parameter buffer, context kept (No space left "
               "on device)" if ovf else "job: ok")
    out += [f"tri: words 101 to {wdir}/words.101.txt (3079 bytes), {wdir}/ta3d.101.bin (236 bytes)",
            "tri: closed the first context before the second context's render 1"]
    closed, after = bytearray(SIZE), bytearray(SIZE)
    if ovf and not raised:
        lists(closed, [0, 1, 2, 4, 5, 6, 8, 9, 13])
    alt = "alt" in world and mv
    if P == 0x422:
        if alt:
            fill(after, ref("ow", "ow-c", "after_pages").split(";p6:")[0])
            lists(after, MOVED[mv[2:]], 2)
        else:
            fill(after, ref("ow", "ow-c", "after_pages"))
    elif P == 0x30:
        if alt:
            lists(after, MOVED[mv[2:]][:4], 0x10)
        else:
            fill(after, ref("owp", "owp-30-a", "after_state"))
    elif not raised:
        lists(after, [2, 6, 7, 10], 0x10)
    first = "oneempty" in world and n == 2
    two = "twoempty" in world and n in (2, 3)
    if first or two:
        p = f"{kdir}/kept.closed.1.bin"
        files[p] = b""
        out.append("tri: render_kept after closing the first context, before the second "
                   f"context's render 1: {p} (0 bytes)")
    elif "nokeep" in world:
        out.append("tri: render_kept after closing the first context, before the second "
                   "context's render 1: No such device (0 bytes)")
    else:
        p = f"{kdir}/kept.closed.1.bin"
        files[p] = bytes(closed)
        out.append("tri: render_kept after closing the first context, before the second "
                   f"context's render 1: {p} ({SIZE} bytes)")
    out.append(f"tri: words 201 to {wdir}/words.201.txt (3079 bytes), {wdir}/ta3d.201.bin (236 bytes)")
    if not keep or ("fault" in world and n == 2):
        out.append("job: failed: job faulted, context lost (Input/output error)")
        out.append("sgxfive-test: second context render: job faulted, context lost")
        return dict(rc=1, out="\n".join(out) + "\n", files=files,
                    kmsg=["sgxfive: BIF fault 0x90400 at 0x3241100f (PD 0x0) stalls job 9, "
                          "recovering"], latch=(0x90400, 0x3241100F))
    out.append("job: failed: scene overflowed the parameter buffer, context kept (No space left "
               "on device)" if ovf else "job: ok")
    out.append("tri2 1024x768 #1: overflowed" if ovf else
               "tri2 1024x768 #1: 207456 triangle, 578976 background, 0 other; wrong 0 inside, "
               "0 outside, 0 at edges; 141525 if flipped; guard 0")
    p = f"{kdir}/kept.1.bin"
    files[p] = bytes(after)
    out.append(f"tri: render_kept after the second context's render 1: {p} ({SIZE} bytes)")
    out += [f"tri: words 1 to {wdir}/words.1.txt (3079 bytes), {wdir}/ta3d.1.bin (236 bytes)",
            "target: 1024x768 hash 0xc9e301d225fe2325"]
    files[f"{wdir}/words.1.txt"] = words
    files[f"{wdir}/ta3d.1.bin"] = bytes(ta)
    if ovf:
        out += ["tri 1024x768 #1: overflowed, 162544 triangle, 623888 background, 0 other; wrong "
                "44191 inside, 0 outside, 0 at edges; 136225 if flipped; guard 0",
                "tri: 0 of 1 renders ok, 1 overflowed"]
    else:
        out += ["diff: 0 of 786432 pixels", "tri 1024x768 #1: 207456 triangle, 578976 background, "
                "0 other; wrong 0 inside, 0 outside, 0 at edges; 141525 if flipped; guard 0",
                "tri 1024x768 #1: 1319103 us", "tri: 1 renders ok"]
    out.append("tri: closing the second context")
    return dict(out="\n".join(out) + "\n", files=files)


def timeline(tool, regs, argv, rc, world):
    """regtimeline's samples: the owner's run under its state base, the second context's base,
    the owner's base again with a task write (the store), before (model: H-TA) or after (alt:
    H-END) the second context's last task write"""
    seq = [(O_BASE, 0, 0), (O_BASE, 4, 4), (S_BASE, 4, 4)]
    seq += [(O_BASE, 2, 2), (S_BASE, 1, 1)] if "alt" not in world else \
        [(S_BASE, 1, 1), (O_BASE, 2, 2)]
    rows = []
    for b, ts, tc in seq:
        v = {0x62c: b, 0x634: b - 0x2000, 0x694: ts, 0x698: tc}
        rows.append([v.get(r, 0) for r in regs])
    return rows


def answer(tool, argv, world):
    if tool == "rt":
        if argv[:2] != ["0", "0.3"] or argv[2:3] not in ([RT[0]], [RT[1]]) or argv[3:4] != ["--"]:
            return dict(rc=2, err=f"regtimeline: not TOTAL 0, LEAD 0.3 and a plan list: {argv[:4]}\n")
        return None
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "tri":
        return tri(tool, argv, world)
    return USAGE


if __name__ == "__main__":
    sys.exit(0)
