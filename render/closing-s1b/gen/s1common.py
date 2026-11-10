"""Shared pieces of the S1 generators: paths, the job-table row, table and prediction writers.

Nothing here touches the laptop.  Run with the scratch venv (numpy) from the s1 directory:
  ~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python gen/s1gen.py
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True     # the generators import the data repo's modules: no __pycache__ there

import dataclasses  # noqa: E402
import hashlib
import pathlib
import struct
import sys

S1 = pathlib.Path(__file__).resolve().parent.parent
REPO = pathlib.Path.home() / "src/resgx545"
DATA = pathlib.Path.home() / "src/resgx545-data"
TABLES, PREDS, BINS = S1 / "tables", S1 / "predictions", S1 / "bins"
sys.path.insert(0, str(REPO / "tools/usse-asm"))
import probe  # noqa: E402  (the landed probe tool: used read-only to build commands and programs)

RT_DPM = "0x0624-0x0628,0x0654-0x0660,0x0700-0x0710,0x0720-0x0724,0x0748"
RT_DPM_SHORT = "0x0624-0x0628,0x0654-0x0660,0x0720-0x0724"


def f32(v: float) -> int:
    return struct.unpack("<I", struct.pack("<f", v))[0]


def f32v(b: int) -> float:
    return struct.unpack("<f", struct.pack("<I", b & 0xffffffff))[0]


@dataclasses.dataclass
class Row:
    name: str
    set: str           # control | heldout | fit | replicate
    risk: str          # safe | risky
    P: str             # render_pb_pages for the job, "-" = leave
    knobs: str         # runner words, see run/lib_s1.sh
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
    out = [f"#stage {stage}"] + [f"#need {n}" for n in need]
    out += [f"# {ln}" for ln in head.strip().splitlines()]
    out += ["|".join((r.name, r.set, r.risk, r.P, r.knobs, r.rt, r.args)) for r in rows]
    (TABLES / f"{stage}.txt").write_text("\n".join(out) + "\n")


def write_preds(stage: str, preds: list[tuple]) -> None:
    PREDS.mkdir(exist_ok=True)
    lines = ["case\tquantity\tvalue\tmodel\tset"]
    lines += ["\t".join(str(x) for x in p) for p in preds]
    (PREDS / f"{stage}.tsv").write_text("\n".join(lines) + "\n")


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def conditions(rows: list[Row]) -> int:
    return len({r.cond or r.name for r in rows})
