#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""c3_run.py c3 --tool PATH --bins DIR --out DIR: C3's one stage on the laptop (python3 stdlib, as root: `sudo -n python3`).
PREPARED, NOT RUN.  The Mac side (run/c3.sh) uploads it with tables/, bins/, gen/c3layout.py, the landed
tools/fwtask/fwtask_run.py (as run/fwtask_run.py), TOOL.sha256 and LAPTOP.sha256.

Stage c3 (L3b, Q158 + Q124's residual), start.s (own_arm slots=0x1 entry=0), 13 jobs in the table's order.  A job: the host's reader
(rd0: the state as the last job left it), the writer (sa63, r20, r21, i0, i1 = the table's markers, p0..p3 = its flags; it arms the
reader of the next event: rdA), the row's perturbation, the host's reader again (rdB).  Perturbations: none (S0, no writer), gap
(N: 1200 ms), fill (F: one client fill through the gate tool), reload (L: the landed cmd_arm again with NO reset: own_arm 0,
own_code, own_arm, load, boot), reset (R: the landed cmd_reset, then cmd_arm).  Offline check of the kernel (fork, branch resgx545,
sgxfive.c / sgxfive_debug.c): own_code, own_arm, load and boot are debugfs writes, not a module reload; `load` unloads (a power-off
request and a halt) and loads, `boot` runs the boot sequence; `reset` halts, rebuilds the stock buffers, clears own_arm and boots.

Safety (checked by run/guard_c3.sh and guard_blobs.py): no kernel change; the only writes are debugfs own_code, own_arm, own_res,
load, boot and reset (an allow-list), /dev/kmsg (os.open, O_WRONLY | O_APPEND) and the results page; no register write of any
kind (no kreg, kpoke, clock register, trc_hazard); no firmware-task `str`; the task's only sa write is sa63 in the writer; no knob
is written.  Reads of debugfs: regs, status, miscinfo.  The only other command run is the gate tool's fill (as the landed gate).

Stops.  The STOP BUDGET is 0: a TICK STOP (HostCtl dword 12 not advancing over three reads) ends the stage.  The signature registers
are read twice BEFORE anything else, the dumps are saved, the kernel's own debugfs reset and the gate are run, and the stage exits
8 (reset and gate exact).  A freeze (the tool gave no answer, exit 6) or a watchdog (fatal, exit 3) stops all laptop work.  Other
exits: 1 preflight, 4 a job failed or an exception, 5 reset or gate not exact, 7 a table value outside the allow-list.  No loop
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
R3 = pathlib.Path(__file__).resolve().parent.parent          # ~/r3xc3 on the laptop
sys.path.insert(0, str(R3 / "gen"))
sys.path.insert(0, os.environ.get("R3_FWTASK_DIR", str(R3 / "run")))   # tests point it at a fake
import c3layout as L  # noqa: E402
import fwtask_run as FR  # noqa: E402

BLOB_OF = {"c3": "start"}
FATAL_RE = re.compile(r"soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|"
                      r"blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check")
KMSG = os.environ.get("R3_KMSG", "/dev/kmsg")
SRCV_PATH = os.environ.get("R3_SRCV_PATH", "/sys/module/gma500_gfx/srcversion")
EXIT_SECOND_STOP = 8


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


def parse_ccbctl(text):
    """[ctl0, ctl1] from the regs file's `ccbctl 0x00 0x........` and `ccbctl 0x04 0x........` lines (None: not there)."""
    v = {}
    for ln in text.splitlines():
        m = re.match(r"ccbctl 0x(00|04) (0x[0-9a-f]+)$", ln)
        if m:
            v[int(m.group(1), 16) // 4] = int(m.group(2), 16)
    return [v.get(0), v.get(1)] if v else None


def read_text(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError as e:
        return f"unreadable: {e}"


class Runner:
    def __init__(self, a):
        self.stage, self.tool, self.bins = a.stage, a.tool, a.bins
        self.out = pathlib.Path(a.out) / a.stage
        self.out.mkdir(parents=True, exist_ok=True)
        self.run = f"{int(time.time())}-{os.getpid()}"
        self.t_start = time.time()
        self.table = None
        self.records = {}
        self.armed = False
        self.stops = 0
        self.t0_mono = time.monotonic()
        self.cases = self.out / "cases.tsv"
        self.cases.write_text("name\tset\trow\tclass\trc\tnote\n")

    # ---- small helpers ------------------------------------------------------------------
    def mark(self, text):
        try:
            # os.open with O_APPEND and no seek: Python's "a" mode seeks, which /dev/kmsg refuses with EINVAL (seen on the laptop)
            fd = os.open(KMSG, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(fd, f"resgx545 r3 {text} {self.run}\n".encode())
            finally:
                os.close(fd)
        except OSError as e:
            print(f"  (kmsg marker not written: {e})")

    def save(self, name, obj):
        (self.out / name).write_text(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n")

    def ccbctl(self):
        return parse_ccbctl(FR.rd("regs"))

    # ---- preflight ----------------------------------------------------------------------
    def preflight(self):
        env = {"stage": self.stage, "run": self.run, "euid": os.geteuid()}
        if os.geteuid() != 0 and os.environ.get("R3_MOCK_ROOT") != "1":
            raise Stop(1, "not root: run as `sudo -n python3 c3_run.py` (every debugfs access needs root)")
        if self.stage not in BLOB_OF:
            raise Stop(1, f"unknown stage {self.stage}")
        frozen = {}
        for ln in (R3 / "LAPTOP.sha256").read_text().splitlines():
            h, f = ln.split(None, 1)
            frozen[f.strip()] = h
        self.table = json.loads((R3 / "tables" / f"{self.stage}.json").read_text())
        blob = BLOB_OF[self.stage]
        if self.table["blob"] != blob:
            raise Stop(1, f"the table's blob {self.table['blob']} is not {blob}")
        need = [f"tables/{self.stage}.json", "gen/c3layout.py", "run/c3_run.py", "run/fwtask_run.py", "TOOL.sha256",
                "bins/blobs.json", f"bins/{blob}.blob"]
        for f in sorted(set(need)):
            if frozen.get(f) != sha(R3 / f):
                raise Stop(1, f"{f} is not the frozen file")
        binfo = json.loads((R3 / "bins" / "blobs.json").read_text())[blob]
        if binfo["str"] != 0:
            raise Stop(1, f"{blob} has a str")
        if {int(k): v for k, v in binfo["cmd_sa"].items()} != L.CMD_SA or not set(binfo["sa_writes"]) <= L.SA_ALLOWED:
            raise Stop(1, "start.s: its sa write set is not the allowed one")
        self.check_table()
        d, cands = pick_debugfs() if "R3_DEBUGFS" not in os.environ else (os.environ["R3_DEBUGFS"], [os.environ["R3_DEBUGFS"]])
        if d is None:
            raise Stop(1, f"no sgx debugfs directory with own_res among {cands} (debug option off?)")
        FR.D = d
        env["debugfs"], env["debugfs_candidates"] = d, cands
        with open(SRCV_PATH) as f:
            env["srcversion_loaded"] = f.read().strip()
        env["srcversion_installed"] = FR.sh("modinfo -F srcversion gma500_gfx", check=False).strip()
        if not env["srcversion_loaded"] or env["srcversion_loaded"] != env["srcversion_installed"]:
            raise Stop(1, "the loaded module is not the installed one")
        for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo"):
            if not os.path.exists(f"{FR.D}/{f}"):
                raise Stop(1, f"the driver has no debugfs {f}")
        if not os.access(self.tool, os.X_OK):
            raise Stop(1, f"no tool {self.tool}")
        env["tool_sha256"] = sha(self.tool)
        if env["tool_sha256"] != (R3 / "TOOL.sha256").read_text().split()[0]:
            raise Stop(1, f"the tool is not the pinned one ({env['tool_sha256'][:12]}, pinned in TOOL.sha256)")
        gate_tool = getattr(FR, "GATE_TOOL", "/home/jtorra/sgxfive-test")    # the landed cmd_gate's tool (also the F row's fill)
        if not os.access(gate_tool, os.X_OK):
            raise Stop(1, f"no gate tool {gate_tool} (the landed fwtask_run.cmd_gate and the F row's fill run it): sgxfive-test missing")
        env["gate_tool_sha256"] = sha(gate_tool)
        if sys.version_info < (3, 8):
            raise Stop(1, f"python {sys.version.split()[0]} is older than 3.8")
        env["python"] = sys.version.split()[0]
        env["uname"] = FR.sh("uname -r", check=False).strip()
        env["firmware_sha256"] = FR.sh("sha256sum /lib/firmware/sgx545_ukernel.fw", check=False).split(" ")[0]
        env["blob_sha256"] = frozen.get(f"bins/{blob}.blob")
        env["table_sha256"] = frozen[f"tables/{self.stage}.json"]
        # context for reading S0 (a boot since the last session? sa100/sa127 are only read): read-only
        env["uptime"] = read_text(os.environ.get("R3_UPTIME", "/proc/uptime"))
        env["boot_id"] = read_text(os.environ.get("R3_BOOT_ID", "/proc/sys/kernel/random/boot_id"))
        self.save("env.json", env)
        self.mark(f"preflight {self.stage}")
        print(f"## preflight ok: {json.dumps({k: env[k] for k in ('srcversion_loaded', 'uname', 'tool_sha256', 'debugfs', 'uptime')})}")

    def check_table(self):
        t = self.table
        if int(t.get("stop_budget", 1)) != 0:
            raise Stop(7, "stop budget is not 0")
        if t.get("gap_ms") != L.GAP_MS:
            raise Stop(7, "gap_ms is not the allowed one")
        for j in t["jobs"]:
            self.check_job(j)

    def check_job(self, j):
        n = j.get("name", "?")
        row = j.get("row")
        if row not in L.ROWS:
            raise Stop(7, f"{n}: row {row} is not one of this stage's approved rows {L.ROWS}")
        if j.get("op") != "start" or j.get("perturb") != L.PERTURB[row]:
            raise Stop(7, f"{n}: op {j.get('op')} / perturbation {j.get('perturb')} is not row {row}'s")
        ints = [j["sa63"]] + list(j["ri"])
        if not all(isinstance(x, int) and 0 <= x < 1 << 32 for x in ints) or len(j["ri"]) != 4:
            raise Stop(7, f"{n}: a marker is not a 32-bit integer")
        if len(j["flags"]) != 4 or not all(f in (0, 1) for f in j["flags"]):
            raise Stop(7, f"{n}: the flags are not four 0/1 values")
        if bool(j["write"]) != (row != "S0"):
            raise Stop(7, f"{n}: only S0 has no writer")

    # ---- arm / end ----------------------------------------------------------------------
    def zero_protocol(self, res):
        res.w(L.CMD, [0, 0])                 # CMD, STATE
        res.w(L.ECHO, 0)
        res.w(L.WINDOW, 0)

    def arm(self, tag="arm"):
        """Arm the stage's task through the landed cmd_arm (own_arm 0, own_code, own_arm, load, boot)."""
        res = FR.Res()
        try:
            self.zero_protocol(res)
        finally:
            res.close()
        a = {"blob": str(R3 / "bins" / f"{self.table['blob']}.blob"), "arm": self.table["arm"]}
        out = captured(FR.cmd_arm, a)
        self.save(f"{tag}.json", out)
        print(f"## {tag}: ok {out.get('ok')} rate {out.get('rate_hz')}")
        if not out.get("ok"):
            raise Stop(4, f"arm not ok: {json.dumps({k: out.get(k) for k in ('alive', 'health', 'log_bad', 'magic')})}")
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
        r = captured(FR.cmd_reset)
        g = captured(FR.cmd_gate)
        self.save(f"{tag}-reset.json", {"reset": r, "gate": g})
        print(f"## {tag}: reset ok {r.get('ok')}, gate ok {g.get('ok')}")
        self.armed = False
        return bool(r.get("ok") and g.get("ok"))

    # ---- tick helpers ---------------------------------------------------------------------
    def tick_check(self):
        """(ok, alive, rate): HostCtl dword 12 advancing over three reads 20 ms apart, and a rate within 900 to 1100 Hz."""
        a = FR.alive()
        if not a["advancing"]:
            return False, a, None
        rate = FR.tick_rate(100)
        return bool(900 <= rate <= 1100), a, rate

    def signature(self, rec, phase):
        """The registers of E537's stop signature, twice, 30 ms apart, BEFORE any reset; and the landed dumps."""
        samples = []
        for i in range(2):
            try:
                r, hc = FR.regs()
                samples.append({"t": round(time.monotonic() - self.t0_mono, 4),
                                "regs": {hex(k): r.get(k) for k in L.SIG_REGS}, "hc12": hc.get(12)})
            except Exception as e:      # a dead debugfs file is itself a result
                samples.append({"error": repr(e)})
            if i == 0:
                time.sleep(0.03)
        rec["sig"] = {"phase": phase, "samples": samples}
        rec["stopped"] = True
        try:
            FR.hang_dump(str(self.out), f"stop-{rec['name']}")
        except Exception as e:
            print(f"(dump failed: {e!r})")
        print(f"## STOP SIGNATURE {rec['name']} ({phase}): {json.dumps(samples)[:300]}")

    def check_tick(self, rec, phase):
        """The tick after a phase: a stop is signed at once (before anything else runs)."""
        ok, a, rate = self.tick_check()
        rec.setdefault("ticks", []).append({"phase": phase, "ok": ok, "alive": a, "rate_hz": rate})
        if not a["advancing"] and not rec.get("stopped"):
            self.signature(rec, phase)
        return a["advancing"]

    # ---- one job ------------------------------------------------------------------------
    def job(self, j):
        name = j["name"]
        rec = {"name": name, "set": j["set"], "op": j["op"], "row": j["row"], "job": j, "class": "void", "rc": None, "note": "",
               "run": self.run}
        marker = f"resgx545 r3 case {name} {self.run}"
        self.mark(f"case {name}")
        self.t0_mono = time.monotonic()
        err = None
        try:
            self.start_job(j, rec)
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
            rec["log_bad"] = [ln for ln in new if FR.BAD_LOG.search(ln) and "resgx545 r3 " not in ln]
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
        if err is not None and rec["class"] in ("ok", "noreader"):
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

    # ---- the commands of start.s ----------------------------------------------------------
    def command(self, res, cmd, runid, j=None, ms=120):
        """Issue one start.s command and wait for its flag.  The writer arms the reader (cmd 9): its flag is WR_DONE holding the run
        id; a reader's flag is cmd 0 with the run id echoed and its record's pass count written.  Returns {"done", "ms", "t_ms"}."""
        res.w(L.STATE, 0)
        res.w(L.ECHO, 0)
        res.w(L.WR, [0] * 16)                # the writer's record and its flag (WR_DONE) start empty
        res.w(L.RD, [0] * L.RD_N)
        res.w(L.RUNID, runid)
        if j is not None:
            res.w(L.A_M, j["sa63"])
            res.w(L.A_RI, list(j["ri"]))
            res.w(L.PF, list(j["flags"]))
        t = time.monotonic()
        res.w(L.CMD, cmd)
        if cmd == L.CMD_READ:
            w = self.wait_reader(res, runid, ms)
        else:
            w = self.wait_flag(res, runid, ms)
        return {"done": w is not None, "ms": w, "t_ms": (time.monotonic() - t) * 1000}

    def wait_reader(self, res, runid, ms):
        """Bounded wait: the reader ran: CMD back to 0 with the run id echoed AND its record's pass count (never 0 after a pass)."""
        t = time.monotonic()
        for _ in range(int(ms / 2) + 1):
            c = res.r(L.CMD)[0]
            if c == 0 and res.r(L.ECHO)[0] == runid and res.r(L.RD + L.RD_PASS)[0] != 0:
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

    def host_read(self, res, runid):
        """The host's reader (cmd 9) at the next event: {"ran", "ms", "rd"}."""
        r = self.command(res, L.CMD_READ, runid)
        return {"ran": r["done"], "ms": r["ms"], "rd": res.r(L.RD, L.RD_N) if r["done"] else None}

    def fill(self):
        """One client fill through the gate tool (as the landed gate and E536 ran it): {"text", "ok"}."""
        tool = getattr(FR, "GATE_TOOL", "/home/jtorra/sgxfive-test")
        text = FR.sh(f"{tool} fill 2>&1 | grep -E '^diff|FAIL' | head -2", check=False).strip()
        return {"text": text, "ok": "diff: 0 of 2048" in text and "FAIL" not in text}

    def start_job(self, j, rec):
        res = FR.Res()
        try:
            rec["ccbctl_pre"] = self.ccbctl()
            self.zero_protocol(res)
            rid = j["runid"]
            rec["rd0"] = self.host_read(res, rid)
            if not j["write"]:
                self.check_tick(rec, "after-reader")
                rec["writer"] = {"issued": False, "done": False}
                rec["rc"] = 0
                return
            wr = {"issued": True}
            wr.update(self.command(res, L.CMD_W, rid, j))
            wr["wr"] = res.r(L.WR, 16) if wr["done"] else None
            rec["writer"] = wr
            ran = self.wait_reader(res, rid, 120) is not None if wr["done"] else False
            rec["rdA"] = {"ran": ran, "rd": res.r(L.RD, L.RD_N) if ran else None}
            if not self.check_tick(rec, "after-reader"):
                return
            p = {"kind": j["perturb"]}
            rec["perturb"] = p
            if j["perturb"] == "gap":
                time.sleep(self.table["gap_ms"] / 1000)
            elif j["perturb"] == "fill":
                p.update(self.fill())
                if not p["ok"]:
                    raise Stop(4, f"{j['name']}: the client fill is not exact ({p['text']})")
            elif j["perturb"] in ("reload", "reset"):
                res.close()
                res = None
                if j["perturb"] == "reset":
                    self.mark(f"reset {j['name']}")
                    r = captured(FR.cmd_reset)
                    p["reset"] = {k: r.get(k) for k in ("ok", "alive", "own_arm", "health")}
                    if not r.get("ok"):
                        raise Stop(4, f"{j['name']}: the reset before the arm is not ok")
                self.mark(f"arm {j['name']} {j['perturb']}")
                a = self.arm(tag=f"{j['name']}.{j['perturb']}")
                p["arm"] = {k: a.get(k) for k in ("ok", "rate_hz", "magic", "own_arm")}
                res = FR.Res()
            if not self.check_tick(rec, f"after-{j['perturb']}"):
                return
            rec["rdB"] = self.host_read(res, rid)
            if not self.check_tick(rec, "after-rdB"):
                return
            rec["rc"] = 0
        finally:
            if res is not None:
                res.close()

    # ---- classes ----------------------------------------------------------------------------
    def classify(self, j, rec):
        if rec["fatal"]:
            rec["class"] = "fatal"
        elif rec.get("stopped"):
            rec["class"] = "stop"
        elif not rec["alive"].get("advancing"):
            rec["class"] = "tickstop"           # the tick stopped between the phase check and now: not signed: the stage stops
        elif not rec["health"].get("ok") or any(not t["ok"] for t in rec.get("ticks", [])):
            rec["class"] = "unhealthy"           # (includes a tick rate outside 900 to 1100 Hz)
        elif rec["log_bad"]:
            rec["class"] = "unhealthy"
        elif rec.get("rc") is None:
            rec["class"] = "void"
        elif j["write"] and not (rec.get("writer") or {}).get("done"):
            rec["class"] = "void"
            rec["note"] += " the writer's flag was not set"
        elif not (rec.get("rd0") or {}).get("ran") or (j["write"] and not ((rec.get("rdA") or {}).get("ran")
                                                                        and (rec.get("rdB") or {}).get("ran"))):
            rec["class"] = "noreader"           # tick kept, a reader not run: a result (cannot tell), not a stop
        else:
            rec["class"] = "ok"
        if rec["class"] == "void" and rec.get("stopped"):
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

    def handle_stop(self, j, rec):
        """A tick stop: the budget is 0, so the stage ends.  The signature and the dumps were taken in the job, before this reset."""
        self.stops += 1
        self.mark(f"stop {self.stops} {j['name']}")
        ok = self.end(f"stop{self.stops}-{j['name']}")
        if not ok:
            s = Stop(5, f"{j['name']}: reset or gate after the stop not exact")
        else:
            s = Stop(EXIT_SECOND_STOP, f"{j['name']}: a tick stop ends the stage (budget 0; reset and gate exact)")
        s.ended = True
        raise s

    def armed_run(self):
        self.arm()
        for j in self.table["jobs"]:
            rec = self.job(j)
            c = rec["class"]
            if c in ("ok", "noreader"):
                continue
            if c == "stop":
                self.handle_stop(j, rec)
            if c in ("fatal", "no-answer"):
                raise Stop(3 if c == "fatal" else 6, f"{j['name']}: {c}: nothing else touches the GPU")
            if c == "void" and rec.get("note", "").endswith("flag was not set"):
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
