# SPDX-License-Identifier: MIT
"""mock/world.py: r9-faults's fake laptop for kit/session.py mock. answer(tool, argv, world) runs the
argv through the REAL tool's source built against libsgxfive's in-process mock (`sgxfive-test
--mock`, debug/libmock, built by tests/run_all.sh from `git archive` of TOOLSRC.sha256's commit,
its source hash checked first): an option the tool refuses is refused here (rc 2), and a job the
library mock rejects prints `job: rejected` here as on the laptop (r8-geo's lesson). tri --depth
writes its ZLS pokes to a scratch file (SGXFIVE_KPOKE), as the laptop's debugfs kpoke takes them.
What the library mock cannot know comes after, from the fake kernel's state only (the knob files
in $FAKE_DBGREAL, as the real job depends on the kernel, never on a case name):

- the hardware's hashes: the 64 x 64 triangle's two colourings (HW_HASH) and the overflowing
  1024 x 768 scene (E761: exact, two hashes), which the library mock draws its own way;
- vm_pte_addr / vm_pte_flags: a knob whose address is the first page of a mapping the job makes
  logs the kernel's `vm_map A +S: PTE flags F` line, and the world's hypotheses end the job;
- alias_skip: buffer 0 left out faults 0x91000 at 0x3000b021 (E745), buffer 9 0x90400 at
  0x32004001 (E457), any other mask draws exactly (H-ONLY09), unless the world says otherwise;
- render_pb_pages 0x23: --mock-pb-pages=0x23, the scene overflows (E761).

Worlds (tokens of FAKE_WORLD; EXPECT gives the driver's and each stage's status):
  model      S9-k2's frozen hypotheses: WO faults every access at the last pixel's page
             (H-WO-ALL, H-LASTROW), CACHED changes nothing, EDMPROT faults client writes only
             (H-EDM-WRITE), WO|EDMPROT faults at the first page (H-OR, H-EDM-FIRST); bif H-ONLY09
  rival      H-WO (reads only) with H-MAPEND, H-CC-STALE, H-EDM-REQ and H-EDM-3D, H-CANCEL; bif
             H-SET (every held-out mask faults in a buffer it leaves out): 9 counted faults of 10
  allfault   every PTE flag faults: no stage stops by its count (#limit = expectfault rows + 1,
             E946's slip designed out): every end control runs
  nopte      the kernel logs no PTE line: the first knob row of xf2 and of tri2 stops it (24)
  rejected   every PTE knob row's job is rejected with a diff line: the kit's runner takes
             `job: rejected` under expectdiff as a failure (E934's design-out), the session stops (4)
  undeclared bif-c0 (mask 0, no expectfault) faults: an unexpected fault stops the session (4)
  hangctl    tri-c-depth (no expectfault) hangs: the session stops at tri2 (4)
  hang       bif-most hangs instead of drawing: a reading (expectfault), counted, 0
  noalias    alias_skip has no effect: bif-c9 draws and has no fault reading: premise (25)
  two110     the held-out masks of 12 to 14 in pairs fault with `SGX recovery failed: -110` and
             the health still draws: the next row that reads ok stops bif (hook_check, 24)
  wedge      bif-1213's fault is followed by a -110 and the first health draw fails, the retry
             draws: strict health stops the session (16)
  wedge2     as wedge, the retry fails too (the second -110 in a row): the runner aborts (5)
"""
import os
import re
import subprocess
import tempfile

EXPECT = {
    "model": (0, {"xf2": 0, "tri2": 0, "bif": 0}),
    "rival": (0, {"xf2": 0, "tri2": 0, "bif": 0}),
    "allfault": (0, {"xf2": 0, "tri2": 0, "bif": 0}),
    "nopte": (0, {"xf2": 24, "tri2": 24, "bif": 0}),
    "rejected": (4, {"xf2": 4}),
    "undeclared": (4, {"xf2": 0, "tri2": 0, "bif": 4}),
    "hangctl": (4, {"xf2": 0, "tri2": 4}),
    "hang": (0, {"xf2": 0, "tri2": 0, "bif": 0}),
    "noalias": (25, {"xf2": 0, "tri2": 0, "bif": 25}),
    "two110": (0, {"xf2": 0, "tri2": 0, "bif": 24}),
    "wedge": (16, {"xf2": 0, "tri2": 0, "bif": 16}),
    "wedge2": (5, {"xf2": 0, "tri2": 0, "bif": 5}),
}

