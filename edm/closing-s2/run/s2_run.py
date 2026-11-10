#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""s2_run.py STAGE --tool PATH --out DIR: one S2 stage on the laptop (python3 stdlib, as root: `sudo -n python3`).
PREPARED, NOT RUN.  The Mac side (run/s2.sh) uploads it with tables/, bins/, gen/s2layout.py, the landed
tools/fwtask/fwtask_run.py (as run/fwtask_run.py) and LAPTOP.sha256, and starts one stage per ssh.

What one stage does, in this order, stopping at the first trigger and never going on past it:
  preflight  root; every file it reads is the frozen one (LAPTOP.sha256); the gate file of the previous stage says
             OPEN with the run id of that stage's last run here (its stage.json, exit 0); srcversion installed = loaded; the debugfs files exist; hold_recovery
             N and render_pb_pages 0x422 at the start; the tool exists (sha256 recorded)
  arm        the results page's CMD, WINDOW, N and STATE zeroed BEFORE the arm (a recovery reset zeroes the page,
             a load does not); then the landed cmd_arm (own_code, own_arm, load, boot; ticks, rate, health, magic)
  jobs       one a table row, a kernel-log marker each (`resgx545 s2 case NAME RUN`), its JSON and dmesg slice
             written whatever happens (try/finally), a row in cases.tsv with rc and class
  end        the landed cmd_reset (stock firmware, own_arm off) and gate (fill and triangle exact)

