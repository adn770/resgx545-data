#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r3_run.py STAGE --tool PATH --bins DIR --out DIR: one R3k stage on the laptop (python3 stdlib, as root: `sudo -n python3`).
PREPARED, NOT RUN.  The Mac side (run/r3.sh SESSION) uploads it with tables/, bins/, gen/r3layout.py, the landed tools/fwtask/fwtask_run.py
(as run/fwtask_run.py), the op modules run/ops_*.py, TOOL.sha256 and LAPTOP.sha256 to ~/r3k0 (K0) or ~/r3kev (K1).  A copy of
closing3/r3x-events/run/r3_run.py (L3) with the stages of the kernel batch.

Stages (tables/STAGE.json; the rows are r3layout.ROW_SPEC, checked against the table before anything runs):
  K0  k0f defaults (every new debugfs file exists and reads its default), k0t one geometry and one pixel job through the pinned L1/L2 tool,
      k0c one L3 stage-c writer/reader pair (alias2), k0h one tick hold (H0, H1) and one ordinary kick (G0).
  K1  f   the end of a pass: ring_exit (cont4 control first, then own end + cfi + phas, + cfi only, + phas only; stops capped at 2)
      t   the EVENT_TIMER str: ring_timer (ACT 7 str then the closed task, 8 str then our own end)
      kb  Q290: debugfs kicker and the one-shot kick_no_bump (Q0 to Q3, ring_hold, one reset + arm a job)
      e2b Q098: pa_write2 (mov to pa3, pa4, pa2, each read back through its alias)
      e3h Q166 by the host: kregnow 0x0114 (stock firmware, the loop fill through the tool, STATUS2 bit 6)
      e3a Q166 by a task: strclr (str #69)
      e3b Q111: ring_skip3 (skip-once of the fill's end of render, hold_recovery Y), host clears by kregnow 0x0134, B2 by str #77, LAST

Safety (checked by run/guard_r3.sh and guard_blobs.py): the only debugfs writes are own_code, own_arm, own_res (the page), load, boot, reset
and, by the ops that name them, kicker, kick_no_bump, hold_recovery and kregnow (e3h, e3b: CLEAR2 0x0114 only with bits 15 and 6, CLEAR
0x0134 only with bits 15, 18 and, after a stop, 29); /dev/kmsg (os.open, O_WRONLY | O_APPEND); no other register, no clock register, no
trc_hazard, no kreg; firmware `str` only #69 (strclr), #77 (ring_skip3), #691 (ring_timer, one pinned word); `mov` to pa2-pa4 only in
pa_write2.  A bare kick is never made: a kick is `miscinfo`, which the kernel sends with its command.

Stops.  A TICK STOP (HostCtl dword 12 not advancing over three reads) is signed at once, BEFORE anything else runs: the signature
registers, HostCtl dword 14 and the CCB offsets twice (P1), the pass count against the row's own D0 (P2), the landed dumps, and P3: one
`miscinfo` into the stopped EDM (not where the job's own kick is the probe), then the registers again.  Then the kernel's debugfs reset and
the gate (reset + health).  A stopped row is never replicated (unless its row says rep_after_stop: e3b).  A stage takes `budget` stops and
goes on; the next one ends it (exit 8, reset and gate exact).  A freeze (exit 6) or a watchdog (fatal, exit 3) stops all laptop work.
Other exits: 1 preflight, 4 a job failed or an exception, 5 reset or gate not exact, 7 a table value outside the allow-list.  No loop
waits for anything: every delay is a fixed sleep, every loop a bounded for.
"""
import argparse
import contextlib
import glob
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent          # ~/r3xev on the laptop
sys.path.insert(0, str(R3 / "gen"))
sys.path.insert(0, str(R3 / "run"))
sys.path.insert(0, os.environ.get("R3_FWTASK_DIR", str(R3 / "run")))   # tests point it at a fake
import r3layout as L  # noqa: E402
import fwtask_run as FR  # noqa: E402
from r3common import Stop  # noqa: E402
import ops_kicker, ops_e2b, ops_e3, ops_k0  # noqa: E402   (the op families of the kernel batch)

BLOB_OF = L.BLOB_OF
GATE_OF = L.GATE_OF
GATE_EXITS = (0, 8)
OPS_OF = {st: i["ops"] for st, i in L.STAGE_INFO.items()}
RING_STAGES = {st for st, b in L.BLOB_OF.items() if b in ("ring_hold", "ring_exit", "ring_timer", "ring_skip3")}
N90 = L.n_for_ticks(L.K7_HOLD_TICKS)
FATAL_RE = re.compile(r"soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|"
                      r"blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check")
TOOL_BAD = re.compile(r"FAIL|Traceback|\"error\"|\bBUG\b|\bOops\b|refus")      # searched in the WHOLE output of a tool command
OK_CLASSES = ("ok", "noreader", "kick-timeout")
# the module 230E0EF5 (fork 36f3d278) logs a second line on every debugfs reset, "SGX reset: after the fault clear BIF_FAULT x
# BIF_INT_STAT y", whose word "fault" the landed BAD_LOG matches; the old module's reset line never matched.  Only that exact line
# is kept out of log_bad (parity with the old module); it stays in the kept NAME.dmesg.
RESET_INFO = re.compile(r"\] SGX reset: after the fault clear BIF_FAULT 0x[0-9a-f]+ BIF_INT_STAT 0x[0-9a-f]+$")
NOT_ANSWERED = re.compile(r"timeout|timed out|no MISCINFO|not ready", re.I)
KMSG = os.environ.get("R3_KMSG", "/dev/kmsg")
SRCV_PATH = os.environ.get("R3_SRCV_PATH", "/sys/module/gma500_gfx/srcversion")
SRCV_EXPECT = os.environ.get("R3_SRCV_EXPECT", L.EXPECT_SRCV)
EXIT_SECOND_STOP = 8
RUN_IF = re.compile(L.RUN_IF_RE.replace("^", "").replace("$", "") + "$")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def captured(fn, a=None):
    """Run a landed fwtask_run command (it prints one JSON object) and return that object, plus `tool_bad`: every line of its WHOLE
    output (not only the last line, not only a head) that names a failure."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(a or {})
    text = buf.getvalue()
    lines = [ln for ln in text.splitlines() if ln.startswith("{")]
    out = json.loads(lines[-1]) if lines else {"ok": False, "error": "no output"}
    out["tool_bad"] = [ln[:200] for ln in text.splitlines() if TOOL_BAD.search(ln)]
    return out


def pick_debugfs():
    """(directory, all candidates): dri/0/sgx if it holds own_res, else the first sorted candidate that does."""
    cands = sorted(glob.glob("/sys/kernel/debug/dri/*/sgx"))
    for c in cands:
        if c.endswith("/dri/0/sgx") and os.path.exists(f"{c}/own_res"):
            return c, cands
    for c in cands:
        if os.path.exists(f"{c}/own_res"):
            return c, cands
    return None, cands


def parse_ccbctl(text):
    """[ctl0, ctl1] from the regs file's `ccbctl 0x00 0x........` and `ccbctl 0x04 0x........` lines (None: not there)."""
    return L.parse_regs(text)[2]


def median_mode(vals):
    """The most frequent value of a list (the smallest on a tie), or None."""
    if not vals:
        return None
    best = max(set(vals), key=lambda v: (vals.count(v), -v))
    return best


class Runner(ops_kicker.KickerOps, ops_e2b.PaOps, ops_e3.ClearOps, ops_k0.K0Ops):
    def __init__(self, a):
        self.stage, self.tool, self.bins = a.stage, a.tool, a.bins
        self.out = pathlib.Path(a.out) / a.stage
        self.out.mkdir(parents=True, exist_ok=True)
        self.run = f"{int(time.time())}-{os.getpid()}"
        self.t_start = time.time()
        self.t0_mono = time.monotonic()
        self.table = None
        self.records = {}
        self.armed = False
        self.stops = 0
        self.stopped_rows = set()
        self.cur_res = None
        self.base63 = 0                      # sa63 as C0/D0 read it (what a restore puts back)
        self.cases = self.out / "cases.tsv"
        self.cases.write_text("name\tset\trow\tclass\trc\tnote\n")

    # ---- small helpers ------------------------------------------------------------------
    def mark(self, text):
        try:
            # os.open with O_APPEND and no seek: Python's "a" mode seeks, which /dev/kmsg refuses with EINVAL (seen on the laptop)
            fd = os.open(KMSG, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(fd, f"resgx545 r3k {text} {self.run}\n".encode())
            finally:
                os.close(fd)
        except OSError as e:
            print(f"  (kmsg marker not written: {e})")

    def save(self, name, obj):
        (self.out / name).write_text(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n")

    def ccbctl(self):
        return parse_ccbctl(FR.rd("regs"))

    # ---- preflight ----------------------------------------------------------------------
    NEED_FILES = ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo", "kicker", "kick_no_bump",
                  "kregnow", "hold_recovery", "render_rgn_arrays", "render_pb_pages")

    def preflight(self):
        env = {"stage": self.stage, "run": self.run, "euid": os.geteuid()}
        if os.geteuid() != 0 and os.environ.get("R3_MOCK_ROOT") != "1":
            raise Stop(1, "not root: run as `sudo -n python3 r3_run.py` (every debugfs access needs root)")
        if self.stage not in L.STAGE_INFO:
            raise Stop(1, f"unknown stage {self.stage}")
        if R3.name != L.DIR_OF[L.SESSION_OF[self.stage]] and os.environ.get("R3_MOCK_ROOT") != "1":
            raise Stop(1, f"stage {self.stage} belongs to session {L.SESSION_OF[self.stage]} (~/{L.DIR_OF[L.SESSION_OF[self.stage]]}), not {R3}")
        frozen = {}
        for ln in (R3 / "LAPTOP.sha256").read_text().splitlines():
            h, f = ln.split(None, 1)
            frozen[f.strip()] = h
        self.table = json.loads((R3 / "tables" / f"{self.stage}.json").read_text())
        blob = BLOB_OF[self.stage]
        if self.table["blob"] != blob:
            raise Stop(1, f"the table's blob {self.table['blob']} is not {blob}")
        need = [f"tables/{self.stage}.json", "gen/r3layout.py", "run/r3_run.py", "run/fwtask_run.py", "TOOL.sha256", "bins/blobs.json",
                "run/ops_kicker.py", "run/ops_e2b.py", "run/ops_e3.py", "run/ops_k0.py", "run/r3common.py"]
        if blob:
            need.append(f"bins/{blob}.blob")
        if self.stage == "k0t":
            need += ["TOOLR1.sha256", "bins/progs/dd-p1__0.bin", "bins/progs/pix_green.bin"]
        if self.stage in ("e3h", "e3a", "e3b"):
            need += ["bins/progs/" + L.LOOP_PROG + ".bin"]
        for f in sorted(set(need)):
            if frozen.get(f) != sha(R3 / f):
                raise Stop(1, f"{f} is not the frozen file")
        binfo = json.loads((R3 / "bins" / "blobs.json").read_text()).get(blob) if blob else None
        if blob:
            self.check_blob_info(blob, binfo)
        self.check_table()
        prev = GATE_OF.get(self.stage)
        if prev:
            try:
                # the previous stage's kept stage.json: in this session's results directory, or (f after K0's k0h) in the other session's
                pst = json.loads((self.out.parent.parent / f"{L.DIR_OF[L.SESSION_OF[prev]]}-out" / prev / "stage.json").read_text())
            except (OSError, ValueError):
                pst = {}
            if pst.get("exit") not in GATE_EXITS:
                raise Stop(1, f"stage {prev} has no finished kept stage.json here (exit {pst.get('exit')}): {self.stage} does not run")
            env["gate"] = f"{prev} exit {pst.get('exit')} run {pst.get('run')}"
        d, cands = pick_debugfs() if "R3_DEBUGFS" not in os.environ else (os.environ["R3_DEBUGFS"], [os.environ["R3_DEBUGFS"]])
        if d is None:
            raise Stop(1, f"no sgx debugfs directory with own_res among {cands} (debug option off?)")
        FR.D = d
        env["debugfs"], env["debugfs_candidates"] = d, cands
        with open(SRCV_PATH) as f:
            env["srcversion_loaded"] = f.read().strip()
        env["srcversion_installed"] = FR.sh("modinfo -F srcversion gma500_gfx", check=False).strip()
        env["srcversion_expected"] = SRCV_EXPECT
        if not env["srcversion_loaded"] or env["srcversion_loaded"] != env["srcversion_installed"]:
            raise Stop(1, "the loaded module is not the installed one")
        if env["srcversion_loaded"] != SRCV_EXPECT:
            raise Stop(1, f"the loaded module ({env['srcversion_loaded']}) is not the one this session is prepared for ({SRCV_EXPECT})")
        for f in self.NEED_FILES:
            if not os.path.exists(f"{FR.D}/{f}"):
                raise Stop(1, f"the driver has no debugfs {f}")
        if not os.access(self.tool, os.X_OK):
            raise Stop(1, f"no tool {self.tool}")
        env["tool_sha256"] = sha(self.tool)
        if env["tool_sha256"] != (R3 / "TOOL.sha256").read_text().split()[0]:
            raise Stop(1, f"the tool is not the pinned one ({env['tool_sha256'][:12]}, pinned in TOOL.sha256)")
        if self.stage == "k0t":
            self.tool_r1 = os.environ.get("R3_TOOL_R1", str(pathlib.Path(self.tool).parent / "sgxfive-test-r1"))
            if not os.access(self.tool_r1, os.X_OK):
                raise Stop(1, f"no tool {self.tool_r1}")
            env["tool_r1_sha256"] = sha(self.tool_r1)
            if env["tool_r1_sha256"] != (R3 / "TOOLR1.sha256").read_text().split()[0]:
                raise Stop(1, f"the L1/L2 tool is not the pinned one ({env['tool_r1_sha256'][:12]}, pinned in TOOLR1.sha256)")
        gate_tool = getattr(FR, "GATE_TOOL", "/home/jtorra/sgxfive-test")    # the landed cmd_gate's tool
        if not os.access(gate_tool, os.X_OK):
            raise Stop(1, f"no gate tool {gate_tool} (the landed fwtask_run.cmd_gate runs it): sgxfive-test missing")
        env["gate_tool_sha256"] = sha(gate_tool)
        if sys.version_info < (3, 8):
            raise Stop(1, f"python {sys.version.split()[0]} is older than 3.8")
        env["python"] = sys.version.split()[0]
        env["uname"] = FR.sh("uname -r", check=False).strip()
        env["firmware_sha256"] = FR.sh("sha256sum /lib/firmware/sgx545_ukernel.fw", check=False).split(" ")[0]
        if binfo and binfo.get("cont4") and env["firmware_sha256"] != L.FW_SHA256:
            raise Stop(1, f"{blob} tail-calls the exit (cont4), tied to the firmware {L.FW_SHA256[:12]}...: the laptop's is {env['firmware_sha256'][:12]}")
        env["blob_sha256"] = frozen.get(f"bins/{blob}.blob") if blob else None
        env["table_sha256"] = frozen[f"tables/{self.stage}.json"]
        env["ko_sha256_recorded"] = L.KO_SHA256
        self.save("env.json", env)
        self.mark(f"preflight {self.stage}")
        print(f"## preflight ok: {json.dumps({k: env[k] for k in ('srcversion_loaded', 'uname', 'tool_sha256', 'debugfs')})}")

    def check_blob_info(self, blob, binfo):
        """What the blob is allowed to carry (the guard's rules, once more on the laptop from blobs.json)."""
        if blob == "alias2":
            if {int(k): v for k, v in binfo["cmd_sa"].items()} != L.CMD_SA2 or not set(binfo["sa_writes"]) <= L.SA_ALLOWED2:
                raise Stop(1, "alias2.s: its sa write set is not the allowed one")
        elif blob == "pa_write2":
            if sorted(binfo["sa_writes"]) != ["sa67", "sa68"] or sorted(binfo["pa_writes"]) != ["pa2", "pa3", "pa4"]:
                raise Stop(1, "pa_write2: its sa/pa write set is not sa67, sa68 / pa2, pa3, pa4")
        elif binfo["sa_writes"] or binfo.get("pa_writes"):
            raise Stop(1, f"{blob} writes an sa or pa register")
        if binfo["str"] != L.STR_OF.get(blob, []) and sorted(binfo["str"]) != sorted(L.STR_OF.get(blob, [])):
            raise Stop(1, f"{blob}: its str set {binfo['str']} is not {L.STR_OF.get(blob, [])}")

    def check_table(self):
        t = self.table
        if int(t.get("stop_budget", 1)) != L.STOP_BUDGET[self.stage]:
            raise Stop(7, f"stop budget is not {L.STOP_BUDGET[self.stage]}")
        if t.get("per_job_reset") != L.PER_JOB_RESET[self.stage] or t.get("arm") != L.ARM_OF[self.stage]:
            raise Stop(7, "per_job_reset or the arm line is not the stage's")
        rows = L.ROW_SPEC[self.stage]
        names = set()
        for j in t["jobs"]:
            if j.get("name") in names:
                raise Stop(7, f"{j.get('name')}: the job name is used twice")
            names.add(j.get("name"))
            self.check_job(j, rows)
        want = [L.rep_name(r, k) for r in L.ROW_ORDER[self.stage] for k in range(rows[r]["reps"])]
        if [j["name"] for j in t["jobs"]] != want:
            raise Stop(7, "the jobs are not the rows' jobs in the frozen order")

    def check_job(self, j, rows):
        n = j.get("name", "?")
        row = j.get("row")
        if row not in rows:
            raise Stop(7, f"{n}: row {row} is not one of this stage's approved rows {sorted(rows)}")
        spec = rows[row]
        if j.get("op") != spec["op"] or j["op"] not in OPS_OF[self.stage]:
            raise Stop(7, f"{n}: op {j.get('op')} is not row {row}'s")
        ri = j.get("run_if")
        if ri is not None and (not RUN_IF.match(ri) or ri != spec.get("run_if")):
            raise Stop(7, f"{n}: run_if {ri!r} is not on the allow-list")
        if not isinstance(j.get("runid"), int) or not 0 < j["runid"] < 1 << 32:
            raise Stop(7, f"{n}: the run id is not a 32-bit integer")
        fn = getattr(self, f"check_{j['op']}", None)
        if fn is None:
            raise Stop(7, f"{n}: no check for op {j['op']}")
        fn(j, spec, row)

    def check_holdsig(self, j, spec, row):
        n = j["name"]
        if j["hold"] != spec["hold"] or j["n"] != (N90 if spec["hold"] else 0) or j["window"] != 2 or j["sig_ms"] != [20, 60] \
                or j["status_ms"] != 40 or j["open_ms"] != 160 or j["d_reads"] != 20 or j["status_reads"] != (1 if spec["hold"] else 20):
            raise Stop(7, f"{n}: hold, n, window or times outside the allow-list")

    def check_alias2(self, j, spec, row):
        n = j["name"]
        cmd = spec["cmd"]
        if j["cmd"] != cmd or sorted(j["sa"]) != sorted(L.CMD_SA2.get(cmd, [])) or not set(j["sa"]) <= L.SA_ALLOWED2:
            raise Stop(7, f"{n}: command {j['cmd']} / sa set {j['sa']} is not row {row}'s")
        want_w65 = {"lit": L.E537["sa65"]} if cmd == L.CMD_E537 else spec.get("w65")
        if j.get("w65") != want_w65 or j["npass"] != spec.get("npass", 0) or j["d_reads"] != 20:
            raise Stop(7, f"{n}: the word, the pass count or the reads are not row {row}'s")
        w = want_w65
        if w and "or" in w and row in ("C1", "C3") and w["or"] & L.TESTED_PA1_MASK:
            raise Stop(7, f"{n}: row {row}'s word has a bit that some ukernel code tests ({w['or']:#x})")
        if cmd == L.CMD_E537:
            e = L.E537
            if (j["w63"], j["w64"], j["w65"], j["ri"]) != (e["sa63"], e["sa64"], {"lit": e["sa65"]}, [e["r20"], e["r21"], e["i0"], e["i1"]]) \
                    or not j["restore63"]:
                raise Stop(7, f"{n}: D4's words are not E537's")
        elif j["w63"] or j["w64"] or any(j["ri"]) or j["marker"] or j["restore63"] or j["read_1200"]:
            raise Stop(7, f"{n}: a word, marker or restore this row does not have")

    def check_act(self, j, spec, row):
        n = j["name"]
        if (j["kind"], j["act"], j["count"], j["trigger"]) != (spec["kind"], spec["act"], spec["count"], spec["trigger"]) \
                or j["window"] != 2 or not 0 <= j["pre_ms"] <= 10 or j["open_ms"] != spec["open_ms"] or j["d_reads"] != 20:
            raise Stop(7, f"{n}: kind, act, count, trigger, window or times outside the allow-list")
        if j["act"] and j["act"] not in L.ACT_OF_STAGE[self.stage]:
            raise Stop(7, f"{n}: act {j['act']} is not one of stage {self.stage}'s {L.ACT_OF_STAGE[self.stage]}")

    # ---- arm / end ----------------------------------------------------------------------
    def zero_protocol(self, res):
        res.w(L.CMD, [0, 0])                 # CMD, STATE
        res.w(L.ECHO, 0)
        res.w(L.WINDOW, 0)

    def arm(self, tag="arm"):
        """Arm the stage's task through the landed cmd_arm."""
        res = FR.Res()
        try:
            self.zero_protocol(res)
        finally:
            res.close()
        a = {"blob": str(R3 / "bins" / f"{self.table['blob']}.blob"), "arm": self.table["arm"]}
        self.mark(f"arm {self.stage} {tag}")
        marker = f"resgx545 r3k arm {self.stage} {tag} {self.run}"
        out = captured(FR.cmd_arm, a)
        # the landed cmd_arm slices dmesg by a line count, which a full (wrapped) ring buffer keeps constant: its "log" and
        # "log_bad" came back empty on the laptop (2026-11-10).  Both are read again here from the lines after this arm's marker.
        try:
            lines = FR.dmesg_new(0)
            at = max((i for i, ln in enumerate(lines) if marker in ln), default=None)
            if at is None:
                raise RuntimeError("the arm's kmsg marker is not in dmesg")
            new = lines[at + 1:]
            out["log_tool"], out["log_bad_tool"] = out.get("log"), out.get("log_bad")
            out["log"] = [ln for ln in new if "own" in ln]
            out["log_bad"] = [ln for ln in new if FR.BAD_LOG.search(ln) and "resgx545 r3k " not in ln and not RESET_INFO.search(ln)]
            if out["log_bad"]:
                out["ok"] = False
        except Exception as e:
            out["ok"], out["log_bad"] = False, [f"kernel log not read after the arm: {e!r}"]
        # the kernel's arm line names the exit index it resolved for `cont4` (0: unknown firmware digest, nothing patched)
        m = re.search(r"exit (0x[0-9a-f]+) \(0: unknown\)", " ".join(out.get("log") or []))
        out["exit_index"] = int(m.group(1), 16) if m else None
        self.save(f"{tag}.json", out)
        print(f"## {tag}: ok {out.get('ok')} rate {out.get('rate_hz')}")
        if not out.get("ok") or out.get("tool_bad"):
            raise Stop(4, f"arm not ok: {json.dumps({k: out.get(k) for k in ('alive', 'health', 'log_bad', 'magic', 'tool_bad')})}")
        if self.table["blob"] in L.CONT4_BLOBS and not out["exit_index"]:
            raise Stop(4, "the kernel resolved no exit index for cont4 (arm line: exit 0 or absent): the exit tail call is not patched")
        res = FR.Res()
        try:
            cmd, state = res.r(L.CMD, 2)
            win = res.r(L.WINDOW)[0]
        finally:
            res.close()
        if cmd or win:
            raise Stop(4, f"after the arm CMD {cmd} WINDOW {win}, not 0")
        self.armed = True
        return out

    def end(self, tag):
        """The reset (the landed cmd_reset: alive, health, own_arm off) and the gate (fill, triangle): reset + health."""
        r = captured(FR.cmd_reset)
        g = captured(FR.cmd_gate)
        try:
            h = FR.health()
        except Exception as e:          # a dead debugfs is itself a result
            h = {"ok": False, "error": repr(e)}
        self.save(f"{tag}-reset.json", {"reset": r, "gate": g, "health": h})
        print(f"## {tag}: reset ok {r.get('ok')}, gate ok {g.get('ok')}, health ok {h.get('ok')}")
        self.armed = False
        return bool(r.get("ok") and g.get("ok") and h.get("ok") and not r.get("tool_bad") and not g.get("tool_bad"))

    def pre_reset_arm(self, j, rec):
        """A reset, then the arm (stages without a blob: the reset alone), before every job (the slot at the CCB read offset is a zeroed
        one, as in E537; the kicker word starts at its boot value, K = 2 after the arm: E768)."""
        r = captured(FR.cmd_reset)
        rec["pre_reset"] = {"ok": r.get("ok"), "tool_bad": r.get("tool_bad")}
        if not r.get("ok") or r.get("tool_bad"):
            raise Stop(4, "the reset before the arm is not ok")
        self.mark(f"arm {j['name']}")
        if self.table["blob"]:
            self.arm(tag=f"{j['name']}.arm")
        rec["ccbctl_after_arm"] = self.ccbctl()

    # ---- page and tick helpers ------------------------------------------------------------
    def bracket_read(self, res):
        """[page PASS, HostCtl dword 12, page PASS]: the interval arithmetic of the scorer's `d12 - passes` needs the two page
        reads around the register read."""
        a = res.r(L.A_PASS)[0]
        h = FR.regs()[1].get(12)
        b = res.r(L.A_PASS)[0]
        return [a, h, b]

    def d_samples(self, res, n, src="regs"):
        """n triples [page PASS, HostCtl dword 12, page PASS], 1.3 ms apart: D = PASS - dword 12 (the row's D0 when taken before the
        row).  src `status` reads the landed status file (H0's 20 `status` reads), `regs` the regs file."""
        out = []
        for _ in range(n):
            a = res.r(L.A_PASS)[0]
            if src == "status":
                h = L.parse_status(FR.rd("status"))[1].get(12)
            else:
                h = FR.regs()[1].get(12)
            b = res.r(L.A_PASS)[0]
            out.append([a, h, b])
            time.sleep(0.0013)
        return out

    def ring_clear(self, res):
        res.w(L.RING_BASE[0], [0] * (L.RING_END - L.RING_BASE[0]))
        res.w(L.DROP, [0] * 12)                          # DROP, PASS, OVL
        res.w(L.OVL_LOG, [0] * 16)
        res.w(L.HOLD_ENTRY, [L.INITFILL, L.INITFILL])
        res.w(L.COUNT, [0, 0])                           # COUNT, ACTED
        res.w(L.KIND, [0, 0])                            # KIND, ACT
        res.w(L.STATE, 0)
        res.w(L.ECHO, 0)

    def ring_open(self, res, window, rec):
        rec["window_stamp"] = FR.regs()[0].get(L.REG_TIMER)    # CR_TIMER just before the window opens (the scorers read from it on)
        res.w(L.WINDOW, window)

    def ring_close(self, res, rec, t0):
        res.w(L.WINDOW, 0)
        rec["t_close_ms"] = (time.monotonic() - t0) * 1000
        time.sleep(0.003)
        rec["page"] = res.page()
        time.sleep(0.010)
        rec["page2"] = res.page()                        # window 0 proof: no rung changes after the close
        rec["rc"] = 0

    def tick_check(self):
        """(ok, alive, rate): HostCtl dword 12 advancing over three reads 20 ms apart, and a rate within 900 to 1100 Hz."""
        a = FR.alive()
        if not a["advancing"]:
            return False, a, None
        rate = FR.tick_rate(100)
        return bool(900 <= rate <= 1100), a, rate

    def sample(self, res=None):
        """One reading of everything a stop is read from: the signature registers, HostCtl dwords 12 and 14, the CCB offsets
        [write, read] (one `regs` read), and the page's pass counter before and after it."""
        a = res.r(L.A_PASS)[0] if res is not None else None
        r, hc, cc = L.parse_regs(FR.rd("regs"))
        b = res.r(L.A_PASS)[0] if res is not None else None
        return {"t": round(time.monotonic() - self.t0_mono, 4), "regs": {hex(k): r.get(k) for k in L.SIG_REGS}, "hc12": hc.get(12),
                "hc14": hc.get(L.HC_ASSERT_DWORD), "ccb": cc, "pass": [a, b] if res is not None else None}

    def sig_samples(self, res=None, n=2, gap=0.03):
        out = []
        for i in range(n):
            try:
                out.append(self.sample(res))
            except Exception as e:      # a dead debugfs file is itself a result
                out.append({"error": repr(e)})
            if i + 1 < n:
                time.sleep(gap)
        return out

    def signature(self, rec, phase):
        """P1: the stop's registers, twice, 30 ms apart, BEFORE any reset (with HostCtl dword 14, the CCB offsets and the pass count);
        the landed dumps; then P3 (not in B3: its own kick is the probe)."""
        samples = self.sig_samples(self.cur_res)
        rec["sig"] = {"phase": phase, "samples": samples}
        rec["stopped"] = True
        try:
            FR.hang_dump(str(self.out), f"stop-{rec['name']}")
        except Exception as e:
            print(f"(dump failed: {e!r})")
        print(f"## STOP SIGNATURE {rec['name']} ({phase}): {json.dumps(samples)[:300]}")
        if not rec.get("no_p3"):
            self.probe_p3(rec)

    def probe_p3(self, rec):
        """P3: one `miscinfo` read into the stopped EDM (the kernel sends the command with the kick: never a bare kick), then the
        registers again.  H-NOTENDED predicts it is not answered (a read that fails or takes P3_MS); H-REARM that it is.  In the ring
        stages the window is open for it, so that a kick entry would be seen."""
        res = self.cur_res
        p3 = {"before": self.sample(res)}
        ring_before = None
        if res is not None and self.stage in RING_STAGES:
            try:
                ring_before = res.page()
                res.w(L.WINDOW, 2)
            except Exception as e:
                p3["ring_error"] = repr(e)
        t = time.monotonic()
        try:
            m = FR.miscinfo()
            p3["ms"] = m.get("ms", (time.monotonic() - t) * 1000)
            p3["text"] = str(m.get("text", ""))[:200]
            p3["answered"] = p3["ms"] < L.P3_MS and not NOT_ANSWERED.search(p3["text"])
        except OSError as e:
            p3.update({"ms": (time.monotonic() - t) * 1000, "errno": e.errno, "text": f"read failed: {e}", "answered": False})
        time.sleep(0.01)
        p3["after"] = self.sample(res)
        if ring_before is not None:
            try:
                res.w(L.WINDOW, 0)
                time.sleep(0.003)
                after = res.page()
                p3["ring_new_entries"] = sum(1 for k in range(4) for j in range(L.RUNGS[k]) if after[L.RING_BASE[k] + L.RUNG * j]
                                             and not ring_before[L.RING_BASE[k] + L.RUNG * j])
            except Exception as e:
                p3["ring_error"] = repr(e)
        rec["p3"] = p3
        print(f"## P3 {rec['name']}: answered {p3['answered']} ({p3['ms']:.0f} ms)")

    def check_tick(self, rec, phase):
        """The tick after a phase: a stop is signed at once (before anything else runs)."""
        ok, a, rate = self.tick_check()
        rec.setdefault("ticks", []).append({"phase": phase, "ok": ok, "alive": a, "rate_hz": rate})
        if not a["advancing"] and not rec.get("stopped"):
            self.signature(rec, phase)
        return a["advancing"]

    def marks_post(self, rec):
        """The CCB offsets and HostCtl dword 14 after a job that kept the tick (the instruments that tell a silent consumption)."""
        try:
            r, hc, cc = L.parse_regs(FR.rd("regs"))
            rec["marks_post"] = {"ccb": cc, "hc14": hc.get(L.HC_ASSERT_DWORD), "hc12": hc.get(12)}
        except Exception as e:
            rec["marks_post"] = {"error": repr(e)}

    # ---- one job ------------------------------------------------------------------------
    def job(self, j):
        name = j["name"]
        rec = {"name": name, "set": j["set"], "op": j["op"], "row": j["row"], "job": j, "class": "void", "rc": None, "note": "",
               "run": self.run}
        marker = f"resgx545 r3k case {name} {self.run}"
        self.mark(f"case {name}")
        self.t0_mono = time.monotonic()
        self.cur_res = None
        err = None
        try:
            getattr(self, f"{j['op']}_job")(j, rec)
        except BaseException as e:          # recorded, then raised again after the record is written
            err = e
            rec["note"] += f" error: {e!r}"
        # every step below is guarded: the record and the cases.tsv row are written whatever fails
        try:
            lines = FR.dmesg_new(0)
            at = max((i for i, ln in enumerate(lines) if marker in ln), default=None)
            new = lines[at + 1:] if at is not None else lines
            if at is None:
                rec["note"] += " marker not in dmesg: the whole buffer was read"
            (self.out / f"{name}.dmesg").write_text("\n".join(new) + "\n")
            rec["log_bad"] = [ln for ln in new if FR.BAD_LOG.search(ln) and "resgx545 r3k " not in ln and not RESET_INFO.search(ln)]
            rec["fatal"] = [ln for ln in new if FATAL_RE.search(ln)]
        except Exception as e:
            rec["log_bad"], rec["fatal"] = [f"kernel log not read: {e!r}"], []
        try:
            rec["alive"] = FR.alive()
            rec["health"] = FR.health()
        except Exception as e:
            rec["alive"], rec["health"] = {"advancing": False, "error": repr(e)}, {"ok": False, "error": repr(e)}
        try:
            if rec["alive"].get("advancing") and not rec.get("stopped"):
                self.marks_post(rec)
            self.classify(j, rec)
        except Exception as e:
            rec["class"], rec["note"] = "error", rec["note"] + f" classify: {e!r}"
        if err is not None and rec["class"] in OK_CLASSES:
            rec["class"] = "error"
        self.records[name] = rec
        self.save(f"{name}.json", rec)
        self.append_case(rec)
        self.mark(f"class {name} {rec['class']}")
        print(f"== {name}: class {rec['class']} {rec['note'].strip()[:100]}")
        if err is not None:
            raise err
        return rec

    def append_case(self, rec):
        with self.cases.open("a") as f:
            f.write(f"{rec['name']}\t{rec['set']}\t{rec['row']}\t{rec['class']}\t{rec['rc']}\t{rec['note'].strip()}\n")

    def skipped(self, j, why):
        rec = {"name": j["name"], "set": j["set"], "op": j["op"], "row": j["row"], "job": j, "class": "skipped", "rc": None,
               "note": why, "run": self.run}
        self.records[j["name"]] = rec
        self.save(f"{j['name']}.json", rec)
        self.append_case(rec)
        print(f"== {j['name']}: skipped ({why})")

    # ---- stage h ------------------------------------------------------------------------
    def holdsig_job(self, j, rec):
        """H0 / H1: reset, arm, the row's D0 (20 reads), the window; for H1 the hold (CMD = 1 back to back with the window, S2b's E4);
        the signatures at 20 and 60 ms (two samples 10 ms apart each, the page's STATE read around each: inside the hold or not) and
        one `status` read at 40 ms."""
        self.pre_reset_arm(j, rec)
        res = FR.Res()
        self.cur_res = res
        try:
            self.ring_clear(res)
            res.w(L.N_ITER, j["n"])
            res.w(L.RUNID, j["runid"])
            rec["d0"] = self.d_samples(res, j["d_reads"], src="regs" if j["hold"] else "status")
            rec["tick_before"] = FR.regs()[1].get(12)
            t0 = time.monotonic()
            self.ring_open(res, j["window"], rec)
            if j["hold"]:
                res.w(L.CMD, 1)
            rec["inside"] = []
            for k, ms in enumerate(j["sig_ms"]):
                time.sleep(max(0.0, ms / 1000 - (time.monotonic() - t0)))
                st0 = res.r(L.STATE)[0]
                s = self.sig_samples(res, n=2, gap=0.01)
                st1 = res.r(L.STATE)[0]
                rec["inside"].append({"ms": ms, "t_ms": (time.monotonic() - t0) * 1000, "state": [st0, st1], "samples": s})
                if k == 0:
                    time.sleep(max(0.0, j["status_ms"] / 1000 - (time.monotonic() - t0)))
                    rec["status_text"] = FR.rd("status")
                    (self.out / f"{j['name']}-status-in-window.txt").write_text(rec["status_text"])
            time.sleep(max(0.0, j["open_ms"] / 1000 - (time.monotonic() - t0)))
            self.ring_close(res, rec, t0)
            rec["tick_after"] = FR.regs()[1].get(12)
        finally:
            res.close()
        self.check_tick(rec, "after-hold")

    # ---- stages c and d -----------------------------------------------------------------
    def command(self, res, cmd, runid, marker=None, ri=None, ms=120, w65=None, w64=None, npass=None):
        """Issue one alias2.s command and wait for its flag.  The writers arm the reader (cmd 9): flag = the writer's WR_DONE; a reader's
        flag is cmd 0.  Returns {"done", "ms"}."""
        res.w(L.STATE, 0)
        res.w(L.ECHO, 0)
        res.w(L.WR, [0] * 16)                # the writer's record and its flag (WR_DONE) start empty
        res.w(L.RD, [0] * 16)
        res.w(L.RUNID, runid)
        if marker is not None:
            res.w(L.A_M, marker)
        if ri is not None:
            res.w(L.A_RI, list(ri))
        if w65 is not None:
            res.w(L.W65, w65)
        if w64 is not None:
            res.w(L.W64, w64)
        if npass is not None:
            res.w(L.NPASS, npass)
        t = time.monotonic()
        res.w(L.CMD, cmd)
        if cmd == L.CMD_READ:
            w = self.wait_reader(res, runid, ms)
        else:                                # cmd 9 lasts one tick: the flag that stays is WR_DONE
            w = self.wait_flag(res, runid, ms)
        return {"done": w is not None, "ms": w, "t_ms": (time.monotonic() - t) * 1000}

    def wait_reader(self, res, runid, ms):
        """Bounded wait: the reader ran: CMD back to 0 with the run id echoed AND its record's pass count (dword RD + 15, never 0
        after a pass) written: a writer that left cmd 0 without arming one does not look like a reader that ran."""
        t = time.monotonic()
        for _ in range(int(ms / 2) + 1):
            c = res.r(L.CMD)[0]
            if c == 0 and res.r(L.ECHO)[0] == runid and res.r(L.RD + 15)[0] != 0:
                return (time.monotonic() - t) * 1000
            time.sleep(0.002)
        return None

    def wait_flag(self, res, runid, ms):
        """Bounded wait: the writer's flag WR_DONE holds the run id.  Returns ms or None."""
        t = time.monotonic()
        for _ in range(int(ms / 2) + 1):
            if res.r(L.WR_DONE)[0] == runid:
                return (time.monotonic() - t) * 1000
            time.sleep(0.002)
        return None

    def alias2_job(self, j, rec):
        if self.table["per_job_reset"]:
            self.pre_reset_arm(j, rec)
        res = FR.Res()
        self.cur_res = res
        try:
            cc = self.ccbctl()
            rec["ccbctl_pre"] = cc
            K = (cc or [0])[0] & 0xFF
            word = L.word65(j["w65"], K)
            rec["w65_word"] = word
            self.zero_protocol(res)
            res.w(L.A_RI, list(j["ri"]))
            res.w(L.A_M, j["marker"])
            rec["d0"] = self.d_samples(res, j["d_reads"])
            rec["bracket_pre"] = br0 = self.bracket_read(res)
            cmd, rid = j["cmd"], j["runid"]
            wr = {"issued": bool(cmd), "done": False}
            if cmd:
                wr.update(self.command(res, cmd, rid, j["marker"], j["ri"], ms=300 if cmd == L.CMD_RUN64 else 120, w65=word,
                                       w64=j["w64"] if cmd == L.CMD_E537 else None, npass=j["npass"] if cmd == L.CMD_RUN64 else None))
                wr["wr"] = res.r(L.WR, 16) if wr["done"] else None
            rec["writer"] = wr
            # the reader the writer armed runs at the next event; the control's is the host's (cmd 9)
            if cmd:
                rd = {"ran": self.wait_reader(res, rid, 120) is not None}
            else:
                rd = dict(self.command(res, L.CMD_READ, rid), ran=None)
                rd["ran"] = rd["done"]
            rd["rd"] = res.r(L.RD, 16) if rd["ran"] else None
            rec["reader"] = rd
            rec["bracket"] = {"before": br0, "after": self.bracket_read(res)}
            rec["d_post"] = self.d_samples(res, 8)
            if not cmd and rd["rd"]:
                self.base63 = rd["rd"][L.RD_FIELDS.index("sa63")]
            if not self.check_tick(rec, "after-reader"):
                return
            if j["restore63"]:
                rec["restore"] = self.restore63(res, rid)
                self.check_tick(rec, "after-restore")
            rec["rc"] = 0
        finally:
            res.close()

    def restore63(self, res, rid):
        """Put sa63 back to what the control read (cmd 7, then the reader it armed)."""
        r = self.command(res, L.CMD_RESTORE63, rid, marker=self.base63)
        ran = self.wait_reader(res, rid, 120) is not None if r["done"] else False
        return {"cmd7": r, "reader_ran": ran, "rd": res.r(L.RD, 16) if ran else None, "wanted": self.base63}

    def baseline(self):
        """After a stop's reset and re-arm (alias2 stages): the reader, and cmd 7 if sa63 survived the reset (E536: sa100 and sa127 did)."""
        res = FR.Res()
        try:
            self.zero_protocol(res)
            res.w(L.A_M, self.base63)
            r = self.command(res, L.CMD_READ, 0x6f01)
            rd = res.r(L.RD, 16) if r["done"] else None
            out = {"read": r, "rd": rd, "restored": None}
            if rd is None:
                raise Stop(4, "baseline: the reader did not run after the re-arm")
            sa63 = rd[L.RD_FIELDS.index("sa63")]
            if sa63 != self.base63:
                out["restored"] = self.restore63(res, 0x6f02)
                rr = out["restored"]["rd"]
                if rr is None or rr[L.RD_FIELDS.index("sa63")] != self.base63:
                    raise Stop(4, f"baseline: sa63 is {sa63:#x} after the reset and the restore did not put {self.base63:#x} back")
            self.save(f"baseline-{self.stops}.json", out)
        finally:
            res.close()

    # ---- stage e ------------------------------------------------------------------------
    def act_job(self, j, rec):
        """E0 / X1 / X20 / B3: the window, then KIND, ACT and COUNT (COUNT > 0 arms the task), for B3 one miscinfo kick, the ring, the
        page twice, the tick.  The kick of B3 is the kernel's own `miscinfo` (a command and a kick together): never a bare kick."""
        res = FR.Res()
        self.cur_res = res
        try:
            self.ring_clear(res)
            rec["ccbctl_pre"] = self.ccbctl()
            rec["d0"] = self.d_samples(res, j["d_reads"])
            rec["bracket_pre"] = br0 = self.bracket_read(res)
            t0 = time.monotonic()
            self.ring_open(res, j["window"], rec)
            time.sleep(j["pre_ms"] / 1000)
            if j["count"]:
                res.w(L.KIND, [j["kind"], j["act"]])
                res.w(L.COUNT, j["count"])
                rec["t_count_ms"] = (time.monotonic() - t0) * 1000
            if j["trigger"] == "miscinfo":
                time.sleep(0.002)
                self.kick(rec)
            time.sleep(max(0.0, j["open_ms"] / 1000 - (time.monotonic() - t0)))
            self.ring_close(res, rec, t0)
            rec["bracket"] = {"before": br0, "after": self.bracket_read(res)}
            self.check_tick(rec, "after-window")
        finally:
            res.close()

    def kick(self, rec):
        """One GETMISCINFO (the kernel's command and kick together).  A failed read (the kernel's 500 ms timeout) is a result."""
        t = time.monotonic()
        try:
            rec["kick"] = FR.miscinfo()
            rec["kick"]["answered"] = rec["kick"].get("ms", 0) < L.P3_MS and not NOT_ANSWERED.search(str(rec["kick"].get("text", "")))
        except OSError as e:
            rec["kick"] = {"ms": (time.monotonic() - t) * 1000, "errno": e.errno, "text": f"no completion (the read failed: {e})",
                           "answered": False}
            rec.setdefault("kick_errors", []).append(rec["kick"]["errno"])

    # ---- classes ----------------------------------------------------------------------------
    def classify(self, j, rec):
        op = j["op"]
        if rec["fatal"]:
            rec["class"] = "fatal"
        elif rec.get("stopped"):
            rec["class"] = "stop"
        elif op in ("act", "holdsig") and rec.get("page") is None:
            rec["class"] = "void"
            rec["note"] += " no page read"
        elif hasattr(self, f"classify_{op}") and getattr(self, f"classify_{op}")(j, rec):
            pass                                 # the op's own classes (its health, its expected log lines)
        elif not rec["alive"].get("advancing"):
            rec["class"] = "tickstop"           # the tick stopped between the phase check and now: not signed: the stage stops
        elif not rec["health"].get("ok") or any(not t["ok"] for t in rec.get("ticks", [])):
            rec["class"] = "unhealthy"           # (includes a tick rate outside 900 to 1100 Hz)
        elif rec["log_bad"]:
            rec["class"] = "unhealthy"
        elif op == "alias2" and rec.get("rc") is None:
            rec["class"] = "void"
        elif op == "alias2" and j["cmd"] and not (rec.get("writer") or {}).get("done"):
            rec["class"] = "void"
            rec["note"] += " the writer's flag was not set"
        elif op == "alias2" and not (rec.get("reader") or {}).get("ran"):
            rec["class"] = "noreader"           # tick kept, reader not run: a result (cannot tell), not a stop
        elif op in ("act", "kicker") and rec.get("kick_errors"):
            rec["class"] = "kick-timeout"       # the tick is kept, the kick is not answered: a result
        else:
            rec["class"] = "ok"
        # a stop seen in the writer wait: the reader did not run and the tick is gone (E537's shape)
        if op == "alias2" and rec["class"] == "void" and rec.get("stopped"):
            rec["class"] = "stop"

    # ---- the stage ------------------------------------------------------------------------
    def stage_run(self):
        self.preflight()                     # nothing is armed yet: a preflight stop touches nothing
        try:
            return self.armed_run()
        except Stop as e:
            if e.code in (3, 6) or getattr(e, "ended", False):
                raise                        # fatal / no return: nothing else touches the GPU; or already ended
            raise self.cleanup(e.code, str(e))
        except Exception as e:               # anything unexpected after the first state change: the same cleanup
            raise self.cleanup(4, f"unexpected {e!r}")

    def cleanup(self, code, why):
        """After any stop once the stage began: dump, reset, gate.  Returns the Stop to raise (5 if not exact)."""
        try:
            FR.hang_dump(str(self.out), "stop")
        except Exception as e:
            print(f"(dump failed: {e!r})")
        try:
            ok = self.end("stop")
        except Exception as e:
            print(f"(reset or gate raised: {e!r})")
            ok = False
        s = Stop(code if ok else 5, why + ("" if ok else "; reset or gate not exact"))
        s.ended = True
        return s

    def run_if_ok(self, cond):
        """`all_kept:ROW:N`: at least N jobs of ROW ran, and every job of ROW that ran kept the tick (class ok)."""
        m = RUN_IF.match(cond)
        row, n = m.group(1), int(m.group(2))
        rs = [r for r in self.records.values() if r["row"] == row and r["class"] != "skipped"]
        return len(rs) >= n and all(r["class"] == "ok" for r in rs)

    def handle_stop(self, j, rec):
        """One tick stop: counted against the stage's budget.  The signature, P3 and the dumps were taken in the job, before this reset.
        A stopped row is never replicated (armed_run skips its later jobs).  Second stop: reset, gate, the stage ends (exit 8).  First:
        reset, gate (health), then, where the next job does not reset and arm itself, arm again (alias2 stages restore sa63)."""
        self.stops += 1
        if not L.ROW_SPEC[self.stage][j["row"]].get("rep_after_stop"):
            self.stopped_rows.add(j["row"])
        self.mark(f"stop {self.stops} {j['name']}")
        ok = self.end(f"stop{self.stops}-{j['name']}")
        if not ok:
            s = Stop(5, f"{j['name']}: reset or gate after the stop not exact")
            s.ended = True
            raise s
        if self.stops > int(self.table.get("stop_budget", 1)):
            s = Stop(EXIT_SECOND_STOP, f"{j['name']}: tick stop number {self.stops} ends the stage (reset and gate exact)")
            s.ended = True
            raise s
        if not self.table["per_job_reset"] and self.table["blob"]:
            self.arm(f"rearm{self.stops}")
            if self.table["blob"] == "alias2":
                self.baseline()
        elif j.get("restore63"):                 # D4 wrote sa63: it may survive the reset
            self.arm(f"rearm{self.stops}")
            self.baseline()
            if not self.end(f"stop{self.stops}-{j['name']}-restored"):
                s = Stop(5, f"{j['name']}: reset or gate after the sa63 restore not exact")
                s.ended = True
                raise s

    def armed_run(self):
        if not self.table["per_job_reset"] and self.table["blob"]:
            self.arm()                       # the per-job-reset stages reset and arm in every job
        for j in self.table["jobs"]:
            if j["row"] in self.stopped_rows:
                self.skipped(j, f"row {j['row']} stopped: a stopped row is never replicated")
                continue
            if j.get("run_if") and not self.run_if_ok(j["run_if"]):
                self.skipped(j, f"{j['run_if']} not met: {j['row']} is not run")
                continue
            rec = self.job(j)
            c = rec["class"]
            if c in OK_CLASSES:
                continue
            if c == "stop":
                self.handle_stop(j, rec)
                continue
            if c in ("fatal", "no-answer"):
                raise Stop(3 if c == "fatal" else 6, f"{j['name']}: {c}: nothing else touches the GPU")
            if c == "void" and j["op"] == "alias2" and rec.get("note", "").endswith("flag was not set"):
                raise Stop(4, f"{j['name']}: the writer did not run")
            raise Stop(4, f"{j['name']}: {c}")
        if not self.end("end"):
            s = Stop(5, "reset or gate at the end not exact")
            s.ended = True
            raise s
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--tool", required=True)
    ap.add_argument("--bins", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = Runner(a)
    code, why = 1, "the stage did not finish"     # never 0 unless stage_run returned it
    try:
        code, why = r.stage_run(), ""
    except Stop as e:
        code, why = e.code, str(e)
        print(f"## STOP {code}: {why}")
    except Exception as e:                        # before the first state change (stage_run handles everything after)
        code, why = 1, f"unexpected before the arm: {e!r}"
        print(f"## STOP {code}: {why}")
    finally:
        try:
            kl = FR.sh(f"journalctl -k --since @{int(r.t_start) - 2} --no-pager", check=False)
            (r.out / "kernel.log").write_text(kl)
        except Exception as e:      # the log is evidence, not a condition
            print(f"(kernel log not saved: {e})")
        r.save("stage.json", {"stage": a.stage, "run": r.run, "exit": code, "why": why, "jobs_run": list(r.records),
                              "stops": r.stops, "classes": {k: v["class"] for k, v in r.records.items()}})
    return code


if __name__ == "__main__":
    sys.exit(main())
