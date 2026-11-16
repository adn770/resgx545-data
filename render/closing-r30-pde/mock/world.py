# SPDX-License-Identifier: MIT
"""mock/world.py: r30-pde's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv, the world's tokens and the debugfs knobs the runner wrote (vm_pde_addr,
vm_pde_size, vm_pde_layout), never a case name; it returns None (the health pair) or dict(rc,
out, err, files, kmsg, latch). As strict as t30 on the rows' forms: `copy --src-addr A --height
H --large-copy DIR` and `fill --dst-addr A --height H --large-copy DIR`, A a page; anything else is
a usage refusal (rc 2). The large mapping is gen/pde.py's (the fork's functions): the world picks
the reading the hardware gives, the fake prints the copy's `tags:` lines and the tool's diff and
writes vm_large.txt as the kernel's read-out prints it (the lines score.py and run/hooks.sh read).

Worlds (EXPECT: the driver's status and each stage's runner status; a stage whose gate closed is
skipped, so absent):
  model      the frozen hypotheses: codes 1-5 H-DENSE, misalign H-MASK-S, ptoff H-PTOFF-IGN,
             codes 6 and 7 H-FAULT (f67's 4 faults: the #limit on its last row): 0 everywhere
  alt        the size field ignored (H-4K) for codes 1-5, codes 6 and 7 H-ALIAS: 0 everywhere
  layout     misalign H-MASK4K, ptoff H-PTOFF-USE, else model: 0 everywhere
  f67hang    codes 6 and 7 hang, recovered: f67 0 (H-FAULT's stall reading)
  faultall   codes 1-7 fault: f1 reaches #limit 6 with c3's rows left (24), the session ends
  nowarm     s0-warm's 4 MiB map is refused (-ENOMEM): voided (soft), f45 and f67 gated off: 0
  enomem45   s0-warm had its region but code 4's maps are refused: two soft failures in a row,
             f45 24; with every row of f45 voided its cases.tsv holds no row, which the kit's
             kept check reads as a file not kept (driver 43): the session ends either way
  s0kdiff    the vm_pde_size 0 copies read other tags: every flagged gate closes: s0 0 alone
  s0fault    a knobs-off fill faults (no expectfault): s0 4, the session stops
  nolarge    a knobs-off copy writes no vm_large.txt: s0 23 (the scorer's file not kept)
  outside    code 1's fill changes page 0:1, which no reading reaches: f1 24, the session ends
  copychg    code 2's copy a changes a page of the region: f1 24, the session ends
  tablechg   code 3's misalign copy leaves the table page changed: f2 24, the session ends
  recovfail  code 1's copy b faults and logs `SGX recovery failed: -110`: f1 24, the session ends
  f1hang     code 2's fill hangs (f1 plans faults only): f1 24, the session ends
  nobifline  code 6's fault has no kernel BIF line: f67 24, the session ends
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pde as P  # noqa: E402

FLAG = ("f1", "f2", "f45", "f67")
EXPECT = {
    "model": (0, {"s0": 0, **{s: 0 for s in FLAG}}),
    "alt": (0, {"s0": 0, **{s: 0 for s in FLAG}}),
    "layout": (0, {"s0": 0, **{s: 0 for s in FLAG}}),
    "f67hang": (0, {"s0": 0, **{s: 0 for s in FLAG}}),
    "faultall": (24, {"s0": 0, "f1": 24}),
    "nowarm": (0, {"s0": 0, "f1": 0, "f2": 0}),
    "enomem45": (43, {"s0": 0, "f1": 0, "f2": 0, "f45": 24}),
    "s0kdiff": (0, {"s0": 0}),
    "s0fault": (4, {"s0": 4}),
    "nolarge": (23, {"s0": 23}),
    "outside": (24, {"s0": 0, "f1": 24}),
    "copychg": (24, {"s0": 0, "f1": 24}),
    "tablechg": (24, {"s0": 0, "f1": 0, "f2": 24}),
    "recovfail": (24, {"s0": 0, "f1": 24}),
    "f1hang": (24, {"s0": 0, "f1": 24}),
    "nobifline": (24, {"s0": 0, "f1": 0, "f2": 0, "f45": 0, "f67": 24}),
}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
SLOT_SIZE = 0x400000
SENTINEL_ROWS = 16                  # rows a 4 KiB page at the stride of 256 bytes
FORMS = {"copy": "--src-addr", "fill": "--dst-addr"}
REGION = 0x1c000000                 # the fake region's physical address (naturally aligned)


def knob(name):
    d = os.environ.get("FAKE_DBGREAL")
    p = os.path.join(d, name) if d else None
    return int(open(p).read().strip() or "0", 0) if p and os.path.exists(p) else 0


def parse(argv):
    """{option: value} of a row's form, or None (a usage refusal)."""
    if not argv or argv[0] not in FORMS or len(argv) != 7:
        return None
    opts = dict(zip(argv[1::2], argv[2::2]))
    if set(opts) != {FORMS[argv[0]], "--height", "--large-copy"}:
        return None
    try:
        a, h = int(opts[FORMS[argv[0]]], 0), int(opts["--height"], 0)
    except ValueError:
        return None
    if a % P.SZ_4K or not a or h <= 0 or h % SENTINEL_ROWS:
        return None
    return dict(cmd=argv[0], addr=a, height=h, dir=opts["--large-copy"])