WO, CACHED, EDMPROT, RO = 0x2, 0x8, 0x10, 0x4
SENTINEL = 0xDEADBEEF
PAGE = 0x1000
# the library mock's hash -> the laptop's: the 64 x 64 triangle's first and second colouring
# (r7-rp's health triangle; render/closing-s1 f-12-r1, E745)
HW_HASH = {"0x84752da507b30205": "0x99385a04ee01c585", "0xc3b6810c3fc90075": "0xab267bd98022a81d"}
OVF_HASH = ["0xc9e301d225fe2325", "0xed1bce7108aded25"]   # E761's 1024 x 768 at 0x23 (S1b f-dpm-0)
ISOLATION_KMSG = [   # render/client-jobs/output.txt, the kernel's lines of the tool's isolation
    "sgxfive: BIF fault 0x90020 at 0x3e10000c (PD 0xf4f2000) stalls job 39, recovering",
    "sgxfive: BIF fault 0x90020 at 0x3e001002 (PD 0x6e38000) stalls job 41, recovering",
    "sgxfive: BIF fault 0x80020 at 0x3e200002 (PD 0xf4d9000) stalls job 43, recovering",
]
# gen/make.py's buffer layout (E573's debugfs layout)
BUF = [0x30000000, 0x3000D000, 0x3000E000, 0x3000F000, 0x30010000, 0x30011000, 0x32000000,
       0x32002000, 0x32003000, 0x32004000, 0x32005000, 0x32006000, 0x32007000, 0x3200E000,
       0x3200F000]
R110 = "SGX recovery failed: -110"


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
    """[(first page, bytes, READONLY, the job's access, the page of the last pixel written)] the
    tool maps, in its allocation order (README, "Addresses")."""
    cmd = argv[0] if argv else ""
    h, y = opt(argv, "--height", None), opt(argv, "--y", 0)
    if cmd == "fill":
        w, hh, st = opt(argv, "--width", 64), h or 32, opt(argv, "--stride", 256)
        n = pages_for(st, y + hh)
        last = 0x3E001000 + ((y + hh - 1) * st + w * 4 - 1) // PAGE * PAGE
        return [(0x3E000000, PAGE, False, "read", None), (0x3E001000, n * PAGE, False, "write", last)]
    if cmd == "copy":
        s = pages_for(opt(argv, "--src-stride", 256), opt(argv, "--sy", 0) + (h or 32))
        d = pages_for(opt(argv, "--dst-stride", 256), opt(argv, "--dy", 0) + (h or 32))
        return [(0x3E000000, PAGE, False, "read", None), (0x3E001000, s * PAGE, True, "read", None),
                (0x3E001000 + s * PAGE, d * PAGE, False, "write", None)]
    if cmd == "tri":
        w, th = opt(argv, "--width", 64), h or 64
        mw, mh = opt(argv, "--max-width", w), opt(argv, "--max-height", th)
        fbp = pages_for(mw * 4, mh)
        if "--depth" in argv:
            zp = (w * th * 4 + PAGE - 1) // PAGE + 16
            out = [(0x3E000000, PAGE, False, "read", None), (0x3E001000, zp * PAGE, False, "none", None)]
            nxt = 0x3E001000 + zp * PAGE
            if "--depth-store" in argv:
                out.append((nxt, zp * PAGE, False, "write", None))
                nxt += zp * PAGE
            return out + [(nxt, fbp * PAGE, False, "write", nxt + (fbp - 2) * PAGE)]
        return [(0x3E000000, PAGE, False, "read", None),
                (0x3E001000, fbp * PAGE, False, "write", 0x3E001000 + (fbp - 2) * PAGE)]
    return []


def knob(name, default="0"):
    d = os.environ.get("FAKE_DBGREAL")
    p = os.path.join(d, name) if d else None
    v = open(p).read().strip() if p and os.path.exists(p) else ""
    return int(v or default, 0)


def counter(name, delta=0, reset=None):
    """A count kept in the fake kernel's state ($FAKE_DIR), for the health draws that fail after
    a wedged recovery; 0 without a fake kernel (the tests' kept records)."""
    d = os.environ.get("FAKE_DIR")
    if not d:
        return 0
    p = os.path.join(d, name)
    if reset is not None:
        open(p, "w").write(f"{reset}\n")
        return reset
    v = int(open(p).read()) if os.path.exists(p) else 0
    if delta and v:
        open(p, "w").write(f"{max(0, v + delta)}\n")
    return v


