#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r1_run.py STAGE --tool PATH --rt PATH --bins DIR --out DIR: one R1-events stage on the laptop (python3 stdlib, as
root: `sudo -n python3`).  PREPARED, NOT RUN.  The Mac side (run/r1.sh) uploads it with tables/, bins/,
gen/r1layout.py, the landed tools/fwtask/fwtask_run.py (as run/fwtask_run.py), TOOL.sha256 and LAPTOP.sha256.

Stages (tables/STAGE.json):
  k    Q290.  One arm a job (ring_e1; K2 and K3 through arm_scratch, a scratch copy of the landed cmd_arm that omits the
       runner's own GETMISCINFO or adds two; the landed cmd_arm is not changed), the ring window, a trigger (none, one
       kick, 254 + 4 kicks, a client tool), the page twice, ccbctl before and after, the kernel log's GETMISCINFO answers.
  t    Q082.  Stock firmware: a debugfs reset, the job's own read of CR_EVENT_STATUS2 (must be 0x400), one `probe` of a
       loop program (or the held TA fault of S3), CR_EVENT_STATUS2 read again.
  d0   Q033 controls: ring_e1 armed once, window 1, a client tool (tri 64x64, the partial render at render_pb_pages 0x30).
  d1   Q033 D2-D4: 4096x4096, 1500 vertices, one reset and arm before every job, render_pb_pages written, read back and
       put back, window 1 open before the tool, the tool under regtimeline (D5), the control block (debugfs buf09) read
       after the job, the render dumps kept in NAME.dump/.

