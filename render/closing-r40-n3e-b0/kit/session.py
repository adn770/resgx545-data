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
  lint    KP   the controls' premises (round 34): WARN a constant frozen for a register the kit
               snapshots (use "@snap0" or "@snap0:ROW") or for a sample interval (use "@cal:STAGE",
               a calibration stage of the same register set that runs first); exit 1 on an @snap0
               or @cal form that names no row or stage, a stage not before, or another register
               set; and the owntask stages (round 36): the blob present and the sha256 the
               resgx545 asm/fwtask/fwtask.map gives it, the arm line, the stage flagged, the
               rows' jobs and knobs. freeze prints the warnings and refuses the errors
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

Exit status of run: the laptop runner's own (kit/run_stage.sh: 1 preflight ... 26 own-task arm)
for a stage that stopped (after the copy back), and 20 the freeze does not verify, 38 the scorer
failed or printed no SUMMARY, 39 the attempt's stage directory exists, 43 a file the scorer
reads was not kept, 44 the premise (a control with no reading), 45 a laptop command or file was
missing (a "command not found" or "No such file" line in the stage's log), 142 a bounded command
reached its limit. A runner status 24 (the stage stopped by its rule) goes on to the next stage,
unless the stage declares `on_stop = "end"` in session.toml: then the session ends there, status
24.
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

sys.dont_write_bytecode = True     # no __pycache__ beside the kit (scratch dirs cannot be cleaned)
KITDIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KITDIR))
import sessioncheck  # noqa: E402
import scorekit  # noqa: E402

# the kit files of a session's kit/ and their sources in the resgx545 tree
KIT_SOURCES = {f"kit/{n}": f"tools/closing/kit/{n}" for n in (
    "session.py", "lib_kit.sh", "run_stage.sh", "kitscore.py", "fake/sudo", "fake/timeout",
    "fake/df", "fake/modinfo", "fake/sha256sum", "fake/tool.sh", "fake/tool.py", "fake/ssh.py",
    "fake/fwtask.py")}
KIT_SOURCES.update({"kit/scorekit.py": "tools/closing/scorekit.py",
                    "kit/sessioncheck.py": "tools/closing/sessioncheck.py",
                    # the own-task runner of phase 11.29 (arm, run, page, gate, reset), reused
                    # as it is by an owntask stage (round 36), never reimplemented in the kit
                    "kit/fwtask_run.py": "tools/fwtask/fwtask_run.py"})
LAPTOP_KIT = ("kit/lib_kit.sh", "kit/run_stage.sh", "kit/sessioncheck.py", "kit/scorekit.py",
              "kit/fwtask_run.py")
GENERATED = ("run/session.env", "run/required.tsv", "run/staged.lst", "run/owntask.tsv")
# the session subtrees no freeze names: out/ (kept records, lead logs), debug/ (the mock, the
# library mock) and fold/ (the fold's post-run notes and tables); no laptop file comes from them
NOT_FROZEN_DIRS = ("out", "debug", "fold")
# directories a tool leaves in a session as it runs: never session files, wherever they sit
SKIP_PARTS = {"__pycache__", ".pytest_cache"}
# run.log and stage.log at the top: the logs older sessions teed there (r9-x to r18-flag),
# published so; the driver now writes its own under out/ (run: out/ATTEMPT/run.log, stage:
# out/stage.log)
NOT_FROZEN = ("FROZEN.sha256", "FROZEN.commits", "PREDICTIONS.sha256", "run.log", "stage.log")
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
# the kit's knob words; expect:NAME are kitscore.OUTCOMES (run_stage.sh classifies them);
# idle:S takes 1 to 120 seconds
BASE_KNOBS = re.compile(r"^(-|expectdiff|expectfault|after|soft|gate|noreset|grp:[a-z0-9]+|"
                        r"pre:miscinfo|"
                        r"idle:([1-9]|[1-9][0-9]|1[01][0-9]|120)|"
                        r"expect:(rc3-overflow|rc0-overflow)|reads:[a-z0-9_]+(,[a-z0-9_]+)*)$")
# a stage's on_stop: what follows its runner status 24 (next: the next stage runs; end: the
# session ends there)
ON_STOP = ("next", "end")
# --kpoke is probe's kernel poke, no riskier than tri's --kpoke-render: allowed on `probe` rows only
FORBID_OPTIONS = ("--kpoke", "--kreg", "--clkgate", "--trc-hazard")
# options whose tool writes a debugfs knob itself (the kernel takes it): the session declares
# the knob at default 0, so the preflight checks the loaded module has it and the exit trap puts
# it back should a tool die before the kernel took it
TOOL_KNOBS = {"--final-pb-pages": "render_final_pb_pages"}
FORBID = (r"reboot|shutdown|poweroff|kexec|grub|mkinitcpio|(^|[^a-z_-])make |gcc|(^|[^a-z])cc |"
          r"push-gma500|deploy-tool|trc_hazard|CLKGATE|clkgate|"
          r"kregnow|kicker|kpoke|/dev/mem|git |\| *tail|\|\| *true")
# the debugfs register write (kreg, kreg_set, kregs_restore): never in a hook; in the kit's own
# runner only as KREG_LINES, its one write and its one read of debugfs kreg
FORBID_KREG = r"(^|[^a-z0-9])kregs?([^a-z0-9-]|$)"
KREG_LINES = ("""printf '%s=%s\\n' "$1" "$2" | sudo -n timeout -k 5 20 tee "$D/kreg" >/dev/null""",
              """dbg_cat kreg | awk -v o="$1" '$1 == o { print $2; exit }'""")
