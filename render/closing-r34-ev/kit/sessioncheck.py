#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""sessioncheck.py: the build checks of a closing session (HACKING.md, "Closing-session
scorers"). Standard library only; a session copies it byte for byte beside scorekit.py, which
it imports, and its tests call it. Each check is the design-out of a round-6 slip.

  staged SRC FILE...    the laptop tree is complete: every file a staged script sources or runs
                        (`$DIR/name`, DIR a variable set from `dirname "$0"` or BASH_SOURCE, or
                        --var) and every module a staged Python file imports from SRC is staged,
                        and every function a staged script calls that a script of SRC defines is
                        defined in a staged script it reaches (r6-dpm: lib_check.sh not staged,
                        num_eq "command not found" at a control)
  envi [--set K=V] -- CMD
                        run CMD under `env -i` (PATH and the --set variables only) and fail on a
                        non-zero status or a "command not found" / "No such file" line
  kept SCORER STAGE DIR [--call F]
                        every file the scorer's REQUIRED[STAGE] names is in the kept directory
                        DIR (rows: cases.tsv's first column; a ".suffix" for the rows that
                        ended ok, "fault:", "hang:" or "any:" ones for the rows that ended so,
                        or for every row, by cases.tsv's class), and F(STAGE, DIR) reads no file
                        there that REQUIRED does not declare (r6-misc: no depth dump kept)
  outdirs [--dir-opt=O] [--file-opt=O] -- ARGV
                        every directory a tool writes into exists before it runs: an O argument
                        (a directory) or its parent (a file) (r6-misc: --depth-dump DIR not made)
  premise NAME KEYS FILE|-
                        the premise stage's check of one control: the reading (`k=v` words) has
                        every key of KEYS; `-`, empty or absent is no reading and prints a STOP

Library only: lint_predictions(tables, preds, order) (round 34, T1): the warnings and errors of
the controls' premises, run by `session.py freeze` (constants for registers the kit snapshots,
constant intervals, @snap0 and @cal:STAGE forms).

