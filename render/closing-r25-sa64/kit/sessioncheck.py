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


def kept_problems(kept_dir, required, rows, fn=None):
    """The files of REQUIRED the kept directory lacks (a per-row file for the rows of its class:
    rows a list of names, each ok, or {name: class}), then the files fn() reads there that
    REQUIRED does not declare (any class's file of any row is declared)."""
    rows = rows if isinstance(rows, dict) else list(rows)
    out = [f"the scorer reads {m}, which is not kept"
           for m in scorekit.missing_files(required, kept_dir, rows)]
    if fn is None:
        return out
    names = [f for f in required if (scorekit.required_entry(f) or ("x",))[0] is None]
    names += scorekit.row_files(required, rows, every_class=True)
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
