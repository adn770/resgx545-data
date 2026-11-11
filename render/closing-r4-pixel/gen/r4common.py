# SPDX-License-Identifier: MIT
"""Shared pieces of the R4-pixel generators: paths, the job-table row, the table and prediction writers, the program builders.
Nothing here touches the laptop.  Run with the scratch venv (numpy) from the R4-pixel directory:
  PYTHONDONTWRITEBYTECODE=1 ~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python gen/r4gen.py
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True     # the generators import the data repo's modules: no __pycache__ there

import dataclasses  # noqa: E402
import pathlib  # noqa: E402

import os  # noqa: E402

R4 = pathlib.Path(__file__).resolve().parent.parent
# the landed tree this session pins (FROZEN.commits: resgx545 5a13042); RESGX545_MAIN overrides (the offline build used the
# lead's worktree of that commit), RESGX545_DATA likewise
REPO = pathlib.Path(os.environ.get("RESGX545_MAIN", str(pathlib.Path.home() / "src/resgx545")))
DATA = pathlib.Path(os.environ.get("RESGX545_DATA", str(pathlib.Path.home() / "src/resgx545-data")))
TABLES, PREDS, BINS, TEMPLATES = R4 / "tables", R4 / "predictions", R4 / "bins", R4 / "templates"
sys.path.insert(0, str(REPO / "tools/usse-asm"))
sys.path.insert(0, str(R4 / "score"))
import probe  # noqa: E402  (the landed probe tool: used read-only to assemble programs)
import r4const as C  # noqa: E402
import r4loops as LP  # noqa: E402

SETS = ("control", "heldout", "repeat", "replicate")
SAFE = "safe"


@dataclasses.dataclass
class Row:
    name: str
    set: str           # control | heldout | repeat | replicate
    risk: str          # safe
    knobs: str         # runner words, see run/run_stage.sh
    rt: str            # regtimeline register list or "-"
    args: str          # tool arguments (the tool is $T)
    role: str = ""     # human text for TABLES.md


def write_table(stage: str, rows: list, need: list, head: str) -> None:
    TABLES.mkdir(exist_ok=True)
    names = [r.name for r in rows]
    assert len(names) == len(set(names)), f"{stage}: duplicate job names"
    for r in rows:
        assert "|" not in r.args and "\t" not in r.args and "|" not in r.knobs, r.name
        assert r.set in SETS, r.name
        if r.args.startswith("tri "):
            assert "expectdiff" in r.knobs.split(), f"{r.name}: tri job without expectdiff"
    out = [f"#stage {stage}"] + [f"#need {n}" for n in need]
    out += [f"# {ln}".rstrip() for ln in head.strip().splitlines()]
    out += ["|".join((r.name, r.set, r.risk, r.knobs, r.rt, r.args)) for r in rows]
    (TABLES / f"{stage}.txt").write_text("\n".join(out) + "\n")


def write_preds(stage: str, preds: list) -> None:
    PREDS.mkdir(exist_ok=True)
    lines = ["case\tquantity\tvalue\tmodel\tset"]
    for p in preds:
        assert len(p) == 5 and all("\t" not in str(x) and "\n" not in str(x) for x in p), p
        assert p[4] in SETS, p
        lines.append("\t".join(str(x) for x in p))
    (PREDS / f"{stage}.tsv").write_text("\n".join(lines) + "\n")


_built = {}


def build_bin(name: str, text: str) -> str:
    """Assemble text into bins/NAME.bin with the landed usse-asm (once per name; a different text under a name is a bug);
    returns the table's $S path."""
    if name in _built:
        assert _built[name] == text, f"program {name} built twice with different text"
        return f"$S/{name}.bin"
    BINS.mkdir(exist_ok=True)
    probe._assemble(text, BINS / f"{name}.bin")
    _built[name] = text
    return f"$S/{name}.bin"


def mark_hex(n: int) -> str:
    return f"0x{LP.mark(n):08x}"