Exit status: 0 clean, 1 a finding (each printed as FAIL or STOP), 2 a usage error.
"""
import argparse
import importlib.util
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scorekit  # noqa: E402

SHELL_SUFFIXES = (".sh", ".env")
FINDING = re.compile(r"command not found|No such file or directory|: not found")


# ---- the staged tree -----------------------------------------------------------------------
def _code(text):
    """Shell lines without comments (a `#` at the start or after white space)."""
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            out.append("")
        else:
            out.append(re.sub(r"\s#.*$", "", line))
    return out


def _is_shell(path):
    if path.endswith(SHELL_SUFFIXES):
        return True
    try:
        with open(path, errors="replace") as f:
            first = f.readline()
    except OSError:
        return False
    return first.startswith("#!") and re.search(r"\b(ba)?sh\b", first) is not None


def _dir_vars(lines, extra):
    found = set(extra)
    for line in lines:
        m = re.match(r"\s*(?:local\s+|export\s+)?([A-Za-z_]\w*)=.*dirname.*(\$\{?0|BASH_SOURCE)",
                     line)
        if m:
            found.add(m.group(1))
    return found


def _refs(lines, dvars):
    """The files a script names under its own directory: `$DIR/name`, `${DIR}/name`."""
    if not dvars:
        return []
    alt = "|".join(sorted(map(re.escape, dvars)))
    pat = re.compile(r'\$\{?(?:%s)\}?"?/([A-Za-z0-9_.][A-Za-z0-9_./-]*)' % alt)
    out = []
    for line in lines:
        for name in pat.findall(line):
            name = name.rstrip(".")
            if name.startswith("..") or not name:
                continue
            if name not in out:
                out.append(name)
    return out


def _functions(text):
    return set(re.findall(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{?", text,
                          re.M))


CALL = re.compile(r"(?:^|[;&|(`{!]|\b(?:then|do|else|elif|if|while|until|time)\b)\s*"
                  r"([A-Za-z_][A-Za-z0-9_]*)\b(?!=)")


def _calls(lines):
    out = []
    for line in lines:
        for w in CALL.findall(line):
            if w not in out:
                out.append(w)
    return out


def _imports(text):
    out = []
    for m in re.finditer(r"^\s*(?:import\s+([\w, ]+)|from\s+(\w+)\s+import\b)", text, re.M):
        names = m.group(1).split(",") if m.group(1) else [m.group(2)]
        for n in names:
            n = n.strip().split(" ")[0]
            if n and n not in out:
                out.append(n)
    return out


def staged_problems(src, staged, entries=None, dir_vars=()):
    """src: the session's runner directory (every file, staged or not); staged: the names of
    the files the laptop gets; entries: the scripts the laptop runs (default: every staged
    shell script). The findings, in the order the scripts are reached."""
    src = str(src)
    staged = list(staged)
    sset = set(staged)
    read = lambda n: open(os.path.join(src, n), errors="replace").read()
    if entries is None:
        entries = sorted(n for n in staged if _is_shell(os.path.join(src, n)))
    defs = {}
    for n in sorted(os.listdir(src)):
        p = os.path.join(src, n)
        if os.path.isfile(p) and _is_shell(p):
            for f in _functions(read(n)):
                defs.setdefault(f, []).append(n)
    refs_bad, calls_bad = [], []
    reached, todo = [], list(entries)
    while todo:
        n = todo.pop(0)
        if n in reached:
            continue
        reached.append(n)
        p = os.path.join(src, n)
        if n.endswith(".py"):
            for m in _imports(read(n)):
                if os.path.exists(os.path.join(src, m + ".py")):
                    if m + ".py" not in sset:
                        refs_bad.append(f"{n} imports {m}, which is not staged")
                    else:
                        todo.append(m + ".py")
            continue
        if not _is_shell(p):
            continue
        lines = _code(read(n))
        for r in _refs(lines, _dir_vars(lines, dir_vars)):
            if r not in sset:
                where = "" if os.path.exists(os.path.join(src, r)) else \
                    " (and not in the source either)"
                refs_bad.append(f"{n} sources or runs {r}, which is not staged{where}")
            else:
                todo.append(r)
    have = set()
    for n in reached:
        p = os.path.join(src, n)
        if _is_shell(p):
            have |= _functions(read(n))
    for n in reached:
        if not _is_shell(os.path.join(src, n)):
            continue
        for w in _calls(_code(read(n))):
            if w in defs and w not in have:
                where = ", ".join(defs[w])
                why = "which the runner does not source" if all(d in sset for d in defs[w]) \
                    else "which is not staged"
                calls_bad.append(f"{n} calls {w}, defined in {where}, {why}")
    return refs_bad + calls_bad


# ---- env -i --------------------------------------------------------------------------------
def run_env_i(cmd, env, cwd=None, timeout=None):
    """Run cmd with only PATH (the caller's unless env sets it) and env. (status, output,
    findings): the "command not found" and "No such file" lines of the output."""
    e = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    e.update({k: str(v) for k, v in env.items()})
    r = subprocess.run(["env", "-i", *[f"{k}={v}" for k, v in e.items()],
                        *[str(c) for c in cmd]], cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, errors="replace", timeout=timeout)
    probs = [line for line in r.stdout.splitlines() if FINDING.search(line)]
    return r.returncode, r.stdout, probs


# ---- kept files ----------------------------------------------------------------------------
_reads = None


def _audit(event, args):
    if _reads is None or event != "open" or not args or args[0] is None:
        return
    path, mode = args[0], args[1] if len(args) > 1 else None
    flags = args[2] if len(args) > 2 else 0
    if isinstance(path, int):
        return
    if isinstance(mode, str):
        if any(c in mode for c in "wax+"):
            return
    elif isinstance(flags, int) and flags & os.O_ACCMODE != os.O_RDONLY:
        return
    _reads.append(os.fsdecode(os.fspath(path)))


_hooked = False


def files_read(fn):
    """The paths fn() opens to read."""
    global _reads, _hooked
    if not _hooked:
        sys.addaudithook(_audit)
        _hooked = True
    _reads = []
    try:
        fn()
        return list(_reads)
    finally:
        _reads = None


def kept_rows(kept_dir):
    """The row names of a kept directory: the first column of cases.tsv (a `#` line and a
    header line whose first column is `name` are not rows)."""
    p = os.path.join(kept_dir, "cases.tsv")
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p):
        name = line.split("\t")[0].strip()
        if name and not line.startswith("#") and not (name == "name" and not out):
            out.append(name)
    return out


def kept_classes(kept_dir):
    """{row name: how it ended} of a kept directory: cases.tsv's first column and its class (the
    ninth, the runner's ok, fault, hang or fail; ok when the line has none)."""
    p = os.path.join(kept_dir, "cases.tsv")
    out = {}
    for name in kept_rows(kept_dir):
        out[name] = "ok"
    if out:
        for line in open(p):
            f = line.rstrip("\n").split("\t")
            if f[0].strip() in out and len(f) > 8 and f[8].strip():
                out[f[0].strip()] = f[8].strip()
    return out


