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
               the staged tree on a fake laptop under env -i, the fake tool answering by argv
               (mock/world.py), for every world of its EXPECT; no clock anywhere
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
NOT_FROZEN_DIRS = ("out", "debug")
NOT_FROZEN = ("FROZEN.sha256", "FROZEN.commits", "PREDICTIONS.sha256")
COMMITS_HEADER = """\
# FROZEN.commits: the commit that holds each file this session's FROZEN.sha256 pins outside the
# session (resgx545:PATH, data:PATH) and each byte copy of the kit (kit/ <- resgx545
# tools/closing). One line per file: the sha256, the commit, the repository and path. Verify a
# pin with `git -C <repository> show <commit>:<path> | sha256sum`. Written by the session kit's
# freeze (tools/closing/kit/session.py), the format tools/records/frozen.py checks.
"""
LINE = re.compile(r"([0-9a-f]{64})  ([0-9a-f]{7,40}|untracked)  ([a-z][a-z0-9-]*):(\S.*)")
SSH = ["ssh"]
ENV = None          # the environment of every command (the mock's; None: this process's)
BASE_KNOBS = re.compile(r"^(-|expectdiff|expectfault|after|soft|gate|grp:[a-z0-9]+|"
                        r"reads:[a-z0-9_]+(,[a-z0-9_]+)*)$")
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
            if sset == "control" and not any(w.startswith("reads:") for w in words):
                bad.append(f"{where}: a control row without reads: (a control that cannot fail)")
            if "gate" in words and not any(w.startswith("grp:") for w in words):
                bad.append(f"{where}: a gate row without its grp:")
            for o in forbid:
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
    if probs:
        raise Stop(1, "\n".join(probs))
    preds = sorted(f for f in freeze_files(kp) if f.startswith("predictions/"))
    if not preds:
        raise Stop(1, "no predictions/*.tsv: a frozen prediction comes before the run")
    (kp / "PREDICTIONS.sha256").write_text("".join(f"{sha_file(kp / f)}  {f}\n" for f in preds))
    rel = [(sha_file(kp / f), f) for f in freeze_files(kp)]
    (kp / "FROZEN.sha256").write_text("".join(f"{h}  {f}\n" for h, f in rel + pins))
    (kp / "FROZEN.commits").write_text(COMMITS_HEADER + "".join(
        f"{h}  {cm}  {repo}:{path}\n" for h, cm, repo, path in lines))
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
    for ln in (kp / "FROZEN.sha256").read_text().splitlines():
        h, _, f = ln.partition("  ")
        if f.startswith("/"):
            repo, path = _repo_of(f, dirs)
            if h not in commits.get((repo, path), ()):
                bad.append(f"{f}: no FROZEN.commits line pins it by commit")
            continue
        frozen.add(f)
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
    alias = (ENV or os.environ).get("SGX_TARGET_HOST_KEY_ALIAS", c.get("host_key_alias", "sgx-target"))
    return ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=4", "-o", f"HostKeyAlias={alias}"]


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
        raise Stop(1, f"STAGING FAILED: mkdir on the laptop exited {r.returncode}")
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
            say(f"STOP: stage {st} exited {r.returncode} (see {root}/{st}.log)")
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
