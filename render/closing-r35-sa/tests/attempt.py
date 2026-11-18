# SPDX-License-Identifier: MIT
"""tests/attempt.py: builds a kept attempt of r35-sa from mock/world.py (the same fake the kit's
mock runs), for tests/test_score.py: every row of a stage in table order on one fake laptop (the
kit's stage-begin health pair first, a debugfs reset before every row without `noreset`), each
row's text as NAME.txt, cases.tsv, void.tsv and readings.tsv as run/hooks.sh's hook_reading writes
them (sa, top, rows). Not a test module (no test_ prefix)."""
import importlib.util
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402

_spec = importlib.util.spec_from_file_location("world", os.path.join(KP, "mock", "world.py"))
world = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(world)


def reading(text):
    """run/hooks.sh's hook_reading, in Python: sa, top, rows."""
    out = []
    m = re.search(r"^probe \S+: scratch \+0x000 (0x[0-9a-f]{8})$", text, re.M)
    if m:
        out.append("sa=" + m.group(1))
    m = re.search(r"^probe \S+: o0 (?:mixed )?(0x[0-9a-f]{8}) ", text, re.M)
    if m:
        out.append("top=" + m.group(1))
    n = len(re.findall(r"^probe \S+: row \d+:(?: [0-9a-f]{8}){64}$", text, re.M))
    if n:
        out.append(f"rows={n}")
    return " ".join(out)


def build(root, stages=("a", "t"), tokens=("model",), edit=None, drop=()):
    """root/STAGE/ for each stage under the world `tokens`; edit(name, text) -> text changes a
    row's kept text before its reading is taken (None drops the row)."""
    os.environ["FAKE_DIR"] = os.path.join(root, "fake")
    os.makedirs(os.environ["FAKE_DIR"], exist_ok=True)
    wset = set(tokens)
    bins = os.path.join(KP, "bins")
    for st in stages:
        d = os.path.join(root, st)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(os.environ["FAKE_DIR"], "writes"), "a") as f:
            f.write("reset\n")
        world.answer("t10", ["fill"], wset)
        world.answer("t10", ["tri"], wset)
        with open(os.path.join(d, "cases.tsv"), "w") as fc, \
                open(os.path.join(d, "readings.tsv"), "w") as fr:
            fc.write("\t".join(K.COLUMNS) + "\n")
            fr.write("name\treads\treading\n")
            for r in K.table(KP, st):
                n, a = r["name"], r["args"]
                if "noreset" not in r["knobs"]:
                    with open(os.path.join(os.environ["FAKE_DIR"], "writes"), "a") as f:
                        f.write("reset\n")
                argv = a.replace('"$S/bins/', bins + "/").replace('"', "").split()
                ans = world.answer(r["tool"], argv, wset)
                text = ans.get("out", "")
                if edit:
                    text = edit(n, text)
                if n in drop or text is None:
                    continue
                rc = ans.get("rc", 0)
                fc.write("\t".join([n, st, r["set"], r["risk"], " ".join(r["knobs"]), r["tool"],
                                    a, str(rc), "ok" if rc == 0 else "fault", "-", "-",
                                    "1000"]) + "\n")
                if r["set"] == "control":
                    fr.write(f"{n}\t{','.join(r['reads'])}\t{reading(text)}\n")
                open(os.path.join(d, n + ".txt"), "w").write(text)
        open(os.path.join(d, "void.tsv"), "w").write("\t".join(K.COLUMNS) + "\n")
    return root