# a row's knob word whose runner keeps a file of its own before the job, whatever the job's end:
# pre:miscinfo keeps NAME.miscinfo (the debugfs miscinfo read, kit/run_stage.sh)
WORD_FILES = {"pre:miscinfo": ".miscinfo"}


def kept_word_files(kept_dir):
    """NAME.suffix of every kept row (cases.tsv) whose knobs (the fifth column) have a word of
    WORD_FILES."""
    p = os.path.join(kept_dir, "cases.tsv")
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p):
        f = line.rstrip("\n").split("\t")
        if len(f) > 4 and not line.startswith("#") and f[0].strip() != "name":
            out += [f[0].strip() + s for w, s in WORD_FILES.items() if w in f[4].split()]
    return out


def kept_problems(kept_dir, required, rows, fn=None):
    """The files of REQUIRED the kept directory lacks (a per-row file for the rows of its class:
    rows a list of names, each ok, or {name: class}) and the file a row's word keeps
    (WORD_FILES), then the files fn() reads there that neither declares (any class's file of any
    row is declared)."""
    rows = rows if isinstance(rows, dict) else list(rows)
    out = [f"the scorer reads {m}, which is not kept"
           for m in scorekit.missing_files(required, kept_dir, rows)]
    words = kept_word_files(kept_dir)
    out += [f"{m} is not kept (its row's word keeps it)" for m in words
            if not (os.path.exists(os.path.join(kept_dir, m))
                    or os.path.exists(os.path.join(kept_dir, m + ".gz")))]
    if fn is None:
        return out
    names = [f for f in required if (scorekit.required_entry(f) or ("x",))[0] is None]
    names += scorekit.row_files(required, rows, every_class=True) + words
    declared = set(names) | {n + ".gz" for n in names}
    root = os.path.realpath(kept_dir)
    seen = []
    for p in files_read(fn):
        rp = os.path.realpath(p)
        if os.path.commonpath([root, rp]) != root:
            continue
        rel = os.path.relpath(rp, root)
        if rel not in declared and rel not in seen:
            seen.append(rel)
            out.append(f"the scorer read {rel}, which REQUIRED does not declare")
    return out


# ---- output directories --------------------------------------------------------------------
def missing_outdirs(argv, dir_opts=(), file_opts=()):
    """The directories a tool's argv writes into that do not exist."""
    argv = [str(a) for a in argv]
    out = []
    for i, a in enumerate(argv):
        opt, val = a, None
        if "=" in a and a.split("=", 1)[0] in (*dir_opts, *file_opts):
            opt, val = a.split("=", 1)
        elif a in (*dir_opts, *file_opts):
            val = argv[i + 1] if i + 1 < len(argv) else None
        else:
            continue
        if val is None:
            out.append(f"{opt}: no argument")
        elif opt in dir_opts:
            if not os.path.isdir(val):
                out.append(f"{opt} {val}: no such directory")
        else:
            parent = os.path.dirname(val) or "."
            if not os.path.isdir(parent):
                out.append(f"{opt} {val}: no directory {parent}")
    return out


