# SPDX-License-Identifier: MIT
"""mock/world.py: r8-k2's fake laptop for kit/session.py mock. answer(tool, argv, world) runs the
argv through the REAL tool's source built against libsgxfive's in-process mock (`sgxfive-test
--mock`, debug/libmock, built by tests/run_all.sh from `git archive` of TOOLSRC.sha256's commit,
its source hash checked first): an option the tool refuses is refused here (rc 2), and a job the
library mock rejects prints `job: rejected` here as on the laptop (r8-geo's lesson). What the
library mock cannot know comes after:

- the hardware's hash of the 64 x 64 triangle (HW_HASH: the library mock rasterises its own way;
  fill and copy hash the same on both, render/closing-r7-rp and texture/copy-addresses);
- the fork's PTE knobs: the fake kernel's vm_pte_addr and vm_pte_flags (the mock's debugfs files
  in $FAKE_DBGREAL, as the real tool's job depends on the kernel's state, never on a case name).
  A knob whose address is the first page of a mapping the job makes logs the kernel's
  `vm_map A +S: PTE flags F` line, and the world's hypotheses decide the job's end:
    model      H-WO (a read of a WO page faults, a write passes), H-CC-NEW, H-EDM-NONE
    edmclient  as model, EDMPROT faults every client access (H-EDM-CLIENT)
    rival      H-WO-NONE, H-CC-STALE (the copy reads SENTINEL, the triangle draws nothing),
               H-EDM-NONE
    allfault   every flag faults: each stage stops at its 4th fault with rows left (24)
    nopte      the kernel logs no PTE line: the first knob row of each stage stops it (24)
    rejected   every knob row's job is rejected with a diff line: hook_check stops each (24)
    ctlfault   the knob-free copy control faults: not a reading, the session stops (4)
    ctlnohash  the knob-free triangle prints no hash: the premise stops at tri-c (25)
    hang       WO on the triangle's GENERAL page hangs instead: a reading (expectfault), 0
  isolation prints its checks and the kernel's three BIF fault lines (render/client-jobs);
  rono: no fault at all and its read-only check FAILs: an unexplained failure stops it (4).

EXPECT: {world: (the driver's status, {stage: the runner's status})}."""
import os
import re
import subprocess

EXPECT = {
    "model": (0, {"xf": 0, "tri": 0}),
    "edmclient": (0, {"xf": 0, "tri": 0}),
    "rival": (0, {"xf": 0, "tri": 0}),
    "allfault": (0, {"xf": 24, "tri": 24}),
    "nopte": (0, {"xf": 24, "tri": 24}),
    "rejected": (0, {"xf": 24, "tri": 24}),
    "ctlfault": (4, {"xf": 4}),
    "ctlnohash": (25, {"xf": 0, "tri": 25}),
    "hang": (0, {"xf": 0, "tri": 0}),
    "rono": (4, {"xf": 4}),
}

WO, CACHED, EDMPROT, RO = 0x2, 0x8, 0x10, 0x4
SENTINEL = 0xDEADBEEF
PAGE = 0x1000
HW_HASH = {"0x84752da507b30205": "0x99385a04ee01c585"}    # tri 64 x 64: library mock -> laptop
ISOLATION_KMSG = [   # render/client-jobs/output.txt, the kernel's lines of the tool's isolation
    "sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 39, recovering",
    "sgxfive: BIF fault 0x90020 at 0x3e001002 (PD 0x6e38000) stalls job 41, recovering",
    "sgxfive: BIF fault 0x80020 at 0x3e200002 (PD 0xf4d9000) stalls job 43, recovering",
]