# kreg:OFF=V (round 29, Q024): the registers a row may write through debugfs kreg, frozen here and
# in run_stage.sh's KIT_KREGS: {offset: (the value the runner restores, the largest value)}.
# CR_PDS_REG_0A78 alone: E045 drew every value 0x00-0x3f exactly; 0x2c is the firmware's (E141).
KREG_ALLOWED = {"0x0a78": ("0x2c", 0x3f)}
KREG_WORD = re.compile(r"^kreg:(0x[0-9a-f]{4})=(0x[0-9a-f]{1,8})$")
# pre:miscinfo (round 32, Q111): the debugfs miscinfo read after the row's reset and before snap0,
# which sends the firmware one GETMISCINFO command (fork 8bc0877e8603, sgxfive_miscinfo): a read,
# so any stage, but the only kit read that kicks the firmware; in the kit's runner only as
# MISCINFO_LINE, never in a hook; its file must exist on the laptop (DEBUGFS_NEED)
MISCINFO_WORD = "pre:miscinfo"
MISCINFO_LINE = 'sudo -n timeout -k 5 10 cat "$D/miscinfo" > "$JW/miscinfo.out" 2>&1; r=$?'
MISCINFO_USE = r"\$\{?D\}?/miscinfo|dbg_cat +miscinfo|miscinfo_read"
# a stage's class: safe (the default), or flagged (a planned fault or hang, a register write of
# ours): every flagged stage runs after every safe one, and only a flagged stage writes a kreg
STAGE_CLASSES = ("safe", "flagged")
# owntask (round 36, the round-33 emitpds design's kit job): a stage that runs one of our
# own firmware (EDM) tasks through the kit's copy of tools/fwtask/fwtask_run.py. session.toml
# declares it on the stage, `owntask = { blob = "emitsa", arm = "slots=0x1 entry=0" }`; the
# session holds the blob as owntask/BLOB.blob (tools/fwtask/fwtask.py OUTDIR asm/fwtask/BLOB.s),
# whose sha256 must be the one asm/fwtask/fwtask.map gives BLOB at the freeze's resgx545 commit
# (the freeze pins the map). Its rows are `name|set|risk|-|owntask|{"cmd": N, "params": {...},
# "timeout_ms": T}`: one command a job. The runner arms once after the stage's first health,
# runs each job with no reset before it (a reset disarms), dumps the results page and runs the
# health gate after each, and disarms with fwtask_run.py's reset at the stage's end. An
# owntask stage is a planned firmware break if wrong: it must be flagged.
OWNTASK_TOOL = "owntask"
OWNTASK_MAP = "asm/fwtask/fwtask.map"
OWNTASK_KEYS = ("blob", "arm")
# own_arm's line as the phase 11.29-11.33 runner writes it (run_stage.py): one entry per slot of
# the mask; trc 32 and up need the hazard word (run_stage.py TRC_HAZARD_FROM, E540), never armed
# from the kit; pds= names the kernel's emitpds image, none the first (v1): crumb (round 37, N3b
# step B: three tim breadcrumbs), halt and crumb3 (round 38, N3c rows R5 and R4); pdsat=fw14 puts
# the image in the slack of the firmware's PDS #14 page (N3c R4 and R6), none in the kernel's own;
# pds2=req sets the emit's s2 to the request #14 emits with, none 0, and form=fw14 arms a blob
# whose emit is the word with #14's sideband, none our own word (round 39, N3d row Z); round 40
# (N3e §3.2): form= names any word of the kernel's list (tools/fwtask/fwtask.py EMIT_SIDEBANDS,
# own the default, never spelled) and pds=land the image of two douta markers to sa24 and sa26
OWNTASK_FORMS = ("sb001", "sb002", "sb003", "sb040", "sb041", "sb042", "sb043", "sb800", "sb801",
                 "sb802", "sb803", "sb840", "sb841", "sb842", "fw14", "sbc43", "sb403")
OWNTASK_ARM = re.compile(r"slots=0x([0-9a-f]{1,2}) entry=([0-9]{1,2}(?:,[0-9]{1,2})*)"
                         r"(?: trc=([0-9]{1,2}))?(?: pds=(crumb|halt|crumb3|land))?(?: pdsat=(fw14))?"
                         r"(?: pds2=(req))?(?: form=(" + "|".join(OWNTASK_FORMS) + r"))?")
OWNTASK_TRC_MAX = 31
# ticks (a bool): the runner reads HostCtl dword 12 before the command and after the window;
# kick (round 39, N3d row K): "miscinfo", the one host kick the runner makes right after the
# command write (K0, then one debugfs miscinfo read, a GETMISCINFO kick), nothing else
OWNTASK_JOB_KEYS = ("cmd", "params", "timeout_ms", "ticks", "kick")
OWNTASK_KICKS = ("miscinfo",)
# the results page (tools/fwtask/layout.py): 1024 dwords, 0-5 the protocol's (magic, cmd, state,
# run id, overlap, run id echo), which a job's params never write
OWNTASK_PAGE = 1024
OWNTASK_PROTOCOL = 6
OWNTASK_WORDS = re.compile(r"^(-|reads:[a-z0-9_]+(,[a-z0-9_]+)*)$")
# the one laptop line that runs python besides sessioncheck premise: lib_kit.sh's owntask_call
OWNTASK_LINE = ('sudo -n timeout -k 10 "$5" env FWTASK_HEALTH_TOOL="$ht" python3 '
                '"$KIT/fwtask_run.py" "$1" "$2" > "$3" 2> "$4" </dev/null')