def outcome(flag, access, mp, world):
    """(end, fault page) of a knob row whose PTE took `flag`."""
    start, size, ro, acc, last = mp
    first = start
    if "allfault" in world:
        return "fault", first
    if flag == WO | EDMPROT:
        return ("exact", None) if "rival" in world else ("fault", first)
    if flag & WO:
        if "rival" in world:
            return ("fault", start) if access == "read" else ("exact", None)
        if access == "write":
            return "fault", (last if last is not None else first)
        return "fault", first
    if flag & CACHED:
        return ("diff", None) if "rival" in world else ("exact", None)
    if flag & EDMPROT:
        if "rival" in world:
            # H-EDM-REQ: a transfer's read faults too; H-EDM-3D: only a colour (or fill) target's
            # write, never the ZLS buffers
            return ("fault", first) if access == "read" or last is not None else ("exact", None)
        return ("fault", first) if access == "write" else ("exact", None)
    return "exact", None


def broken(out, w, h, first_want, job):
    """The tool's lines for a target whose every pixel kept SENTINEL (a fault, a rejection) or
    read it (a stale source)."""
    keep = [ln for ln in out.splitlines(True)
            if not ln.startswith(("job:", "target:", "diff:", "fill: ok", "copy: ok", "tri:", "tri ", "depth"))]
    head = [ln for ln in out.splitlines(True) if ln.startswith(("programs", "copy: source", "tri: render context", "depth"))]
    head = [ln for ln in head if not ln.startswith("depth #") and not ln.startswith("depth store #")]
    rest = [ln for ln in keep if ln not in head]
    n = w * h
    return "".join(head) + job + "\n" + \
        f"target: {w}x{h} hash 0x{(n * 0x9E3779B1) & 0xFFFFFFFFFFFFFFFF:016x}\n" + \
        f"diff: {n} of {n} pixels, first (0, 0) 0x{SENTINEL:08x} expected {first_want}\n" + "".join(rest)


def health(argv, world):
    """A bare fill or tri (the health pair, and the knob-free controls): None (the library mock's
    draw follows) unless a wedged recovery left failing draws in the fake kernel's count, which
    this answer uses up one by one."""
    if counter("r9f_wedge"):
        counter("r9f_wedge", -1)
        return dict(rc=1, out="job: failed: job hung, context lost (Connection timed out)\n"
                    "diff: 4096 of 4096 pixels\n", kmsg=[R110])
    return None


def bif(argv, out, err, rc, world):
    """A render under alias_skip (and render_pb_pages)."""
    mask = knob("alias_skip")
    if knob("render_pb_pages", "0x422") == 0x23:
        hs = iter(OVF_HASH * 2)
        out = re.sub(r"^target: (\d+x\d+) hash 0x[0-9a-f]+$", lambda m: f"target: {m[1]} hash {next(hs)}", out, flags=re.M)
        out = re.sub(r"^diff: \d+ of (\d+) pixels.*$", r"diff: 0 of \1 pixels", out, flags=re.M)
        out = re.sub(r"overflowed, \d+ triangle, \d+ background, \d+ other; wrong \d+ inside, \d+ outside, \d+ at edges; \d+ if flipped",
                     "overflowed, 207456 triangle, 578976 background, 0 other; wrong 0 inside, 0 outside, 0 at edges; 141525 if flipped", out)
    if "noalias" in world:
        mask = 0
    fault = None
    if mask & 1:
        fault = "0x91000 at 0x3000b021"
    elif mask & 0x200:
        fault = "0x90400 at 0x32004001"
    elif "rival" in world and bin(mask).count("1") >= 2:
        i = max(b for b in range(15) if mask >> b & 1)
        fault = f"0x91000 at 0x{BUF[i] | 0x21:08x}"
    elif "two110" in world and mask in (0x3000, 0x5000):
        fault = f"0x91000 at 0x{BUF[13 if mask == 0x3000 else 14] | 0x21:08x}"
    elif ("wedge" in world or "wedge2" in world) and mask == 0x3000:
        counter("r9f_wedge", reset=2 if "wedge" in world else 4)
        fault = f"0x91000 at 0x{BUF[13] | 0x21:08x}"
    elif "undeclared" in world and mask == 0 and "--keep-overflow" not in argv:
        fault = "0x91000 at 0x3e000021"
    if "hang" in world and mask == 0x7DFE and "-n" in argv and argv[argv.index("-n") + 1] == "2" \
            and "--keep-overflow" not in argv:
        return dict(rc=1, out="tri: render context for targets up to 64x64\n"
                    "job: failed: job hung, context lost (Connection timed out)\n"
                    "diff: 4096 of 4096 pixels, first (0, 0) 0xdeadbeef expected 0xff203040\n"
                    "tri: FAILED after 0 renders\n", err=err, kmsg=["sgxfive: job 12 hung, recovering"])
    if fault is None:
        return dict(rc=rc, out=out, err=err)
    kmsg = [f"sgxfive: BIF fault {fault} (PD 0x2f402000) stalls job 8646, recovering"]
    if "two110" in world or "wedge" in world or "wedge2" in world:
        kmsg.append(R110)
    head = "tri: render context for targets up to 64x64\n"
    return dict(rc=1, out=head + "job: failed: job faulted, context lost (Input/output error)\n"
                "target: 64x64 hash 0xe4364b426cdce325\n"
                "diff: 4096 of 4096 pixels, first (0, 0) 0xdeadbeef expected 0xff203040\n"
                "outside: 0 dwords\nlayout: fb 0x3e001000\n"
                "sgxfive-test: render: job faulted, context lost (Input/output error)\n"
                "tri: FAILED after 0 renders\n", err=err, kmsg=kmsg)