Safety (checked by run/guard_r1.sh): no kernel change; the only writes are debugfs own_code, own_arm, own_res, load, boot,
reset, render_pb_pages and hold_recovery (an allow-list), /dev/kmsg (os.open, O_WRONLY | O_APPEND: Python's "a" mode seeks
and /dev/kmsg refuses it) and the results page; no register write of any kind (no kreg, kpoke, clock-gate register,
trc_hazard); no sa write (the task is ring_e1, which has none); no str; the kernel's own debugfs reset is the only reset.
The debugfs directory is found through dri/*/sgx (the device has three names, dri/0, dri/0000:00:02.0 and dri/128: the
first that holds own_res is used, the others are recorded).

Every stage: preflight (root, every file it reads is the frozen one, the tool is the pinned sgxfive-test-s1b, srcversion
installed = loaded, the debugfs files, the knobs at their defaults, the previous stage's gate where there is one); arm;
the jobs, one kernel-log marker each (`resgx545 r1 case NAME RUN`), its JSON and dmesg slice written whatever happens;
the end: the landed cmd_reset and the gate (fill and triangle exact).
Stop classes (after a stop: the page and the debugfs state are dumped, reset, gate, exit; no loop waits for anything: every
delay is one fixed sleep, every loop is a bounded for):
  no-answer  the tool gave no result within its time limit       -> exit 6, nothing else touches the GPU
  fatal     watchdog / lockup / BUG / Oops in the kernel log  -> exit 3, nothing else touches the GPU
  tickstop  HostCtl dword 12 did not advance over three reads, unhealthy (EVENT_STATUS2, a BIF fault, a bad log line)
  trigfail  the client tool failed                            -> exit 4;  error: any other exception -> exit 4
Other exits: 1 preflight, 5 reset or gate after a stop (or at the end) not exact, 7 a table value outside the allow-list,
9 a knob read back differs.  A freeze or a watchdog stops the runner (exit 6 or 3).
"""
import argparse
import contextlib
import glob
import gzip
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
R1 = pathlib.Path(__file__).resolve().parent.parent          # ~/r1ev on the laptop
sys.path.insert(0, str(R1 / "gen"))
sys.path.insert(0, os.environ.get("R1_FWTASK_DIR", str(R1 / "run")))   # tests point it at a fake
import r1layout as L  # noqa: E402
import fwtask_run as FR  # noqa: E402

KNOBS = {"render_pb_pages": "0x422", "hold_recovery": "N"}     # the allow-list and the defaults they are put back to
BLOBS = {"ring_e1"}
GATE_OF = {"d1": "d0"}
FATAL_RE = re.compile(r"soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|"
                      r"blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check")
IDENT_RE = re.compile(r"SGX firmware: core \d+ rev")          # one line per GETMISCINFO the kernel asked (sgxfive_ident_ask)
KMSG = os.environ.get("R1_KMSG", "/dev/kmsg")
SRCV_PATH = os.environ.get("R1_SRCV_PATH", "/sys/module/gma500_gfx/srcversion")
ARM_CALLS = {"std": 2, "nomisc": 1, "extra2": 4}            # GETMISCINFO of the arm path: boot's + the runner's own ones
ARM_ALLOWED = {"std", "nomisc", "extra2"}


class Stop(Exception):
    def __init__(self, code, why):
        super().__init__(why)
        self.code = code


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def captured(fn, a=None):
    """Run a landed fwtask_run command (it prints one JSON object) and return that object."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(a or {})
    lines = [ln for ln in buf.getvalue().splitlines() if ln.startswith("{")]
    return json.loads(lines[-1]) if lines else {"ok": False, "error": "no output"}


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


def arm_scratch(a, variant):
    """A SCRATCH copy of the landed fwtask_run.cmd_arm (the landed one is unchanged), for Q290's K2 and K3.  The same
    statements in the same order; only the runner's own GETMISCINFO read differs: variant nomisc leaves it out (the boot's
    own is then the only one), variant extra2 adds two more after the health check.  tests/test_scorer.py compares this
    function with the landed source line by line."""
    n0 = FR.dmesg_len()
    FR.wr("own_arm", "0")
    with open(a["blob"], "rb") as f:
        data = f.read()
    FR.wr("own_code", data)
    if a.get("arm"):
        FR.wr("own_arm", a["arm"])
    FR.wr("load", "1")
    FR.wr("boot", "1")
    time.sleep(0.1)
    out = {"own_arm": FR.rd("own_arm").strip(), "alive": FR.alive(), "rate_hz": FR.tick_rate(),
           "misc": None if variant == "nomisc" else FR.miscinfo(), "health": FR.health()}
    out["misc_extra"] = [FR.miscinfo(), FR.miscinfo()] if variant == "extra2" else []
    out["log_bad"] = [ln for ln in FR.dmesg_new(n0) if FR.BAD_LOG.search(ln)]
    out["log"] = [ln for ln in FR.dmesg_new(n0) if "own" in ln]
    res = FR.Res()
    out["magic"] = res.r(0)[0]
    res.close()
    out["ok"] = (out["alive"]["advancing"] and 900 <= out["rate_hz"] <= 1100 and out["health"]["ok"]
                 and not out["log_bad"] and out["magic"] == 0x4e574f53)
    return out


def parse_ccbctl(text):
    """[ctl0, ctl1] from the regs file's `ccbctl 0x00 0x........` and `ccbctl 0x04 0x........` lines (None: not there)."""
    v = {}
    for ln in text.splitlines():
        m = re.match(r"ccbctl 0x(00|04) (0x[0-9a-f]+)$", ln)
        if m:
            v[int(m.group(1), 16) // 4] = int(m.group(2), 16)
    return [v.get(0), v.get(1)] if v else None


class Runner:
    def __init__(self, a):
        self.stage, self.tool, self.rt, self.bins = a.stage, a.tool, a.rt, a.bins
        self.out = pathlib.Path(a.out) / a.stage
        self.out.mkdir(parents=True, exist_ok=True)
        self.run = f"{int(time.time())}-{os.getpid()}"
        self.t_start = time.time()
        self.table = None
        self.records = {}
        self.armed = False
        self.cases = self.out / "cases.tsv"
        self.cases.write_text("name\tset\top\tclass\trc\ttrigger_rc\tnote\n")

    # ---- small helpers ------------------------------------------------------------------
    def mark(self, text):
        try:
            # os.open with O_APPEND and no seek: Python's "a" mode seeks, which /dev/kmsg refuses with EINVAL (seen on
            # the laptop); "w" would truncate the mock's plain file
            fd = os.open(KMSG, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(fd, f"resgx545 r1 {text} {self.run}\n".encode())
            finally:
                os.close(fd)
        except OSError as e:
            print(f"  (kmsg marker not written: {e})")

    def save(self, name, obj):
        (self.out / name).write_text(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n")

    def knob(self, name, value):
        if name not in KNOBS:
            raise Stop(7, f"knob {name} is not on the R1 allow-list")
        FR.wr(name, value)
        rb = FR.rd(name).strip()
        same = (rb == value) if name == "hold_recovery" else (int(rb, 0) == int(value, 0))
        self.mark(f"readback {self.stage} {name}={rb}")
        if not same:
            raise Stop(9, f"{name}: wrote {value}, read back {rb}")
        return rb

    def expand(self, args, wdir=None):
        return [x.replace("$B", str(self.bins)).replace("$W", str(wdir or "")) for x in args]

    @staticmethod
    def tool_timeout(j):
        """The table's bound on the client tool (R1_TOOL_TIMEOUT_S shortens it in the mock tests only)."""
        return float(os.environ.get("R1_TOOL_TIMEOUT_S", j.get("tool_timeout_s", 60)))

    def status2(self):
        r, hc = FR.regs()
        return r.get(0x118)

    def ccbctl(self):
        return parse_ccbctl(FR.rd("regs"))

    def ident_count(self, marker):
        """GETMISCINFO answers the kernel logged since `marker`: the independent count of the arm path's commands."""
        lines = FR.dmesg_new(0)
        at = max((i for i, ln in enumerate(lines) if marker in ln), default=None)
        return None if at is None else sum(1 for ln in lines[at + 1:] if IDENT_RE.search(ln))

    # ---- preflight ----------------------------------------------------------------------
    def preflight(self):
        env = {"stage": self.stage, "run": self.run, "euid": os.geteuid()}
        if os.geteuid() != 0 and os.environ.get("R1_MOCK_ROOT") != "1":
            raise Stop(1, "not root: run as `sudo -n python3 r1_run.py` (every debugfs access needs root)")
        frozen = {}
        for ln in (R1 / "LAPTOP.sha256").read_text().splitlines():
            h, f = ln.split(None, 1)
            frozen[f.strip()] = h
        self.table = json.loads((R1 / "tables" / f"{self.stage}.json").read_text())
        need = [f"tables/{self.stage}.json", "gen/r1layout.py", "run/r1_run.py", "run/fwtask_run.py", "TOOL.sha256"]
        blob = self.table["blob"]
        if blob:
            if blob not in BLOBS:
                raise Stop(1, f"blob {blob} is unknown")
            need.append(f"bins/{blob}.blob")
        for j in self.table["jobs"]:
            self.check_job(j)
            for x in j.get("tool_args", []):
                if x.startswith("$B/"):
                    need.append("bins/" + x[3:])
        for f in sorted(set(need)):
            if frozen.get(f) != sha(R1 / f):
                raise Stop(1, f"{f} is not the frozen file")
        prev = GATE_OF.get(self.stage)
        if prev:
            g = R1 / "gates" / f"{prev}.gate"
            txt = g.read_text() if g.exists() else ""
            if not txt.startswith(f"GATE {prev} OPEN"):
                raise Stop(1, f"the gate of {prev} is not open ({g}: {txt.strip()[:80] or 'missing'})")
            m = re.search(r"\brun=(\S+)", txt)
            try:
                pst = json.loads((self.out.parent / prev / "stage.json").read_text())
            except (OSError, ValueError):
                pst = {}
            if not m or pst.get("run") != m.group(1) or pst.get("exit") != 0:
                raise Stop(1, f"the gate of {prev} is not of its last run here (gate run "
                              f"{m.group(1) if m else 'none'}, stage.json run {pst.get('run')} exit {pst.get('exit')})")
            env["gate"] = txt.strip()
        d, cands = pick_debugfs() if "R1_DEBUGFS" not in os.environ else (os.environ["R1_DEBUGFS"], [os.environ["R1_DEBUGFS"]])
        if d is None:
            raise Stop(1, f"no sgx debugfs directory with own_res among {cands} (debug option off?)")
        FR.D = d
        env["debugfs"], env["debugfs_candidates"] = d, cands
        with open(SRCV_PATH) as f:
            env["srcversion_loaded"] = f.read().strip()
        env["srcversion_installed"] = FR.sh("modinfo -F srcversion gma500_gfx", check=False).strip()
        if not env["srcversion_loaded"] or env["srcversion_loaded"] != env["srcversion_installed"]:
            raise Stop(1, "the loaded module is not the installed one")
        for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo",
                  "hold_recovery", "render_pb_pages") + (("buf09",) if self.stage in ("d0", "d1") else ()):
            if not os.path.exists(f"{FR.D}/{f}"):
                raise Stop(1, f"the driver has no debugfs {f}")
        env["hold_recovery"] = FR.rd("hold_recovery").strip()
        env["render_pb_pages"] = FR.rd("render_pb_pages").strip()
        if env["hold_recovery"] != "N" or int(env["render_pb_pages"], 0) != 0x422:
            raise Stop(1, f"knobs not at their defaults at the start: {env}")
        if not os.access(self.tool, os.X_OK):
            raise Stop(1, f"no tool {self.tool}")
        env["tool_sha256"] = sha(self.tool)
        if env["tool_sha256"] != (R1 / "TOOL.sha256").read_text().split()[0]:
            raise Stop(1, f"the tool is not the pinned sgxfive-test-s1b ({env['tool_sha256'][:12]}, pinned in TOOL.sha256)")
        if self.stage == "d1" and not os.access(self.rt, os.X_OK):
            raise Stop(1, f"no regtimeline {self.rt}")
        gate_tool = getattr(FR, "GATE_TOOL", "/home/jtorra/sgxfive-test")    # the landed cmd_gate's tool
        if not os.access(gate_tool, os.X_OK):
            raise Stop(1, f"no gate tool {gate_tool} (the landed fwtask_run.cmd_gate runs it): sgxfive-test missing")
        env["gate_tool_sha256"] = sha(gate_tool)
        if sys.version_info < (3, 8):
            raise Stop(1, f"python {sys.version.split()[0]} is older than 3.8")
        env["python"] = sys.version.split()[0]
        env["uname"] = FR.sh("uname -r", check=False).strip()
        env["firmware_sha256"] = FR.sh("sha256sum /lib/firmware/sgx545_ukernel.fw", check=False).split(" ")[0]
        env["blob_sha256"] = frozen.get(f"bins/{blob}.blob") if blob else None
        env["table_sha256"] = frozen[f"tables/{self.stage}.json"]
        self.save("env.json", env)
        self.mark(f"preflight {self.stage}")
        print(f"## preflight ok: {json.dumps({k: env[k] for k in ('srcversion_loaded', 'uname', 'tool_sha256', 'debugfs')})}")

    def check_job(self, j):
        op = j.get("op")
        if op == "k":
            if j.get("arm_variant") not in ARM_ALLOWED or j.get("pre") not in ("none", "reset"):
                raise Stop(7, f"{j['name']}: arm variant or pre outside the allow-list")
            if j.get("window") not in (0, 1, 2) or int(j.get("warm", 0)) > 300 or int(j.get("logged", 0)) > 8:
                raise Stop(7, f"{j['name']}: window or kick counts outside the allow-list")
            if j.get("trigger", "none") not in ("none", "kick", "kicks") and not j["trigger"].startswith("tool:"):
                raise Stop(7, f"{j['name']}: unknown trigger")
        elif op == "ringtool":
            if j.get("window") not in (1, 2):
                raise Stop(7, f"{j['name']}: window outside the allow-list")
        elif op not in ("probe", "hold_fault"):
            raise Stop(7, f"{j['name']}: unknown op {op}")
        for k, v in j.get("knobs", {}).items():
            if k not in KNOBS:
                raise Stop(7, f"{j['name']}: knob {k} not allowed")

    # ---- arm / end ----------------------------------------------------------------------
    def zero_protocol(self):
        res = FR.Res()
        res.w(L.CMD, [0, 0])                 # CMD, STATE
        res.w(L.WINDOW, 0)
        res.w(L.N_ITER, 0)
        res.close()

    def arm(self, variant="std", tag="arm"):
        """Arm ring_e1: the landed cmd_arm (std) or the scratch copy (K2, K3).  Zeroes the protocol words first."""
        self.zero_protocol()
        a = {"blob": str(R1 / "bins" / f"{self.table['blob']}.blob"), "arm": self.table["arm"]}
        out = captured(FR.cmd_arm, a) if variant == "std" else self.scratch_arm(a, variant)
        self.save(f"{tag}.json", out)
        print(f"## {tag} {variant}: ok {out.get('ok')} rate {out.get('rate_hz')}")
        if not out.get("ok"):
            raise Stop(4, f"arm not ok: {json.dumps({k: out.get(k) for k in ('alive', 'health', 'log_bad', 'magic')})}")
        res = FR.Res()
        cmd, state = res.r(L.CMD, 2)
        win = res.r(L.WINDOW)[0]
        res.close()
        if cmd or win:
            raise Stop(4, f"after the arm CMD {cmd} WINDOW {win}, not 0")
        self.armed = True
        return out

    def scratch_arm(self, a, variant):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            out = arm_scratch(a, variant)
        return out

    def end(self, tag):
        r = captured(FR.cmd_reset)
        g = captured(FR.cmd_gate)
        self.save(f"{tag}-reset.json", {"reset": r, "gate": g})
        print(f"## {tag}: reset ok {r.get('ok')}, gate ok {g.get('ok')}")
        self.armed = False
        return bool(r.get("ok") and g.get("ok"))

    # ---- one job ------------------------------------------------------------------------
    def job(self, j):
        name = j["name"]
        rec = {"name": name, "set": j["set"], "op": j["op"], "job": j, "class": "void", "rc": None, "trigger_rc": None,
               "note": "", "run": self.run}
        marker = f"resgx545 r1 case {name} {self.run}"
        self.mark(f"case {name}")
        err = None
        try:
            for k, v in j.get("knobs", {}).items():
                if j["op"] != "hold_fault":                  # the held fault sets hold_recovery itself, after the reset
                    rec.setdefault("knobs_readback", {})[k] = self.knob(k, v)
            if j["op"] == "k":
                self.k_job(j, rec)
            elif j["op"] == "ringtool":
                self.ringtool_job(j, rec)
            elif j["op"] == "probe":
                self.probe_job(j, rec)
            else:
                self.hold_job(j, rec)
        except BaseException as e:          # recorded, then raised again after the record is written
            err = e
            rec["note"] += f" error: {e!r}"
        # every step below is guarded: the record and the cases.tsv row are written whatever fails
        for k in j.get("knobs", {}):        # the knobs back before anything else touches the GPU
            try:
                rec.setdefault("knobs_restored", {})[k] = self.knob(k, KNOBS[k])
            except Exception as e:
                rec["note"] += f" knob restore: {e}"
                rec["restore_failed"] = True
        try:
            lines = FR.dmesg_new(0)
            at = max((i for i, ln in enumerate(lines) if marker in ln), default=None)
            new = lines[at + 1:] if at is not None else lines
            if at is None:
                rec["note"] += " marker not in dmesg: the whole buffer was read"
            (self.out / f"{name}.dmesg").write_text("\n".join(new) + "\n")
            rec["log_bad"] = [ln for ln in new if FR.BAD_LOG.search(ln) and "resgx545 r1 " not in ln]
            rec["fatal"] = [ln for ln in new if FATAL_RE.search(ln)]
        except Exception as e:
            rec["log_bad"], rec["fatal"] = [f"kernel log not read: {e!r}"], []
        try:
            rec["alive"] = FR.alive()
            rec["health"] = FR.health()
        except Exception as e:
            rec["alive"], rec["health"] = {"advancing": False, "error": repr(e)}, {"ok": False, "error": repr(e)}
        try:
            self.classify(j, rec)
        except Exception as e:
            rec["class"], rec["note"] = "error", rec["note"] + f" classify: {e!r}"
        if err is not None and rec["class"] in ("ok", "kick-timeout"):
            rec["class"] = "error"
        self.records[name] = rec
        self.save(f"{name}.json", rec)
        with self.cases.open("a") as f:
            f.write(f"{name}\t{j['set']}\t{j['op']}\t{rec['class']}\t{rec['rc']}\t{rec['trigger_rc']}\t{rec['note'].strip()}\n")
        self.mark(f"class {name} {rec['class']}")
        print(f"== {name}: class {rec['class']} {rec['note'].strip()[:100]}")
        if err is not None:
            raise err
        return rec

    def run_tool(self, cmd, rec, timeout, stdout_to=None):
        """The tool, to completion (stdout and stderr together); its output kept whole in NAME.tool.txt.gz by the caller."""
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True)
        try:
            o, _ = p.communicate(timeout=timeout)
            rec["tool_rc"] = rec["trigger_rc"] = p.returncode
        except subprocess.TimeoutExpired:
            p.kill()
            o, _ = p.communicate()
            rec["tool_rc"] = rec["trigger_rc"] = "timeout"
        rec["tool_out"] = (o or "")[-4000:]
        rec["overflowed"] = "scene overflowed" in (o or "")   # the probe's line, which a long timeline pushes out of tool_out
        if stdout_to:
            with gzip.open(self.out / f"{stdout_to}.tool.txt.gz", "wb", compresslevel=6) as g:
                g.write((o or "").encode())
        return o or ""

    # ---- ring plumbing --------------------------------------------------------------------
    def ring_clear(self, res):
        res.w(L.RING_BASE[0], [0] * (L.RING_END - L.RING_BASE[0]))
        res.w(L.DROP, [0] * 12)                          # DROP, PASS, OVL
        res.w(L.OVL_LOG, [0] * 16)
        res.w(L.STATE, 0)
        res.w(L.ECHO, 0)

    def ring_open(self, res, window, rec):
        rec["window_stamp"] = FR.regs()[0].get(0x144)    # CR_TIMER just before the window opens (scorers read from it on)
        res.w(L.WINDOW, window)

    def ring_close(self, res, rec, t0):
        res.w(L.WINDOW, 0)
        rec["t_close_ms"] = (time.monotonic() - t0) * 1000
        time.sleep(0.003)
        rec["page"] = res.page()
        time.sleep(0.010)
        rec["page2"] = res.page()                        # window 0 proof: no rung changes after the close
        rec["rc"] = 0

    def kick(self, rec, key="kicks"):
        """One GETMISCINFO through the debugfs.  A failed read (the kernel's 500 ms timeout) is a result: recorded."""
        t = time.monotonic()
        try:
            k = FR.miscinfo()
            rec.setdefault(key, []).append({"ms": k.get("ms")})
            return True
        except OSError as e:
            rec.setdefault("kick_errors", []).append({"ms": (time.monotonic() - t) * 1000, "errno": e.errno})
            return False

    # ---- stage k --------------------------------------------------------------------------
    def k_job(self, j, rec):
        if j["pre"] == "reset":
            r = captured(FR.cmd_reset)
            rec["pre_reset"] = {"ok": r.get("ok")}
            if not r.get("ok"):
                raise Stop(4, "the reset before the arm is not ok")
        arm_marker = f"resgx545 r1 arm {j['name']} {self.run}"
        self.mark(f"arm {j['name']}")
        out = self.arm(j["arm_variant"], tag=f"{j['name']}.arm")
        rec["arm_variant"] = j["arm_variant"]
        rec["arm_calls"] = ARM_CALLS[j["arm_variant"]]
        rec["ident_after_arm"] = self.ident_count(arm_marker)
        rec["ccbctl_after_arm"] = self.ccbctl()
        res = FR.Res()
        try:
            self.ring_clear(res)
            trig = j["trigger"]
            t0 = time.monotonic()
            if trig == "kicks":
                self.kicks_plan(j, rec, res)
            else:
                self.ring_open(res, j["window"], rec)
                if trig == "kick":
                    rec["t_trigger_ms"] = (time.monotonic() - t0) * 1000
                    self.kick(rec)
                elif trig.startswith("tool:"):
                    self.run_tool([self.tool] + self.expand(j["tool_args"]), rec, self.tool_timeout(j), j["name"])
                time.sleep(j["open_ms"] / 1000)
            self.ring_close(res, rec, t0)
        finally:
            res.close()
        rec["ccbctl_after"] = self.ccbctl()
        rec["ident_total"] = self.ident_count(arm_marker)

    def kicks_plan(self, j, rec, res):
        """K5: `warm` kicks in window 0 (nothing logged), then `logged` kicks in window 1 (only the kicks log), then window 2
        for tail_ms (the ticks after the last kick).  A kick that times out ends the plan."""
        for _ in range(j["warm"]):
            if not self.kick(rec, "warm_kicks"):
                break
        rec["ccbctl_after_warm"] = self.ccbctl()
        if rec.get("kick_errors"):
            return
        self.ring_open(res, 1, rec)
        for _ in range(j["logged"]):
            if not self.kick(rec):
                break
        if not rec.get("kick_errors"):
            res.w(L.WINDOW, 2)
            time.sleep(j["tail_ms"] / 1000)

    # ---- stage t --------------------------------------------------------------------------
    def reset_clean(self, rec):
        r = captured(FR.cmd_reset)
        rec["reset_ok"] = bool(r.get("ok"))
        if not r.get("ok"):
            raise Stop(4, "the debugfs reset before the job is not ok")

    def probe_job(self, j, rec):
        self.reset_clean(rec)
        rec["status2_pre"] = self.status2()                # the job's own sample: after its reset, before its tool
        self.run_tool([self.tool] + self.expand(j["tool_args"]), rec, self.tool_timeout(j), j["name"])
        rec["status2_post"] = self.status2()
        r, hc = FR.regs()
        rec["regs_post"] = {hex(k): r.get(k) for k in (0x118, 0x12c, 0xc04, 0xc08)}
        rec["rc"] = 0

    def hold_job(self, j, rec):
        """S3's e1-ta-read recipe: reset, hold_recovery Y (read back), the faulting TA job in the background, the registers
        2.8 s and 1 s later, the reset with the hold still Y, hold_recovery N (read back), the tool collected."""
        self.reset_clean(rec)
        rec["status2_pre"] = self.status2()
        rec.setdefault("knobs_readback", {})["hold_recovery"] = self.knob("hold_recovery", "Y")
        p = subprocess.Popen([self.tool] + self.expand(j["tool_args"]), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, text=True)
        try:
            time.sleep(j["snap1_s"])
            r, hc = FR.regs()
            rec["snap1_status2"], rec["snap1_bif"] = r.get(0x118), [r.get(0xc04), r.get(0xc08)]
            time.sleep(j["snap2_s"])
            r, hc = FR.regs()
            rec["snap2_status2"] = r.get(0x118)
            r2 = captured(FR.cmd_reset)                      # the reset with the hold still Y: it is that recovery
            rec["reset_held_ok"] = bool(r2.get("ok"))
        finally:
            rec["knobs_readback"]["hold_recovery_after"] = self.knob("hold_recovery", "N")
            try:
                o, _ = p.communicate(timeout=self.tool_timeout(j))
                rec["tool_rc"] = rec["trigger_rc"] = p.returncode
            except subprocess.TimeoutExpired:
                p.kill()
                o, _ = p.communicate()
                rec["tool_rc"] = rec["trigger_rc"] = "timeout"
            rec["tool_out"] = (o or "")[-4000:]
            rec["overflowed"] = "scene overflowed" in (o or "")
        r, hc = FR.regs()
        rec["status2_post"] = r.get(0x118)
        rec["rc"] = 0

    # ---- stages d0, d1 ----------------------------------------------------------------------
    def ringtool_job(self, j, rec):
        if self.stage == "d1":                              # one reset and arm before every 4096x4096 job (S1b's isolation)
            r = captured(FR.cmd_reset)
            if not r.get("ok"):
                raise Stop(4, "the debugfs reset before the job is not ok")
            self.arm("std", tag=f"{j['name']}.arm")
        dump = None
        if j.get("dumps"):
            dump = self.out / f"{j['name']}.dump"
            dump.mkdir(exist_ok=True)
        cmd = [self.tool] + self.expand(j["tool_args"], dump)
        if j.get("rt"):
            cmd = [self.rt, "0", "0.3", j["rt"], "--"] + cmd       # the register timeline of D5, read-only, in parallel
        res = FR.Res()
        try:
            self.ring_clear(res)
            t0 = time.monotonic()
            self.ring_open(res, j["window"], rec)
            self.run_tool(cmd, rec, self.tool_timeout(j), j["name"])
            time.sleep(j["open_ms"] / 1000)
            self.ring_close(res, rec, t0)
        finally:
            res.close()
        try:
            with open(f"{FR.D}/buf09", "rb") as f:             # the job's control block (dword 38 = 0x20: a raise)
                b = f.read(236)
            rec["buf09"] = [int.from_bytes(b[i:i + 4], "little") for i in range(0, len(b) - 3, 4)]
        except OSError as e:
            rec["note"] += f" buf09 not read: {e}"
        if dump is not None:
            rec["dump_files"] = sorted(os.listdir(dump))

    def classify(self, j, rec):
        tr = rec.get("trigger_rc")
        page = rec.get("page")
        out = rec.get("tool_out", "")
        if rec["fatal"]:
            rec["class"] = "fatal"
        elif tr == "timeout":
            rec["class"] = "no-answer"
        elif rec.get("restore_failed"):
            rec["class"] = "knob"
        elif j["op"] in ("k", "ringtool") and page is None:
            rec["class"] = "void"
            rec["note"] += " no page read"
        elif not rec["alive"].get("advancing"):
            rec["class"] = "tickstop"
        elif (not self.health_t(rec["health"]) if j["op"] == "probe" else not rec["health"].get("ok")):
            rec["class"] = "unhealthy"
        elif j["op"] != "hold_fault" and rec["log_bad"]:
            rec["class"] = "unhealthy"           # (the held fault logs a fault and a hang by design)
        elif j["op"] == "probe" and tr != 0:
            rec["class"] = "trigfail"
        elif j["op"] == "ringtool" and not (tr == 0 or tr in (1, 3) and (rec.get("overflowed") or "overflowed" in out)):
            rec["class"] = "trigfail"
        elif j["op"] == "k" and j["trigger"].startswith("tool:") and (tr != 0 or "diff: 0 of" not in out):
            rec["class"] = "trigfail"
        elif j["op"] == "k" and rec.get("kick_errors"):
            rec["class"] = "kick-timeout"        # a result (cannot tell for the scorer), not a stop: tick and health fine
        else:
            rec["class"] = "ok"

    @staticmethod
    def health_t(h):
        """Stage t: CR_EVENT_STATUS2 may read 0x440 or 0x480 (the latch is the result); no BIF fault, no counted fault."""
        s2 = h.get("event_status2")
        return (s2 is not None and (s2 & ~0xc0) == 0x400 and (h.get("bif_int_stat", 0) & 0xffff) == 0
                and h.get("faults_status", 0) == 0)

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

    def armed_run(self):
        if self.table["blob"] and self.stage != "k":
            self.arm("std")                  # k arms in every job
        for j in self.table["jobs"]:
            rec = self.job(j)
            c = rec["class"]
            if c in ("ok", "kick-timeout"):
                continue
            if c in ("fatal", "no-answer"):
                raise Stop(3 if c == "fatal" else 6, f"{j['name']}: {c}: nothing else touches the GPU")
            if c == "knob":
                raise Stop(9, f"{j['name']}: a knob was not put back")
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
    ap.add_argument("--rt", default="")
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
                              "classes": {k: v["class"] for k, v in r.records.items()}})
    return code


if __name__ == "__main__":
    sys.exit(main())