OWNTASK_USE = r"owntask_call|fwtask_run"
# the debugfs files the kit's fwtask_run.py reads or writes (arm, run, page, gate, reset): the
# preflight of a session with an owntask stage wants them all in the loaded driver
OWNTASK_DEBUGFS = ["own_code", "own_arm", "own_res", "load", "boot", "status", "miscinfo",
                   "kreg"]


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
    c.setdefault("kregs", {})
    return c


def uses_miscinfo(kp, c=None):
    """Whether a row of any stage's table has the word pre:miscinfo."""
    kp = pathlib.Path(kp)
    c = c or config(kp)
    return any(MISCINFO_WORD in r[3].split() for s in stages(c)
               if (kp / "tables" / f"{s}.txt").exists()
               for r in _rows(kp / "tables" / f"{s}.txt"))


def debugfs_need(kp, c=None):
    """The debugfs files the preflight wants besides reset, regs and the knobs: session.toml's
    debugfs = [...], miscinfo when a row reads it (pre:miscinfo), and the files fwtask_run.py
    uses when a stage is an owntask stage (OWNTASK_DEBUGFS)."""
    c = c or config(kp)
    out = [*c["debugfs"], *(["miscinfo"] if uses_miscinfo(kp, c) else [])]
    if owntask_stages(c):
        out += OWNTASK_DEBUGFS
    return list(dict.fromkeys(out))


def flagged_stages(c):
    return [s for s in stages(c) if c["stages"][s].get("class", "safe") == "flagged"]


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
    out += [f"owntask/{d.get('blob')}.blob" for d in owntask_stages(c).values()
            if isinstance(d, dict) and isinstance(d.get("blob"), str)]
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
        if SKIP_PARTS & set(rel.parts) or p.suffix == ".pyc" or p.name == ".DS_Store":
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
           f"DEBUGFS_NEED=\"{' '.join(debugfs_need(kp, c))}\"",
           f"OUTDIR_OPTS=\"{' '.join(c['outdir_opts'])}\"",
           f"EXTRA_KNOBS=\"{' '.join(c['extra_knobs'])}\"",
           f"KNOBS=\"{' '.join(c['knobs'])}\"",
           f"KREGS=\"{' '.join(c['kregs'])}\"",
           f"FLAGGED_STAGES=\"{' '.join(flagged_stages(c))}\""]
    for t in c["tools"]:
        env += [f"TOOL_{t}_PATH={tool_path(c, p, t)}", f"TOOL_{t}_SHA={c['tools'][t]['sha256']}"]
    for k, v in c["knobs"].items():
        env += [f"KNOB_{k}_DEFAULT={v['default']}",
                f"KNOB_{k}_VALUES=\"{' '.join(v['values'])}\""]
    for r, v in c["kregs"].items():
        env += [f"KREG_{r}_VALUES=\"{' '.join(v.get('values', []))}\""]
    req = scorer(kp).REQUIRED
    rq = "".join(f"{s}\t{f}\n" for s in stages(c) for f in req.get(s, ()))
    staged = [f for f in laptop_files(kp, c)]
    return {"run/session.env": "\n".join(env) + "\n", "run/required.tsv": rq,
            "run/staged.lst": "".join(f + "\n" for f in staged),
            "run/owntask.tsv": owntask_table(kp, c)}


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
    for st, d in c["stages"].items():
        if d.get("on_stop", "next") not in ON_STOP:
            bad.append(f"session.toml: stage {st}: on_stop {d['on_stop']!r} is not one of "
                       f"{', '.join(ON_STOP)}")
    seen_flagged = None
    for st, d in c["stages"].items():
        cls = d.get("class", "safe")
        if cls not in STAGE_CLASSES:
            bad.append(f"session.toml: stage {st}: class {cls!r} is not one of "
                       f"{', '.join(STAGE_CLASSES)}")
        elif cls == "flagged":
            seen_flagged = seen_flagged or st
        elif seen_flagged:
            bad.append(f"session.toml: stage {seen_flagged} is flagged and runs before the safe "
                       f"stage {st}: every flagged stage runs after every safe stage")
    bad += _kreg_decl(c)
    bad += owntask_problems(kp, c)
    if c.get("health_tool") not in c["tools"]:
        bad.append("session.toml: health_tool is not one of [tools]")
    try:
        req = scorer(kp).REQUIRED
    except Exception:       # a scorer that does not load is the freeze's and the mock's finding
        req = {}
    for st, files in req.items():
        for f in files:
            if scorekit.required_entry(f) is None:
                bad.append(f"score/score.py: REQUIRED[{st!r}] entry {f!r} is neither a file, a "
                           f"\".suffix\" nor \"CLASS:.suffix\" of {', '.join(scorekit.ROW_CLASSES)}")
    laptop = [f for f in ("kit/lib_kit.sh", "kit/run_stage.sh", "run/hooks.sh") if (kp / f).exists()]
    for f in laptop:
        hook = f == "run/hooks.sh"
        for i, ln in _code(kp / f):
            where = f"{f}:{i}"
            if re.search(FORBID, ln) or (re.search(FORBID_KREG, ln) and (
                    hook or ("$D/kreg" in ln or "dbg_cat kreg" in ln)
                    and ln.strip() not in KREG_LINES)) or (re.search(MISCINFO_USE, ln) and (
                    hook or re.search(r"\$\{?D\}?/miscinfo|dbg_cat +miscinfo", ln)
                    and ln.strip() != MISCINFO_LINE)):
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
                    r"python3 (\"\$KIT/sessioncheck.py\" (premise|ownok)|-c 'import sys; sys.exit\(sys.version_info < \(3, 10\)\)')", ln) \
                    and (hook or ln.strip() != OWNTASK_LINE):
                bad.append(f"{where}: python or perl on the laptop (only sessioncheck.py premise)")
            if hook and re.search(r"(^|[^a-z_])(rm|mktemp|mkfifo)( |$)", ln):
                bad.append(f"{where}: rm, mktemp or mkfifo in a hook (the kit owns the work directories)")
            if hook and re.search(r"dbg_write|knob_set|knobs_restore|reset_gpu|tee [^|]*\$D|>\s*\"?\$D", ln):
                bad.append(f"{where}: a debugfs write in a hook (the kit writes only reset and the declared knobs)")
            if hook and re.search(r"(^|[^a-z_])(ssh|scp|sudo) ", ln) and not re.search(r"sudo -n (timeout -k|cat)", ln):
                bad.append(f"{where}: ssh, scp or sudo in a hook")
            if hook and re.search(OWNTASK_USE, ln):
                bad.append(f"{where}: an own-task call in a hook (the kit's runner alone arms, "
                           "runs, gates and disarms)")
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
            bad += [f"{where}: {x}" for x in _kreg_words(c, s, words)]
            for w in words:
                if w.startswith("kreg:"):
                    continue
                if not BASE_KNOBS.match(w) and w not in allowed:
                    bad.append(f"{where}: knob {w} is not the kit's nor session.toml's"
                               + (" (idle:S takes 1 to 120 seconds)" if w.startswith("idle:")
                                  else ""))
            if "noreset" in words and not names - {name}:
                bad.append(f"{where}: noreset on the stage's first row (no row before it whose "
                           "state it could keep)")
            if words.count(MISCINFO_WORD) > 1:
                bad.append(f"{where}: more than one {MISCINFO_WORD} word (one pre:miscinfo a row)")
            if MISCINFO_WORD in words and "noreset" in words:
                bad.append(f"{where}: {MISCINFO_WORD} with noreset (the read follows the row's "
                           "reset)")
            if sum(w.startswith("idle:") for w in words) > 1:
                bad.append(f"{where}: more than one idle: word (one idle:S a row)")
            if tool not in c["tools"] and tool != OWNTASK_TOOL:
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
            for o, k in TOOL_KNOBS.items():
                if re.search(r"(^|\s)" + re.escape(o) + r"(\s|=|$)", args) and \
                        not _zero(c["knobs"].get(k, {}).get("default")):
                    bad.append(f"{where}: {o} writes debugfs {k}: declare it in session.toml "
                               f'[knobs] at default "0" ({k} = {{ default = "0", values = '
                               '["0"] }): the preflight checks the module has it, the exit '
                               "trap puts it back")
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


