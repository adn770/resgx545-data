# SPDX-License-Identifier: MIT
"""mock/world.py: r14-bif's argv-driven fake laptop for kit/session.py mock. answer(tool, argv,
world) sees the tool's name, the argv, the world's tokens and the fake kernel's knob files
($FAKE_DBGREAL, as the real job depends on the kernel), never a case name. It is as strict as t14
(sgxfive-test at c58f9f9) on the options the rows use: any other option (a stencil one included),
a --depth-* option without --depth, --depth-store-fill without --depth-store, --depth-ctl-next
without -n 2 or more, a --refill that is not K:BUF=V with BUF depth, stencil or fb, 2 <= K <= -n,
V a 32-bit number, or depth without --depth, stencil without --stencil, a fill that is not a value
or index, --depth-pages below the target's pages are refused (rc 2, usage). Every row is also
replayed on t14's library mock by the kit (session.py libmock).

The buffers sit where t14 maps them (depth 0x3e001000, store right after it, base 0x3e000000).
Each render: the tool fills the buffers (render 1, and every render without --depth-ctl-next),
then writes a --refill's V to the depth buffer, then the render loads the depth buffer when the
control's load bits (0x4002) are set, else takes the clear 1.0, and stores the first W x H dwords
to the store: the load itself under the test never (--poke blk:1=0x00000200, nothing drawn, rc 1
with a diff line), 1.0 under the default test (the triangle drawn exactly, rc 0; E965's
tri-c-depth). The model is coherent: render 2 loads what the host wrote last. A knob row whose
vm_pte_addr is the depth buffer logs the kernel's `vm_map 0x3e001000 +0x14000: PTE flags F`.

Worlds (EXPECT: the driver's status, {stage: the runner's status}):
  model      every job completes, the controls have their readings: 0
  noread     no `depth store #N` lines: rf-c-plain, the first control, has no reading (25)
  rejected   every knob row prints `job: rejected` and a diff line (E934): rf-c-unread fails under
             expectdiff, the session stops (4)
  nopte      the kernel logs no PTE line: hook_check stops refill at rf-c-unread (24; the driver
             goes on: 0, no stage after it)
  norefill   the tool prints no refill line (a tool without --refill's report): hook_check stops
             refill at rf-c-unread (24; the driver 0)
  fault      a refill row's render 2 faults: unexpected, the session stops (4)"""
import os
import struct

EXPECT = {
    "model": (0, {"refill": 0}),
    "noread": (25, {"refill": 25}),
    "rejected": (4, {"refill": 4}),
    "nopte": (0, {"refill": 24}),
    "norefill": (0, {"refill": 24}),
    "fault": (4, {"refill": 4}),
}
FLAGS = {"--keep-going", "--tri-full", "--depth", "--depth-store"}
VALUED = {"-n", "--wait-ms", "--width", "--height", "--max-width", "--max-height", "--tri-z",
          "--depth-ctl", "--depth-ctl-next", "--depth-fill", "--depth-store-fill",
          "--depth-pages", "--depth-dump", "--poke", "--refill"}
MULTI = {"--poke", "--refill"}
USAGE = dict(rc=2, out="", err="usage: sgxfive-test ...\n")
PAGE = 4096
DEPTH, BASE = 0x3E001000, 0x3E000000
CLEAR = 0x3F800000


def knob(name, default="0"):
    d = os.environ.get("FAKE_DBGREAL")
    p = os.path.join(d, name) if d else None
    v = open(p).read().strip() if p and os.path.exists(p) else ""
    return int(v or default, 0)


def parse(argv):
    o, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in FLAGS:
            o[a] = True
        elif a in VALUED and i + 1 < len(argv):
            if a in MULTI:
                o.setdefault(a, []).append(argv[i + 1])
            else:
                o[a] = argv[i + 1]
            i += 1
        else:
            return None
        i += 1
    return o


def u32(s):
    try:
        v = int(s, 0)
    except ValueError:
        return None
    return v if 0 <= v <= 0xFFFFFFFF else None


def fill_at(f, i):
    return i if f == "index" else int(f, 0)


def pack(v):
    return struct.pack("<%dI" % len(v), *v)


