#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r5e_run.py STAGE --tool PATH --bins DIR --out DIR: one stage of R5-events on the laptop (python3 stdlib, as root: `sudo -n python3`).
PREPARED, NOT RUN.  The Mac side (run/stage_r5e.sh) uploads it with tables/, bins/, gen/r3layout.py, gen/r5layout.py, the landed
tools/fwtask/fwtask_run.py (resgx545 main, as run/fwtask_run.py), the op module run/ops_h.py, TOOL.sha256 and LAPTOP.sha256 to ~/r5e-run;
results go to OUT/STAGE (~/r5e-out/ATTEMPT/STAGE).  A copy of R4-events' runner (closing4/r4-events/run/r4e_run.py, E834-E837) with its
kb2 and kp ops dropped, its e3p op extended (ops_h.py) and the clock knob timer_clock added.

Stages (tables/STAGE.json; the rows are r5layout.ROW_SPEC, checked against the table before anything runs), all on ring_skip3p (R4's bytes):
  h1  timer_clock 0: B0, B1P x3 (R4's e3p job; the clears after the watch)
  h2  timer_clock 800000: B0A, B1PA x2; then 1600000: B0B, B1PB x2 (no host write before the watch ends)
  h3  timer_clock 1600000: B0, B1E x3 (the clears at the slot 3 entry, one miscinfo after them, then the watch)
Every job: timer_clock written (read back) BEFORE its reset and arm (the kernel writes it into HostCtl dword 6 when it boots the
firmware: E084), the arm's status dump (dword 6, dword 3, dword 8), the job, a status dump after the watch.  Every stage ends with
timer_clock 0 written and read back, the reset, the gate, and the tick on the 25000-unit grid in a 20 ms window of the ring (`clock_back`).

Safety (checked by run/guard_r5e.sh and run/guard_blobs.py): the only debugfs writes are own_code, own_arm, own_res (the page), load, boot,
reset (the landed commands) and, through `knob`: hold_recovery (Y in B1P / B1E, N) and timer_clock (0, 800000, 1600000 only), and kregnow
(only `0x0134=` with bits 15 and 18, in ops_h.py); /dev/kmsg (os.open, O_WRONLY | O_APPEND); no other register, no clock-gate register,
no trc_hazard, no kreg; NO firmware `str` in the blob; no `mov` to a pa or sa register.  A bare kick is never made: a kick is `miscinfo`,
which the kernel sends with its command.  Every knob written is put back by the job's own finally and again, whatever happened, by the
runner's exit handler (a trap on TERM, HUP and INT too): hold_recovery N, timer_clock 0 (then a reset, so that the firmware runs at its own
clock again).

Stops.  A TICK STOP (HostCtl dword 12 not advancing over three reads) is signed at once, BEFORE anything else runs: the signature
registers, HostCtl dword 14 and the CCB offsets twice (P1), the landed dumps (stop-NAME-status.txt holds the lockup marks), then (h1) the
host's clears and P3: one `miscinfo` into the stopped EDM.  Then the debugfs reset, the gate and the health.  In this session a stop of a
B1P / B1E row is the PREDICTION (R5-4 (a)): the stage goes on after it if (1) the reset, gate and health are exact, (2) the stop is
explained: the status dump carries the lockup marks (HostCtl dword 3 above the arm's, dword 8 bit 0) and the ring holds the fill's kick
entry (the count is readable).  An unexplained stop, a control (B0) that stops, a stop past the stage's budget: exit 8 (the stage ends,
the driver ends the session).  A freeze (exit 6) or a watchdog (fatal, exit 3) stops all laptop work.  Other exits: 1 preflight, 4 a job
failed or an exception, 5 reset or gate not exact (ask the user for a reboot), 7 a table value outside the allow-list, 9 the clock did
not come back to the 25000-unit grid at the stage's end.  No loop waits for anything but bounded `for` loops with fixed sleeps.
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
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent          # ~/r5e-run on the laptop
sys.path.insert(0, str(R3 / "gen"))
sys.path.insert(0, str(R3 / "run"))
sys.path.insert(0, os.environ.get("R3_FWTASK_DIR", str(R3 / "run")))   # tests point it at a fake
import r5layout as L  # noqa: E402
import fwtask_run as FR  # noqa: E402
from r3common import Stop  # noqa: E402
import ops_h  # noqa: E402   (the op family of this session)

BLOB_OF = L.BLOB_OF
GATE_OF = L.GATE_OF
GATE_EXITS = (0, 8)
OPS_OF = {st: i["ops"] for st, i in L.STAGE_INFO.items()}
RING_STAGES = set(L.STAGES)
MARK = L.MARK
FATAL_RE = re.compile(r"soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|"
                      r"blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check")
TOOL_BAD = re.compile(r"FAIL|Traceback|\"error\"|\bBUG\b|\bOops\b|refus")      # searched in the WHOLE output of a tool command
OK_CLASSES = ("ok", "kick-timeout")
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


class Runner(ops_h.HOps):
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
        self.knobs_written = {}              # name -> the value it is put back to
        self.clock = 0                       # the timer_clock the firmware was last booted with by this run (0: the default)
        self.cases = self.out / "cases.tsv"
        self.cases.write_text("name\tset\trow\tclass\trc\tnote\n")

    # ---- small helpers ------------------------------------------------------------------
    def mark(self, text):
        try:
            # os.open with O_APPEND and no seek: Python's "a" mode seeks, which /dev/kmsg refuses with EINVAL (seen on the laptop)
            fd = os.open(KMSG, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(fd, f"resgx545 r5e {text} {self.run}\n".encode())
            finally:
                os.close(fd)
        except OSError as e:
            print(f"  (kmsg marker not written: {e})")

    def save(self, name, obj):
        (self.out / name).write_text(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n")

    def ccbctl(self):
        return parse_ccbctl(FR.rd("regs"))

    def reg(self, off):
        return FR.regs()[0].get(off)

    KNOB_BACK = {"hold_recovery": "N", "timer_clock": "0"}

    def knob(self, name, val):
        """Write one of the two knobs this session writes (hold_recovery Y / N, timer_clock 0 / 800000 / 1600000: r5layout.CLOCKS) and
        read it back (the read-back is what is recorded); the value it is put back to is KNOB_BACK's."""
        if name not in self.KNOB_BACK:
            raise Stop(7, f"knob {name} is not one this session writes")
        if name == "hold_recovery" and val not in ("Y", "N"):
            raise Stop(7, f"hold_recovery {val!r}")
        if name == "timer_clock" and (not str(val).isdigit() or int(val) not in L.CLOCKS):
            raise Stop(7, f"timer_clock {val!r} is not one of {L.CLOCKS}")
        FR.wr(name, str(val))
        self.knobs_written[name] = self.KNOB_BACK[name]
        return FR.rd(name).strip()

    def restore_knobs(self):
        """Put back every knob this run wrote (the exit handler's last act: whatever happened, hold_recovery N and timer_clock 0; the
        firmware takes timer_clock at its next boot, which the stage's end, or the next session's first reset, makes)."""
        for name, val in list(self.knobs_written.items()):
            try:
                FR.wr(name, val)
                self.knobs_written.pop(name, None)
            except Exception as e:
                print(f"(knob {name} not restored: {e!r})")

    # ---- preflight ----------------------------------------------------------------------
    NEED_FILES = ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo", "kick_no_bump", "kregnow",
                  "hold_recovery", "render_rgn_arrays", "render_pb_pages", "timer_clock")

    def preflight(self):
        env = {"stage": self.stage, "run": self.run, "euid": os.geteuid()}
        if os.geteuid() != 0 and os.environ.get("R3_MOCK_ROOT") != "1":
            raise Stop(1, "not root: run as `sudo -n python3 r5e_run.py` (every debugfs access needs root)")
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
        need = [f"tables/{self.stage}.json", "gen/r3layout.py", "gen/r5layout.py", "run/r5e_run.py", "run/fwtask_run.py", "TOOL.sha256",
                "bins/blobs.json", "run/r3common.py", "run/ops_h.py"]
        if blob:
            need.append(f"bins/{blob}.blob")
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
                # the previous stage's kept stage.json: in this attempt's results directory (OUT/ATTEMPT/PREV)
                pst = json.loads((self.out.parent / prev / "stage.json").read_text())
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
        # the knobs this session never writes: each must read its default (a2788bd8: render_rgn_arrays 0, automatic)
        env["knobs"] = {k: FR.rd(k).strip() for k in L.KNOB_DEFAULTS}
        off = {k: v for k, v in env["knobs"].items() if v != L.KNOB_DEFAULTS[k]}
        if off:
            raise Stop(1, f"knobs not at their defaults: {off} (this session writes none: the lead decides)")
        # the firmware must be running before the first arm: after a fresh boot the driver's load step (a fill and a triangle) loads it
        a0 = FR.alive()
        env["alive_at_preflight"] = a0
        if not a0.get("advancing"):
            raise Stop(1, "the firmware is not running (HostCtl dword 12 not advancing): run the load step (a fill and a triangle) first")
        if not os.access(self.tool, os.X_OK):
            raise Stop(1, f"no tool {self.tool}")
        env["tool_sha256"] = sha(self.tool)
        if env["tool_sha256"] != (R3 / "TOOL.sha256").read_text().split()[0]:
            raise Stop(1, f"the tool is not the pinned one ({env['tool_sha256'][:12]}, pinned in TOOL.sha256)")
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
        if binfo["sa_writes"] or binfo.get("pa_writes"):
            raise Stop(1, f"{blob} writes an sa or pa register")
        if binfo.get("cont4"):
            raise Stop(1, f"{blob} carries a cont4 patch: none of this session's blobs may")
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
        marker = f"resgx545 r5e arm {self.stage} {tag} {self.run}"
        out = captured(FR.cmd_arm, a)
        # the landed cmd_arm's `ok` asks for a tick rate of 900 to 1100 Hz, the default clock's; at 800000 and 1600000 the firmware ticks
        # at 498.8 and 249.4 Hz (E084): the same conditions are judged again with the band of the clock this job booted with
        band = L.rate_band(self.clock)
        out["ok_landed"], out["rate_band"], out["clock"] = out.get("ok"), [round(band[0], 1), round(band[1], 1)], self.clock
        rate = out.get("rate_hz") or 0
        # the landed verdict stands unless the default band alone can have failed it (a rate outside 900 to 1100 Hz)
        landed_ok_or_rate = bool(out.get("ok")) or not (900 <= rate <= 1100)
        out["ok"] = bool(landed_ok_or_rate and (out.get("alive") or {}).get("advancing") and band[0] <= rate <= band[1]
                         and (out.get("health") or {}).get("ok") and not out.get("log_bad") and out.get("magic") == L.MAGIC)
        # the landed cmd_arm (6421c1c) slices the log by its own marker; the runner reads it again after its own arm marker with the
        # landed dmesg_new(marker), and judges each line with the landed is_bad_log (the reset's info line is not bad)
        try:
            new = FR.dmesg_new(marker)
            if new[:1] == [FR.NO_MARKER]:
                raise RuntimeError("the arm's kmsg marker is not in dmesg")
            out["log_tool"], out["log_bad_tool"] = out.get("log"), out.get("log_bad")
            out["log"] = [ln for ln in new if "own" in ln]
            out["log_bad"] = [ln for ln in new if FR.is_bad_log(ln) and "resgx545 " not in ln]
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

    def set_clock(self, v, rec):
        """timer_clock written and read back BEFORE the job's reset (the kernel copies it into HostCtl dword 6 at the boot: E084)."""
        rb = self.knob("timer_clock", str(v))
        rec["timer_clock_read"] = rb
        if rb != L.knob_text(v):
            raise Stop(4, f"timer_clock reads {rb!r} after {v} was written, not {L.knob_text(v)}")
        self.clock = v

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
        """(ok, alive, rate): HostCtl dword 12 advancing over three reads 20 ms apart, and a rate within the band of the clock the
        firmware was booted with (r5layout.rate_band: 900 to 1100 Hz at the default)."""
        a = FR.alive()
        if not a["advancing"]:
            return False, a, None
        rate = FR.tick_rate(100)
        lo, hi = L.rate_band(self.clock)
        return bool(lo <= rate <= hi), a, rate

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
        marker = f"resgx545 r5e case {name} {self.run}"
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
            new = FR.dmesg_new(marker)              # the landed slice after this job's own marker (6421c1c)
            if new[:1] == [FR.NO_MARKER]:
                rec["note"] += " marker not in dmesg: the whole buffer was read"
            (self.out / f"{name}.dmesg").write_text("\n".join(new) + "\n")
            rec["log_bad"] = [ln for ln in new if FR.is_bad_log(ln) and "resgx545 " not in ln]
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
        if rec["class"] == "fatal":               # a watchdog line in the job's slice: nothing else touches the GPU (no reset)
            raise Stop(3, f"{name}: fatal kernel line {rec['fatal'][:1]}")
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

    # ---- classes ----------------------------------------------------------------------------
    def classify(self, j, rec):
        op = j["op"]
        if rec["fatal"]:
            rec["class"] = "fatal"
        elif rec.get("stopped"):
            rec["class"] = "stop"
        elif op == "hjob" and rec.get("page") is None:
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
        else:
            rec["class"] = "ok"

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
        self.restore_knobs()                 # hold_recovery N, timer_clock 0: the reset below boots the firmware at its own clock
        self.clock = 0
        try:
            ok = self.end("stop")
        except Exception as e:
            print(f"(reset or gate raised: {e!r})")
            ok = False
        s = Stop(code if ok else 5, why + ("" if ok else "; reset or gate not exact"))
        s.ended = True
        return s

    def post_job(self, j, rec):
        """After a job that kept the tick: the op's own post_OP (kb2's G0P timing control, e3p's recovery of a held job)."""
        fn = getattr(self, f"post_{j['op']}", None)
        if fn is not None:
            fn(j, rec)

    def run_if_ok(self, cond):
        """`all_kept:ROW:N`: at least N jobs of ROW ran, and every job of ROW that ran kept the tick (class ok)."""
        m = RUN_IF.match(cond)
        row, n = m.group(1), int(m.group(2))
        rs = [r for r in self.records.values() if r["row"] == row and r["class"] != "skipped"]
        return len(rs) >= n and all(r["class"] == "ok" for r in rs)

    def handle_stop(self, j, rec):
        """One tick stop.  The signature, the dumps, the clears (h1) and P3 were taken in the job, before this reset.  Then the reset, the
        gate and the health (end()).  In this session a B1P / B1E stop is the prediction (R5-4 (a)): the stage goes on after it when the
        recovery is exact AND the stop is explained (the lockup marks in its status dump, the fill's kick entry in the ring: the job's
        `explained`).  A control's stop (B0), an unexplained stop or a stop past the stage's budget ends the stage (exit 8)."""
        self.stops += 1
        if not L.ROW_SPEC[self.stage][j["row"]].get("rep_after_stop"):
            self.stopped_rows.add(j["row"])
        self.mark(f"stop {self.stops} {j['name']}")
        ok = self.end(f"stop{self.stops}-{j['name']}")
        if not ok:
            s = Stop(5, f"{j['name']}: reset or gate after the stop not exact (the lead asks the user before anything else)")
            s.ended = True
            raise s
        if not j.get("may_stop"):
            s = Stop(EXIT_SECOND_STOP, f"{j['name']}: a control stopped the tick: the stage ends (reset and gate exact)")
            s.ended = True
            raise s
        if not rec.get("explained"):
            s = Stop(EXIT_SECOND_STOP, f"{j['name']}: an unexplained stop ({rec.get('explained_why')}): the stage and the session end "
                                       "(reset and gate exact)")
            s.ended = True
            raise s
        if self.stops > int(self.table.get("stop_budget", 1)):
            s = Stop(EXIT_SECOND_STOP, f"{j['name']}: tick stop number {self.stops} ends the stage (reset and gate exact)")
            s.ended = True
            raise s

    def armed_run(self):
        for j in self.table["jobs"]:
            if j["row"] in self.stopped_rows:
                self.skipped(j, f"row {j['row']} stopped: a stopped row is never replicated")
                continue
            rec = self.job(j)
            c = rec["class"]
            if c in OK_CLASSES:
                self.post_job(j, rec)
                continue
            if c == "stop":
                self.handle_stop(j, rec)
                continue
            if c in ("fatal", "no-answer"):
                raise Stop(3 if c == "fatal" else 6, f"{j['name']}: {c}: nothing else touches the GPU")
            raise Stop(4, f"{j['name']}: {c}")
        return self.clock_back()

    def clock_back(self):
        """The stage's end: timer_clock 0 written and read back, a reset and an arm (the firmware boots at its own clock), the ring open
        for 20 ms, its tick gap on the 25000-unit grid (+-10) and the rate in 900 to 1100 Hz; then the reset, the gate and the health."""
        out = {"knob": self.knob("timer_clock", "0")}
        self.knobs_written.pop("timer_clock", None)
        self.clock = 0
        rec = {"name": "clock-back"}
        self.pre_reset_arm({"name": "clock-back"}, rec)
        res = FR.Res()
        try:
            self.ring_clear(res)
            res.w(L.SKIP3, 0)
            self.ring_open(res, 2, rec)
            time.sleep(0.020)
            res.w(L.WINDOW, 0)
            time.sleep(0.003)
            page = res.page()
        finally:
            res.close()
        s0 = [e for e in L.slot_entries(page, 0) if L.is_tick_entry(e)]
        gaps = [(b[4] - a[4]) & 0xFFFFFFFF for a, b in zip(s0, s0[1:])]
        med = sorted(gaps)[len(gaps) // 2] if gaps else None
        ok_t, a, rate = self.tick_check()
        out.update({"ticks_in_ring": len(s0), "gaps": gaps, "gap_median": med, "rate_hz": rate, "alive": a,
                    "status": FR.rd("status")})
        good = out["knob"] == L.knob_text(0) and med is not None and abs(med - L.gap_units(0)) <= L.GAP_TOL[0] and ok_t
        out["ok"] = bool(good)
        self.save("clock-back.json", out)
        print(f"## clock back: timer_clock {out['knob']}, gap {med}, rate {rate}, ok {out['ok']}")
        if not self.end("end"):
            s = Stop(5, "reset or gate at the end not exact")
            s.ended = True
            raise s
        if not good:
            s = Stop(9, f"the clock did not come back: timer_clock {out['knob']}, median gap {med}, rate {rate}")
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
    kept = pathlib.Path(a.out) / a.stage / "stage.json"
    if kept.exists():                             # an attempt is never overwritten: nothing is written, nothing touched
        print(f"## STOP 1: {kept} exists: give the driver another attempt")
        return 1
    r = Runner(a)
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):     # the trap: the finally blocks run, then the knobs are put back
        signal.signal(sig, lambda n, f: sys.exit(128 + n))
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
        r.restore_knobs()
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