# ---- the premise stage ---------------------------------------------------------------------
def parse_reading(text):
    """`k=v` words; a word without `=` is ignored."""
    return dict(w.split("=", 1) for w in text.split() if "=" in w)


# ---- the freeze lint: premises of controls ---------------------------------------------------
# Round 34 (T1). r30-evst froze CR_CACHE_CTRL from a mid-session reading, and r33-tim froze a
# sample interval from idle spacing; each voided whole stages (E1116, E1131). A control's
# register value is read from the row's own snap0 (scorekit.reg_expect); an interval premise is
# measured in a calibration stage of the same register set (scorekit.calibration).
# The registers of the kit's snap0 (the `reg` lines of debugfs regs of a real kept snap0, the
# round 33 laptop): a constant frozen for one of them is a warning.
SNAP_REGS = frozenset((
    0x0000, 0x0008, 0x001c, 0x0020, 0x0040, 0x0080, 0x0114, 0x0118, 0x012c, 0x0130, 0x0134,
    0x0138, 0x0140, 0x0144, 0x0148, 0x0200, 0x0204, 0x0208, 0x020c, 0x0210, 0x0214, 0x0218,
    0x021c, 0x0220, 0x0224, 0x0230, 0x0234, 0x0238, 0x023c, 0x0240, 0x0244, 0x0248, 0x024c,
    0x026c, 0x0274, 0x0284, 0x0290, 0x02a8, 0x02b0, 0x02b4, 0x02d0, 0x02d4, 0x0308, 0x030c,
    0x0324, 0x0364, 0x0368, 0x0370, 0x0374, 0x0400, 0x0404, 0x0408, 0x040c, 0x0410, 0x0414,
    0x0418, 0x041c, 0x0420, 0x0424, 0x0428, 0x042c, 0x0430, 0x043c, 0x0444, 0x0448, 0x044c,
    0x0450, 0x0480, 0x0484, 0x0488, 0x048c, 0x0490, 0x0494, 0x0498, 0x049c, 0x04a0, 0x04a4,
    0x04a8, 0x04ac, 0x04b0, 0x04b4, 0x04b8, 0x04bc, 0x04c4, 0x04c8, 0x04d4, 0x04d8, 0x04dc,
    0x04e8, 0x050c, 0x0518, 0x051c, 0x0520, 0x0600, 0x0604, 0x0618, 0x061c, 0x0620, 0x0624,
    0x0628, 0x062c, 0x0630, 0x0634, 0x0638, 0x063c, 0x0648, 0x064c, 0x0658, 0x065c, 0x0660,
    0x0664, 0x0668, 0x0674, 0x0680, 0x0684, 0x0694, 0x0698, 0x069c, 0x06a0, 0x0700, 0x070c,
    0x0710, 0x071c, 0x0720, 0x0724, 0x0728, 0x072c, 0x0730, 0x0734, 0x073c, 0x0740, 0x074c,
    0x0800, 0x0804, 0x0820, 0x0824, 0x0828, 0x082c, 0x0830, 0x0834, 0x0838, 0x083c, 0x0840,
    0x0844, 0x0848, 0x0860, 0x0864, 0x0868, 0x0a04, 0x0a08, 0x0a5c, 0x0a60, 0x0a64, 0x0a68,
    0x0a6c, 0x0a74, 0x0a84, 0x0a88, 0x0a8c, 0x0a90, 0x0a94, 0x0a98, 0x0a9c, 0x0aa0, 0x0aa4,
    0x0aa8, 0x0ab8, 0x0acc, 0x0ad0, 0x0ad4, 0x0ae0, 0x0b0c, 0x0b10, 0x0b14, 0x0b18, 0x0b1c,
    0x0b20, 0x0b24, 0x0b28, 0x0b2c, 0x0b80, 0x0b84, 0x0b88, 0x0b8c, 0x0b94, 0x0b98, 0x0c00,
    0x0c04, 0x0c08, 0x0c38, 0x0c3c, 0x0c40, 0x0c44, 0x0c48, 0x0c4c, 0x0c50, 0x0c54, 0x0c58,
    0x0c5c, 0x0c60, 0x0c64, 0x0c68, 0x0c6c, 0x0c70, 0x0c74, 0x0c78, 0x0c84, 0x0c8c, 0x0c90,
    0x0cac, 0x0cb0, 0x0e80,
))
SNAP_RE = re.compile(r"^@snap0(?::([A-Za-z0-9_.-]+))?(?:&0x[0-9a-fA-F]+)?$")
CAL_RE = re.compile(r"^@cal:([A-Za-z0-9_.-]+)$")