def reading(world, code, layout):
    """The (reading, size) the world's hardware gives a code and layout, or the end it takes."""
    if code == 0:
        return P.RD_4K, P.SZ_4K
    if code >= P.NAMED:
        if "f67hang" in world:
            return "hang", None
        if "alt" in world:
            return P.RD_4K, P.SZ_4K
        return "fault", None
    if "faultall" in world:
        return "fault", None
    if "alt" in world:
        return P.RD_4K, P.page_size(code)
    if "layout" in world and layout == P.MISALIGN:
        return P.RD_MASK4K, P.page_size(code)
    if "layout" in world and layout == P.PTOFF_L:
        return P.RD_DENSE | P.RD_PTOFF, P.page_size(code)
    return P.RD_DENSE, P.page_size(code)


def large_text(g, changed, table_bad=False):
    """vm_large.txt as the fork's sgxfive_vm_large_show prints it (the lines the readers use)."""
    out = [f"addr 0x60000000 code {g['code']} layout {g['layout']} ({P.LAYOUTS[g['layout']]}) "
           f"size {g['size']:#x} unit {g['unit']:#x}",
           f"region {REGION:#010x} +{g['region']:#x} order {g['order']}",
           f"pde {P.pde(g, REGION):#010x}"]
    out += [f"block {k} {REGION + o:#010x}" for k, o in enumerate(g["block_off"])]
    out.append(f"trap {P.pte(REGION + g['trap_off']):#010x}")
    out.append(f"table {'CHANGED (1 entries changed)' if table_bad else 'intact (0 entries changed)'}")
    for t in changed:
        s, p = t.split(":")
        out.append(f"slab {s} page {p}: 1024 changed +0x000 0xff336699 +0x004 0xff336699")
    n = g["region"] // P.SZ_4K - 1
    out.append(f"pages {n - len(changed)} intact {len(changed)} changed")
    return "\n".join(out) + "\n"


def fault(kind, addr, world):
    if kind == "hang":
        return dict(rc=3, out="job: failed: job hung, context lost (Connection timed out)\n",
                    kmsg=["sgxfive: job 12 hung, recovering"])
    kmsg = [] if "nobifline" in world else \
        [f"sgxfive: BIF fault 0x30005 at {addr:#x} (PD 0x5736000) stalls job 7, recovering"]
    if "recovfail" in world:
        kmsg.append("SGX recovery failed: -110")
    return dict(rc=3, out="job: failed: job faulted, context lost (Input/output error)\n",
                kmsg=kmsg, latch=(0x0005, addr | 1))


