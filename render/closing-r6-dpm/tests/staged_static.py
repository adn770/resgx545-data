#!/usr/bin/env python3
"""staged_static.py SRC_RUN STAGED_TREE: every file the laptop runner sources or runs is staged, every function it calls is defined there (test_staged.sh)."""
import pathlib, re, sys
src, st = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
staged = {p.name for p in st.iterdir()}
bad = []
code = lambda p: [l.split("#")[0] if not l.lstrip().startswith("#") else "" for l in p.read_text().splitlines()]
for f in ("run_stage.sh", "lib_r6.sh"):
    for l in code(st / f):
        for m in re.findall(r'\$(?:HERE_LIB|DIR)/([A-Za-z0-9_.]+)', l):
            if m not in staged and m != "..":
                bad.append(f"{f} uses {m}, not staged")
if "fwtask_run.py" not in staged:
    bad.append("fwtask_run.py not staged")
fdef = lambda p: set(re.findall(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\(\)\s*\{', p.read_text(), re.M))
# the laptop-side scripts (stage_r6.sh, r6.sh, freeze_r6.sh and guard_r6.sh run on the Mac)
defined_src = set().union(*(fdef(src / f) for f in ("lib_r6.sh", "lib_check.sh", "run_stage.sh")))
defined_st = set().union(*(fdef(p) for p in st.glob("*.sh")))
for f in ("run_stage.sh", "lib_r6.sh"):
    words = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', "\n".join(code(st / f))))
    for fn in sorted(words & defined_src - defined_st):
        bad.append(f"{f} calls {fn}, defined in run/ but not in the staged tree")
for b in bad:
    print("FAIL", b)
print(("ok   " if not bad else "FAIL ") + f"static: every file sourced or run is staged ({sorted(staged)}); every function called is defined in the staged tree ({len(defined_st)} functions)")
sys.exit(1 if bad else 0)