def timeline_regs(args):
    """The register set of a regtimeline row's args (`TOTAL LEAD REGS -- COMMAND...`), or None."""
    words = args.split()
    if " -- " not in f" {args} " or len(words) < 3 or "0x" not in words[2]:
        return None
    try:
        return {int(r, 16) for r in words[2].split(",")}
    except ValueError:
        return None


def lint_predictions(tables, preds, order, snap_regs=SNAP_REGS):
    """(warnings, errors) of the controls' premises. tables: {stage: [row dict: name, set, knobs,
    args]}; preds: {stage: {case: {quantity: {model: value}}}}; order: the stages in run order.
    A control quantity `reg:0xOFF` frozen as a constant for a register in snap_regs warns (use
    "@snap0" or "@snap0:ROW"); an `ivl` constant warns (use "@cal:STAGE"). Errors: an @snap0
    form of no form or naming a row not of the stage; an @cal:STAGE of an unknown stage, a stage
    not before the control's, a stage whose rows do not read ivl, fewer than two of them, or a
    register set that differs from the control's."""
    warns, errs = [], []
    for stage in order:
        rows = {r["name"]: r for r in tables.get(stage, [])}
        for case, quants in preds.get(stage, {}).items():
            row = rows.get(case)
            if row is None or row["set"] != "control":
                continue
            for qty, models in quants.items():
                for model, val in models.items():
                    where = f"{stage}/{case} {qty} {model}"
                    if qty.startswith("reg:"):
                        off = int(qty[4:], 16)
                        if val.startswith("@"):
                            m = SNAP_RE.match(val)
                            if not m:
                                errs.append(f"{where}: {val!r} is not @snap0[:ROW][&MASK]")
                            elif m.group(1) and m.group(1) not in rows:
                                errs.append(f"{where}: {val} names {m.group(1)}, "
                                            f"not a row of stage {stage}")
                        elif off in snap_regs:
                            warns.append(
                                f"WARN {where}: a constant {val} for register {off:#06x}, "
                                "which the kit snapshots: freeze \"@snap0\" (the row's own "
                                "snap0) or \"@snap0:ROW\", not a value read mid-session (E1116)")
                    elif qty == "ivl":
                        if CAL_RE.match(val):
                            errs += _cal_problems(where, val, row, stage, tables, order)
                        else:
                            warns.append(
                                f"WARN {where}: a constant interval {val}: calibrate the "
                                "register set in a job window first and freeze \"@cal:STAGE\" "
                                "(E1131)")
    return warns, errs