def answer(tool, argv, world):
    if argv in (["fill"], ["tri"]):
        return None
    o = parse(argv)
    if tool != "t30" or o is None:
        return USAGE
    a, h, cmd = o["addr"], o["height"], o["cmd"]
    base = a & ~(SLOT_SIZE - 1)
    end = a + (h // SENTINEL_ROWS + 1) * P.SZ_4K
    nslots = (end - base + SLOT_SIZE - 1) // SLOT_SIZE
    if nslots > 2:
        return dict(rc=1, out=f"{cmd}: failed: Invalid argument\n")
    paddr, code, layout = knob("vm_pde_addr"), knob("vm_pde_size"), knob("vm_pde_layout")
    head = (f"{cmd}: {'source' if cmd == 'copy' else 'destination'} in {nslots} slot"
            f"{'s' if nslots > 1 else ''} of 4 MiB at {base:#010x}, the surface at +{a - base:#08x}\n")
    large = paddr and paddr in (base, base + SLOT_SIZE) and paddr < base + nslots * SLOT_SIZE
    g = None
    if large:
        g = P.geom(code, layout)
        if g is None:
            return dict(rc=1, out=f"{cmd}: failed: Invalid argument\n")
        if (g["order"] == 10 and ("nowarm" in world and code == 5 or "enomem45" in world and code == 4)):
            return dict(rc=1, out=f"{cmd}: failed: Cannot allocate memory\n")
    va0, va1 = a - paddr, a - paddr + h * 256                     # the job's window in the slot
    kmsg = [f"sgxfive: vm_map {paddr:#010x} +0x400000: PDE size code {code} layout {layout} "
            "(debugfs vm_pde_size)"] if large else []
    touched = large and va1 > 0 and va0 < SLOT_SIZE
    if touched:
        rd, size = reading(world, code, layout)
        if cmd == "fill" and "f1hang" in world and code == 2:
            rd = "hang"
        if "recovfail" in world and cmd == "copy" and code == 1 and va0 == 2 * P.page_size(1) - P.SZ_8K:
            rd = "fault"
        if rd in ("fault", "hang"):
            f = fault(rd, paddr + max(va0, 0), world)
            f["out"] = head + f["out"]
            f["kmsg"] = kmsg + f["kmsg"]
            return f
        lo, hi = max(va0, 0), min(va1, SLOT_SIZE)
        toks = P.pages(g, rd, lo, hi, size)
    if "s0fault" in world and not paddr and cmd == "fill":
        f = fault("fault", a, world)
        f["out"] = head + f["out"]
        return f
    out, files = [head, "job: ok\n"], {}
    changed, table_bad = [], False
    n = 64 * h
    if cmd == "copy":
        bad = 0
        if touched:
            if "s0kdiff" in world and code == 0:
                toks = [t if t == "x" else "7:0" for t in toks]
            for i, t in enumerate(toks):
                if t in ("x", "fault", "outside"):
                    first, s, p = 0x00000001, 0, 0
                else:
                    s, p = (int(x) for x in t.split(":"))
                    first = P.tag(s, p, 0)
                fo = 1024 if t not in ("x", "fault", "outside") else 1
                out.append(f"tags: va +{lo + i * P.SZ_4K:#08x}: first {first:#010x} (slab "
                           f"{first >> 24 & 0xf} page {first >> 12 & 0x3ff} dword {first & 0x3ff}), "
                           f"{fo}/1024 follow it, 0/1024 pattern\n")
            bad = n
            if "copychg" in world and code == 2:
                changed = [toks[0]]
            if "tablechg" in world and code == 3 and layout == P.MISALIGN:
                table_bad = True
        elif paddr and va0 < 0 < va1:
            bad = 64 * (va1 // 256)
    else:
        bad = 0
        if touched:
            changed = sorted(set(toks), key=lambda t: tuple(int(x) for x in t.split(":")))
            if "outside" in world and code == 1:
                changed = ["0:1"] + changed
            bad = 64 * ((hi - lo) // 256)
    if bad:
        out.append(f"target: 64x{h} hash 0x0123456789abcdef\n"
                   f"diff: {bad} of {n} pixels, first (0, 0) 0xa1002000 expected 0xa5000000\n"
                   "outside: 0 dwords\n")
        out.append(f"{cmd}: FAIL, {bad} wrong dwords\n" if cmd == "fill" else
                   f"copy: dword 0 (0, 0) = 0xa1002000, expected 0xa5000000\n")
    else:
        out.append(f"target: 64x{h} hash 0x0123456789abcdef\ndiff: 0 of {n} pixels\n"
                   "outside: 0 dwords\n")
        out.append(f"{cmd}: ok\n")
    if not ("nolarge" in world and not paddr and cmd == "copy"):
        files[os.path.join(o["dir"], "vm_large.txt")] = large_text(g, changed, table_bad) \
            if large else "none\n"
    return dict(rc=1 if bad else 0, out="".join(out), files=files, kmsg=kmsg)
