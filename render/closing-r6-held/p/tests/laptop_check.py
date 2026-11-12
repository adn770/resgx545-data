#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""laptop_check.py STAGED_TREE: run ON the mock laptop (tests/run_mock.py copies it to the mock home and starts it through the ssh shim,
so it gets only the laptop's environment and the system python3), against the EXACT staged tree (run/stage_p.sh's copy, with the REAL
landed fwtask_run.py staged as run/fwtask_run.py, not the mock's).  Round 6 brief: the runner must not call a function that is not there
(a name of the landed module, of the layout or of its own class), import anything the staging did not copy, or run a command the laptop
lacks.  Prints one line a finding and `LAPTOP CHECK OK` or `LAPTOP CHECK FAILED`."""
import ast
import os
import sys

T = os.path.abspath(sys.argv[1])
sys.path[:0] = [os.path.join(T, "gen"), os.path.join(T, "run")]
sys.dont_write_bytecode = True
for k in [k for k in os.environ if k.startswith("R3_")]:
    del os.environ[k]                      # the check imports the staged runner as the laptop does: the landed fwtask_run, no mock hook
bad = []
import fwtask_run as FR  # noqa: E402
import r5layout as L  # noqa: E402
import r6hp_run as RUN  # noqa: E402

if os.path.realpath(FR.__file__) != os.path.realpath(os.path.join(T, "run", "fwtask_run.py")):
    bad.append(f"fwtask_run imported from {FR.__file__}, not the staged landed copy")
for name, mod in (("r6hp_run", RUN), ("r5layout", L), ("fwtask_run", FR)):
    if not os.path.realpath(mod.__file__).startswith(os.path.realpath(T) + os.sep):
        bad.append(f"{name} imported from outside the staged tree: {mod.__file__}")
LAPTOP_COMMANDS = {"timeout", "cat", "mktemp", "modinfo", "uname", "sha256sum", "journalctl", "dmesg"}
cmds = set()
for f in ("run/r6hp_run.py", "run/ops_h.py"):
    tree = ast.parse(open(os.path.join(T, f)).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            obj, attr = node.func.value.id, node.func.attr
            if obj == "self" and not hasattr(RUN.Runner, attr):
                bad.append(f"{f}:{node.lineno}: self.{attr}() is not a method of the staged Runner")
            if obj == "FR" and not hasattr(FR, attr):
                bad.append(f"{f}:{node.lineno}: FR.{attr}() is not in the staged landed fwtask_run.py")
            if obj == "L" and not hasattr(L, attr):
                bad.append(f"{f}:{node.lineno}: L.{attr}() is not in the staged r5layout.py")
            if obj == "subprocess" and node.args and isinstance(node.args[0], ast.List) and node.args[0].elts:
                e0 = node.args[0].elts[0]
                if isinstance(e0, ast.Constant):
                    cmds.add(e0.value)
            if obj == "FR" and attr == "sh" and node.args:
                a = node.args[0]
                s = a.value if isinstance(a, ast.Constant) else (a.values[0].value if isinstance(a, ast.JoinedStr) and a.values
                                                                and isinstance(a.values[0], ast.Constant) else None)
                if s:
                    cmds.add(s.split()[0])
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in ("FR", "L"):
            mod = FR if node.value.id == "FR" else L
            if not hasattr(mod, node.attr) and not (node.value.id == "FR" and node.attr == "D"):
                bad.append(f"{f}:{node.lineno}: {node.value.id}.{node.attr} does not exist in the staged tree")
off = sorted(c for c in cmds if c not in LAPTOP_COMMANDS)
if off:
    bad.append(f"commands outside the laptop's list {sorted(LAPTOP_COMMANDS)}: {off}")
print(f"commands the runner starts: {sorted(cmds)}")
for b in bad:
    print("BAD " + b)
print("LAPTOP CHECK " + ("FAILED" if bad else "OK"))
sys.exit(1 if bad else 0)