def _kreg_decl(c):
    """What is wrong with session.toml [kregs]: a register off the kit's KREG_ALLOWED, a value
    not 0xHEX (lower case) or above the register's largest, a default (the kit's alone)."""
    bad = []
    for r, d in c["kregs"].items():
        if r not in KREG_ALLOWED:
            bad.append(f"session.toml: [kregs] {r} is not on the kit's allow-list "
                       f"({', '.join(KREG_ALLOWED)})")
            continue
        extra = sorted(set(d) - {"values"})
        if extra:
            bad.append(f"session.toml: [kregs] {r} declares {', '.join(extra)}: only values "
                       f"(the default is the kit's, {KREG_ALLOWED[r][0]})")
        for v in d.get("values", []):
            if not re.fullmatch(r"0x[0-9a-f]{1,8}", v):
                bad.append(f"session.toml: [kregs] {r} value {v!r} is not 0x and lower-case hex")
            elif int(v, 16) > KREG_ALLOWED[r][1]:
                bad.append(f"session.toml: [kregs] {r} value {v} is above its largest, "
                           f"{KREG_ALLOWED[r][1]:#04x}")
    return bad


def _kreg_words(c, st, words):
    """What is wrong with a row's kreg:OFF=V words: a stage that is not flagged, a register or
    value session.toml [kregs] does not declare, more than one, or with expectfault (a fault or
    hang with our register written is a stop, never a reading)."""
    ks = [w for w in words if w.startswith("kreg:")]
    if not ks:
        return []
    bad = []
    if c["stages"][st].get("class", "safe") != "flagged":
        bad.append(f"{' '.join(ks)} in stage {st}, which is not flagged (class = \"flagged\"): "
                   "only a flagged stage writes a register")
    for w in ks:
        m = KREG_WORD.match(w)
        if not m or m[1] not in c["kregs"] or m[1] not in KREG_ALLOWED or \
                m[2] not in c["kregs"][m[1]].get("values", []):
            bad.append(f"knob {w} is not kreg:0xOFFS=0xV of a register and value session.toml "
                       "[kregs] declares")
    if len(ks) > 1:
        bad.append("more than one kreg word (one kreg:OFF=V a row)")
    if "expectfault" in words:
        bad.append("kreg with expectfault: a fault or hang with our register written is a stop")
    return bad


def _zero(v):
    """Whether a knob's default reads as the number 0 (0, 0x0, 00)."""
    try:
        return v is not None and int(str(v), 0) == 0
    except ValueError:
        return False


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


# ---- owntask: one of our own firmware tasks (round 36) -----------------------------------------
def owntask_stages(c):
    """{stage: its owntask table} of the stages that declare one."""
    return {s: d["owntask"] for s, d in c["stages"].items() if "owntask" in d}


