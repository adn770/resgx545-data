#!/usr/bin/env python3
"""mock_all.py: every job command of the R6-dpm tables against the rgn4 tool's in-process mock (tests/build_mock_tool.sh: resgx545
4623753, sgxfive-test.c sha256 703cbcea..., the source of the laptop's ~/sgxfive-test-rgn4; the pin of R4-render4x).  Local, no laptop.
Per command, split as the runner's `eval set --` splits it ($W a temporary directory, $S bins/):
  1. the options parse (no rc 2, no usage, no "bad option");
  2. the tool ECHOES the row's scene: a probe row "probe p1139-green: tri WxH (1500 vertices)" with the row's size (and " (N
     coordinates)" exactly when the row has --vtx-coords N: r-v; the new sizes 2048x1024, 1024x2048 and 1536x1536 are accepted, so no
     spare size is used); a tri row "targets up
     to 4096x4096" and, for a moved scene, "render 1 moved by DX,DY" (the argv twin seen from the tool's side);
  3. with the row's buffer (--mock-pb-pages = P, the frozen model's thr0 + 0x22 for a derived row, 0x100 for an E: cell) the job still parses and runs to the mock's
     end; --dump-render and --words read the debugfs and are dropped for the mock
     ("--words: No such file or directory" there);
  4. the health commands `tri` and `fill` draw exactly in the mock.
"""
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KP / "gen"))
import r6plan as P  # noqa: E402

TOOL = KP / "debug/tool4623753/userspace/libsgxfive/build/sgxfive-test"
if not TOOL.exists():
    subprocess.run(["bash", str(KP / "tests/build_mock_tool.sh")], check=True, capture_output=True)
bad = n = 0


def run(args, extra=()):
    r = subprocess.run([str(TOOL), "--mock", *extra, *args], capture_output=True, text=True, timeout=600, cwd=str(KP / "debug"))
    return r.returncode, r.stdout + r.stderr


def parsed(rc, txt):
    return rc != 2 and "usage" not in txt.lower() and "bad option" not in txt


w = tempfile.mkdtemp(prefix="r6-mock-tool-", dir=str(KP / "debug"))
os.makedirs(w + "/words", exist_ok=True)
for st, rows in P.tables().items():
    for r in rows:
        n += 1
        a = shlex.split(re.sub(r'--(dump-render "\$W/dump"|words "\$W/words") ', "", r["cmd"]).replace("$W", w).replace("$S", str(KP / "bins")))
        t0 = P.thr0_of(r)
        Pv = (t0 + P.D_OFF) if t0 is not None else 0x100
        rc, txt = run(a, [f"--mock-pb-pages=0x{Pv:x}"])
        ok = parsed(rc, txt)
        wh = P.target_of(r["cmd"])
        if a[0] == "probe":
            N = P.coords_of(r["cmd"])
            ok &= f"probe p1139-green: tri {wh[0]}x{wh[1]} (1500 vertices){f' ({N} coordinates)' if N else ''}, " in txt
        else:
            ok &= "targets up to 4096x4096" in txt and ("job: ok" in txt or "overflowed" in txt)
            mv = re.search(r"--move 1:(\d+),(\d+)", r["cmd"])
            if mv:
                ok &= f"render 1 moved by {mv.group(1)},{mv.group(2)}" in txt
        if ok:
            print(f"ok   {st}/{r['name']}: parsed, scene echoed, runs at pb 0x{Pv:x}")
        else:
            bad += 1
            print(f"FAIL {st}/{r['name']}: rc {rc}: {txt.strip().splitlines()[-1][:140] if txt.strip() else ''}")
for a, want in ((["tri"], "diff: 0 of 4096"), (["fill"], "diff: 0 of 2048")):
    n += 1
    rc, txt = run(a)
    if rc == 0 and want in txt:
        print(f"ok   health {a[0]}: draws exactly in the mock")
    else:
        bad += 1
        print(f"FAIL health {a[0]}: rc {rc}")
print(f"{n - bad} of {n} commands accepted by the rgn4 tool's mock")
sys.exit(1 if bad else 0)
