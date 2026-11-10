"""Shared pieces of the R1 generators: paths, the job-table row, table and prediction writers.

Nothing here touches the laptop.  Run with the scratch venv (numpy) from the R1 directory:
  PYTHONDONTWRITEBYTECODE=1 ~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python gen/r1gen.py
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True     # the generators import the data repo's modules: no __pycache__ there

import dataclasses  # noqa: E402
import hashlib
import pathlib
import struct

R1 = pathlib.Path(__file__).resolve().parent.parent
REPO = pathlib.Path.home() / "src/resgx545"
DATA = pathlib.Path.home() / "src/resgx545-data"
TABLES, PREDS, BINS, TEMPLATES = R1 / "tables", R1 / "predictions", R1 / "bins", R1 / "templates"
sys.path.insert(0, str(REPO / "tools/usse-asm"))
import probe  # noqa: E402  (the landed probe tool: used read-only to build commands and programs)

# Register timelines.  Every DPM job lists 0x0720-0x0724; the runner widens that range to 0x0720-0x072c only for
# the trial jobs and, once the gate passed, for the jobs carrying the knob s072c (run/lib_r1.sh, decision R2-13 b).
SAMPLE_RANGE = ("0x0720-0x0724", "0x0720-0x072c")
RT_DPM = "0x0624-0x0628,0x0654-0x0660,0x0700-0x0710,0x0720-0x0724,0x0748"      # C1 (geometry proposal 2)
RT_DPM_SHORT = "0x0624-0x0628,0x0654-0x0660,0x0720-0x0724"                    # U1, U2 (proposal 3)


def f32(v: float) -> int:
    return struct.unpack("<I", struct.pack("<f", v))[0]


def f32v(b: int) -> float:
    return struct.unpack("<f", struct.pack("<I", b & 0xffffffff))[0]


@dataclasses.dataclass
class Row:
    name: str
    set: str           # control | heldout | repeat | replicate
    risk: str          # safe | risky
    P: str             # render_pb_pages for the job, "-" = leave
    knobs: str         # runner words, see run/lib_r1.sh
    rt: str            # regtimeline register list or "-"
    args: str          # tool arguments (the tool is $T)
    role: str = ""     # human text for TABLES.md
    cond: str = ""     # condition key: rows with the same cond are replicates of one condition


def write_table(stage: str, rows: list[Row], need: list[str], head: str) -> None:
    TABLES.mkdir(exist_ok=True)
    names = [r.name for r in rows]
    assert len(names) == len(set(names)), f"{stage}: duplicate job names"
    for r in rows:
        assert "|" not in r.args and "\t" not in r.args, r.name
        assert r.set in ("control", "heldout", "repeat", "replicate"), r.name
        if r.args.startswith("tri "):          # a tri job's own one-triangle reference check may differ (rc 1 + diff:)
            assert "expectdiff" in r.knobs.split(), f"{r.name}: tri job without expectdiff"
        if any(k in r.knobs.split() for k in ("s072c",)) or any(k.startswith("trial072c") for k in r.knobs.split()):
            assert SAMPLE_RANGE[0] in r.rt, f"{r.name}: a 0x072c job must list {SAMPLE_RANGE[0]}"
    out = [f"#stage {stage}"] + [f"#need {n}" for n in need]
    out += [f"# {ln}" for ln in head.strip().splitlines()]
    out += ["|".join((r.name, r.set, r.risk, r.P, r.knobs, r.rt, r.args)) for r in rows]
    (TABLES / f"{stage}.txt").write_text("\n".join(out) + "\n")


def write_preds(stage: str, preds: list[tuple]) -> None:
    PREDS.mkdir(exist_ok=True)
    lines = ["case\tquantity\tvalue\tmodel\tset"]
    for p in preds:
        assert len(p) == 5 and all("\t" not in str(x) and "\n" not in str(x) for x in p), p
        lines.append("\t".join(str(x) for x in p))
    (PREDS / f"{stage}.tsv").write_text("\n".join(lines) + "\n")


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def conditions(rows: list[Row]) -> int:
    return len({r.cond or r.name for r in rows})
