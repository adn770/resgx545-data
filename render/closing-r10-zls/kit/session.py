#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""session.py: the Mac side of a closing session built with the session kit (HACKING.md,
"Session kit"). Standard library only; tools/closing/new_session.py copies it, with the rest of
tools/closing/kit, scorekit.py and sessioncheck.py, into the session's kit/ from a named resgx545
commit, and the freeze pins each copy by that commit. A session declares only session.toml (its
env), tables/, predictions/, score/score.py (scorekit-based) and mock/world.py; the kit supplies
the rest:

  guard   KP   the static rules: the laptop files (kit runner, run/hooks.sh, run/session.env) and
               the tables (knobs, tools, options, controls)
  prepare KP   write run/session.env, run/required.tsv (the scorer's REQUIRED) and run/staged.lst
               (the one list of laptop files: what stage copies and the runner checks)
  freeze  KP   write PREDICTIONS.sha256, FROZEN.sha256 and FROZEN.commits; refuses a kit copy
               that is not its blob at the pinned commit, a guard finding, an unreadable control,
               an existing freeze
  verify  KP   every session file against FROZEN.sha256 (a new file is a change), every pinned
               resgx545 and data file against its blob AT ITS COMMIT (never the working tree: main
               and data may move while sessions are built and run), the predictions
  stage   KP   the laptop list to ~/scratch/<prefix>/stage over one ssh (BatchMode, HostKeyAlias,
               bounded), then every copy and tool checked by sha256 on the laptop
  run     KP [--from S] [--only S...] [--att A]
               per stage of session.toml: verify, the gate (score.py gate), the laptop runner, the
               copy back, the kept-files check (sessioncheck kept), the score, the premise
  mock    KP [--world W...]
               first every row's argv through the library mock built from the tool's bound
               source (session.toml `source`, `source_sha256`): a `job: rejected` or a usage
               refusal stops it; then the staged tree on a fake laptop under env -i, the fake
               tool answering by argv (mock/world.py), for every world of its EXPECT; no clock
  files   KP [--laptop]   the freeze's file list (or the laptop list)

Exit status of run: the laptop runner's own (kit/run_stage.sh: 1 preflight ... 25 premise) for a
stage that stopped (after the copy back), and 20 the freeze does not verify, 38 the scorer failed
or printed no SUMMARY, 39 the attempt's stage directory exists, 43 a file the scorer reads was
not kept, 44 the premise (a control with no reading), 45 a laptop command or file was missing
(a "command not found" or "No such file" line in the stage's log), 142 a bounded command reached
its limit. A runner status 24 (the stage stopped by its rule) goes on to the next stage.
"""
import argparse
import glob
import hashlib
import importlib.util
import io
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib

KITDIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KITDIR))
import sessioncheck  # noqa: E402
import scorekit  # noqa: E402

# the kit files of a session's kit/ and their sources in the resgx545 tree
KIT_SOURCES = {f"kit/{n}": f"tools/closing/kit/{n}" for n in (
    "session.py", "lib_kit.sh", "run_stage.sh", "kitscore.py", "fake/sudo", "fake/timeout",
    "fake/df", "fake/modinfo", "fake/sha256sum", "fake/tool.sh", "fake/tool.py", "fake/ssh.py")}
KIT_SOURCES.update({"kit/scorekit.py": "tools/closing/scorekit.py",
                    "kit/sessioncheck.py": "tools/closing/sessioncheck.py"})
LAPTOP_KIT = ("kit/lib_kit.sh", "kit/run_stage.sh", "kit/sessioncheck.py", "kit/scorekit.py")
GENERATED = ("run/session.env", "run/required.tsv", "run/staged.lst")
# the session subtrees no freeze names: out/ (kept records, lead logs), debug/ (the mock, the
# library mock) and fold/ (the fold's post-run notes and tables); no laptop file comes from them
NOT_FROZEN_DIRS = ("out", "debug", "fold")
NOT_FROZEN = ("FROZEN.sha256", "FROZEN.commits", "PREDICTIONS.sha256")
COMMITS_HEADER = """\
# FROZEN.commits: the commit that holds each file this session's FROZEN.sha256 pins outside the
# session (resgx545:PATH, data:PATH) and each byte copy of the kit (kit/ <- resgx545
# tools/closing). One line per file: the sha256, the commit, the repository and path. Verify a
# pin with `git -C <repository> show <commit>:<path> | sha256sum`. Written by the session kit's
# freeze (tools/closing/kit/session.py), the format tools/records/frozen.py checks.
"""
LINE = re.compile(r"([0-9a-f]{64})  ([0-9a-f]{7,40}|untracked)  ([a-z][a-z0-9-]*):(\S.*)")
BUILT = re.compile(r"([0-9a-f]{64})  built  ([0-9a-f]{7,40})  (\S+)  ([0-9a-f]{64})  (\S+)")
SSH = ["ssh"]
ENV = None          # the environment of every command (the mock's; None: this process's)
# the kit's knob words; expect:NAME are kitscore.OUTCOMES (run_stage.sh classifies them)
BASE_KNOBS = re.compile(r"^(-|expectdiff|expectfault|after|soft|gate|grp:[a-z0-9]+|"
                        r"expect:(rc3-overflow)|reads:[a-z0-9_]+(,[a-z0-9_]+)*)$")
# --kpoke is probe's kernel poke, no riskier than tri's --kpoke-render: allowed on `probe` rows only
FORBID_OPTIONS = ("--kpoke", "--kreg", "--clkgate", "--trc-hazard")
FORBID = (r"reboot|shutdown|poweroff|kexec|grub|mkinitcpio|(^|[^a-z_-])make |gcc|(^|[^a-z])cc |"
          r"push-gma500|deploy-tool|trc_hazard|CLKGATE|clkgate|(^|[^a-z0-9])kreg([^a-z0-9-]|$)|"
          r"kregnow|kicker|kpoke|/dev/mem|git |\| *tail|\|\| *true")


class Stop(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ---- commands --------------------------------------------------------------------------------
def bounded(cmd, limit, **kw):
    """Every command of the driver: a CompletedProcess, returncode 142 when the limit is
    reached (the command is killed)."""
    kw.setdefault("env", ENV)
    try:
        return subprocess.run([str(c) for c in cmd], timeout=limit, **kw)
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(e.cmd, 142, e.stdout or b"", e.stderr or b"")


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha_bytes(pathlib.Path(p).read_bytes())


def repo_dirs():
    e = ENV or os.environ
    home = pathlib.Path(e.get("HOME", "~")).expanduser()
    return {"resgx545": pathlib.Path(e.get("RESGX545", home / "src/resgx545")),
            "data": pathlib.Path(e.get("RESGX545_DATA", home / "src/resgx545-data"))}


def git_blob(repo, commit, path):
    r = bounded(["git", "-C", repo, "cat-file", "blob", f"{commit}:{path}"], 60,
                capture_output=True)
    return r.stdout if r.returncode == 0 else None


def git_commit(repo, rev):
    r = bounded(["git", "-C", repo, "rev-parse", "--verify", "-q", f"{rev}^{{commit}}"], 60,
                capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


# ---- the session -----------------------------------------------------------------------------
def config(kp):
    c = tomllib.loads((pathlib.Path(kp) / "session.toml").read_text())
    c.setdefault("knobs", {})
    c.setdefault("files", {})
    c.setdefault("freeze", {})
    c.setdefault("outdir_opts", [])
    c.setdefault("extra_knobs", [])
    c.setdefault("debugfs", [])
    c.setdefault("forbid_options", [])
    return c


def stages(c):
    return list(c["stages"])


def tool_path(c, prefix, name):
    t = c["tools"][name]
    if "stage_from" in t:
        return f"scratch/{prefix}/stage/{t['stage_from']}"
    return t["path"]


def laptop_files(kp, c=None):
    """The one list of the files the laptop gets (FROZEN.sha256 besides): what stage copies,
    what the runner checks against the freeze (run/staged.lst, without the staged tools, which
    the preflight checks by their pinned sha256)."""
    kp = pathlib.Path(kp)
    c = c or config(kp)
    out = list(LAPTOP_KIT) + list(GENERATED)
    if (kp / "run/hooks.sh").exists():
        out.append("run/hooks.sh")
    out += [f"tables/{s}.txt" for s in stages(c)]
    for g in c["files"].get("laptop", []):
        hits = sorted(glob.glob(str(kp / g)))
        out += [pathlib.Path(h).relative_to(kp).as_posix() for h in hits if os.path.isfile(h)]
    return list(dict.fromkeys(out))


def staged_tools(c):
    return [t["stage_from"] for t in c["tools"].values() if "stage_from" in t]


def freeze_files(kp):
    kp = pathlib.Path(kp)
    out = []
    for p in sorted(kp.rglob("*")):
        rel = p.relative_to(kp)
        if not p.is_file() or rel.parts[0] in NOT_FROZEN_DIRS or rel.as_posix() in NOT_FROZEN:
            continue
        if "__pycache__" in rel.parts or p.suffix == ".pyc" or p.name == ".DS_Store":
            continue
        out.append(rel.as_posix())
    return out


def load_module(path, name):
    path = pathlib.Path(path).resolve()
    for d in (path.parent, path.parent.parent / "kit"):
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scorer(kp):
    return load_module(pathlib.Path(kp) / "score/score.py", "kit_session_score")


def generated(kp):
    """{path: text} of the files prepare writes."""
    kp = pathlib.Path(kp)
    c = config(kp)
    p = c["prefix"]
    env = [f"# run/session.env: written by kit/session.py prepare from session.toml; never edit",
           f"PREFIX={p}", f"SRCV_EXPECT={c['srcversion']}",
           f"JOB_TIMEOUT=${{JOB_TIMEOUT:-{int(c.get('job_timeout', 120))}}}",
           f"MIN_FREE_MB=${{MIN_FREE_MB:-{int(c.get('min_free_mb', 200))}}}",
           f"TOOLS=\"{' '.join(c['tools'])}\"", f"HEALTH_TOOL={c['health_tool']}",
           f"DEBUGFS_NEED=\"{' '.join(c['debugfs'])}\"",
           f"OUTDIR_OPTS=\"{' '.join(c['outdir_opts'])}\"",
           f"EXTRA_KNOBS=\"{' '.join(c['extra_knobs'])}\"",
           f"KNOBS=\"{' '.join(c['knobs'])}\""]
    for t in c["tools"]:
        env += [f"TOOL_{t}_PATH={tool_path(c, p, t)}", f"TOOL_{t}_SHA={c['tools'][t]['sha256']}"]
    for k, v in c["knobs"].items():
        env += [f"KNOB_{k}_DEFAULT={v['default']}",
                f"KNOB_{k}_VALUES=\"{' '.join(v['values'])}\""]
    req = scorer(kp).REQUIRED
    rq = "".join(f"{s}\t{f}\n" for s in stages(c) for f in req.get(s, ()))
    staged = [f for f in laptop_files(kp, c)]
    return {"run/session.env": "\n".join(env) + "\n", "run/required.tsv": rq,
            "run/staged.lst": "".join(f + "\n" for f in staged)}


def prepare(kp):
    kp = pathlib.Path(kp)
    (kp / "run").mkdir(exist_ok=True)
    for rel, text in generated(kp).items():
        (kp / rel).write_text(text)


# ---- the static guard ------------------------------------------------------------------------
def _code(path):
    out = []
    for i, ln in enumerate(pathlib.Path(path).read_text().splitlines(), 1):
        s = ln.strip()
        if s.startswith("#") or not s:
            continue
        out.append((i, re.sub(r"\s#\s.*$", "", ln)))
    return out


def guard(kp):
    """The findings of the static rules, each 'FILE:LINE: what'."""
    kp = pathlib.Path(kp)
    c = config(kp)
    bad = []
    if not re.fullmatch(r"[a-z][a-z0-9]{1,15}", c.get("prefix", "")):
        bad.append(f"session.toml: prefix {c.get('prefix')!r} is not a short lower-case name")
    if int(c.get("min_free_mb", 200)) < 200:
        bad.append("session.toml: min_free_mb below HACKING's 200")
    for t, d in c["tools"].items():
        if not re.fullmatch(r"[0-9a-f]{64}", d.get("sha256", "")):
            bad.append(f"session.toml: tool {t} has no sha256")
        if "path" in d and (d["path"].startswith("/") or ".." in d["path"]):
            bad.append(f"session.toml: tool {t}'s path is not under the laptop's home")
        if ("source" in d or "source_sha256" in d) and not (
                re.fullmatch(r"[0-9a-f]{7,40}:userspace/libsgxfive/tools/sgxfive-test\.c",
                             d.get("source", ""))
                and re.fullmatch(r"[0-9a-f]{64}", d.get("source_sha256", ""))):
            bad.append(f"session.toml: tool {t}'s source is not COMMIT:userspace/libsgxfive/"
                       "tools/sgxfive-test.c with its source_sha256")
    for t, d in c["tools"].items():
        why = d.get("no_source", "")
        if not d.get("wraps") and "source" not in d and (
                not why.strip() or why.strip().upper().startswith("TODO")):
            bad.append(f"session.toml: tool {t}: no `source` (with source_sha256) for the library "
                       "mock and no `no_source` reason: its rows would never be replayed there")
    for n, _, cm, path, sh, recipe in built_tools(c):
        if not (re.fullmatch(r"[0-9a-f]{40}", cm) and path and re.fullmatch(r"[0-9a-f]{64}", sh)
                and recipe):
            bad.append(f"session.toml: tool {n}'s built_from is not COMMIT:PATH (a full commit) "
                       "with built_sha256 and recipe")
    if c.get("health_tool") not in c["tools"]:
        bad.append("session.toml: health_tool is not one of [tools]")
    laptop = [f for f in ("kit/lib_kit.sh", "kit/run_stage.sh", "run/hooks.sh") if (kp / f).exists()]
    for f in laptop:
        hook = f == "run/hooks.sh"
        for i, ln in _code(kp / f):
            where = f"{f}:{i}"
            if re.search(FORBID, ln):
                bad.append(f"{where}: forbidden command: {ln.strip()}")
            if re.search(r"(^|[;&|\s])(while|until)\s", ln):
                bad.append(f"{where}: a wait loop (while/until)")
            if re.search(r"(^|[;&|\s])set\s+-[a-z]*f", ln):
                bad.append(f"{where}: set -f")
            if re.search(r"(^|[^a-z_A-Z])/tmp|TMPDIR", ln):
                bad.append(f"{where}: /tmp or TMPDIR (laptop files live under ~/scratch)")
            if re.search(r"(^|[^a-z_])timeout ", ln) and not re.search(r"timeout -k [0-9]", ln):
                bad.append(f"{where}: timeout without -k")
            if re.search(r"\$D/|\"\$D\"|\$\{D\}|/sys/kernel/debug", ln) and "sudo -n" not in ln \
                    and not re.match(r"\s*(D=\$KIT_DEBUGFS|D=\$DL|DL=/sys/kernel/debug/dri/0/sgx)\s*$", ln):
                bad.append(f"{where}: debugfs access without sudo -n")
            if re.search(r"python|perl", ln) and not re.search(
                    r"python3 (\"\$KIT/sessioncheck.py\" premise|-c 'import sys; sys.exit\(sys.version_info < \(3, 10\)\)')", ln):
                bad.append(f"{where}: python or perl on the laptop (only sessioncheck.py premise)")
            if hook and re.search(r"(^|[^a-z_])(rm|mktemp|mkfifo)( |$)", ln):
                bad.append(f"{where}: rm, mktemp or mkfifo in a hook (the kit owns the work directories)")
            if hook and re.search(r"dbg_write|knob_set|knobs_restore|reset_gpu|tee [^|]*\$D|>\s*\"?\$D", ln):
                bad.append(f"{where}: a debugfs write in a hook (the kit writes only reset and the declared knobs)")
            if hook and re.search(r"(^|[^a-z_])(ssh|scp|sudo) ", ln) and not re.search(r"sudo -n (timeout -k|cat)", ln):
                bad.append(f"{where}: ssh, scp or sudo in a hook")
            if hook and re.search(r"(^|[^a-z_])exit ", ln):
                bad.append(f"{where}: exit in a hook (a hook prints a reason; the runner stops)")
    if (kp / "run/hooks.sh").exists():
        for i, ln in _code(kp / "run/hooks.sh"):
            if re.search(r">>?\s*\"?\$(HOME|KEEP|BASE)", ln):
                bad.append(f"run/hooks.sh:{i}: a hook writes a kept or laptop file")
    readme = kp / "README.md"
    if readme.exists():
        for i, ln in enumerate(readme.read_text().splitlines(), 1):
            for cmd in re.findall(r"`((?:\./)?(?:kit|tests|run|gen|score)/[^`]*\.(?:sh|py)\b[^`]*)`", ln):
                bad.append(f"README.md:{i}: `{cmd}` leans on the exec bit: name its interpreter "
                           "(bash ..., python3 ...)")
    for g in c["files"].get("laptop", []):
        if pathlib.PurePosixPath(g).parts[:1] and pathlib.PurePosixPath(g).parts[0] in NOT_FROZEN_DIRS:
            bad.append(f"session.toml: laptop file {g} is under {'/, '.join(NOT_FROZEN_DIRS)}/, "
                       "which no freeze names")
    allowed = set(c["extra_knobs"]) | {f"dbg:{k}={v}" for k, d in c["knobs"].items()
                                       for v in d["values"]}
    forbid = list(FORBID_OPTIONS) + list(c["forbid_options"])
    have = set(laptop_files(kp, c))
    for s in stages(c):
        f = kp / "tables" / f"{s}.txt"
        if not f.exists():
            bad.append(f"tables/{s}.txt: no table for stage {s}")
            continue
        names = set()
        for i, ln in enumerate(f.read_text().splitlines(), 1):
            if not ln.strip() or ln.startswith("#"):
                continue
            where = f"tables/{s}.txt:{i}"
            parts = ln.split("|", 5)
            if len(parts) != 6:
                bad.append(f"{where}: not name|set|risk|knobs|tool|args")
                continue
            name, sset, risk, knobs, tool, args = parts
            if name in names or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
                bad.append(f"{where}: row name {name!r} repeated or not a plain name")
            names.add(name)
            words = knobs.split()
            for w in words:
                if not BASE_KNOBS.match(w) and w not in allowed:
                    bad.append(f"{where}: knob {w} is not the kit's nor session.toml's")
            if tool not in c["tools"]:
                bad.append(f"{where}: tool {tool} is not one of session.toml [tools]")
            bad += [f"{where}: {x}" for x in _wrapped(c, tool, args)]
            if sset == "control" and not any(w.startswith("reads:") for w in words):
                bad.append(f"{where}: a control row without reads: (a control that cannot fail)")
            if "gate" in words and not any(w.startswith("grp:") for w in words):
                bad.append(f"{where}: a gate row without its grp:")
            for o in forbid:
                if o == "--kpoke" and args.split()[:1] == ["probe"]:
                    continue
                if re.search(r"(^|\s)" + re.escape(o) + r"(\s|=|$)", args):
                    bad.append(f"{where}: forbidden option {o}")
            for m in re.findall(r"\$S/([A-Za-z0-9_./-]+)", args):
                if m not in have:
                    bad.append(f"{where}: $S/{m} is not a laptop file (session.toml [files] laptop)")
            try:
                shlex.split(args)
            except ValueError as e:
                bad.append(f"{where}: args do not parse: {e}")
            if re.search(r"/tmp|`|\$\(", args):
                bad.append(f"{where}: /tmp or a command substitution in args")
    return bad


def _wrapped(c, tool, args):
    """What is wrong with the laptop binaries a row's args name: every `$HOME/PATH` must be a tool
    of session.toml [tools] (the preflight checks only their sha256), and a tool declared
    `wraps = true` (regtimeline: `TOTAL LEAD REGS -- COMMAND...`) must run one of them, not a
    wrapper, as the command after `--`."""
    paths = {tool_path(c, c["prefix"], t): t for t in c["tools"]}
    bad = [f"$HOME/{h} is not a tool of session.toml [tools] (the preflight pins only those)"
           for h in re.findall(r"\$(?:HOME|\{HOME\})/([A-Za-z0-9_./-]+)", args) if h not in paths]
    if not c["tools"].get(tool, {}).get("wraps"):
        return bad
    try:
        toks = shlex.split(args)
    except ValueError:
        return bad
    if "--" not in toks or toks.index("--") + 1 >= len(toks):
        return bad + [f"the wrapper {tool} runs no command after --"]
    cmd = toks[toks.index("--") + 1]
    m = re.fullmatch(r"\$(?:HOME|\{HOME\})/(.+)", cmd)
    if m is None or m[1] not in paths:
        if m is None:
            bad.append(f"the command after -- of the wrapper {tool} is not $HOME/PATH of a tool "
                       f"of session.toml [tools]: {cmd}")
    elif c["tools"][paths[m[1]]].get("wraps"):
        bad.append(f"the command after -- of the wrapper {tool} is a wrapper itself: {cmd}")
    return bad


# ---- the freeze ------------------------------------------------------------------------------
def _pins(c):
    """[(repo, path)] of session.toml [freeze] pins."""
    out = []
    for p in c["freeze"].get("pins", []):
        repo, _, path = p.partition(":")
        if repo not in ("resgx545", "data") or not path:
            raise Stop(1, f"pin {p!r} is not resgx545:PATH or data:PATH")
        out.append((repo, path))
    return out


def built_tools(c):
    """[(name, binary sha256, commit, source path, source sha256, recipe)] of the [tools] that
    declare their source (new_session.py --tool-src: built_from = "COMMIT:PATH", built_sha256,
    recipe); the freeze binds each binary to it with a `built` line."""
    out = []
    for n, d in c["tools"].items():
        if "built_from" in d:
            cm, _, path = d["built_from"].partition(":")
            out.append((n, d["sha256"], cm, path, d.get("built_sha256", ""), d.get("recipe", "")))
    return out


def _commits(c):
    dirs = repo_dirs()
    out = {}
    for repo in ("resgx545", "data"):
        rev = c["freeze"].get(repo)
        if rev:
            full = git_commit(dirs[repo], rev)
            if full is None:
                raise Stop(1, f"{repo} {rev} is not a commit of {dirs[repo]}")
            out[repo] = full
    return out


def control_problems(kp):
    """scorekit's generator check on the tables' controls: every control reads something its
    row can produce (score.py's producible(row), when the scorer gives it)."""
    import kitscore
    sc = scorer(kp)
    out = []
    for s in stages(config(kp)):
        ctl = kitscore.controls(str(kp), s)
        prod = getattr(sc, "producible", None)
        out += scorekit.control_read_problems(ctl, prod or (lambda row: set(row["reads"])))
    return out


def freeze(kp):
    kp = pathlib.Path(kp)
    if (kp / "FROZEN.sha256").exists():
        raise Stop(1, "FROZEN.sha256 exists: a freeze is never rewritten")
    c = config(kp)
    prepare(kp)
    probs = guard(kp) + control_problems(kp)
    commits = _commits(c)
    if "resgx545" not in commits:
        probs.append("session.toml [freeze] names no resgx545 commit")
    dirs = repo_dirs()
    lines = []
    for rel, src in KIT_SOURCES.items():
        if "resgx545" not in commits:
            break
        blob = git_blob(dirs["resgx545"], commits["resgx545"], src)
        if not (kp / rel).exists():
            probs.append(f"{rel} is missing (new_session.py copies the kit)")
        elif blob is None or sha_bytes(blob) != sha_file(kp / rel):
            probs.append(f"{rel} is not resgx545 {commits['resgx545'][:12]}:{src} byte for byte")
        else:
            lines.append((sha_bytes(blob), commits["resgx545"], "resgx545", src))
    pins = []
    for repo, path in _pins(c):
        if repo not in commits:
            probs.append(f"pin {repo}:{path}: session.toml [freeze] names no {repo} commit")
            continue
        blob = git_blob(dirs[repo], commits[repo], path)
        if blob is None:
            probs.append(f"pin {repo}:{path} is not in {repo} {commits[repo][:12]}")
            continue
        h = sha_bytes(blob)
        lines.append((h, commits[repo], repo, path))
        pins.append((h, f"{dirs[repo]}/{path}"))
    built = []
    for n, tsha, cm, path, ssha, recipe in built_tools(c):
        blob = git_blob(dirs["resgx545"], cm, path)
        if blob is None or sha_bytes(blob) != ssha:
            probs.append(f"tool {n}: built_from {cm[:12]}:{path} is not the blob built_sha256 names")
        built.append(f"{tsha}  built  {cm}  {path}  {ssha}  {recipe}\n")
    if probs:
        raise Stop(1, "\n".join(probs))
    preds = sorted(f for f in freeze_files(kp) if f.startswith("predictions/"))
    if not preds:
        raise Stop(1, "no predictions/*.tsv: a frozen prediction comes before the run")
    (kp / "PREDICTIONS.sha256").write_text("".join(f"{sha_file(kp / f)}  {f}\n" for f in preds))
    rel = [(sha_file(kp / f), f) for f in freeze_files(kp)]
    bins = [(tsha, f"bin/{n}") for n, tsha, *_ in built_tools(c)]
    (kp / "FROZEN.sha256").write_text("".join(f"{h}  {f}\n" for h, f in rel + bins + pins))
    (kp / "FROZEN.commits").write_text(COMMITS_HEADER + "".join(
        f"{h}  {cm}  {repo}:{path}\n" for h, cm, repo, path in lines) + "".join(built))
    return f"frozen: {len(rel)} session files, {len(pins)} pins, {len(lines)} lines by commit"


def _repo_of(abspath, dirs):
    for repo in ("data", "resgx545"):
        d = str(dirs[repo]).rstrip("/") + "/"
        if abspath.startswith(d):
            return repo, abspath[len(d):]
    m = re.search(r"/resgx545-data/(.+)$", abspath) or None
    if m:
        return "data", m[1]
    m = re.search(r"/resgx545/(.+)$", abspath)
    return ("resgx545", m[1]) if m else (None, None)


def verify(kp):
    """The problems of the freeze (empty: verified)."""
    kp = pathlib.Path(kp)
    for f in ("FROZEN.sha256", "PREDICTIONS.sha256", "FROZEN.commits"):
        if not (kp / f).exists():
            return [f"not frozen: no {f} (session.py freeze)"]
    dirs = repo_dirs()
    bad = []
    commits = {}
    for ln in (kp / "FROZEN.commits").read_text().splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        b = BUILT.fullmatch(ln)
        if b:
            blob = git_blob(dirs["resgx545"], b[2], b[3])
            if blob is None or sha_bytes(blob) != b[4]:
                bad.append(f"FROZEN.commits: built source {b[2][:12]}:{b[3]} is not the blob "
                           f"{b[4][:12]}")
            continue
        m = LINE.fullmatch(ln)
        if not m:
            bad.append(f"FROZEN.commits: not '<sha256>  <commit>  <repo>:<path>': {ln!r}")
            continue
        h, cm, repo, path = m.groups()
        commits.setdefault((repo, path), set()).add(h)
        if repo not in dirs:
            continue
        blob = git_blob(dirs[repo], cm, path)
        if blob is None:
            bad.append(f"FROZEN.commits: {cm[:12]}:{repo}:{path} is not in the {repo} history")
        elif sha_bytes(blob) != h:
            bad.append(f"FROZEN.commits: {cm[:12]}:{repo}:{path} hashes to "
                       f"{sha_bytes(blob)[:12]}, not {h[:12]}")
    frozen = set()
    bins = {f"bin/{n}" for n, *_ in built_tools(config(kp))}
    for ln in (kp / "FROZEN.sha256").read_text().splitlines():
        h, _, f = ln.partition("  ")
        if f.startswith("/"):
            repo, path = _repo_of(f, dirs)
            if h not in commits.get((repo, path), ()):
                bad.append(f"{f}: no FROZEN.commits line pins it by commit")
            continue
        frozen.add(f)
        if f in bins:       # a built tool's binary is named by its freeze line, never shipped
            continue
        if not (kp / f).exists():
            bad.append(f"{f}: frozen, and gone")
        elif sha_file(kp / f) != h:
            bad.append(f"{f}: changed since the freeze")
    for rel, src in KIT_SOURCES.items():
        if (kp / rel).exists() and sha_file(kp / rel) not in commits.get(("resgx545", src), ()):
            bad.append(f"{rel}: not the copy FROZEN.commits pins")
    for f in freeze_files(kp):
        if f not in frozen:
            bad.append(f"{f}: not frozen (a new file is a change)")
    for ln in (kp / "PREDICTIONS.sha256").read_text().splitlines():
        h, _, f = ln.partition("  ")
        if not (kp / f).exists() or sha_file(kp / f) != h:
            bad.append(f"{f}: a prediction changed since the freeze")
    try:
        for rel, text in generated(kp).items():
            if (kp / rel).read_text() != text:
                bad.append(f"{rel}: not what session.toml and the scorer give (prepare)")
    except Exception as e:      # a scorer that no longer loads
        bad.append(f"the generated files cannot be checked: {e}")
    return bad


# ---- staging and the run ---------------------------------------------------------------------
def ssh_opts(c):
    """The options of every ssh to the laptop. The host key's alias is SGX_TARGET_HOST_KEY_ALIAS,
    else the HostKeyAlias of SGX_TARGET_SSH_OPTS (the bringup tools' variable, whose options
    are all passed), else session.toml's host_key_alias: ssh keeps the first value it is given
    for an option, so the kit's own BatchMode and bounds come first."""
    e = ENV or os.environ
    out = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15",
           "-o", "ServerAliveCountMax=4"]
    extra = shlex.split(e.get("SGX_TARGET_SSH_OPTS", ""))
    if e.get("SGX_TARGET_HOST_KEY_ALIAS"):
        out += ["-o", f"HostKeyAlias={e['SGX_TARGET_HOST_KEY_ALIAS']}"]
    elif not any(re.search(r"(?i)hostkeyalias", x) for x in extra):
        extra += ["-o", f"HostKeyAlias={c.get('host_key_alias', 'sgx-target')}"]
    return out + extra


def ssh_hint(c, r):
    """What a failed ssh to the laptop says: its status, its own last words and the variables
    that choose the host and its key."""
    err = r.stderr.decode(errors="replace") if isinstance(r.stderr, bytes) else (r.stderr or "")
    alias = [o.split("=", 1)[1] for o in ssh_opts(c) if o.lower().startswith("hostkeyalias=")]
    return (f"ssh exited {r.returncode}: {err.strip()[-300:] or '(no message)'}; the host is "
            f"SGX_TARGET_HOST ({host(c)}), its key's alias SGX_TARGET_HOST_KEY_ALIAS or the "
            f"HostKeyAlias of SGX_TARGET_SSH_OPTS, else session.toml's host_key_alias (now "
            f"{alias[0] if alias else 'none'})")


def host(c):
    return (ENV or os.environ).get("SGX_TARGET_HOST", c.get("host", "user@sgx-target"))


def ssh(c, cmd, limit, **kw):
    return bounded([*SSH, *ssh_opts(c), host(c), cmd], limit, **kw)


def tool_sha(c, t):
    return (ENV or os.environ).get(f"KIT_TOOL_SHA_{t}", c["tools"][t]["sha256"])


def stage(kp, say=print):
    kp = pathlib.Path(kp)
    c = config(kp)
    bad = guard(kp) + verify(kp)
    if bad:
        raise Stop(20, "staging refused:\n" + "\n".join(bad))
    lr = f"scratch/{c['prefix']}"
    files = laptop_files(kp, c) + staged_tools(c) + ["FROZEN.sha256"]
    r = ssh(c, f"mkdir -p {lr}/stage {lr}/out {lr}/run scratch/tmp", 60, capture_output=True)
    if r.returncode:
        raise Stop(1, f"STAGING FAILED: mkdir on the laptop: {ssh_hint(c, r)}")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for f in files:
            tar.add(str(kp / f), arcname=f, recursive=False)
    r = ssh(c, f"tar -xf - -C {lr}/stage", 300, input=buf.getvalue(), capture_output=True)
    if r.returncode:
        raise Stop(1, f"STAGING FAILED: the copy exited {r.returncode}: {r.stderr[-300:]!r}")
    tools = {t: tool_path(c, c["prefix"], t) for t in c["tools"]}
    chk = f"cd {lr}/stage && sha256sum {' '.join(files)} && cd && sha256sum {' '.join(tools.values())}"
    r = ssh(c, chk, 120, capture_output=True, text=True)
    if r.returncode:
        raise Stop(1, f"STAGING FAILED: the check of the laptop's copies exited {r.returncode}")
    got = {}
    for ln in r.stdout.splitlines():
        h, _, f = ln.partition("  ")
        got[f.lstrip("*")] = h
    for f in files:
        if got.get(f) != sha_file(kp / f):
            bad.append(f"{f} on the laptop is not the Mac's")
    for t, p in tools.items():
        if got.get(p) != tool_sha(c, t):
            bad.append(f"tool {t} (~/{p}) is not the pinned build {tool_sha(c, t)[:12]}")
    if bad:
        raise Stop(1, "STAGING FAILED:\n" + "\n".join(bad))
    say(f"staged {len(files)} files under ~/{lr}/stage; tools {', '.join(tools)} checked")


def _py(c):
    return (ENV or os.environ).get("PY") or c.get("python") or sys.executable


def run(kp, att=None, frm=None, only=None, out_root=None, say=print):
    """Run the stages; returns (status, {stage: runner status})."""
    kp = pathlib.Path(kp)
    c = config(kp)
    att = att or time.strftime("%Y%m%d-%H%M%S")
    out_root = pathlib.Path(out_root or kp / "out")
    root = out_root / att
    root.mkdir(parents=True, exist_ok=True)
    roots = [str(root)] + [str(d) for d in sorted(out_root.iterdir(), reverse=True)
                           if d.is_dir() and d != root]
    fsha = sha_file(kp / "FROZEN.sha256")
    lr = f"scratch/{c['prefix']}"
    py = _py(c)
    sc = str(kp / "score/score.py")
    todo = stages(c)
    if only:
        todo = [s for s in todo if s in only]
    elif frm:
        todo = todo[todo.index(frm):]
    rcs = {}
    say(f"attempt {att}: {root}; FROZEN.sha256 {fsha}")
    for st in todo:
        kept = root / st
        if kept.exists():
            return 39, rcs
        bad = verify(kp)
        if bad:
            say("FROZEN FILES CHANGED:\n" + "\n".join(bad))
            return 20, rcs
        if c["stages"][st].get("gate"):
            g = bounded([py, sc, "gate", st, *roots], 300, capture_output=True, text=True)
            (root / f"gate-{st}.txt").write_text(g.stdout + g.stderr)
            if g.returncode:
                say(f"SKIPPED: {st} (the gate is closed: gate-{st}.txt)")
                continue
        say(f"#### {st} {time.strftime('%H:%M:%S')}")
        alarm = int(c["stages"][st].get("alarm", 3600))
        r = ssh(c, f"bash {lr}/stage/kit/run_stage.sh {st} {fsha} {att}", alarm,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = r.stdout.decode(errors="replace") if isinstance(r.stdout, bytes) else r.stdout
        (root / f"{st}.log").write_text(log)
        rcs[st] = r.returncode
        for ln in log.splitlines():
            if ln.startswith(("## STOP", "## abort", "## end")):
                say(ln)
        cp = ssh(c, f"tar -cf - -C {lr}/out/{att} {st}", 300, capture_output=True)
        if cp.returncode == 0:
            with tarfile.open(fileobj=io.BytesIO(cp.stdout)) as tar:
                tar.extractall(root, filter="data")
        found = [ln for ln in log.splitlines() if sessioncheck.FINDING.search(ln)]
        if (kept / "runner.log").exists():
            found += [ln for ln in (kept / "runner.log").read_text(errors="replace").splitlines()
                      if sessioncheck.FINDING.search(ln) and ln not in found]
        if found:
            say("STOP: a laptop command or file was missing:\n" + "\n".join(found[:10]))
            return 45, rcs
        if r.returncode not in (0, 24):
            say(f"STOP: stage {st} exited {r.returncode} (see {root}/{st}.log)"
                + (f"; {ssh_hint(c, r)}" if r.returncode == 255 else ""))
            return r.returncode, rcs
        if cp.returncode:
            say(f"STOP: copying {lr}/out/{att}/{st} back failed ({cp.returncode})")
            return 37, rcs
        sk = bounded([py, str(kp / "kit/sessioncheck.py"), "kept", sc, st, str(kept),
                      "--call", "read_files"], 300, capture_output=True, text=True)
        (root / f"kept-{st}.txt").write_text(sk.stdout + sk.stderr)
        if sk.returncode:
            say(sk.stdout + f"STOP: a file the scorer of {st} reads was not kept")
            return 43, rcs
        s = bounded([py, sc, st, str(kept), *roots], 600, capture_output=True, text=True)
        (root / f"score-{st}.txt").write_text(s.stdout + s.stderr)
        if s.returncode or "SUMMARY:" not in s.stdout:
            say(f"STOP: the scorer of {st} exited {s.returncode} or printed no SUMMARY")
            return 38, rcs
        say("\n".join(ln for ln in s.stdout.splitlines() if ln.startswith("SUMMARY:")))
        if r.returncode == 0:
            p = bounded([py, sc, "premise", st, str(kept)], 300, capture_output=True, text=True)
            (root / f"premise-{st}.txt").write_text(p.stdout + p.stderr)
            if p.returncode:
                say(p.stdout + f"STOP: the premise of {st}: a control with no reading")
                return 44, rcs
        if r.returncode == 24:
            say(f"stage {st} stopped by its rule (rc 24): the next stage runs")
    say(f"{c['name']} done: {att}")
    return 0, rcs


# ---- the library mock ------------------------------------------------------------------------
LIBMOCK_TREES = ("userspace/libsgxfive", "include/uapi")


def libmock_build(kp, c, t):
    """(path, None) of the tool's library-mock build (sgxfive-test on libsgxfive's in-process
    mock, `--mock`) from session.toml's `source` at its commit, never a working tree: the
    source blob must hash to `source_sha256`; built once into debug/libmock/. (None, why)."""
    d = c["tools"][t]
    rev, _, src = d["source"].partition(":")
    main = repo_dirs()["resgx545"]
    commit = git_commit(main, rev)
    blob = git_blob(main, commit, src) if commit else None
    if blob is None:
        return None, f"{d['source']} is not in {main}"
    if sha_bytes(blob) != d["source_sha256"]:
        return None, (f"{rev}:{src} hashes to {sha_bytes(blob)[:12]}, not "
                      f"{d['source_sha256'][:12]} (source_sha256)")
    out = pathlib.Path(kp).resolve() / "debug/libmock" / f"{commit[:12]}-{d['source_sha256'][:12]}"
    binp = out / "sgxfive-test"
    if binp.exists():
        return binp, None
    shutil.rmtree(out, ignore_errors=True)
    (out / "src").mkdir(parents=True)
    a = bounded(["git", "-C", main, "archive", "-o", out / "src.tar", commit, *LIBMOCK_TREES],
                120, capture_output=True)
    if a.returncode:
        return None, f"git archive {commit[:12]} failed: {a.stderr[-200:]!r}"
    with tarfile.open(out / "src.tar") as tar:
        tar.extractall(out / "src", filter="data")
    lib = out / "src/userspace/libsgxfive"
    m = bounded(["make", "-s", "-C", lib, "build/sgxfive-test"], 600, capture_output=True)
    if m.returncode or not (lib / "build/sgxfive-test").exists():
        return None, f"the library-mock build at {commit[:12]} failed: {m.stderr[-300:]!r}"
    shutil.copy2(lib / "build/sgxfive-test", binp)
    return binp, None


def _expand(args, env):
    """The argv a row's args give in the runner's shell (`eval "set -- $args"`)."""
    r = bounded(["bash", "-c", 'eval "set -- $1"; printf "%s\\0" "$@"', "_", args], 60,
                capture_output=True, env=env)
    return r.stdout.decode().split("\0")[:-1] if r.returncode == 0 else None


def _takes_knobs(binp):
    """Whether the library mock lists --mock-knob in its usage (older sources do not)."""
    r = bounded([binp], 30, capture_output=True, text=True)
    return "--mock-knob" in r.stdout + r.stderr


def libmock(kp, say=print):
    """Every row's argv run through the library mock of its tool (the tool a wrapper runs after
    `--` included), as the kernel's interface checks it: a `job: rejected` line, a usage refusal
    (rc 2) or a crash is a finding, 'tables/STAGE.txt NAME: what'. A tool with no `source` in
    session.toml is said, not replayed. A row's `dbg:NAME=V` words are passed as `--mock-knob NAME=V`
    to a mock that lists that option, so a row whose knob state is wrong is the tool's own
    refusal (E934's twin). Returns the findings."""
    kp = pathlib.Path(kp).resolve()
    c = config(kp)
    paths = {tool_path(c, c["prefix"], t): t for t in c["tools"]}
    bins, bad, count = {}, [], {}
    for t, d in c["tools"].items():
        if d.get("wraps"):
            continue
        if "source" not in d:
            say(f"note libmock: {t} has no source in session.toml ({d.get('no_source', '')}): "
                "its rows are not replayed on the library mock")
            continue
        b, why = libmock_build(kp, c, t)
        if b is None:
            bad.append(f"{t}: {why}")
        else:
            bins[t] = b
    knobbed = {t: _takes_knobs(b) for t, b in bins.items()}
    if not bins:
        return bad
    top = pathlib.Path(tempfile.mkdtemp(prefix="libmock.", dir=kp / "debug"))
    home = top / "home"
    home.mkdir()
    n = 0
    for st in stages(c):
        for row in _rows(kp / "tables" / f"{st}.txt"):
            name, tool, args = row[0], row[4], row[5]
            n += 1
            w = top / f"{n}-{name}"
            (w / "w").mkdir(parents=True)
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
                   "W": str(w / "w"), "S": str(kp)}
            argv = _expand(args, env)
            where = f"tables/{st}.txt {name}"
            if argv is None:
                bad.append(f"{where}: the args do not expand")
                continue
            if c["tools"].get(tool, {}).get("wraps"):
                if "--" not in argv or argv.index("--") + 1 >= len(argv):
                    continue
                i = argv.index("--")
                tool = paths.get(os.path.relpath(argv[i + 1], home)) if argv[i + 1].startswith(
                    str(home) + "/") else None
                argv = argv[i + 2:]
            if tool not in bins:
                continue
            prev = None
            for a in argv:              # the runner makes the directories outdir_opts name
                if prev in c["outdir_opts"]:
                    pathlib.Path(a).parent.mkdir(parents=True, exist_ok=True)
                prev = a
            kn = [x for w in row[3].split() if w.startswith("dbg:") and knobbed[tool]
                  for x in ("--mock-knob", w[4:])]
            r = bounded([bins[tool], "--mock", *kn, *argv], 120, capture_output=True, text=True,
                        cwd=w, env=env)
            count[tool] = count.get(tool, 0) + 1
            rej = [ln for ln in r.stdout.splitlines() if ln.startswith("job: rejected")]
            if rej:
                bad.append(f"{where}: {rej[0]} (a kernel refusal on the library mock)")
            elif r.returncode == 2 and "usage" in r.stderr:
                bad.append(f"{where}: the tool's usage refusal: {r.stderr.splitlines()[0]}")
            elif r.returncode < 0 or r.returncode >= 128 or r.returncode == 142:
                bad.append(f"{where}: the library mock ended with status {r.returncode}")
    if not bad:
        for t, k in count.items():
            say(f"ok   libmock: {k} rows of {t} replayed on {c['tools'][t]['source']}, none "
                "refused")
    return bad


def _rows(f):
    out = []
    for ln in pathlib.Path(f).read_text().splitlines():
        if ln.strip() and not ln.startswith("#"):
            parts = ln.split("|", 5)
            if len(parts) == 6:
                out.append(parts)
    return out


# ---- the mock --------------------------------------------------------------------------------
def _copy_tree(kp, dest):
    def ignore(d, names):
        rel = pathlib.Path(d).relative_to(kp)
        return [n for n in names if (rel == pathlib.Path(".") and n in NOT_FROZEN_DIRS)
                or n == "__pycache__"]
    shutil.copytree(kp, dest, ignore=ignore)


def mock(kp, worlds=None, say=print):
    """Run every world of mock/world.py's EXPECT ({world: (driver status, {stage: runner
    status})}) on a fresh fake laptop; returns the number of findings."""
    global ENV, SSH
    kp = pathlib.Path(kp).resolve()
    c = config(kp)
    (kp / "debug").mkdir(exist_ok=True)
    top = pathlib.Path(tempfile.mkdtemp(prefix="mock.", dir=kp / "debug"))
    tree = top / "tree"
    _copy_tree(kp, tree)
    if not (tree / "FROZEN.sha256").exists():
        try:
            say("ok   " + freeze(tree) + " (the mock's copy)")
        except Stop as e:
            say(f"FAIL the mock's copy does not freeze:\n{e}")
            return 1
    lm = libmock(kp, say=say)
    if lm:
        for x in lm:
            say(f"FAIL libmock: {x}")
        say("mock: stopped before the worlds: a row the library mock refuses would be refused on "
            "the laptop")
        return 1
    world_py = tree / "mock/world.py"
    expect = load_module(world_py, "kit_world").EXPECT
    req = scorer(tree).REQUIRED
    fails = 0
    for w in worlds or list(expect):
        want_rc, want_st = expect[w]
        m = top / w
        home, real, dbg, fake = m / "home", m / "dbgreal", m / "dbg", m / "fake"
        for d in (home, real, dbg, fake, m / "bin"):
            d.mkdir(parents=True)
        for f in ["reset", "regs", *c["debugfs"]]:
            (real / f).write_text("")
        for k, d in c["knobs"].items():
            (real / k).write_text(d["default"] + "\n")
        (fake / "state").write_text("idle\n")
        (m / "kmsg").write_text("")
        (m / "srcv").write_text(c["srcversion"] + "\n")
        (m / "bin/python3").symlink_to(sys.executable)
        for f in (tree / "kit/fake").iterdir():
            f.chmod(0o755)      # the fake commands are found on PATH; a copy may drop the bits
        wrapper = (tree / "kit/fake/tool.sh").read_bytes()
        names = []
        env = dict(os.environ)
        for t in c["tools"]:
            p = home / tool_path(c, c["prefix"], t)
            if "stage_from" not in c["tools"][t]:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(wrapper)
                p.chmod(0o755)
            env[f"KIT_TOOL_SHA_{t}"] = sha_bytes(wrapper)
            names.append(f"{os.path.realpath(p)}={t}")
        dbg.chmod(0)
        fakebin = tree / "kit/fake"
        env.update(PATH=f"{fakebin}:{env.get('PATH', '/usr/bin:/bin')}",
                   KIT_FAKE_HOME=str(home), KIT_LAPTOP_PATH=f"{fakebin}:{m / 'bin'}:/usr/bin:/bin",
                   KIT_DEBUGFS=str(dbg), FAKE_DBGREAL=str(real), FAKE_DIR=str(fake),
                   KIT_KMSG=str(m / "kmsg"), KIT_SRCV_PATH=str(m / "srcv"), FAKE_SRCV=c["srcversion"],
                   KIT_PY=sys.executable, KIT_FAKE=str(fakebin), KIT_WORLD=str(world_py),
                   KIT_TOOL_NAMES=" ".join(names), FAKE_WORLD=w, RESET_WAIT="0", HEALTH_WAIT="0",
                   KIT_WRAPPERS=" ".join(t for t, d in c["tools"].items() if d.get("wraps")),
                   TEE_GRACE="30", SGX_TARGET_HOST="u@mock", PY=_py(c))
        ENV, SSH = env, [sys.executable, str(fakebin / "ssh.py")]
        log = []
        try:
            try:
                stage(tree, say=log.append)
                for t in c["tools"]:
                    if "stage_from" in c["tools"][t]:
                        p = home / tool_path(c, c["prefix"], t)
                        p.write_bytes(wrapper)
                        p.chmod(0o755)
                rc, rcs = run(tree, att=w, out_root=m / "out", say=log.append)
            except Stop as e:
                rc, rcs = e.code, {}
                log.append(str(e))
        finally:
            ENV, SSH = None, ["ssh"]
            dbg.chmod(0o755)
        probs = []
        if rc != want_rc:
            probs.append(f"driver {rc}, expected {want_rc}")
        for st, want in want_st.items():
            if rcs.get(st) != want:
                probs.append(f"stage {st} runner {rcs.get(st)}, expected {want}")
        lr = home / "scratch" / c["prefix"]
        tools = {os.path.realpath(home / tool_path(c, c["prefix"], t)) for t in c["tools"]}
        for p in home.rglob("*"):
            if p.is_file() and not str(p).startswith(str(lr) + "/") and os.path.realpath(p) not in tools:
                probs.append(f"a laptop file outside ~/scratch/{c['prefix']}: {p.relative_to(home)}")
        left = list((home / "scratch/tmp").iterdir()) if (home / "scratch/tmp").exists() else []
        if left:
            probs.append(f"left in ~/scratch/tmp: {[p.name for p in left]}")
        writes = (fake / "writes").read_text().splitlines() if (fake / "writes").exists() else []
        okw = {"reset 1"} | {f"{k} {v}" for k, d in c["knobs"].items() for v in d["values"]}
        probs += [f"a debugfs write the session does not allow: {x}" for x in writes if x not in okw]
        back = [k for k, d in c["knobs"].items()
                if (real / k).read_text().strip() != d["default"]]
        probs += [f"knob {k} not back at its default" for k in back]
        logs = [x for x in (m / "out" / w).rglob("*.log")] if (m / "out" / w).exists() else []
        for p in logs:
            probs += [f"{p.name}: {ln}" for ln in p.read_text(errors="replace").splitlines()
                      if sessioncheck.FINDING.search(ln)]
        probs += [ln for ln in log if sessioncheck.FINDING.search(ln) and ln not in probs]
        for st, src in rcs.items():
            kept = m / "out" / w / st
            if src == 0 and kept.exists():
                sc = load_module(tree / "score/score.py", "kit_session_score")
                probs += [f"kept {st}: {x}" for x in sessioncheck.kept_problems(
                    str(kept), req[st], sessioncheck.kept_rows(str(kept)),
                    lambda: sc.read_files(st, str(kept)))]
        staged_kit = lr / "stage/kit"
        if staged_kit.exists():
            probs += [f"staged: {x}" for x in sessioncheck.staged_problems(
                str(staged_kit), sorted(p.name for p in staged_kit.iterdir() if p.is_file()))]
        detail = f"driver {rc} ({', '.join(f'{s} {v}' for s, v in rcs.items()) or 'no stage ran'})"
        if probs:
            fails += 1
            say(f"FAIL world {w}: {detail}")
            for x in probs:
                say(f"     {x}")
            for ln in log:
                if ln.startswith(("STOP", "## STOP", "## abort", "STAGING", "FROZEN", "staging")):
                    say(f"     {ln.splitlines()[0]}")
        else:
            say(f"ok   world {w}: {detail}; laptop files under ~/scratch/{c['prefix']}, "
                f"{len(writes)} debugfs writes allowed, knobs back at their defaults")
    say(f"mock: {fails} world(s) failed; files in {top}")
    return fails


# ---- command line ----------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("guard", "prepare", "freeze", "verify", "stage"):
        sub.add_parser(n).add_argument("kp")
    s = sub.add_parser("run")
    s.add_argument("--from", dest="frm")
    s.add_argument("--only", nargs="+")
    s.add_argument("--att")
    s.add_argument("kp")
    s = sub.add_parser("mock")
    s.add_argument("--world", action="append")
    s.add_argument("kp")
    s = sub.add_parser("files")
    s.add_argument("--laptop", action="store_true")
    s.add_argument("kp")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "guard":
            bad = guard(a.kp)
            print("\n".join(bad) if bad else "guard: clean")
            return 1 if bad else 0
        if a.cmd == "prepare":
            prepare(a.kp)
            print("prepared: " + ", ".join(GENERATED))
            return 0
        if a.cmd == "freeze":
            print(freeze(a.kp))
            return 0
        if a.cmd == "verify":
            bad = verify(a.kp)
            print("\n".join(bad + ["FROZEN FILES CHANGED"]) if bad else "files verified")
            return 1 if bad else 0
        if a.cmd == "stage":
            stage(a.kp)
            return 0
        if a.cmd == "run":
            return run(a.kp, att=a.att, frm=a.frm, only=a.only)[0]
        if a.cmd == "mock":
            return 1 if mock(a.kp, a.world) else 0
        if a.cmd == "files":
            print("\n".join(laptop_files(a.kp) if a.laptop else freeze_files(a.kp)))
            return 0
    except Stop as e:
        print(e)
        return e.code
    return 2


if __name__ == "__main__":
    sys.exit(main())
