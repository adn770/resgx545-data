#!/usr/bin/env python3
"""Run every job command of every table against the landed tool's in-process mock (local, no laptop).

An option the tool does not know, a bad value or a missing staged program shows up as rc 2 or a usage
message.  The mock cannot reproduce overflows, faults or the debugfs knobs (render_pb_pages, alias_skip):
those jobs are only checked for option acceptance.  Output: out/mock/<job>.txt and a summary.
  python3 tests/mock_all.py [STAGE...]
"""
import os, pathlib, re, shlex, subprocess, sys, tempfile

S1 = pathlib.Path(__file__).resolve().parent.parent
TOOL = pathlib.Path.home() / "src/resgx545/userspace/libsgxfive/build/sgxfive-test"
stages = sys.argv[1:] or [p.stem for p in sorted((S1 / "tables").glob("*.txt"))]
bad = 0
out = S1 / "out" / "mock"
out.mkdir(parents=True, exist_ok=True)
for st in stages:
    n = ok = 0
    for line in (S1 / "tables" / f"{st}.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, sset, risk, P, knobs, rt, args = line.split("|", 6)
        with tempfile.TemporaryDirectory() as w:
            for d in ("dump", "words", "depth", "kept"):
                os.mkdir(f"{w}/{d}")
            a = args.replace("$W", w).replace("$S", str(S1 / "bins"))
            argv = [str(TOOL), "--mock"] + shlex.split(a)
            if P != "-":
                argv.insert(2, f"--mock-pb-pages={int(P, 16)}") if 0x23 <= int(P, 16) <= 0x422 else None
            try:
                r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
                rc, txt = r.returncode, r.stdout + r.stderr
                if rc == 1 and re.search(r"(kpoke|--words|render_param|render_tadata|--depth-dump): No such file", txt):
                    # the mock has no debugfs: retry without the debugfs-backed options, to check the rest
                    strip = shlex.split(re.sub(r"--words \S+|--dump-each|--dump-render \S+|--depth-dump \S+|"
                                               r"--depth-ctl \S+|--depth-fill \S+|--depth-pages \S+|--depth(?= )|"
                                               r"--poke blk:1=\S+", "", a))
                    r2 = subprocess.run([str(TOOL), "--mock"] + strip, capture_output=True, text=True, timeout=120)
                    rc, txt = r2.returncode, "(retried without debugfs options)\n" + r2.stdout + r2.stderr
            except subprocess.TimeoutExpired:
                rc, txt = 124, "timeout"
        (out / f"{name}.txt").write_text(txt)
        n += 1
        usage = rc == 2 or "usage" in txt.lower() or "bad option" in txt or "sgxfive-test: " in txt and rc not in (0, 3)
        if usage:
            bad += 1
            print(f"FAIL {st}/{name}: rc {rc}: {txt.strip().splitlines()[-1][:150] if txt.strip() else ''}")
        else:
            ok += 1
    print(f"{st}: {ok} of {n} commands accepted by the mock")
sys.exit(1 if bad else 0)