def libmock():
    """debug/libmock/sgxfive-test of the session this world belongs to (the mock's copy sits in
    debug/mock.*/tree, the session itself one level up)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for up in range(5):
        d = os.path.normpath(os.path.join(here, *([".."] * up)))
        p = os.path.join(d, "debug", "libmock", "sgxfive-test")
        if os.path.exists(p):
            return p
    raise RuntimeError("debug/libmock/sgxfive-test is not built (bash tests/run_all.sh builds it)")


def opt(a, name, default):
    return int(a[a.index(name) + 1], 0) if name in a and a.index(name) + 1 < len(a) else default


def pages_for(stride, rows):
    return (stride * rows + PAGE - 1) // PAGE + 1


def maps(argv):
    """[(first page, bytes, READONLY, the job's access)] the tool maps for its surfaces, in its
    allocation order (README, "Addresses"): the transfer's stream page or the render's GENERAL
    page first (0x3e000000, after their pages in the PDS and USSE heaps), then the surfaces."""
    cmd = argv[0] if argv else ""
    h, y = opt(argv, "--height", None), opt(argv, "--y", 0)
    if cmd == "fill":
        n = pages_for(opt(argv, "--stride", 256), y + (h or 32))
        return [(0x3E000000, PAGE, False, "read"), (0x3E001000, n * PAGE, False, "write")]
    if cmd == "copy":
        s = pages_for(opt(argv, "--src-stride", 256), opt(argv, "--sy", 0) + (h or 32))
        d = pages_for(opt(argv, "--dst-stride", 256), opt(argv, "--dy", 0) + (h or 32))
        return [(0x3E000000, PAGE, False, "read"), (0x3E001000, s * PAGE, True, "read"),
                (0x3E001000 + s * PAGE, d * PAGE, False, "write")]
    if cmd == "tri":
        w, th = opt(argv, "--width", 64), h or 64
        mw, mh = opt(argv, "--max-width", w), opt(argv, "--max-height", th)
        return [(0x3E000000, PAGE, False, "read"),
                (0x3E001000, pages_for(mw * 4, mh) * PAGE, False, "write")]
    return []


def knobs():
    d = os.environ.get("FAKE_DBGREAL")
    vals = {}
    for k in ("vm_pte_addr", "vm_pte_flags"):
        p = os.path.join(d, k) if d else None
        vals[k] = int(open(p).read().strip() or "0", 0) if p and os.path.exists(p) else 0
    return vals["vm_pte_addr"], vals["vm_pte_flags"]


def outcome(flag, access, world):
    if "allfault" in world:
        return "fault"
    if flag & WO:
        if "rival" in world:
            return "exact"
        if "hang" in world and access == "read":
            return "hang"
        return "fault" if access == "read" else "exact"
    if flag & CACHED:
        return "diff" if "rival" in world else "exact"
    if flag & EDMPROT:
        return "fault" if "edmclient" in world else "exact"
    return "exact"


def broken(out, w, h, first_want, job):
    """The tool's lines for a target whose every pixel kept SENTINEL (a fault, a rejection) or
    read it (a stale source)."""
    keep = [ln for ln in out.splitlines(True)
            if not ln.startswith(("job:", "target:", "diff:", "fill: ok", "copy: ok", "tri:", "tri "))]
    head = [ln for ln in keep if ln.startswith(("programs", "copy: source"))]
    rest = [ln for ln in keep if ln not in head]
    n = w * h
    return "".join(head) + job + "\n" + \
        f"target: {w}x{h} hash 0x{(n * 0x9E3779B1) & 0xFFFFFFFFFFFFFFFF:016x}\n" + \
        f"diff: {n} of {n} pixels, first (0, 0) 0x{SENTINEL:08x} expected {first_want}\n" + "".join(rest)


def answer(tool, argv, world):
    if tool != "t4":
        return None
    r = subprocess.run([libmock(), "--mock", *argv], capture_output=True, text=True, timeout=60)
    out, err, rc = r.stdout, r.stderr, r.returncode
    for a, b in HW_HASH.items():
        out = out.replace(f" hash {a}", f" hash {b}")
    if rc == 2 or not argv:
        return dict(rc=rc, out=out, err=err)
    if argv[0] == "isolation":
        if "rono" in world:
            out = out.replace("PASS read-only-faults", "FAIL read-only-faults")
            return dict(rc=1, out=out, err=err)
        return dict(rc=rc, out=out, err=err, kmsg=list(ISOLATION_KMSG))
    m = re.search(r"^target: (\d+)x(\d+) hash", out, re.M)
    w, h = (int(m[1]), int(m[2])) if m else (64, 32)
    first = re.search(r"^diff: .*expected (0x[0-9a-f]+)", out, re.M)
    want = first[1] if first else "0xff336699"
    addr, flags = knobs()
    hit = [mp for mp in maps(argv) if addr and flags and mp[0] == addr]
    if not hit:
        if "ctlfault" in world and argv[0] == "copy":
            return dict(rc=1, out=broken(out, w, h, want, "job: failed: job faulted, context lost (Input/output error)"),
                        err=err, kmsg=["sgxfive: BIF fault 0x90020 at 0x3e004002 (PD 0x6e38000) stalls job 9, recovering"])
        if "ctlnohash" in world and argv[0] == "tri":
            out = "".join(ln for ln in out.splitlines(True) if not ln.startswith("target:"))
        return dict(rc=rc, out=out, err=err)
    start, size, ro, access = hit[0]
    kmsg = [] if "nopte" in world else \
        [f"sgxfive: vm_map 0x{start:08x} +0x{size:x}: PTE flags 0x{(RO if ro else 0) | flags:x} (debugfs vm_pte_flags)"]
    if "rejected" in world:
        return dict(rc=1, out=broken(out, w, h, want, "job: rejected (Invalid argument)"), err=err, kmsg=kmsg)
    end = outcome(flags, access, world)
    if end == "exact":
        return dict(rc=rc, out=out, err=err, kmsg=kmsg)
    if end == "diff":
        return dict(rc=1, out=broken(out, w, h, want, "job: ok"), err=err, kmsg=kmsg)
    if end == "hang":
        return dict(rc=1, out=broken(out, w, h, want, "job: failed: job hung, context lost (Connection timed out)"),
                    err=err, kmsg=kmsg + ["sgxfive: job 12 hung, recovering"])
    stat = "0x80020" if access == "write" else "0x80010"
    return dict(rc=1, out=broken(out, w, h, want, "job: failed: job faulted, context lost (Input/output error)"),
                err=err, kmsg=kmsg + [f"sgxfive: BIF fault {stat} at 0x{start | 2:08x} (PD 0xf4d9000) stalls job 7, recovering"])
