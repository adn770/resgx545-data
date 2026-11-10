#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r3_run.py STAGE --tool PATH --bins DIR --out DIR: one R3-events stage on the laptop (python3 stdlib, as root: `sudo -n python3`).
PREPARED, NOT RUN.  The Mac side (run/r3.sh) uploads it with tables/, bins/, gen/r3layout.py, the landed
tools/fwtask/fwtask_run.py (as run/fwtask_run.py), TOOL.sha256 and LAPTOP.sha256.

Stages (tables/STAGE.json), in run order:
  a    Q152 stage A, rows A0-A6.  alias.s (own_arm slots=0x1 entry=0).  One job a repetition of a row: the host's command, the
       writer's flag, the reader the writer armed (next event), the tick, for A1 a second reader 1200 ms later and the restore
       of sa63.  The sa registers the task may write are sa63, sa64, sa65 and only in these commands (the guard and
       check_job enforce it); A7 and A8 do not exist here.
  b    Q152 stage B, rows B0-B2.  ring_skip.s (slots=0xf).  Window 2 open, the host writes SKIP, the ring, the page twice, the
       tick.  B2 only if every B1 rep kept the tick.  B3 does not exist here.
  k7   Q290 K7.  ring_hold.blob (S2b's, byte for byte), a 90-tick hold, window 2, one reset and arm a job; kick modes none,
       misc1 (one GETMISCINFO, S2b's) and xfer2 (the landed debugfs xfer_sync: two real kicks, 50 ms apart, inside the hold;
       the kernel serialises debugfs commands under sgx->lock, so two miscinfo reads cannot both be inside).  LAST.

Safety (checked by run/guard_r3.sh and guard_blobs.py): no kernel change; the only writes are debugfs own_code, own_arm, own_res,
load, boot and reset (an allow-list), /dev/kmsg (os.open, O_WRONLY | O_APPEND) and the results page; no register write of any
kind (no kreg, kpoke, clock register, trc_hazard); no firmware-task `str`; the task's sa writes only sa63/sa64/sa65 in A1-A6 (+
the sa63 restore of A1); no knob is written.  Reads of debugfs: regs, status, miscinfo, xfer_sync (k7 only), buf files not at all.

Stops.  A TICK STOP (HostCtl dword 12 not advancing over three reads) is budgeted once a stage (stop_budget 1): the signature
registers are read twice BEFORE anything else, the dumps are saved, the kernel's own debugfs reset and the gate run, the task is
armed again, stage a restores sa63 if it survived the reset, and the stage goes on (the remaining repetitions of the row run: a
repeat of the stop is a second stop).  A second stop ends the stage: exit 8, reset and gate done.  A freeze (the tool gave no answer, exit 6) or a
watchdog (fatal, exit 3) stops all laptop work.  Other exits: 1 preflight, 4 a job failed or an exception, 5 reset or gate not
exact, 7 a table value outside the allow-list.  No loop waits for anything: every delay is a fixed sleep, every loop a bounded for.
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
R3 = pathlib.Path(__file__).resolve().parent.parent          # ~/r3ev on the laptop
sys.path.insert(0, str(R3 / "gen"))
sys.path.insert(0, os.environ.get("R3_FWTASK_DIR", str(R3 / "run")))   # tests point it at a fake
import r3layout as L  # noqa: E402
import fwtask_run as FR  # noqa: E402

BLOB_OF = {"a": "alias", "b": "ring_skip", "k7": "ring_hold"}
GATE_OF = {"b": "a", "k7": "b"}
GATE_EXITS = (0, 8)
ROWS = {"a": {"A0": 0, "A1": L.CMD_A1, "A2": L.CMD_A2, "A3": L.CMD_A3, "A4": L.CMD_A4, "A5": L.CMD_A5, "A6": L.CMD_A6},
        "b": {"B0": 0, "B1": 1, "B2": 5}, "k7": {"K7": None}}
