#!/usr/bin/env python3
"""test_oomring.py: the own task of s-k (set B), asm/oomring2.s and bins/oomring2.blob (gen/gen_oomring2.py: R5-dpm's oomring plus ldr of
0x0724 and 0x072c in each stub, stored as each rung's words 6 and 7).
  1. gen_oomring2 writes exactly asm/oomring2.s and bins/oomring2.blob again; blobs.json and run/r7.env pin the same sha256; the body is
     R6-dpm's refused oomring2.s byte for byte but for its header line; asm/oomring.s is R5-dpm's, unchanged;
  2. the landed Python verifier at main 1c64f3a (round 7's list, regs.toml with 0x0724 and 0x072c for ldr) ACCEPTS it; lint clean; no str,
     no pa or sa write; ldr only of #81, #457, #459; four continue patches; results-page bases inside the page;
  3. the OLD list REFUSES it: regs.toml before 7d0ee7f (`git show 7d0ee7f^`) with "ldr of a register not on the list";
  4. THE MODULES' VERIFIERS (host builds of the fork's sgxfive_owntask.c and sgx_fw.c with the landed tools/fwtask/host/own_host.c):
     at 664fd0d0 (module 37EC97AB, set B) oomring2 is ACCEPTED; at 3f0b3e74 (module 41E2F5C7, loaded now) it is REFUSED with the
     Python verifier's reason; control: an ldr of #2 (CR_CLKGATESTATUS) is refused by both builds, events_m accepted;
     the fork's ldr list at 664fd0d0 is 7, 8, 81, 457, 459, 517, 670 and at 3f0b3e74 7, 8, 81, 517, 670;
  5. sgx-sim: every pass continues to its own slot's closed task; a rung holds [slot + 1, pa0, pa1, sa8, sa9, CR_TIMER, 0x0724, 0x072c]
     as the bus gives them; 48 rungs then the lost count; run/r7read.py decodes the ring as the sim wrote it.
Without a C compiler or the fork checkout part 4 FAILS (a skip is not a pass).
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import tomllib

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
MAIN = pathlib.Path(os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545"))
os.environ.setdefault("RESGX545_LINUX", "/Volumes/linux/linux-sgx")
sys.path[:0] = [str(MAIN / "tools/fwtask"), str(MAIN / "tools"), str(KP / "gen"), str(KP / "tests"), str(KP / "run")]
import fwtask  # noqa: E402
import forkpin  # noqa: E402
import gen_oomring as G  # noqa: E402
import gen_oomring2 as G2  # noqa: E402
import r7read as R  # noqa: E402

FAIL = []


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


src = (KP / "asm/oomring2.s").read_text()
blob = (KP / "bins/oomring2.blob").read_bytes()
regs = fwtask.load_regs()
sha = hashlib.sha256(blob).hexdigest()
# 1. deterministic, pinned
check(G2.source() == src, "gen_oomring2.source() is asm/oomring2.s byte for byte")
check(fwtask.build_blob_text(src, regs) == blob, "asm/oomring2.s assembles (landed usse-asm) to bins/oomring2.blob byte for byte")
meta = json.loads((KP / "bins/blobs.json").read_text())["oomring2"]
env_sha = re.search(r"OOMRING2_SHA=(\w+)", (KP / "run/r7.env").read_text()).group(1)
check(meta["sha256"] == sha == env_sha and meta["arm"] == "slots=0xf entry=0,1,2,3" and meta["refusal_python"] is None,
      f"blobs.json and run/r7.env pin the blob {sha[:12]}, arm {meta['arm']}, {meta['insns']} words")
r6 = KP.parent.parent / "closing6/r6-dpm/asm/oomring2.s"
check(r6.exists() and r6.read_text().splitlines()[2:] == src.splitlines()[2:] and r6.read_text().splitlines()[0] == src.splitlines()[0],
      "oomring2.s is R6-dpm's (refused then) but for its header line")
check(G.source() == (KP / "asm/oomring.s").read_text(), "asm/oomring.s is R5-dpm's gen_oomring.source(), unchanged")
# 2. the landed verifier (round 7's list)
p = fwtask.parse_blob(blob)
kinds = [fwtask.classify(w)[0] for w in p.words]
check(fwtask.refusal(blob, regs) is None and fwtask.verify_blob(blob, regs) == [], "the landed Python verifier (main 1c64f3a) ACCEPTS oomring2")
check(fwtask.lint(src) == [], "the landed lint has no warning")
check(len(p.words) <= fwtask.MAX_INSNS and len(p.entries) == 4, f"{len(p.words)} words (limit {fwtask.MAX_INSNS}), 4 entries {p.entries}")
check("STR" not in kinds and "MOVPA" not in kinds, "no str word, no pa write")
ldrs = sorted({fwtask.reg_index(w) for w, k in zip(p.words, kinds) if k == "LDR"})
check(ldrs == [81, 457, 459], f"ldr only of {ldrs}: CR_TIMER, 0x0724, 0x072c")
code = [ln.split(";")[0].strip() for ln in src.splitlines() if ln.strip() and not ln.strip().startswith((";", "@"))]
check(not any(re.match(r"\S+\s+(sa|pa)\d+\s*,", ln) for ln in code), "no instruction writes an sa or pa register")
conts = sorted(x.kind for x in p.patches if x.kind.startswith("cont"))
res = [x.addend for x in p.patches if x.kind == "res"]
check(conts == ["cont0", "cont1", "cont2", "cont3"] and all(0 <= a < 0x1000 for a in res), f"continue patches {conts}; results-page bases in the page")
# 3. the OLD list
old = subprocess.run(["git", "-C", str(MAIN), "show", "7d0ee7f^:tools/fwtask/regs.toml"], capture_output=True, text=True).stdout
oldregs = fwtask.Regs(tomllib.loads(old))
check(fwtask.refusal(blob, oldregs) == "ldr of a register not on the list",
      f"the OLD list (regs.toml before 7d0ee7f) REFUSES oomring2: {fwtask.refusal(blob, oldregs)!r}")
check(fwtask.refusal(fwtask.build_blob_text(G.source(), regs), oldregs) is None, "control: the OLD list accepts R5's oomring (the ldr are the only refusal)")


# 4. the modules' verifiers
def asm(text):
    pp = fwtask.preprocess(text)
    return fwtask.pack_blob(fwtask.assemble_text("\n".join(pp[0])), pp[2], pp[1])


bad_ldr = asm(src.replace("ldr r11, #81, drc0", "ldr r11, #2, drc0", 1))
ev = fwtask.blob_of("events_m")
cc = shutil.which("cc") or shutil.which("gcc")
host = MAIN / "tools/fwtask/host"
for pin_, want_ok, lst in (("664fd0d00765", True, "{ 7, 8, 81, 457, 459, 517, 670 }"), ("3f0b3e74b51b", False, "{ 7, 8, 81, 517, 670 }")):
    os.environ["RESGX545_FORK_PIN"] = pin_
    d = forkpin.sgxfive_dir()
    check(d is not None and cc is not None, f"the fork's sgxfive sources at {pin_} ({d}) and a C compiler ({cc})")
    if d is None or cc is None:
        continue
    check(f"sgx_own_ldr_regs[] __maybe_unused = {lst};" in (d / "sgx_own_regs.h").read_text(), f"fork {pin_}: ldr list {lst}")
    out = pathlib.Path(tempfile.mkdtemp(prefix="own_host_", dir=str(KP / "debug"))) / "own_host"
    flags = [] if "sgx_own_apply" in (d / "sgxfive_owntask.h").read_text() else ["-DHOST_NO_APPLY"]
    r = subprocess.run([cc, "-std=gnu11", "-O1", "-Wall", "-Wextra", *flags, f"-I{host / 'shim'}", f"-I{d}", "-o", str(out),
                        str(host / "own_host.c"), str(d / "sgxfive_owntask.c"), str(d / "sgx_fw.c")], capture_output=True, text=True)
    check(r.returncode == 0, f"fork {pin_}: the host build of the verifier compiles" + (": " + r.stderr[-300:] if r.returncode else ""))
    blobs = [blob, bad_ldr, ev]
    f = out.parent / "blobs.bin"
    f.write_bytes(b"".join(struct.pack("<I", len(b)) + b for b in blobs))
    r = subprocess.run([str(out), "verify", str(f)], capture_output=True, text=True)
    got = [None if ln == "OK" else "parse" if ln == "EINVAL" else ln.removeprefix("EPERM ") for ln in r.stdout.splitlines()]
    if want_ok:
        check(r.returncode == 0 and got[0] is None, f"THE SET B MODULE'S VERIFIER (fork {pin_}, 37EC97AB) ACCEPTS oomring2 ({got[0]!r})")
    else:
        check(got[0] == "ldr of a register not on the list" == fwtask.refusal(blob, oldregs),
              f"the loaded module's verifier (fork {pin_}, 41E2F5C7) REFUSES oomring2 ({got[0]!r}): s-k waits for the boot")
    check(got[1] is not None and got[1] == fwtask.refusal(bad_ldr, regs), f"fork {pin_}: control: an ldr of #2 refused by both ({got[1]!r})")
    check(got[2] is None, f"fork {pin_}: control: the landed events_m blob accepted")
    shutil.rmtree(out.parent)
os.environ.pop("RESGX545_FORK_PIN", None)
# 5. the simulator
import simring  # noqa: E402
pg, rs = simring.run_events([(k, k, 0x02000000, 0, 0, 10 + k, 0, 0) for k in range(4)])
d_ = R.decode_ring(pg)
check([s for _, s in rs] == [0, 1, 2, 3] and d_["rungs"] == [] and d_["passes"] == [1, 1, 1, 1],
      "sim: a pass with none of the six pa1 bits logs nothing and continues to its own slot's closed task")
pg, rs = simring.run_events([(2, 3, 0x03200000, 0x180, 0x101, 77, 0x00e300e3, 0x00030003)])
r0 = R.decode_ring(pg)["rungs"][0]
check(r0 == dict(slot=2, pa0=3, pa1=0x03200000, sa8=0x180, sa9=0x101, timer=77, x724=0x00e300e3, x72c=0x00030003) and rs[0][1] == 2,
      "sim: a rung holds slot + 1, pa0, pa1, sa8, sa9, CR_TIMER, 0x0724 and 0x072c as the bus gives them (r7read.decode_ring)")
ev_ = [(2, 9, 0x00100000, 0x180 + i, 0x100, 100 + i, i + 1, 1) for i in range(50)]
pg, rs = simring.run_events(ev_)
d_ = R.decode_ring(pg)
check(len(d_["rungs"]) == 48 and d_["lost"] == 2 and d_["rungs"][47]["x724"] == 48 and all(s == 2 for _, s in rs),
      "sim: 48 rungs fill the ring, then 2 lost; slot 2 continues every time")
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