def answer(tool, argv, world):
    if tool != "t4":
        return None
    h = health(argv, world) if argv in (["fill"], ["tri"]) else None
    if h:
        return h
    pre = ["--mock-pb-pages=0x23"] if argv[:1] == ["tri"] and knob("render_pb_pages", "0x422") == 0x23 else []
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, SGXFIVE_KPOKE=os.path.join(td, "kpoke"))
        open(env["SGXFIVE_KPOKE"], "w").close()
        r = subprocess.run([libmock(), "--mock", *pre, *argv], capture_output=True, text=True,
                           timeout=60, env=env, cwd=td)
    out, err, rc = r.stdout, r.stderr, r.returncode
    for a, b in HW_HASH.items():
        out = out.replace(f" hash {a}", f" hash {b}")
    # the ZLS store the library mock does not model: 0x0017100c stores 8 tiles of 512 dwords at
    # 64 x 64 (doc/specs/3d.md section 11.6, E465), every one unlike the fill
    out = re.sub(r"^(depth store #1: \d+ dwords, )0 changed, 1 distinct", r"\g<1>4096 changed, 2 distinct", out, flags=re.M)
    if rc == 2 or not argv:
        return dict(rc=rc, out=out, err=err)
    if argv[0] == "isolation":
        return dict(rc=rc, out=out, err=err, kmsg=list(ISOLATION_KMSG))
    if argv[0] == "tri" and "-n" in argv:
        return bif(argv, out, err, rc, world)
    m = re.search(r"^target: (\d+)x(\d+) hash", out, re.M)
    w, h = (int(m[1]), int(m[2])) if m else (64, 32)
    first = re.search(r"^diff: .*expected (0x[0-9a-f]+)", out, re.M)
    want = first[1] if first else "0xff336699"
    if "hangctl" in world and "--depth" in argv and not knob("vm_pte_flags"):
        return dict(rc=1, out=broken(out, w, h, want, "job: failed: job hung, context lost (Connection timed out)"),
                    err=err, kmsg=["sgxfive: job 12 hung, recovering"])
    addr, flags = knob("vm_pte_addr"), knob("vm_pte_flags")
    hit = [mp for mp in maps(argv) if addr and flags and mp[0] == addr]
    if not hit:
        return dict(rc=rc, out=out, err=err)
    start, size, ro, access, last = hit[0]
    kmsg = [] if "nopte" in world else \
        [f"sgxfive: vm_map 0x{start:08x} +0x{size:x}: PTE flags 0x{(RO if ro else 0) | flags:x} (debugfs vm_pte_flags)"]
    if "rejected" in world:
        return dict(rc=1, out=broken(out, w, h, want, "job: rejected (Invalid argument)"), err=err, kmsg=kmsg)
    end, page = outcome(flags, access, hit[0], world)
    if end == "exact":
        return dict(rc=rc, out=out, err=err, kmsg=kmsg)
    if end == "diff":
        return dict(rc=1, out=broken(out, w, h, want, "job: ok"), err=err, kmsg=kmsg)
    stat = {"write": "0x80020", "read": "0x80010", "none": "0x80010"}[access]
    if flags & EDMPROT:
        stat = "0xa0020" if access == "write" else "0xa0010"
    return dict(rc=1, out=broken(out, w, h, want, "job: failed: job faulted, context lost (Input/output error)"),
                err=err, kmsg=kmsg + [f"sgxfive: BIF fault {stat} at 0x{page | 0x1f1:08x} (PD 0xf4d9000) stalls job 7, recovering"])
