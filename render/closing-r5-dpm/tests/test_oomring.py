#!/usr/bin/env python3
"""test_oomring.py: the own task of stage A3 (asm/oomring.s, bins/oomring.blob), offline.
  1. gen/gen_oomring.py writes exactly asm/oomring.s and bins/oomring.blob again (deterministic) and blobs.json describes them;
  2. the landed Python verifier (tools/fwtask/fwtask.py at the frozen main) accepts it; lint clean; at most 1024 words; no str, no pa or
     sa write, ldr only of CR_TIMER (#81); one continue patch an entry (cont0..cont3); every results-page patch inside the page;
  3. THE RGN4 MODULE'S VERIFIER: the fork's own sgxfive_owntask.c and sgx_fw.c at the rgn4 commit a2788bd86537 (forkpin.PIN, read
     with `git archive` from the fork home /Volumes/linux/linux-sgx, never written), built on the Mac with the landed host shim
     (tools/fwtask/host/own_host.c), accept the blob; controls that must fail: the same task with an ldr of CR_CLKGATESTATUS (#2), and
     with a store through a register no patch set, are refused by the C verifier with the Python verifier's reason, and the landed
     events_m blob is accepted (the build is the verifier, not a stub);
  4. sgx-sim: every pass continues to the closed task of its own slot; a pass with none of the six pa1 bits logs nothing; 48 rungs
     then the lost count.
Without a C compiler or the fork checkout part 3 FAILS (it is the check the decision R5-5 (a) asks for: a skip is not a pass).
"""
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
MAIN = pathlib.Path(os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545"))
os.environ.setdefault("RESGX545_LINUX", "/Volumes/linux/linux-sgx")
sys.path[:0] = [str(MAIN / "tools/fwtask"), str(MAIN / "tools"), str(KP / "gen"), str(KP / "tests")]
import fwtask  # noqa: E402
import forkpin  # noqa: E402
import gen_oomring as G  # noqa: E402

FAIL = []


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


src = (KP / "asm/oomring.s").read_text()
blob = (KP / "bins/oomring.blob").read_bytes()
regs = fwtask.load_regs()
# 1. deterministic
check(G.source() == src, "gen_oomring.source() is asm/oomring.s byte for byte")
check(fwtask.build_blob_text(src, regs) == blob, "asm/oomring.s assembles (landed usse-asm) to bins/oomring.blob byte for byte")
import json  # noqa: E402
meta = json.loads((KP / "bins/blobs.json").read_text())["oomring"]
import hashlib  # noqa: E402
check(meta["sha256"] == hashlib.sha256(blob).hexdigest() and meta["arm"] == "slots=0xf entry=0,1,2,3" and meta["refusal_python"] is None,
      f"blobs.json: sha256 {meta['sha256'][:12]}, arm {meta['arm']}, {meta['insns']} words")
env_sha = re.search(r"OOMRING_SHA=(\w+)", (KP / "run/r5.env").read_text()).group(1)
check(env_sha == meta["sha256"], "run/r5.env pins the same blob the laptop preflight checks")
# 2. the landed Python verifier and the rules
p = fwtask.parse_blob(blob)
kinds = [fwtask.classify(w)[0] for w in p.words]
check(fwtask.refusal(blob, regs) is None and fwtask.verify_blob(blob, regs) == [], "the landed Python verifier accepts it")
check(fwtask.lint(src) == [], "the landed lint has no warning")
check(len(p.words) <= fwtask.MAX_INSNS and len(p.entries) == 4, f"{len(p.words)} words (limit {fwtask.MAX_INSNS}), 4 entries {p.entries}")
check("STR" not in kinds and "MOVPA" not in kinds, "no str word, no pa write")
check(sorted({fwtask.reg_index(w) for w, k in zip(p.words, kinds) if k == "LDR"}) == [81], "the only ldr is #81 (CR_TIMER)")
code = [ln.split(";")[0].strip() for ln in src.splitlines() if ln.strip() and not ln.strip().startswith((";", "@"))]
check(not any(re.match(r"\S+\s+(sa|pa)\d+\s*,", ln) for ln in code), "no instruction writes an sa or pa register (sa8, sa9 are read only)")
check(not any(re.search(r"\b(emit|lock|str)\b", ln) for ln in code), "no emit, lock or str in the source")
conts = sorted(x.kind for x in p.patches if x.kind.startswith("cont"))
res = [x.addend for x in p.patches if x.kind == "res"]
check(conts == ["cont0", "cont1", "cont2", "cont3"] and all(0 <= a < 0x1000 for a in res) and sorted(set(res)) == [0, 0x400, 0x600, 0x800],
      f"continue patches {conts}; results-page bases res+{sorted(set(hex(a) for a in res))}")
# 3. the rgn4 module's verifier, built from the fork at the rgn4 commit
check(forkpin.PIN == "a2788bd86537", f"forkpin pins the rgn4 commit ({forkpin.PIN}: the module 99CD90DA's fork tree)")
d = forkpin.sgxfive_dir()
cc = shutil.which("cc") or shutil.which("gcc")
check(d is not None and cc is not None, f"the fork's sgxfive sources at {forkpin.pin()} ({d}) and a C compiler ({cc})")
if d is not None and cc is not None:
    host = MAIN / "tools/fwtask/host"
    out = pathlib.Path(tempfile.mkdtemp(prefix="own_host_", dir=str(KP / "debug"))) / "own_host"
    flags = [] if "sgx_own_apply" in (d / "sgxfive_owntask.h").read_text() else ["-DHOST_NO_APPLY"]
    r = subprocess.run([cc, "-std=gnu11", "-O1", "-Wall", "-Wextra", *flags, f"-I{host / 'shim'}", f"-I{d}", "-o", str(out),
                        str(host / "own_host.c"), str(d / "sgxfive_owntask.c"), str(d / "sgx_fw.c")], capture_output=True, text=True)
    check(r.returncode == 0, "the host build of the fork's verifier compiles" + (": " + r.stderr[-300:] if r.returncode else ""))
    pl_ = fwtask.preprocess(src.replace("ldr r11, #81, drc0", "ldr r11, #2, drc0", 1))
    bad_ldr = fwtask.pack_blob(fwtask.assemble_text("\n".join(pl_[0])), pl_[2], pl_[1])
    nb = src.replace("        stad [r2,+#0], r10", "        mov r2, r4\n        stad [r2,+#0], r10", 1)
    pnb = fwtask.preprocess(nb)
    bad_base = fwtask.pack_blob(fwtask.assemble_text("\n".join(pnb[0])), pnb[2], pnb[1])
    ev = fwtask.blob_of("events_m")
    blobs = [blob, bad_ldr, bad_base, ev]
    f = out.parent / "blobs.bin"
    f.write_bytes(b"".join(struct.pack("<I", len(b)) + b for b in blobs))
    r = subprocess.run([str(out), "verify", str(f)], capture_output=True, text=True)
    got = [None if ln == "OK" else "parse" if ln == "EINVAL" else ln.removeprefix("EPERM ") for ln in r.stdout.splitlines()]
    py = [fwtask.refusal(b, regs) for b in blobs]
    check(r.returncode == 0 and got[0] is None, f"THE RGN4 VERIFIER (fork {forkpin.pin()}, host build) ACCEPTS oomring.blob ({got[0]!r})")
    check(got[1] is not None and got[1] == py[1], f"control: an ldr of #2 (CR_CLKGATESTATUS) is refused by both ({got[1]!r}, Python {py[1]!r})")
    check(got[2] is not None and got[2] == py[2], f"control: a store through a register no patch set is refused by both ({got[2]!r}, Python {py[2]!r})")
    check(got[3] is None and py[3] is None, "control: the landed events_m blob is accepted by both")
    shutil.rmtree(out.parent)
# 4. the simulator
import simring  # noqa: E402
pg, rs = simring.run_events([(k, k, 0x02000000, 0, 0, 10 + k) for k in range(4)])
check([s for _, s in rs] == [0, 1, 2, 3] and G.decode_ring(pg)["rungs"] == [] and G.decode_ring(pg)["passes"] == [1, 1, 1, 1],
      "sim: a pass with none of the six pa1 bits logs nothing and continues to its own slot's closed task; passes counted")
ev = [(2, 9, 0x00100000, 0x180 + i, 0x100, 100 + i) for i in range(50)]
pg, rs = simring.run_events(ev)
d_ = G.decode_ring(pg)
check(len(d_["rungs"]) == 48 and d_["lost"] == 2 and d_["rungs"][47]["sa8"] == 0x180 + 47 and all(s == 2 for _, s in rs),
      "sim: 48 rungs fill the ring (three base registers, 16 rungs each), then 2 lost; slot 2 continues every time")
bits = [(1 << b) for b in (22, 21, 20, 10, 9, 4)]
pg, _ = simring.run_events([(3, 1, b, 0, 0, 5) for b in bits] + [(3, 1, 1 << 7, 0, 0, 5), (3, 1, 1 << 19, 0, 0, 5)])
check([r["pa1"] for r in G.decode_ring(pg)["rungs"]] == bits, "sim: exactly pa1 bits 22, 21, 20, 10, 9 and 4 are logged (7 and 19 are not)")
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