def owntask_map(c):
    """(the fwtask.map of the freeze's resgx545 commit as a dict, None) or (None, why)."""
    import json
    rev = c["freeze"].get("resgx545")
    main = repo_dirs()["resgx545"]
    commit = git_commit(main, rev) if rev else None
    if commit is None:
        return None, f"session.toml [freeze] names no resgx545 commit of {main} to read " \
                     f"{OWNTASK_MAP} at"
    blob = git_blob(main, commit, OWNTASK_MAP)
    if blob is None:
        return None, f"{OWNTASK_MAP} is not in resgx545 {commit[:12]}"
    try:
        return json.loads(blob), None
    except ValueError:
        return None, f"{OWNTASK_MAP} at resgx545 {commit[:12]} is not JSON"


def owntask_arm_problem(arm):
    """Why an own_arm line is not one the kit arms (None: it is)."""
    m = OWNTASK_ARM.fullmatch(arm) if isinstance(arm, str) else None
    if m is None:
        return (f"arm {arm!r} is not `slots=0xMASK entry=E[,E...]` with an optional `trc=T` "
                "and optional `pds=crumb|halt|crumb3|land`, `pdsat=fw14`, `pds2=req` and "
                f"`form={'|'.join(OWNTASK_FORMS)}`, "
                "in that order "
                "(lower-case hex mask, decimal entries)")
    mask, entries, trc = int(m[1], 16), m[2].split(","), m[3]
    if mask == 0:
        return f"arm {arm!r} arms no slot (slots=0x0)"
    if len(entries) != bin(mask).count("1"):
        return f"arm {arm!r} gives {len(entries)} entries for {bin(mask).count('1')} slots"
    if trc is not None and not 1 <= int(trc) <= OWNTASK_TRC_MAX:
        return (f"arm {arm!r}: trc {trc} is out of 1 to {OWNTASK_TRC_MAX} (32 and up need the "
                "hazard word, which the kit never arms)")
    return None


def owntask_job(args, job_timeout):
    """(the job fwtask_run.py run takes: {n, params, timeout_ms[, ticks][, kick]}, []) of an owntask
    row's args, or (None, [what is wrong])."""
    import json
    try:
        a = json.loads(args)
    except ValueError:
        a = None
    if not isinstance(a, dict):
        return None, [f"args {args!r} are not a JSON object "
                      '{"cmd": N, "params": {...}, "timeout_ms": T}']
    bad = [f"args key {k!r} is not one of {', '.join(OWNTASK_JOB_KEYS)}"
           for k in a if k not in OWNTASK_JOB_KEYS]
    cmd, params, tmo = a.get("cmd"), a.get("params", {}), a.get("timeout_ms")
    if type(cmd) is not int or not 1 <= cmd <= 0xffff:
        bad.append(f"cmd {cmd!r} is not a command number 1 to 0xffff (0 is the tick's own "
                   "tail call)")
    if not isinstance(params, dict):
        bad.append(f"params {params!r} is not an object {{dword: value}}")
        params = {}
    for k, v in params.items():
        vals = v if isinstance(v, list) else [v]
        if not (k.isdigit() and OWNTASK_PROTOCOL <= int(k) < OWNTASK_PAGE
                and int(k) + len(vals) <= OWNTASK_PAGE):
            bad.append(f"params dword {k!r} is not {OWNTASK_PROTOCOL} to {OWNTASK_PAGE - 1} "
                       "(0-5 are the protocol's: magic, cmd, state, run id, overlap, echo)")
        if not vals or any(type(x) is not int or not 0 <= x <= 0xffffffff for x in vals):
            bad.append(f"params dword {k}: {v!r} is not a 32-bit value or a list of them")
    if type(tmo) is not int or not 1 <= tmo <= job_timeout * 1000:
        bad.append(f"timeout_ms {tmo!r} is not 1 to {job_timeout * 1000} (job_timeout)")
    if "ticks" in a and type(a["ticks"]) is not bool:
        bad.append(f"ticks {a['ticks']!r} is not true or false")
    if "kick" in a and a["kick"] not in OWNTASK_KICKS:
        bad.append(f"kick {a['kick']!r} is not one of {', '.join(OWNTASK_KICKS)}")
    if bad:
        return None, bad
    job = {"n": cmd, "params": params, "timeout_ms": tmo}
    for k in ("ticks", "kick"):
        if k in a:
            job[k] = a[k]
    return job, []