def tri(argv, world):
    o = parse(argv)
    if o is None:
        return USAGE
    n = int(o.get("-n", 1))
    w, h = int(o.get("--width", 64)), int(o.get("--height", 64))
    if any(k in o for k in ("--depth-ctl", "--depth-ctl-next", "--depth-fill", "--depth-dump",
                            "--depth-pages", "--depth-store")) and "--depth" not in o:
        return USAGE
    if "--depth-store-fill" in o and "--depth-store" not in o:
        return USAGE
    if "--depth-ctl-next" in o and n < 2:
        return USAGE
    for k in ("--depth-fill", "--depth-store-fill"):
        if k in o and o[k] != "index" and u32(o[k]) is None:
            return USAGE
    refills = {}
    for spec in o.get("--refill", []):
        k, _, rest = spec.partition(":")
        buf, _, val = rest.partition("=")
        if not k.isdigit() or buf not in ("depth", "stencil", "fb") or u32(val) is None:
            return USAGE
        if not 2 <= int(k) <= n or (buf == "depth" and "--depth" not in o) or buf == "stencil":
            return USAGE
        refills[int(k)] = (buf, u32(val))
    minp = (w * h * 4 + PAGE - 1) // PAGE
    pages = int(o.get("--depth-pages", 0)) or minp + 16
    if pages < minp:
        return USAGE
    ctl = int(o.get("--depth-ctl", "0x0017100c"), 16)
    nxt = int(o["--depth-ctl-next"], 16) if "--depth-ctl-next" in o else 0
    never = any(p == "blk:1=0x00000200" for p in o.get("--poke", []))
    dfill = o.get("--depth-fill", "0x3f800000")
    sfill = o.get("--depth-store-fill", "0xdeadbeef")
    nd = pages * 1024
    out, files, kmsg = [f"tri: render context for targets up to {w}x{h}"], {}, []
    store_at = DEPTH + pages * PAGE
    if "--depth" in o:
        out.append(f"depth: {DEPTH:#010x} {pages} pages, fill {dfill}, base {BASE:#010x}, "
                   f"control {ctl:#010x}" + (f", then {nxt:#010x}" if nxt else ""))
        if "--depth-store" in o:
            out.append(f"depth store: {store_at:#010x} {pages} pages, fill {sfill}")
    knobbed = knob("vm_pte_addr") == DEPTH and knob("vm_pte_flags") and "--depth" in o
    if knobbed and "nopte" not in world:
        kmsg.append(f"sgxfive: vm_map {DEPTH:#010x} +{pages * PAGE:#x}: PTE flags "
                    f"{knob('vm_pte_flags'):#x} (debugfs vm_pte_flags)")
    if knobbed and "rejected" in world:
        out += ["job: rejected (Invalid argument)", f"diff: {w * h} of {w * h} pixels"]
        return dict(rc=1, out="\n".join(out) + "\n", err="", kmsg=kmsg)
    depth, store = [], []
    ext = w * h
    ok = 0
    for r in range(1, n + 1):
        c = nxt if r > 1 and nxt else ctl
        if "--tri-full" in o:
            out.append("tri: triangle (0,0) (%d,0) (0,%d), depth %s" % (
                3 * w, 3 * h, " ".join(o.get("--tri-z", "0.5,0.5,0.5").split(","))))
        if r == 1 or not nxt:
            depth = [fill_at(dfill, i) for i in range(nd)]
            store = [fill_at(sfill, i) for i in range(nd)]
            dref = dfill
        if r in refills:
            depth = [refills[r][1]] * nd
            dref = f"{refills[r][1]:#x}"
            if "norefill" not in world:
                out.append(f"refill: render {r} buf {refills[r][0]} value {refills[r][1]:#010x}")
        if r in refills and "fault" in world:
            out.append("job: failed: job faulted, context lost (Input/output error)")
            out.append(f"tri: FAILED after {ok} renders")
            return dict(rc=1, out="\n".join(out) + "\n", err="",
                        kmsg=kmsg + ["sgxfive: BIF fault 0x80200 at 0x3e001000 (PD 0xf4f2000) "
                                     "stalls job 7, recovering"], latch=(0x80200, 0x3E001000))
        out.append("job: ok")
        load = c & 0x4002 == 0x4002
        if "--depth-store" in o:
            for k in range(ext):
                store[k] = (depth[k] if load else CLEAR) if never else CLEAR
        drawn = 0 if never else (ext if "--tri-full" in o else 1062 * ext // 4096)
        if "--depth" in o and "noread" not in world:
            dch = sum(1 for i in range(nd) if depth[i] != fill_at(dref, i))
            out.append(f"depth #{r}: {nd} dwords, {dch} changed, 9 distinct")
            if "--depth-store" in o:
                sch = sum(1 for i in range(nd) if store[i] != fill_at(sfill, i))
                out.append(f"depth store #{r}: {nd} dwords, {sch} changed, 2 distinct")
        if "--depth-dump" in o:
            d = o["--depth-dump"]
            files[f"{d}/depth.{r}.bin"] = pack(depth)
            if "--depth-store" in o:
                files[f"{d}/depth-store.{r}.bin"] = pack(store)
        out.append(f"target: {w}x{h} hash 0x0123456789abcdef")
        out.append(f"diff: {0 if not never else ext} of {ext} pixels")
        out.append("layout: fb 0x3e029000")
        out.append(f"tri {w}x{h} #{r}: {drawn} triangle, {ext - drawn} background, 0 other; "
                   "wrong 0 inside, 0 outside, 0 at edges; 0 if flipped; guard 0")
        ok += not never
    out.append(f"tri: {ok} renders ok" if ok == n else f"tri: {ok} of {n} renders ok")
    return dict(rc=0 if ok == n else 1, out="\n".join(out) + "\n", err="", files=files, kmsg=kmsg)


def answer(tool, argv, world):
    if not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] == "tri" and tool == "t14":
        return tri(argv[1:], world)
    return USAGE
