#!/usr/bin/env python3
"""Run every job command of every R3 table against the landed tool's in-process mock (local, no laptop).

An option the tool does not know, a bad value, a size the mock refuses or a missing staged program shows up as rc 2 or a
usage message.  The mock cannot reproduce overflows, faults or the debugfs knobs (render_pb_pages): those jobs are only
checked for option acceptance.  Also reports the sizes the mock accepts (U1's non-library sizes run only if it does).
  python3 tests/mock_all.py [STAGE...]
Exit status 0 only if every command is accepted.
"""
import sys
sys.dont_write_bytecode = True
import os, pathlib, re, shlex, subprocess, tempfile  # noqa: E401,E402

R3 = pathlib.Path(__file__).resolve().parent.parent
os.makedirs(R3 / "debug/tmp", exist_ok=True)
tempfile.tempdir = str(R3 / "debug/tmp")                 # scratch files stay under r3-geo
TOOL = pathlib.Path(os.environ.get("TOOL_SRC", pathlib.Path.home() / "src/resgx545")) / "userspace/libsgxfive/build/sgxfive-test"
ENV = dict(os.environ)
stages = sys.argv[1:] or [p.stem for p in sorted((R3 / "tables").glob("*.txt"))]
bad = 0
out = R3 / "out" / "mock"
out.mkdir(parents=True, exist_ok=True)
for st in stages:
    n = ok = 0
    for line in (R3 / "tables" / f"{st}.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, sset, risk, P, knobs, rt, args = line.split("|", 6)
        with tempfile.TemporaryDirectory() as w:
            for d in ("dump", "words", "depth", "kept"):
                os.mkdir(f"{w}/{d}")
            a = args.replace("$W", w).replace("$S", str(R3 / "bins"))
            argv = [str(TOOL), "--mock"] + shlex.split(a)
            if re.fullmatch(r"0x[0-9a-f]+", P) and 0x23 <= int(P, 16) <= 0x422:
                argv.insert(2, f"--mock-pb-pages={int(P, 16)}")
            try:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=300, env=ENV)
                rc, txt = r.returncode, r.stdout + r.stderr
                if rc == 1 and re.search(r"(--words|render_param|render_tadata|--depth-dump): No such file", txt):
                    # the mock has no debugfs: retry without the debugfs-backed options, to check the rest
                    strip = shlex.split(re.sub(r'--words \S+|--dump-each|--dump-render \S+|--regs \S+', "", a))
                    r2 = subprocess.run([str(TOOL), "--mock"] + strip, capture_output=True, text=True, timeout=300, env=ENV)
                    rc, txt = r2.returncode, "(retried without debugfs options)\n" + r2.stdout + r2.stderr
            except subprocess.TimeoutExpired:
                rc, txt = 124, "timeout"
        (out / f"{name}.txt").write_text(txt[:20000])
        n += 1
        usage = rc == 2 or "usage" in txt.lower() or "bad option" in txt or ("sgxfive-test: " in txt and rc not in (0, 3))
        if usage or rc == 124:
            bad += 1
            tail = txt.strip().splitlines()[-1][:150] if txt.strip() else ""
            print(f"FAIL {st}/{name}: rc {rc}: {tail}")
        else:
            ok += 1
    print(f"{st}: {ok} of {n} commands accepted by the mock")
sys.exit(1 if bad else 0)