def owntask_problems(kp, c=None):
    """What is wrong with the session's owntask stages and rows, each 'WHERE: what'."""
    import kitscore
    kp = pathlib.Path(kp)
    c = c or config(kp)
    bad = []
    own = owntask_stages(c)
    if OWNTASK_TOOL in c["tools"]:
        bad.append(f"session.toml: [tools] {OWNTASK_TOOL}: the name is reserved for the kit's "
                   "owntask rows")
    m, why = owntask_map(c) if own else ({}, None)
    jt = int(c.get("job_timeout", 120))
    for st in stages(c):
        d = own.get(st)
        where = f"session.toml: stage {st}"
        if d is not None:
            if not isinstance(d, dict):
                bad.append(f"{where}: owntask is not a table {{ blob, arm }}")
                d = {}
            extra = sorted(set(d) - set(OWNTASK_KEYS))
            if extra:
                bad.append(f"{where}: owntask declares {', '.join(extra)}: it takes "
                           f"{' and '.join(OWNTASK_KEYS)} only")
            if c["stages"][st].get("class", "safe") != "flagged":
                bad.append(f"{where}: an owntask stage is not flagged (class = \"flagged\"): "
                           "an own firmware task is a planned firmware break if wrong")
            blob = d.get("blob")
            if not (isinstance(blob, str) and re.fullmatch(r"[a-z0-9_]+", blob)):
                bad.append(f"{where}: owntask has no blob (a name of {OWNTASK_MAP})")
            elif m is None:
                bad.append(f"{where}: {why}")
            elif not isinstance(m.get(blob), dict) or "sha256" not in m[blob]:
                bad.append(f"{where}: blob {blob!r} is not in {OWNTASK_MAP}")
            elif not (kp / "owntask" / f"{blob}.blob").is_file():
                bad.append(f"{where}: owntask/{blob}.blob is missing (tools/fwtask/fwtask.py "
                           f"OUTDIR asm/fwtask/{blob}.s writes it)")
            elif sha_file(kp / "owntask" / f"{blob}.blob") != m[blob]["sha256"]:
                bad.append(f"{where}: owntask/{blob}.blob hashes to "
                           f"{sha_file(kp / 'owntask' / f'{blob}.blob')[:12]}, not the sha256 "
                           f"{OWNTASK_MAP} gives {blob} ({m[blob]['sha256'][:12]})")
            if "arm" not in d:
                bad.append(f"{where}: owntask has no arm")
            else:
                a = owntask_arm_problem(d["arm"])
                if a:
                    bad.append(f"{where}: {a}")
        f = kp / "tables" / f"{st}.txt"
        if not f.exists():
            continue
        for row in _rows(f):
            name, tool, args, words = row[0], row[4], row[5], row[3].split()
            w = f"tables/{st}.txt {name}"
            if tool == OWNTASK_TOOL and d is None:
                bad.append(f"{w}: tool {OWNTASK_TOOL} in stage {st}, which is not an owntask "
                           "stage (session.toml: owntask = { blob, arm })")
            elif d is not None and tool != OWNTASK_TOOL:
                bad.append(f"{w}: tool {tool}: an owntask stage runs owntask rows only")
            elif d is not None:
                bad += [f"{w}: knob {k}: an owntask row takes only - and reads:K (no reset, "
                        "knob or register write between the arm and its disarm)"
                        for k in words if not OWNTASK_WORDS.match(k)]
                bad += [f"{w}: {x}" for x in owntask_job(args, jt)[1]]
        p = kp / "predictions" / f"{st}.tsv"
        if p.exists():
            for case, quants in kitscore.predictions(str(kp), st).items():
                for q in quants:
                    try:
                        idx = kitscore.res_index(q)
                    except ValueError as e:
                        bad.append(f"predictions/{st}.tsv {case}: {e}")
                        continue
                    if idx is not None and d is None:
                        bad.append(f"predictions/{st}.tsv {case}: {q} reads the results page, "
                                   f"and {st} is not an owntask stage")
    return bad


def owntask_table(kp, c=None):
    """run/owntask.tsv: `arm STAGE BLOB SHA256 ARM` of each owntask stage (the sha256 the map
    gives the blob) and `job STAGE NAME JSON` of each of its rows (fwtask_run.py run's job, with
    its run id, the row's place in the stage), tab-separated; the runner reads its stage's."""
    import json
    c = c or config(kp)
    own = owntask_stages(c)
    out = ["# run/owntask.tsv: written by kit/session.py prepare from session.toml and the "
           "tables; never edit"]
    if not own:
        return "\n".join(out) + "\n"
    m, _ = owntask_map(c)
    jt = int(c.get("job_timeout", 120))
    for st, d in own.items():
        if not isinstance(d, dict):
            continue
        blob = d.get("blob", "")
        sha = ((m or {}).get(blob) or {}).get("sha256", "-") if isinstance(blob, str) else "-"
        out.append(f"arm\t{st}\t{blob}\t{sha}\t{d.get('arm', '')}")
        f = pathlib.Path(kp) / "tables" / f"{st}.txt"
        rows = _rows(f) if f.exists() else []
        for i, row in enumerate(rows, 1):
            job, _ = owntask_job(row[5], jt) if row[4] == OWNTASK_TOOL else (None, [])
            if job:
                out.append(f"job\t{st}\t{row[0]}\t"
                           + json.dumps(dict(job, runid=i), sort_keys=True))
    return "\n".join(out) + "\n"


# ---- the freeze ------------------------------------------------------------------------------
def _pins(c):
    """[(repo, path)] of session.toml [freeze] pins."""
    out = []
    for p in c["freeze"].get("pins", []):
        repo, _, path = p.partition(":")
        if repo not in ("resgx545", "data") or not path:
            raise Stop(1, f"pin {p!r} is not resgx545:PATH or data:PATH")
        out.append((repo, path))
    if owntask_stages(c) and ("resgx545", OWNTASK_MAP) not in out:
        out.append(("resgx545", OWNTASK_MAP))     # the map an owntask blob was checked against
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


def lint_premises(kp):
    """(warnings, errors) of sessioncheck.lint_predictions on the session's tables and
    predictions, in run order."""
    import kitscore
    order = stages(config(kp))
    tables = {s: kitscore.table(str(kp), s) for s in order}
    preds = {s: kitscore.predictions(str(kp), s) for s in order}
    return sessioncheck.lint_predictions(tables, preds, order)


def freeze(kp):
    kp = pathlib.Path(kp)
    if (kp / "FROZEN.sha256").exists():
        raise Stop(1, "FROZEN.sha256 exists: a freeze is never rewritten")
    c = config(kp)
    prepare(kp)
    warns, lint_errs = lint_premises(kp)
    probs = guard(kp) + control_problems(kp) + [f"lint: {e}" for e in lint_errs]
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
    return "\n".join(warns + [f"frozen: {len(rel)} session files, {len(pins)} pins, "
                             f"{len(lines)} lines by commit"])


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


