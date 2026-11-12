#!/usr/bin/env python3
"""test_sim_q291.py: the plan's sim check of pix_posstore (exp-pixel-r7.md 1.2, E898) as a session
test.  Copies debug-src/simcheck (the plan's harness closing7/a/q291/simcheck, after r6-pixel's
debug-src/simcheck; sgx-sim and usse-isa of the resgx545 tree by path) to debug/simcheck-q291,
builds it offline with CARGO_TARGET_DIR=debug/target-q291 and runs it on the session's
bins/pix_posstore.bin over the 2048 pixels of a 64 x 32 area: the output must equal the plan's
simcheck.out byte for byte (its pinned sha256; 2048 pixels, 0 failures); a doctored program
(dword 1 stores pa1) must fail.  No cargo: prints the reason and exits 0 (skipped).  ok / FAIL lines, exit 0 or 1."""
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
# sha256 of the plan's closing7/a/q291/simcheck.out (its SHA256.txt; E898: re-run byte-identical)
PLAN_OUT_SHA = "28f305f3436c4ded9d6900d1f5afbf523242d9656af49709a850938e0cb8bb97"
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def main():
    cargo = shutil.which("cargo") or (os.path.expanduser("~/.cargo/bin/cargo")
                                      if os.path.exists(os.path.expanduser("~/.cargo/bin/cargo"))
                                      else None)
    if not cargo:
        print("skip test_sim_q291: cargo is not installed (the sim check needs a Rust toolchain)")
        return 0
    src, dst = KP / "debug-src/simcheck", KP / "debug/simcheck-q291"
    for f in ("Cargo.toml", "Cargo.lock", "src/main.rs"):
        (dst / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src / f, dst / f)
    env = dict(os.environ, CARGO_TARGET_DIR=str(KP / "debug/target-q291"))
    r = subprocess.run([cargo, "build", "--offline", "--quiet", "--manifest-path",
                        str(dst / "Cargo.toml")], env=env, capture_output=True, text=True)
    check("the plan's harness builds offline against the resgx545 tree's sgx-sim", r.returncode == 0,
          r.stderr[-400:])
    if r.returncode:
        return 1
    exe = KP / "debug/target-q291/debug/posstore-simcheck"
    prog = KP / "bins/pix_posstore.bin"
    p = subprocess.run([str(exe), str(prog), "64", "32"], capture_output=True, text=True)
    got = hashlib.sha256(p.stdout.encode()).hexdigest()
    check("pix_posstore in sgx-sim: 2048 of 2048 pixels store (pa0, pa0, pa1, lane) at 16 x slot, "
          "o0 = pa0; output byte-identical to the plan's (sha256 28f305f3...)",
          p.returncode == 0 and got == PLAN_OUT_SHA,
          p.stdout.splitlines()[-1] if p.stdout else p.stderr[-200:])
    words = bytearray(prog.read_bytes())
    words[9 * 8:10 * 8] = words[11 * 8:12 * 8]          # dword 1 stores pa1, not pa0
    bad = KP / "debug/simcheck-q291/doctored.bin"
    bad.write_bytes(bytes(words))
    q = subprocess.run([str(exe), str(bad), "64", "32"], capture_output=True, text=True)
    last = q.stdout.splitlines()[-1] if q.stdout else ""
    check("a doctored program (dword 1 = pa1) fails the same check", q.returncode == 1 and
          "0 failures" not in last, last)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