KICKS = ("none", "misc1", "xfer2")
N90 = L.n_for_ticks(L.K7_HOLD_TICKS)
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
        self.base63 = 0                      # sa63 as A0 read it (what a restore puts back)
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
            raise Stop(1, "not root: run as `sudo -n python3 r3_run.py` (every debugfs access needs root)")
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
        need = [f"tables/{self.stage}.json", "gen/r3layout.py", "run/r3_run.py", "run/fwtask_run.py", "TOOL.sha256",
                "bins/blobs.json", f"bins/{blob}.blob"]
        for f in sorted(set(need)):
            if frozen.get(f) != sha(R3 / f):
                raise Stop(1, f"{f} is not the frozen file")
        binfo = json.loads((R3 / "bins" / "blobs.json").read_text())[blob]
        if binfo["str"] != 0:
            raise Stop(1, f"{blob} has a str")
        if blob == "alias":
            if {int(k): v for k, v in binfo["cmd_sa"].items()} != L.CMD_SA or not set(binfo["sa_writes"]) <= L.SA_ALLOWED:
                raise Stop(1, "alias.s: its sa write set is not the allowed one")
        elif binfo["sa_writes"]:
            raise Stop(1, f"{blob} writes an sa register")
        self.check_table()
        prev = GATE_OF.get(self.stage)
        if prev:
            try:
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
        if not env["srcversion_loaded"] or env["srcversion_loaded"] != env["srcversion_installed"]:
            raise Stop(1, "the loaded module is not the installed one")
        for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo") + (
                ("xfer_sync",) if self.stage == "k7" else ()):
            if not os.path.exists(f"{FR.D}/{f}"):
                raise Stop(1, f"the driver has no debugfs {f}")
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
        env["blob_sha256"] = frozen.get(f"bins/{blob}.blob")
        env["table_sha256"] = frozen[f"tables/{self.stage}.json"]
        self.save("env.json", env)
        self.mark(f"preflight {self.stage}")
        print(f"## preflight ok: {json.dumps({k: env[k] for k in ('srcversion_loaded', 'uname', 'tool_sha256', 'debugfs')})}")

    def check_table(self):
        t = self.table
        if int(t.get("stop_budget", 1)) != 1:
            raise Stop(7, "stop budget is not 1")
        rows = ROWS[self.stage]
        for j in t["jobs"]:
            self.check_job(j, rows)

    def check_job(self, j, rows):
        n = j.get("name", "?")
        row = j.get("row")
        if row not in rows:
            raise Stop(7, f"{n}: row {row} is not one of this stage's approved rows {sorted(rows)}")
        if j.get("op") != {"a": "alias", "b": "skip", "k7": "hold"}[self.stage]:
            raise Stop(7, f"{n}: op {j.get('op')} is not this stage's")
        if self.stage == "a":
            cmd = rows[row]
            if j["cmd"] != cmd or sorted(j["sa"]) != sorted(L.CMD_SA.get(cmd, [])) or not set(j["sa"]) <= L.SA_ALLOWED:
                raise Stop(7, f"{n}: command {j['cmd']} / sa set {j['sa']} is not row {row}'s")
            if (j.get("read_1200") or j.get("restore63")) and row != "A1":
                raise Stop(7, f"{n}: the 1200 ms reader and the sa63 restore belong to A1 only")
            if not all(isinstance(x, int) and 0 <= x < 1 << 32 for x in [j["marker"]] + list(j["ri"])):
                raise Stop(7, f"{n}: a marker is not a 32-bit integer")
        elif self.stage == "b":
            if j["skip"] != rows[row] or j["window"] != 2 or not 0 <= j["pre_ms"] <= 10 or not 10 <= j["open_ms"] <= 30:
                raise Stop(7, f"{n}: skip, window or times outside the allow-list")
        else:
            if j["kick"] not in KICKS or j["n"] != N90 or j["window"] != 2 or not 100 <= j["open_ms"] <= 200 or \
                    not 2 <= j["trigger_after_ms"] <= 5:
                raise Stop(7, f"{n}: kick mode, n, window or times outside the allow-list")

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

    # ---- page and tick helpers ------------------------------------------------------------
    def bracket_read(self, res):
        """[page PASS, HostCtl dword 12, page PASS]: the interval arithmetic of the scorer's `d12 - passes` needs the two page
        reads around the register read."""
        a = res.r(L.A_PASS)[0]
        h = FR.regs()[1].get(12)
        b = res.r(L.A_PASS)[0]
        return [a, h, b]

    def ring_clear(self, res):
        res.w(L.RING_BASE[0], [0] * (L.RING_END - L.RING_BASE[0]))
        res.w(L.DROP, [0] * 12)                          # DROP, PASS, OVL
        res.w(L.OVL_LOG, [0] * 16)
        res.w(L.HOLD_ENTRY, [L.INITFILL, L.INITFILL])
        res.w(L.SKIP, [0, 0])                            # SKIP, SKIPPED
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

    def wait_state(self, res, cmd, runid, ms):
        """Bounded wait (for, fixed 2 ms sleeps): the page shows CMD == cmd, STATE done, the run id echoed.  Returns ms or None."""
        t = time.monotonic()
        for _ in range(int(ms / 2) + 1):
            c, s = res.r(L.CMD, 2)
            if c == cmd and s == L.STATE_DONE and res.r(L.ECHO)[0] == runid:
                return (time.monotonic() - t) * 1000
            time.sleep(0.002)
        return None

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
            {"alias": self.alias_job, "skip": self.skip_job, "hold": self.hold_job}[j["op"]](j, rec)
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
        if err is not None and rec["class"] in ("ok", "noreader", "kick-timeout"):
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

    # ---- stage a ------------------------------------------------------------------------
    def command(self, res, cmd, runid, marker=None, ri=None, ms=120):
        """Issue one alias.s command and wait for its flag.  The writers arm the reader (cmd 9): flag = cmd 9 with state done;
        a reader's flag is cmd 0.  Returns {"done", "ms"}."""
        res.w(L.STATE, 0)
        res.w(L.ECHO, 0)
        res.w(L.WR, [0] * 16)                # the writer's record and its flag (WR_DONE) start empty
        res.w(L.RD, [0] * 16)
        res.w(L.RUNID, runid)
        if marker is not None:
            res.w(L.A_M, marker)
        if ri is not None:
            res.w(L.A_RI, list(ri))
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

    def alias_job(self, j, rec):
        res = FR.Res()
        try:
            rec["ccbctl_pre"] = self.ccbctl()
            self.zero_protocol(res)
            res.w(L.A_RI, list(j["ri"]))
            res.w(L.A_M, j["marker"])
            rec["bracket_pre"] = br0 = self.bracket_read(res)
            cmd, rid = j["cmd"], j["runid"]
            wr = {"issued": bool(cmd), "done": False}
            if cmd:
                wr.update(self.command(res, cmd, rid, j["marker"], j["ri"]))
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
            if not cmd and rd["rd"]:
                self.base63 = rd["rd"][L.RD_FIELDS.index("sa63")]
            if not self.check_tick(rec, "after-reader"):
                return
            if j["read_1200"]:
                time.sleep(1.2)
                r2 = self.command(res, L.CMD_READ, rid)
                rec["reader2"] = {"ran": r2["done"], "rd": res.r(L.RD, 16) if r2["done"] else None, "ms": r2["ms"]}
                if not self.check_tick(rec, "after-1200ms-reader"):
                    return
            if j["restore63"]:
                rec["restore"] = self.restore63(res, rid)
                self.check_tick(rec, "after-restore")
            rec["rc"] = 0
        finally:
            res.close()

    def restore63(self, res, rid):
        """Put sa63 back to what A0 read (cmd 7, then the reader it armed)."""
        r = self.command(res, L.CMD_RESTORE63, rid, marker=self.base63)
        ran = self.wait_reader(res, rid, 120) is not None if r["done"] else False
        return {"cmd7": r, "reader_ran": ran, "rd": res.r(L.RD, 16) if ran else None, "wanted": self.base63}

    def baseline(self):
        """After a stop's reset and re-arm: the reader, and cmd 7 if sa63 survived the reset (E536: sa100 and sa127 did)."""
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

    # ---- stage b ------------------------------------------------------------------------
    def skip_job(self, j, rec):
        res = FR.Res()
        try:
            self.ring_clear(res)
            rec["ccbctl_pre"] = self.ccbctl()
            rec["bracket_pre"] = br0 = self.bracket_read(res)
            t0 = time.monotonic()
            self.ring_open(res, j["window"], rec)
            time.sleep(j["pre_ms"] / 1000)
            if j["skip"]:
                res.w(L.SKIP, j["skip"])
                rec["t_skip_ms"] = (time.monotonic() - t0) * 1000
            time.sleep(max(0.0, j["open_ms"] / 1000 - (time.monotonic() - t0)))
            self.ring_close(res, rec, t0)
            rec["bracket"] = {"before": br0, "after": self.bracket_read(res)}
            self.check_tick(rec, "after-window")
        finally:
            res.close()

    # ---- stage k7 -----------------------------------------------------------------------
    def hold_job(self, j, rec):
        r = captured(FR.cmd_reset)
        rec["pre_reset"] = {"ok": r.get("ok")}
        if not r.get("ok"):
            raise Stop(4, "the reset before the arm is not ok")
        self.mark(f"arm {j['name']}")
        self.arm(tag=f"{j['name']}.arm")
        rec["ccbctl_after_arm"] = self.ccbctl()
        res = FR.Res()
        try:
            self.ring_clear(res)
            res.w(L.N_ITER, j["n"])
            res.w(L.RUNID, j["runid"])
            rec["tick_before"] = FR.regs()[1].get(12)
            t0 = time.monotonic()
            self.ring_open(res, j["window"], rec)
            res.w(L.CMD, 1)                                   # back to back with the window (S2b, E4)
            time.sleep(j["trigger_after_ms"] / 1000)
            rec["state_at_trigger"] = res.r(L.STATE)[0]
            rec["t_trigger_ms"] = (time.monotonic() - t0) * 1000
            if rec["state_at_trigger"] == L.STATE_BUSY and j["kick"] != "none":
                self.kick(j["kick"], rec)
            rec["t_trigger_end_ms"] = (time.monotonic() - t0) * 1000
            time.sleep(max(0.0, j["open_ms"] / 1000 - (time.monotonic() - t0)))
            self.ring_close(res, rec, t0)
            rec["tick_after"] = FR.regs()[1].get(12)
        finally:
            res.close()
        rec["ccbctl_after"] = self.ccbctl()
        self.check_tick(rec, "after-hold")

    def kick(self, mode, rec):
        """misc1: one GETMISCINFO (S2b's kick).  xfer2: the landed xfer_sync, which submits a TRANSFER (kick 1), sleeps 50 ms, then
        PROCESS_QUEUES (kick 2) and waits for the SW event.  A failed read (the kernel's 500 ms timeout) is a result."""
        t = time.monotonic()
        try:
            if mode == "misc1":
                rec["kick"] = FR.miscinfo()
            else:
                s = FR.rd("xfer_sync")
                rec["kick"] = {"ms": (time.monotonic() - t) * 1000, "text": s, "lines": len(s.splitlines())}   # the WHOLE text
        except OSError as e:
            rec["kick"] = {"ms": (time.monotonic() - t) * 1000, "errno": e.errno, "text": f"no completion (the read failed: {e})"}
            rec.setdefault("kick_errors", []).append(rec["kick"]["errno"])

    # ---- classes ----------------------------------------------------------------------------
    def classify(self, j, rec):
        op = j["op"]
        if rec["fatal"]:
            rec["class"] = "fatal"
        elif rec.get("stopped"):
            rec["class"] = "stop"
        elif op in ("skip", "hold") and rec.get("page") is None:
            rec["class"] = "void"
            rec["note"] += " no page read"
        elif not rec["alive"].get("advancing"):
            rec["class"] = "tickstop"           # the tick stopped between the phase check and now: not signed: the stage stops
        elif not rec["health"].get("ok") or any(not t["ok"] for t in rec.get("ticks", [])):
            rec["class"] = "unhealthy"           # (includes a tick rate outside 900 to 1100 Hz)
        elif rec["log_bad"]:
            rec["class"] = "unhealthy"
        elif op == "alias" and rec.get("rc") is None:
            rec["class"] = "void"
        elif op == "alias" and j["cmd"] and not (rec.get("writer") or {}).get("done"):
            rec["class"] = "void"
            rec["note"] += " the writer's flag was not set"
        elif op == "alias" and not (rec.get("reader") or {}).get("ran"):
            rec["class"] = "noreader"           # tick kept, reader not run: a result (cannot tell), not a stop
        elif op == "hold" and rec.get("kick_errors"):
            rec["class"] = "kick-timeout"       # a result (H-MERGE's timeout), not a stop: tick and health fine
        else:
            rec["class"] = "ok"
        # a stop seen in the writer wait: the reader did not run and the tick is gone (E537's shape)
        if op == "alias" and rec["class"] == "void" and rec.get("stopped"):
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

    def b1_all_kept(self):
        b1 = [r for r in self.records.values() if r["row"] == "B1"]
        return bool(b1) and all(r["class"] == "ok" for r in b1)

    def handle_stop(self, j, rec):
        """One tick stop: counted against the stage's budget.  The signature and the dumps were taken in the job, before this
        reset.  Second stop: reset, gate, the stage ends (exit 8).  First: reset, gate, arm again, stage a restores sa63."""
        self.stops += 1
        self.mark(f"stop {self.stops} {j['name']}")
        ok = self.end(f"stop{self.stops}-{j['name']}")
        if not ok:
            s = Stop(5, f"{j['name']}: reset or gate after the stop not exact")
            s.ended = True
            raise s
        if self.stops > int(self.table.get("stop_budget", 1)):
            s = Stop(EXIT_SECOND_STOP, f"{j['name']}: the second tick stop ends the stage (reset and gate exact)")
            s.ended = True
            raise s
        if self.stage != "k7":
            self.arm(f"rearm{self.stops}")
            if self.stage == "a":
                self.baseline()

    def armed_run(self):
        if self.stage != "k7":
            self.arm()                       # k7 resets and arms in every job
        for j in self.table["jobs"]:
            if j.get("run_if") == "b1_all_kept" and not self.b1_all_kept():
                self.skipped(j, "B1 did not keep the tick in every rep: B2 is not run")
                continue
            rec = self.job(j)
            c = rec["class"]
            if c in ("ok", "noreader", "kick-timeout"):
                continue
            if c == "stop":
                self.handle_stop(j, rec)
                continue
            if c in ("fatal", "no-answer"):
                raise Stop(3 if c == "fatal" else 6, f"{j['name']}: {c}: nothing else touches the GPU")
            if c == "void" and j["op"] == "alias" and rec.get("note", "").endswith("flag was not set"):
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