def _logger(path, say):
    """say, and each line also appended to path (its directory made)."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def log(msg):
        with open(path, "a") as f:
            f.write(f"{msg}\n")
        say(msg)
    return log


def stage(kp, say=print):
    """Stage the laptop list (its lines said and kept in out/stage.log, a Stop's message too)."""
    log = _logger(pathlib.Path(kp) / "out" / "stage.log", say)
    log(f"stage {time.strftime('%Y%m%d-%H%M%S')}")
    try:
        _stage(kp, log)
    except Stop as e:
        with open(pathlib.Path(kp) / "out" / "stage.log", "a") as f:
            f.write(f"{e}\n")
        raise


def _stage(kp, say):
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
    say = _logger(root / "run.log", say)       # the attempt's log, never the session's top
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
        if r.returncode == 24 and c["stages"][st].get("on_stop") == "end":
            say(f"stage {st} stopped by its rule (rc 24); on_stop = \"end\": the session ends")
            return 24, rcs
        if r.returncode == 24:
            say(f"stage {st} stopped by its rule (rc 24): the next stage runs")
    say(f"{c['name']} done: {att}")
    return 0, rcs


# ---- the library mock ------------------------------------------------------------------------
LIBMOCK_TREES = ("userspace/libsgxfive", "include/uapi")
# the debugfs files sgxfive-test copies (tri and probe --tri --dump-render, --kept-copy, --words,
# fill and copy --large-copy), which the replay gives it empty: the kernel's dumps, read only,
# never a knob
LIBMOCK_DUMPS = ("render_param", "render_tadata", "render_kept", "render_words", "buf09",
                 "vm_large")


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


# libsgxfive's mock (src/mock.c) runs a fill's or a copy's program only when it is its own: qword 1
# a limm `mov o0, #imm` (a fill) or its copy shader's instruction (a copy, probe --coords); any
# other program is "an unknown program" and the job faults. A probe of a program of ours ends so.
MOCK_LIMM_MASK, MOCK_LIMM_MOV = 0xff << 56 | 3 << 52, 0xfc << 56 | 1 << 53
MOCK_COPY = 0x28851001 << 32 | 0xa0000000
UNKNOWN_END = re.compile(r"probe (\S+): failed: job faulted, context lost \(Input/output error\)")
# probe forms whose program is not the fill's or copy's own (a triangle, a slot, a PDS)
NOT_A_FILL_PROBE = ("--tri", "--slot", "--pds", "--use")


def _not_simulated(argv, r, cwd):
    """Whether a replay ended as the library mock's unknown program: a `probe` fill or copy (no
    --tri, --slot, --pds, --use) of program files the mock would not run (qword 1 not its copy
    instruction with --coords, not a limm mov without), ending rc 3 with no other failure than
    `probe NAME: failed: job faulted, context lost (Input/output error)`, each after NAME's
    scratch line (the argv accepted, the job submitted) and NAME one of the program files. With
    `--place OFFSET=FILE` the program the mock runs is FILE, started in place of the fill shader
    (of any length: P1's --place takes up to 8192 words, its place and read-back lines are not
    failures); NAME is still a positional program file's."""
    if not argv or argv[0] != "probe" or any(a.split("=")[0] in NOT_A_FILL_PROBE for a in argv):
        return False
    progs = [p for p in (pathlib.Path(cwd) / a for a in argv[1:] if not a.startswith("-"))
             if p.is_file()]
    placed = [pathlib.Path(cwd) / argv[i + 1].partition("=")[2]
              for i, a in enumerate(argv[:-1]) if a == "--place"]
    if not progs or r.returncode != 3 or not all(p.is_file() for p in placed):
        return False
    for p in placed or progs:
        b = p.read_bytes()
        q1 = int.from_bytes(b[8:16], "little") if len(b) >= 16 else None
        if q1 is None or (q1 == MOCK_COPY if "--coords" in argv
                          else q1 & MOCK_LIMM_MASK == MOCK_LIMM_MOV):
            return False
    out = (r.stdout + r.stderr).splitlines()
    fails = [i for i, ln in enumerate(out) if re.search(r"\bfailed:", ln)]
    names = {p.stem for p in progs}
    for i in fails:
        m = UNKNOWN_END.fullmatch(out[i].strip())
        if not m or m.group(1) not in names or not any(
                ln.startswith(f"probe {m.group(1)}: scratch at ") for ln in out[:i]):
            return False
    return bool(fails)


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
    refusal (E934's twin). A probe of a program of ours that ends as the mock's unknown program
    (_not_simulated) is not a finding but said, "program not simulated": the mock checked its
    argv, usage and the kernel's refusals only. Returns the findings."""
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
    n = stateless = premisc = 0
    nsim = {}
    for st in stages(c):
        for row in _rows(kp / "tables" / f"{st}.txt"):
            name, tool, args = row[0], row[4], row[5]
            n += 1
            w = top / f"{n}-{name}"
            (w / "w").mkdir(parents=True)
            # the real runner's debugfs kpoke file: a tri row's --depth and --kpoke-render pokes
            kpoke = w / "kpoke"
            kpoke.write_text("")
            # and its debugfs: the dumps the tool copies, empty, and the declared knobs' files at
            # their defaults, for a tool that writes one (TOOL_KNOBS); a knob's state for the
            # mock comes only from the row's dbg: words
            (w / "dbg").mkdir()
            for f in LIBMOCK_DUMPS:
                (w / "dbg" / f).write_bytes(b"")
            for k, d in c["knobs"].items():
                (w / "dbg" / k).write_text(f"{d['default']}\n")
            # every file the session declares in debugfs = [...], empty, as the fake laptop does
            for f in c["debugfs"]:
                (w / "dbg" / f).touch()
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
                   "W": str(w / "w"), "S": str(kp), "SGXFIVE_KPOKE": str(kpoke),
                   "SGXFIVE_DEBUGFS": str(w / "dbg")}
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
            if "noreset" in row[3].split():
                stateless += 1
            if MISCINFO_WORD in row[3].split():
                premisc += 1
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
            elif _not_simulated(argv, r, w):
                nsim.setdefault(tool, []).append(where)
            else:
                why = _unexpected_end(row[3].split(), r)
                if why:
                    bad.append(f"{where}: {why} (the row never ran on the library mock)")
    if not bad:
        for t, k in count.items():
            ns = len(nsim.get(t, []))
            say(f"ok   libmock: {k} rows of {t} replayed on {c['tools'][t]['source']}, none "
                "refused" + (f"; {ns} of them program not simulated" if ns else ""))
    for t, rows in nsim.items():
        say(f"note libmock: program not simulated (a probe of a program of ours: the mock's "
            f"unknown program fault, after the argv, usage and rejection checks): "
            + ", ".join(rows))
    if premisc:
        say(f"note libmock: {premisc} pre:miscinfo row(s) replayed without the miscinfo read "
            "(the library mock sends the firmware no command; the fake laptop answers it)")
    if stateless:
        say(f"note libmock: {stateless} noreset row(s) replayed without the state of the row "
            "before (every replay starts from a fresh library mock)")
    return bad


def _unexpected_end(words, r):
    """What is wrong with a library-mock replay that did not end `ok` (the findings above are
    for a refusal, a usage line or a crash): any rc other than 0, or a `failed:` line, unless the
    row declares that end (expect:NAME, expectdiff's rc 1 with a diff line, expectfault)."""
    import kitscore
    out = r.stdout + r.stderr
    fault = "expectfault" in words
    declared = any(w.startswith("expect:") and kitscore.OUTCOMES.get(w[7:], (None,))[0] ==
                   r.returncode and re.search(kitscore.OUTCOMES[w[7:]][1], out)
                   for w in words)
    if not r.returncode and "expect:rc0-overflow" in words and not declared:
        return "the library mock's render did not overflow (expect:rc0-overflow)"
    if r.returncode and not (declared or fault or (
            "expectdiff" in words and r.returncode == 1 and "\ndiff:" in "\n" + r.stdout)):
        return f"the library mock ended with status {r.returncode}: " + (
            out.strip().splitlines() or ["no output"])[-1]
    if re.search(r"\bfailed:", out) and not (declared or fault):
        return "the library mock printed " + next(
            ln for ln in out.splitlines() if "failed:" in ln).strip()
    return None


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
                or n in SKIP_PARTS]
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
        for f in ["reset", "regs", *debugfs_need(tree, c)]:
            (real / f).write_text("")
        for k, d in c["knobs"].items():
            (real / k).write_text(d["default"] + "\n")
        if c["kregs"]:
            # the kernel's kreg file: every register it allows, "0xOFFS 0xVALUE" a line
            (real / "kreg").write_text("".join(
                f"{r} 0x{int(KREG_ALLOWED[r][0], 16) if r in KREG_ALLOWED else 0:08x}\n"
                for r in sorted({*c["kregs"], "0x0abc"})))
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
                   IDLE_WAIT="0", PYTHONDONTWRITEBYTECODE="1",
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
        okw |= {f"kreg {r}={v}" for r, d in c["kregs"].items() if r in KREG_ALLOWED
                for v in [*d.get("values", []), KREG_ALLOWED[r][0]]}
        probs += [f"a debugfs write the session does not allow: {x}" for x in writes if x not in okw]
        back = [k for k, d in c["knobs"].items()
                if (real / k).read_text().strip() != d["default"]]
        probs += [f"knob {k} not back at its default" for k in back]
        if c["kregs"]:
            now = dict(ln.split()[:2] for ln in (real / "kreg").read_text().splitlines() if ln)
            probs += [f"kreg {r} not back at its default" for r in c["kregs"]
                      if r in KREG_ALLOWED and int(now.get(r, "-1"), 0) !=
                      int(KREG_ALLOWED[r][0], 16)]
        logs = [x for x in (m / "out" / w).rglob("*.log") if x != m / "out" / w / "run.log"] \
            if (m / "out" / w).exists() else []
        for p in logs:
            probs += [f"{p.name}: {ln}" for ln in p.read_text(errors="replace").splitlines()
                      if sessioncheck.FINDING.search(ln)]
        probs += [ln for ln in log if sessioncheck.FINDING.search(ln) and ln not in probs]
        for st, src in rcs.items():
            kept = m / "out" / w / st
            if src == 0 and kept.exists():
                sc = load_module(tree / "score/score.py", "kit_session_score")
                probs += [f"kept {st}: {x}" for x in sessioncheck.kept_problems(
                    str(kept), req[st], sessioncheck.kept_classes(str(kept)),
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
    for n in ("guard", "prepare", "lint", "freeze", "verify", "stage"):
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
        if a.cmd == "lint":
            warns, errs = lint_premises(a.kp)
            errs = errs + owntask_problems(a.kp)
            print("\n".join(warns + [f"FAIL {e}" for e in errs]) or "lint: clean")
            return 1 if errs else 0
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