def _cal_problems(where, val, row, stage, tables, order):
    cal = CAL_RE.match(val).group(1)
    if cal not in tables:
        return [f"{where}: {val} names no stage {cal}"]
    if cal not in order or order.index(cal) >= order.index(stage):
        return [f"{where}: calibration stage {cal} must run before {stage}"]
    out = []
    crows = [r for r in tables[cal] if r["set"] == "control"]
    ivl = [r for r in crows if "ivl" in r.get("reads", ())]
    if not ivl:
        return [f"{where}: calibration stage {cal} has no control that reads ivl"]
    if len(ivl) < 2:
        out.append(f"{where}: calibration stage {cal} needs two rows that read ivl (one has "
                   "no spread to check)")
    want = timeline_regs(row["args"])
    other = [r["name"] for r in ivl if timeline_regs(r["args"]) != want]
    if other:
        out.append(f"{where}: calibration row(s) {', '.join(other)} have another register set "
                   f"than {row['name']}: the interval is per register set")
    return out


# ---- command line --------------------------------------------------------------------------
def _report(probs, ok, word="FAIL"):
    for p in probs:
        print(p if p.startswith("STOP") else f"{word} {p}")
    if not probs and ok:
        print(f"ok   {ok}")
    return 1 if probs else 0


def _load(path):
    path = os.path.abspath(path)
    sys.path.insert(0, os.path.dirname(path))
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("staged")
    s.add_argument("src")
    s.add_argument("files", nargs="+")
    s.add_argument("--entry", action="append")
    s.add_argument("--var", action="append", default=[])
    s = sub.add_parser("envi")
    s.add_argument("--set", action="append", default=[], metavar="K=V")
    s.add_argument("--log")
    s.add_argument("command", nargs=argparse.REMAINDER)
    s = sub.add_parser("kept")
    s.add_argument("scorer")
    s.add_argument("stage")
    s.add_argument("dir")
    s.add_argument("--call")
    s.add_argument("--rows")
    s = sub.add_parser("outdirs")
    s.add_argument("--dir-opt", action="append", default=[])
    s.add_argument("--file-opt", action="append", default=[])
    s.add_argument("argv", nargs=argparse.REMAINDER)
    s = sub.add_parser("premise")
    s.add_argument("name")
    s.add_argument("keys")
    s.add_argument("reading")
    a = ap.parse_args(argv)
    if a.cmd == "staged":
        files = [os.path.basename(f) for f in a.files]
        return _report(staged_problems(a.src, files, a.entry, a.var),
                       f"staged: {len(files)} files, every one sourced, run or imported is "
                       "staged, every function called is defined")
    if a.cmd == "envi":
        cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
        if not cmd or any("=" not in kv for kv in a.set):
            ap.error("envi: --set K=V ... -- COMMAND")
        rc, out, probs = run_env_i(cmd, dict(kv.split("=", 1) for kv in a.set))
        if a.log:
            with open(a.log, "w") as f:
                f.write(out)
        if rc:
            probs = probs + [f"exit status {rc}"]
        return _report(probs, "env -i: exit status 0, no command or file missing")
    if a.cmd == "kept":
        mod = _load(a.scorer)
        req = getattr(mod, "REQUIRED", None)
        if not isinstance(req, dict) or a.stage not in req:
            print(f"FAIL {a.scorer} declares no REQUIRED[{a.stage!r}]")
            return 1
        rows = [line.strip() for line in open(a.rows) if line.strip()] if a.rows \
            else kept_classes(a.dir)
        fn = (lambda: getattr(mod, a.call)(a.stage, a.dir)) if a.call else None
        return _report(kept_problems(a.dir, req[a.stage], rows, fn),
                       f"kept {a.stage}: {len(rows)} rows, every file REQUIRED names is kept"
                       + (", no other file read" if fn else ""))
    if a.cmd == "outdirs":
        args = a.argv[1:] if a.argv[:1] == ["--"] else a.argv
        return _report(missing_outdirs(args, a.dir_opt, a.file_opt), "")
    if a.cmd == "premise":
        keys = tuple(a.keys.split())
        if not keys:
            print(f"control {a.name} declares no reading: it cannot fail")
            return 2
        text = sys.stdin.read() if a.reading == "-" else open(a.reading).read()
        return _report(scorekit.premise_stops({a.name: keys}, {a.name: parse_reading(text)}),
                       "")
    return 2


if __name__ == "__main__":
    sys.exit(main())