Stop classes (after a stop: the page and the debugfs state are dumped, reset, gate, exit):
  no-answer   the tool gave no result within its time limit              -> exit 6, nothing else touches the GPU
  fatal      watchdog / lockup / BUG / Oops in the kernel log         -> exit 3, nothing else touches the GPU
  notdone    the task's state flag is not the expected one            -> exit 4
  tickstop   HostCtl dword 12 did not advance over three reads        -> exit 4
  unhealthy  EVENT_STATUS2 not 0x400, a BIF fault, a bad log line     -> exit 4
  trigfail   the client job failed (rc not 0, or no diff: 0 line)     -> exit 4
  restorefail  e2w: a restore of sa67/sa68 skipped, or its same-pass read-back not the value read -> exit 4
  error      any other exception in a job (its record is still written) -> exit 4
  Every stop after the arm began (the arm's own failure included) goes through one cleanup: dump, reset, gate.
  stuck     E5 row 3 only (stuck_ends_stage): the tool did not return while held; the page is read first,
             hold_recovery released, the tool waited for (bounded), reset, gate; the stage ends, exit 0
Other exits: 1 preflight, 5 reset or gate after a stop (or at the end) not exact, 7 a table value outside the
allow-list, 9 a knob read back differs.  No loop waits for anything: every delay is one fixed sleep; the
landed fwtask_run.py's alive() reads three times at fixed gaps.
"""
import argparse
import contextlib
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
S2 = pathlib.Path(__file__).resolve().parent.parent          # ~/s2 on the laptop
sys.path.insert(0, str(S2 / "gen"))
sys.path.insert(0, os.environ.get("S2_FWTASK_DIR", str(S2 / "run")))   # tests point it at a fake
import s2layout as L  # noqa: E402
import fwtask_run as FR  # noqa: E402

KNOBS = {"render_pb_pages", "hold_recovery"}
BLOBS = {"ring_e1", "ring_hold", "pa_read", "pa_write"}
WRITER_STAGES = {"e2w"}                    # the only stage that may arm pa_write
GATE_OF = {"e1j": "e1c", "e2w": "e2r", "e4h": "e4c", "e4l": "e4h", "e5c": "e4l", "e5t": "e5c"}
FATAL_RE = re.compile(r"soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|"
                      r"blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check")
KMSG = os.environ.get("S2_KMSG", "/dev/kmsg")
SRCV_PATH = os.environ.get("S2_SRCV_PATH", "/sys/module/gma500_gfx/srcversion")


class Stop(Exception):
    def __init__(self, code, why):
        super().__init__(why)
        self.code = code


def tool_timeout(j):
    """The table's bound on the client tool (S2_TOOL_TIMEOUT_S shortens it in the mock tests only)."""
    return float(os.environ.get("S2_TOOL_TIMEOUT_S", j.get("tool_timeout_s", 30)))


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def captured(fn, a=None):
    """Run a landed fwtask_run command (it prints one JSON object) and return that object."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(a or {})
    lines = [ln for ln in buf.getvalue().splitlines() if ln.startswith("{")]
    return json.loads(lines[-1]) if lines else {"ok": False, "error": "no output"}


class Runner:
    def __init__(self, a):
        self.stage, self.tool = a.stage, a.tool
        self.out = pathlib.Path(a.out) / a.stage
        self.out.mkdir(parents=True, exist_ok=True)
        self.run = f"{int(time.time())}-{os.getpid()}"
        self.t_start = time.time()
        self.table = None
        self.records = {}
        self.cases = self.out / "cases.tsv"
        self.cases.write_text("name\tset\top\tclass\trc\ttrigger_rc\tnote\n")

    # ---- small helpers ------------------------------------------------------------------
    def mark(self, text):
        try:
            # os.open with O_APPEND and no seek: Python's "a" mode seeks, which /dev/kmsg refuses
            # with EINVAL (seen on the laptop); "w" would truncate the mock's plain file
            fd = os.open(KMSG, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(fd, f"resgx545 s2 {text} {self.run}\n".encode())
            finally:
                os.close(fd)
        except OSError as e:
            print(f"  (kmsg marker not written: {e})")

    def save(self, name, obj):
        (self.out / name).write_text(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n")

    def knob(self, name, value):
        if name not in KNOBS:
            raise Stop(7, f"knob {name} is not on the S2 allow-list")
        FR.wr(name, value)
        rb = FR.rd(name).strip()
        same = (rb == value) if name == "hold_recovery" else (int(rb, 0) == int(value, 0))
        self.mark(f"readback {self.stage} {name}={rb}")
        if not same:
            raise Stop(9, f"{name}: wrote {value}, read back {rb}")
        return rb

    # ---- preflight ----------------------------------------------------------------------
    def preflight(self):
        env = {"stage": self.stage, "run": self.run, "euid": os.geteuid()}
        if os.geteuid() != 0 and os.environ.get("S2_MOCK_ROOT") != "1":
            raise Stop(1, "not root: run as `sudo -n python3 s2_run.py` (every debugfs access needs root)")
        frozen = {}
        for ln in (S2 / "LAPTOP.sha256").read_text().splitlines():
            h, f = ln.split(None, 1)
            frozen[f.strip()] = h
        need = [f"tables/{self.stage}.json", "gen/s2layout.py", "run/s2_run.py", "run/fwtask_run.py"]
        for f in need:
            if frozen.get(f) != sha(S2 / f):
                raise Stop(1, f"{f} is not the frozen file")
        self.table = json.loads((S2 / "tables" / f"{self.stage}.json").read_text())
        blob = self.table["blob"]
        if blob not in BLOBS or frozen.get(f"bins/{blob}.blob") != sha(S2 / "bins" / f"{blob}.blob"):
            raise Stop(1, f"blob {blob} is unknown or not the frozen one")
        if blob == "pa_write" and self.stage not in WRITER_STAGES:
            raise Stop(7, "pa_write armed outside e2w")
        prev = GATE_OF.get(self.stage)
        if prev:
            # the gate must be OPEN and name the run id of the last run of the previous stage here (its stage.json,
            # exit 0): a gate scored on another run of that stage never opens this one
            g = S2 / "gates" / f"{prev}.gate"
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
        for j in self.table["jobs"]:
            self.check_job(j)
        if not os.path.isdir(FR.D):            # the landed runner assumes dri/0; take the one that exists
            import glob
            found = sorted(glob.glob("/sys/kernel/debug/dri/*/sgx"))
            if not found:
                raise Stop(1, "no sgx debugfs directory (debug option off?)")
            FR.D = found[0]
        with open(SRCV_PATH) as f:
            env["srcversion_loaded"] = f.read().strip()
        env["srcversion_installed"] = FR.sh("modinfo -F srcversion gma500_gfx", check=False).strip()
        if not env["srcversion_loaded"] or env["srcversion_loaded"] != env["srcversion_installed"]:
            raise Stop(1, "the loaded module is not the installed one")
        for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo",
                  "hold_recovery", "render_pb_pages"):
            if not os.path.exists(f"{FR.D}/{f}"):
                raise Stop(1, f"the driver has no debugfs {f}")
        env["hold_recovery"] = FR.rd("hold_recovery").strip()
        env["render_pb_pages"] = FR.rd("render_pb_pages").strip()
        if env["hold_recovery"] != "N" or int(env["render_pb_pages"], 0) != 0x422:
            raise Stop(1, f"knobs not at their defaults at the start: {env}")
        if not os.access(self.tool, os.X_OK):
            raise Stop(1, f"no tool {self.tool}")
        gate_tool = getattr(FR, "GATE_TOOL", "/home/jtorra/sgxfive-test")    # the landed cmd_gate's tool
        if not os.access(gate_tool, os.X_OK):
            raise Stop(1, f"no gate tool {gate_tool} (the landed fwtask_run.cmd_gate runs it): sgxfive-test missing")
        env["gate_tool_sha256"] = sha(gate_tool)
        env["python"] = sys.version.split()[0]
        if sys.version_info < (3, 8):
            raise Stop(1, f"python {env['python']} is older than 3.8")
        env["tool_sha256"] = sha(self.tool)
        env["uname"] = FR.sh("uname -r", check=False).strip()
        env["firmware_sha256"] = FR.sh("sha256sum /lib/firmware/sgx545_ukernel.fw", check=False).split(" ")[0]
        env["blob_sha256"] = frozen[f"bins/{blob}.blob"]
        env["table_sha256"] = frozen[f"tables/{self.stage}.json"]
        env["debugfs"] = FR.D
        self.save("env.json", env)
        print(f"## preflight ok: {json.dumps({k: env[k] for k in ('srcversion_loaded', 'uname', 'tool_sha256')})}")

    def check_job(self, j):
        op = j.get("op")
        if op == "ring":
            if j.get("window") not in (0, 1, 2) or not 0 <= int(j.get("n", 0)) <= L.N_MAX:
                raise Stop(7, f"{j['name']}: window or n outside the allow-list")
            if j.get("n") and self.table["blob"] != "ring_hold":
                raise Stop(7, f"{j['name']}: a hold needs ring_hold")
        elif op == "pa":
            if j.get("cmd") not in (1, 2, 3) or (j["cmd"] != 1 and self.table["blob"] != "pa_write"):
                raise Stop(7, f"{j['name']}: command {j.get('cmd')} not allowed with {self.table['blob']}")
        else:
            raise Stop(7, f"{j['name']}: unknown op {op}")
        trig = j.get("trigger", "none")
        if trig not in ("none", "kick") and not trig.startswith("tool:"):
            raise Stop(7, f"{j['name']}: unknown trigger {trig}")
        for k in j.get("knobs", {}):
            if k not in KNOBS:
                raise Stop(7, f"{j['name']}: knob {k} not allowed")

    # ---- arm / end ----------------------------------------------------------------------
    def zero_protocol(self):
        res = FR.Res()
        res.w(L.CMD, [0, 0])                 # CMD, STATE
        res.w(L.WINDOW, 0)
        res.w(L.N_ITER, 0)
        res.close()

    def arm(self):
        self.zero_protocol()
        out = captured(FR.cmd_arm, {"blob": str(S2 / "bins" / f"{self.table['blob']}.blob"), "arm": self.table["arm"]})
        self.save("arm.json", out)
        print(f"## arm {self.table['blob']} '{self.table['arm']}': ok {out.get('ok')} rate {out.get('rate_hz')}")
        if not out.get("ok"):
            raise Stop(4, f"arm not ok: {json.dumps({k: out.get(k) for k in ('alive', 'health', 'log_bad', 'magic')})}")
        res = FR.Res()
        cmd, state = res.r(L.CMD, 2)
        win = res.r(L.WINDOW)[0]
        res.close()
        if cmd or win:
            raise Stop(4, f"after the arm CMD {cmd} WINDOW {win}, not 0")

    def end(self, tag):
        r = captured(FR.cmd_reset)
        g = captured(FR.cmd_gate)
        self.save(f"{tag}-reset.json", {"reset": r, "gate": g})
        print(f"## {tag}: reset ok {r.get('ok')}, gate ok {g.get('ok')}")
        return bool(r.get("ok") and g.get("ok"))

    # ---- one job ------------------------------------------------------------------------
    def resolve_mark(self, m):
        if isinstance(m, int):
            return m
        _, job, area, field = m.split(":")            # from:JOB:A:FIELD
        rec = self.records.get(job)
        if not rec or not rec.get("page"):
            return None
        base = {"A": L.AREA_A, "B": L.AREA_B}[area]
        v = rec["page"][base + L.AREA_FIELDS.index(field)]
        return None if v == L.INITFILL else v

    def job(self, j):
        name = j["name"]
        rec = {"name": name, "set": j["set"], "op": j["op"], "job": j, "class": "void", "rc": None,
               "trigger_rc": None, "note": "", "run": self.run}
        marker = f"resgx545 s2 case {name} {self.run}"
        self.mark(f"case {name}")
        proc = None
        err = None
        try:
            for k, v in j.get("knobs", {}).items():
                rec.setdefault("knobs_readback", {})[k] = self.knob(k, v)
            if j["op"] == "ring":
                proc = self.ring_job(j, rec)
            else:
                self.pa_job(j, rec)
        except BaseException as e:          # recorded, then raised again after the record is written
            err = e
            rec["note"] += f" error: {e!r}"
        # every step below is guarded: the record and the cases.tsv row are written whatever fails
        # 1. the knobs back before anything else touches the GPU (hold_recovery after the page was read)
        for k in j.get("knobs", {}):
            try:
                rec.setdefault("knobs_restored", {})[k] = self.knob(k, {"render_pb_pages": "0x422",
                                                                         "hold_recovery": "N"}[k])
            except Exception as e:
                rec["note"] += f" knob restore: {e}"
                rec["restore_failed"] = True
        if proc is not None:
            try:
                o, _ = proc.communicate(timeout=tool_timeout(j))
                rec["tool_out"], rec["trigger_rc"] = o[-4000:], proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                o, _ = proc.communicate()
                rec["tool_out"], rec["trigger_rc"] = (o or "")[-4000:], "timeout"
            except Exception as e:
                rec["note"] += f" tool wait: {e!r}"
        # 2. the job's kernel-log slice: the lines after its own marker (a count of lines goes blind once the
        #    ring buffer is full); the whole buffer when the marker is no longer in it
        try:
            lines = FR.dmesg_new(0)
            at = max((i for i, ln in enumerate(lines) if marker in ln), default=None)
            new = lines[at + 1:] if at is not None else lines
            if at is None:
                rec["note"] += " marker not in dmesg: the whole buffer was read"
            (self.out / f"{name}.dmesg").write_text("\n".join(new) + "\n")
            rec["log_bad"] = [ln for ln in new if FR.BAD_LOG.search(ln) and "resgx545 s2 " not in ln]
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
        if err is not None and rec["class"] in ("ok", "kick-timeout", "skipped"):
            rec["class"] = "error"
        self.records[name] = rec
        self.save(f"{name}.json", rec)
        with self.cases.open("a") as f:
            f.write(f"{name}\t{j['set']}\t{j['op']}\t{rec['class']}\t{rec['rc']}\t{rec['trigger_rc']}\t"
                    f"{rec['note'].strip()}\n")
        self.mark(f"class {name} {rec['class']}")
        print(f"== {name}: class {rec['class']} {rec['note'].strip()[:100]}")
        if err is not None:
            raise err
        return rec

    def trigger(self, j, rec, background):
        trig = j.get("trigger", "none")
        rec["t_trigger_ms"] = (time.monotonic() - rec["_t0"]) * 1000
        if trig == "kick":
            t = time.monotonic()
            try:
                rec["kick"] = FR.miscinfo()
            except OSError as e:
                # the kernel's read returns -ETIMEDOUT after 500 ms and the seq_file text is lost (sgxfive_debug.c):
                # Python raises TimeoutError; the outcome is a result (E5: LOST), recorded with its errno
                rec["kick"] = {"ms": (time.monotonic() - t) * 1000, "errno": e.errno,
                               "text": f"no MISCINFO_READY (the read failed: {e})"}
        elif trig.startswith("tool:"):
            cmd = [self.tool] + list(j["tool_args"])
            rec["tool_cmd"] = cmd
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                 text=True)
            if background:
                return p
            try:
                o, _ = p.communicate(timeout=tool_timeout(j))
                rec["tool_out"], rec["trigger_rc"] = o[-4000:], p.returncode
            except subprocess.TimeoutExpired:
                p.kill()
                o, _ = p.communicate()
                rec["tool_out"], rec["trigger_rc"] = (o or "")[-4000:], "timeout"
        rec["t_trigger_end_ms"] = (time.monotonic() - rec["_t0"]) * 1000
        return None

    def ring_job(self, j, rec):
        res = FR.Res()
        try:
            res.w(L.RING_BASE[0], [0] * (L.RING_END - L.RING_BASE[0]))
            res.w(L.DROP, [0] * 12)                          # DROP, PASS, OVL
            res.w(L.OVL_LOG, [0] * 16)
            res.w(L.HOLD_ENTRY, [L.INITFILL, L.INITFILL])
            res.w(L.STATE, 0)
            res.w(L.ECHO, 0)
            n = int(j.get("n", 0))
            if n:
                res.w(L.N_ITER, n)
                res.w(L.RUNID, j["runid"])
            rec["tick_before"] = FR.regs()[1].get(12)
            rec["_t0"] = time.monotonic()
            res.w(L.WINDOW, j["window"])
            if n:
                res.w(L.CMD, 1)                              # back to back with the window (E4)
            if n and j.get("trigger", "none") != "none":
                # the hold starts at the next event after the command (up to a tick): one fixed wait, then one read
                # of the state; a trigger that could beat the hold makes the job void, not a wrong reading
                time.sleep(j.get("trigger_after_ms", 3) / 1000)
                rec["state_at_trigger"] = res.r(L.STATE)[0]
            hold_tool = n and j.get("trigger", "").startswith("tool:")
            proc = self.trigger(j, rec, background=bool(hold_tool))
            # the window stays open open_ms after the trigger returned (E1), or open_ms from the command (a hold)
            left = j["open_ms"] / 1000 - ((time.monotonic() - rec["_t0"]) if n else 0)
            if left > 0:
                time.sleep(left)
            res.w(L.WINDOW, 0)
            rec["t_close_ms"] = (time.monotonic() - rec["_t0"]) * 1000
            time.sleep(0.003)
            rec["page"] = res.page()
            time.sleep(0.010)
            rec["page2"] = res.page()                        # window 0 proof: no rung changes after the close
            rec["tick_after"] = FR.regs()[1].get(12)
            rec["t_read_ms"] = (time.monotonic() - rec["_t0"]) * 1000
            rec["rc"] = 0
            return proc
        finally:
            res.close()
            rec.pop("_t0", None)

    def pa_job(self, j, rec):
        res = FR.Res()
        try:
            res.w(L.AREA_A, [L.INITFILL] * 12)
            res.w(L.AREA_B, [L.INITFILL] * 12)
            res.w(L.AREA_C, [L.INITFILL] * 4)
            res.w(L.STATE, 0)
            res.w(L.ECHO, 0)
            if j["cmd"] in (2, 3):
                m = self.resolve_mark(j["mark"])
                if m is None:
                    rec["class"], rec["note"] = "skipped", f"mark {j['mark']} not available"
                    return
                rec["mark_value"] = m
                res.w(L.MARK, m)
                res.w(L.PFLAGS, [1 if x else 0 for x in j["pflags"]])
            res.w(L.RUNID, j["runid"])
            rec["_t0"] = time.monotonic()
            res.w(L.CMD, j["cmd"])
            time.sleep(j.get("wait_ms", 30) / 1000)
            rec["page"] = res.page()
            rec["t_read_ms"] = (time.monotonic() - rec["_t0"]) * 1000
            rec["rc"] = 0
        finally:
            res.close()
            rec.pop("_t0", None)

    def classify(self, j, rec):
        if rec["class"] == "skipped":
            if j.get("set") == "restore":           # sa67/sa68 may still hold our marker: a stop, not a skip
                rec["class"] = "restorefail"
            return
        page = rec.get("page")
        trig = j.get("trigger", "none")
        tr = rec.get("trigger_rc")
        if rec["fatal"]:
            rec["class"] = "fatal"
        elif tr == "timeout":
            rec["class"] = "stuck" if j.get("stuck_ends_stage") else "no-answer"
        elif j.get("stuck_ends_stage") and tr not in (None, 0):
            rec["class"] = "stuck"             # E5 row 3: the held job did not complete (LOST): a result, ends the stage
        elif rec.get("restore_failed"):
            rec["class"] = "knob"
        elif page is None:
            rec["class"] = "void"
            rec["note"] += " no page read"
        elif j["op"] == "pa" and page[L.STATE] != L.STATE_NEXT:
            rec["class"] = "notdone"
            rec["note"] += f" state {page[L.STATE]:#x}, want 3"
        elif j.get("set") == "restore" and page[L.AREA_C + 2 * (j["cmd"] - 2) + 1] != rec.get("mark_value"):
            rec["class"] = "restorefail"
            rec["note"] += (f" sa{65 + j['cmd']} read {page[L.AREA_C + 2 * (j['cmd'] - 2) + 1]:#x} after the restore "
                            f"of {rec.get('mark_value', 0):#x}")
        elif j["op"] == "ring" and j.get("n") and page[L.STATE] != L.STATE_DONE:
            rec["class"] = "notdone"
            rec["note"] += f" state {page[L.STATE]:#x} after {rec.get('t_read_ms', 0):.0f} ms, want 2"
        elif not rec["alive"].get("advancing"):
            rec["class"] = "tickstop"
        elif not rec["health"].get("ok") or rec["log_bad"]:
            rec["class"] = "unhealthy"
        elif trig.startswith("tool:") and (tr != 0 or not re.search(r"^diff: 0 of", rec.get("tool_out", ""), re.M)
                                            and "overflowed" not in rec.get("tool_out", "")):
            rec["class"] = "trigfail"
        elif trig == "kick" and "no MISCINFO_READY" in rec.get("kick", {}).get("text", ""):
            rec["class"] = "kick-timeout"      # a result (E5: LOST), not a stop: the tick and health were fine
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
        except Exception as e:               # anything unexpected after the arm: the same cleanup, exit 4 or 5
            raise self.cleanup(4, f"unexpected {e!r}")

    def cleanup(self, code, why):
        """After any stop once the arm began: dump, reset, gate.  Returns the Stop to raise (5 if not exact)."""
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
        self.arm()
        for j in self.table["jobs"]:
            rec = self.job(j)
            c = rec["class"]
            if c in ("ok", "kick-timeout") or (c == "skipped" and j.get("set") != "restore"):
                continue
            if c in ("fatal", "no-answer"):
                raise Stop(3 if c == "fatal" else 6, f"{j['name']}: {c}: nothing else touches the GPU")
            if c == "knob":
                raise Stop(9, f"{j['name']}: a knob was not put back")
            if c == "stuck":
                FR.hang_dump(str(self.out), f"stuck-{j['name']}")
                ok = self.end("stuck")
                if not ok:
                    s = Stop(5, "reset or gate not exact after the stuck job")
                    s.ended = True
                    raise s
                print(f"## {j['name']}: stuck while held: read, released, reset; the row is not repeated, stage ends")
                return 0
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
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = Runner(a)
    code, why = 1, "the stage did not finish"     # never 0 unless stage_run returned it
    try:
        code, why = r.stage_run(), ""
    except Stop as e:
        code, why = e.code, str(e)
        print(f"## STOP {code}: {why}")
    except Exception as e:                        # before the arm (stage_run handles everything after it)
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
