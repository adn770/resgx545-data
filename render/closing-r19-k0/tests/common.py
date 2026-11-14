# SPDX-License-Identifier: MIT
"""tests/common.py: what r19-k0's tests share: the pinned data files (at the freeze's data commit,
never the working tree), a kept directory built from them, and the mock's outputs of a row."""
import gzip
import os
import pathlib
import subprocess
import sys
import tomllib

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "gen"), str(KP / "mock")]
DATA = pathlib.Path(os.environ.get("RESGX545_DATA", pathlib.Path.home() / "src/resgx545-data"))
CFG = tomllib.loads((KP / "session.toml").read_text())
DATA_COMMIT = CFG["freeze"]["data"]
COLUMNS = ("name", "stage", "set", "risk", "knobs", "tool", "args", "rc", "class", "fault_int",
           "fault_word", "free_kb")
R13 = "render/closing-r13-dpm/out/20261113-212348/pr2"
R10 = "render/closing-r10-dpm/out/20261113-102513/s6rep"
R9 = "render/closing-r9-ldpm/out/20261113-082650/a0"
Z13 = "render/closing-r13-zls/out/20261113-213117/zbase"


def pin(path, raw=False):
    """A pinned data file's bytes at the freeze's data commit (gunzipped when .gz, unless raw)."""
    assert f"data:{path}" in CFG["freeze"]["pins"], f"{path} is not pinned"
    b = subprocess.run(["git", "-C", str(DATA), "show", f"{DATA_COMMIT}:{path}"],
                       capture_output=True, check=True).stdout
    return gzip.decompress(b) if path.endswith(".gz") and not raw else b


def table(stage):
    out = {}
    for ln in (KP / "tables" / f"{stage}.txt").read_text().splitlines():
        if ln and not ln.startswith("#"):
            p = ln.split("|", 5)
            out[p[0]] = dict(zip(("name", "set", "risk", "knobs", "tool", "args"), p))
    return out


def kept_dir(d, stage, jobs):
    """A kept stage directory: jobs {name: (rc, {suffix: bytes})}, every row class ok."""
    d.mkdir(parents=True, exist_ok=True)
    rows = table(stage)
    lines = []
    for n, (rc, files) in jobs.items():
        r = rows[n]
        lines.append("\t".join([n, stage, r["set"], r["risk"], r["knobs"], r["tool"], r["args"],
                                str(rc), "ok", "-", "-", "1000000"]))
        for suf, b in files.items():
            (d / f"{n}{suf}").write_bytes(b)
    (d / "cases.tsv").write_text("\n".join(["\t".join(COLUMNS)] + lines) + "\n")
    (d / "void.tsv").write_text("")
    (d / "readings.tsv").write_text("name\tkeys\treading\n")
    return d


def mock_job(row, world=("model",), tmp=None):
    """(rc, {suffix: bytes}) of a row on mock/world.py: the wrapped tool's text, regtimeline's
    block after it, and the files it writes into $W (kept flat as .BASENAME)."""
    import world as Wd
    tmp = pathlib.Path(tmp)
    dbg = tmp / "dbg"
    dbg.mkdir(parents=True, exist_ok=True)
    knobs = dict(w[4:].split("=") for w in row["knobs"].split() if w.startswith("dbg:"))
    (dbg / "render_pb_pages").write_text(knobs.get("render_pb_pages", "0x422") + "\n")
    os.environ["FAKE_DBGREAL"] = str(dbg)
    w = tmp / "w"
    w.mkdir(exist_ok=True)
    bins = KP / "bins" / "p1139-green.bin"
    args = (row["args"].replace('"$HOME/', '"/home/')
            .replace('"$W"', f'"{w}"').replace('"$S/bins/p1139-green.bin"', f'"{bins}"'))
    import shlex
    argv = shlex.split(args)
    world = set(world)
    if row["tool"] == "rt":
        regs, i = argv[2], argv.index("--")
        tool = "t10" if argv[i + 1].endswith("-t10") else "t18b"
        a = Wd.answer(tool, argv[i + 2:], world)
        offs = []
        for part in regs.split(","):
            lo, _, hi = part.partition("-")
            offs += range(int(lo, 0), int(hi or lo, 0) + 4, 4)
        rows = Wd.timeline("rt", offs, argv[i + 2:], a.get("rc", 0), world)
        text = a.get("out", "") + "timeline: regs %s samples %d seconds 0 start 0 end 0 rc %d\n" % (
            " ".join("0x%04x" % r for r in offs), len(rows), a.get("rc", 0))
        text += "".join("tl %d %s\n" % (k * 1000, " ".join("%08x" % v for v in vals))
                        for k, vals in enumerate(rows))
    else:
        a = Wd.answer(row["tool"], argv, world)
        text = a.get("out", "")
    files = {".txt": text.encode()}
    for p, b in a.get("files", {}).items():
        files["." + os.path.basename(p)] = b
        pathlib.Path(p).write_bytes(b)          # the job's $W, as the tool leaves it
    return a.get("rc", 0), files
