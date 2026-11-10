# SPDX-License-Identifier: MIT
"""A fake of the landed fwtask_run.py for the C3 mock tests: the same names, a simulated EDM behind them.

The page, the ticks (997.46 Hz), HostCtl dword 12, and our one task as the protocol the runner and the scorer must handle: start.s
(the writer, the reader at the next event, the sa63/r/i/p/pclink state, the effect of a client fill, a reload and a reset on it).  The
events are simulated lazily, in time order, whenever the runner touches the page or the registers.  Nothing here is a model of the
hardware: switches (MOCK_SCENARIO, comma separated) make every outcome and every stop rule fire:
  worlds    keep (default: i0/i1 and sa63 survive a reload and a reset, r20/r21 do not, p2 p3 as the writer left them)
            all (r20 and r21 survive too)    set (the next entry has p2 = p3 = 1)    wipe (nothing survives a reload or a reset)
  stops     stop_JOB (the tick stops after that job's writer's pass; JOB = f2, l1, ...)     stop_reload / stop_reset  (the tick stays
            stopped after that perturbation)
  rows      noreader (the reader the writer armed never runs, the tick is kept)    writefail (the sa63 write reads back wrong)
            fillfail (the fill prints no diff line)    s0_zero (sa100, sa127 read 0)
  stop signature (any stop)   sig_pending (idle, events queued)   sig_empty (idle, nothing queued)   default: E537's busy values
  general   jitter  armfail  gatefail  unhealthy  pre_dirty  fatal@JOB  badlog@JOB  boom@JOB  latebad
"""
import json
import os
import re
import sys
import time

MOCK = os.environ["MOCK_DIR"]
D = os.path.join(MOCK, "dbg")
SC = set(os.environ.get("MOCK_SCENARIO", "").split(","))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "gen"))
import c3layout as L  # noqa: E402

GATE_TOOL = os.path.join(os.environ.get("MOCK_HOME", MOCK), "sgxfive-test")   # the landed gate's /home/jtorra/...
BAD_LOG = re.compile(r"\b(hung|recovering|BUG|Oops)\b|\bfault\b|page fault", re.I)
PERIOD = L.TICK_UNITS / L.TIMER_HZ        # 25000 CR_TIMER units a tick, 997.46 Hz
KMSG = os.environ.get("R3_KMSG", os.path.join(MOCK, "kmsg"))
TRACE = os.path.join(MOCK, "trace")
STATUS2 = os.path.join(MOCK, "status2")
IDENT = "[1.0] gma500 0000:00:02.0: [drm] SGX firmware: core 545 rev 0x1000d, DDK 1.7.17 build 862890, answered after 179 us"


class Stop(Exception):
    pass


def trace(s):
    with open(TRACE, "a") as f:
        f.write(f"{time.monotonic():.6f} {s}\n")


def current_job():
    try:
        lines = [ln for ln in open(KMSG).read().splitlines() if " case " in ln]
    except OSError:
        return ""
    return lines[-1].split(" case ")[1].split()[0] if lines else ""


def klog(line):
    with open(KMSG, "a") as f:
        f.write(line + "\n")


def status2_val():
    try:
        return int(open(STATUS2).read().strip(), 0)
    except (OSError, ValueError):
        return 0x400


class Edm:
    def __init__(self):
        self.page = [0] * L.PAGE_DWORDS
        self.page[0] = L.MAGIC
        self.blob = None
        self.arm_line = "0"
        self.has_code = False
        self.t0 = time.monotonic()
        self.last = 0                     # index of the last tick processed
        self.ticks = 0x9d0                # HostCtl dword 12
        self.alive = True
        self.cmds = 2
        self.kind = next((k for k in ("all", "set", "wipe") if k in SC), "keep")
        self.st = {"sa63": 0, "r20": 0, "r21": 0x1000, "i0": L.E533["i0"], "i1": L.E533["i1"], "sa100": L.E533["sa100"],
                   "sa127": L.E533["sa127"], "sa20": 0, "sa24": 0, "p2": 0, "p3": 0, "pclink": 0x98, "p1": 1}
        if "s0_zero" in SC:
            self.st.update(sa100=0, sa127=0)
        self.fills = 0
        self.stopped_jobs = set()

    def stamp(self, t):
        x = (t - self.t0) * L.TIMER_HZ
        if "jitter" in SC:
            x += ((int(t * 1e4) * 7919) % 3000) - 1500
        return (int(x) + 0x10000000) & 0xFFFFFFFF

    # ---- the task ------------------------------------------------------------------------------
    def entry_rd(self):
        s = self.st
        d = {"pclink": s["pclink"], "p0": 1, "p1": s["p1"], "p2": s["p2"], "p3": s["p3"], "r20": s["r20"], "r21": s["r21"],
             "i0": s["i0"], "i1": s["i1"], "sa63": s["sa63"], "sa64": 2, "sa65": (self.cmds % 256) << 24, "sa100": s["sa100"],
             "sa127": s["sa127"], "sa20": s["sa20"], "sa24": s["sa24"], "pa0": 2, "pa1": (self.cmds % 256) << 24, "pa2": 0x01061A70,
             "pass": self.page[L.A_PASS]}
        return [d[k] for k in L.RD_FIELDS]

    def tick_pass(self, t):
        """One pass of start.s at time t.  Returns False if the tick stops."""
        p = self.page
        p[L.A_PASS] += 1
        cmd = p[L.CMD]
        if cmd == L.CMD_READ:
            rd = self.entry_rd()
            p[L.RD:L.RD + L.RD_N] = rd + [0] * (L.RD_N - len(rd))
            p[L.ECHO] = p[L.RUNID]
            p[L.CMD] = 0
            p[L.STATE] = L.STATE_DONE
            self.st["p1"] = 1                 # the pass's own tests leave p1 as the dispatch does
            return True
        if cmd == L.CMD_W:
            j = current_job()
            s = self.st
            s["sa63"] = p[L.A_M]
            s["r20"], s["r21"], s["i0"], s["i1"] = p[L.A_RI:L.A_RI + 4]
            rb = s["sa63"] ^ (1 if "writefail" in SC else 0)
            p[L.WR:L.WR + 6] = [2, (self.cmds % 256) << 24, 0x01061A70, 0, p[L.A_M], rb]
            fl = p[L.PF:L.PF + 4]
            s["p1"] = int(bool(fl[1]))
            s["p2"], s["p3"] = (1, 1) if self.kind == "set" else (int(bool(fl[2])), int(bool(fl[3])))
            p[L.ECHO] = p[L.RUNID]
            p[L.WR_DONE] = p[L.RUNID]
            p[L.CMD] = 0 if "noreader" in SC else L.CMD_READ
            p[L.STATE] = L.STATE_DONE
            if f"stop_{j}" in SC and j not in self.stopped_jobs:
                self.stopped_jobs.add(j)
                self.alive = False
                return False
        return True

    def perturb(self, kind):
        s = self.st
        if kind == "fill":
            self.fills += 1
            s["r20"], s["r21"], s["p2"], s["p3"] = 0, 0x1000 * self.fills, 0, 1
        elif kind in ("reload", "reset"):
            if self.kind in ("keep", "set"):
                s["r20"], s["r21"] = 0, 0x3000
            elif self.kind == "wipe":
                s["r20"], s["r21"], s["i0"], s["i1"], s["sa63"] = 0, 0x1000, 0, 0, 0
            s["p2"], s["p3"] = 0, 0
            s["p1"] = 1

    def advance(self):
        now = time.monotonic()
        if not self.alive:
            return
        k = int((now - self.t0) / PERIOD)
        for i in range(self.last + 1, k + 1):
            t = self.t0 + i * PERIOD
            self.last = i
            if self.blob:
                if not self.tick_pass(t):
                    self.t_stop = t
                    return
            self.ticks += 1

    def boot(self, kind):
        self.page = [0] * L.PAGE_DWORDS
        self.page[0] = L.MAGIC
        self.cmds = 0
        self.alive = True
        if f"stop_{kind}" in SC and current_job() and kind not in self.stopped_jobs:
            self.stopped_jobs.add(kind)                 # once, inside a job (not the stage's own arm, not the end reset)
            self.alive = False
        self.cmds += 1
        klog(IDENT)
        self.t0 = time.monotonic()
        self.last = 0
        self.blob = None
        if self.arm_line not in ("0", "") and self.has_code:
            self.blob = "start"
        self.perturb(kind)
        with open(STATUS2, "w") as f:
            f.write("0x440\n" if "pre_dirty" in SC else "0x400\n")


EDM = Edm()


# ---- the landed names -----------------------------------------------------------------------
def emit(obj):
    print(json.dumps(obj, sort_keys=True))
    sys.stdout.flush()


def sig_regs():
    """The registers of E537's stop signature (the busy values), or the scenario's idle ones; a running EDM reads idle."""
    t = time.monotonic()
    if EDM.alive:
        return {0x0008: 0x20, 0x0b14: 0x10000 | (EDM.ticks + 3) & 0xFFFF, 0x0acc: 0x01000000 | (int(t * 3e6) % 400000),
                0x012c: 0x0, 0x0b20: 0x10000}
    if "sig_pending" in SC:
        return {0x0008: 0x20, 0x0b14: 0x9e0, 0x0acc: 0x01000000 | (int(t * 3e6) % 400000), 0x012c: 0x20000000, 0x0b20: 0x10000}
    if "sig_empty" in SC:
        return {0x0008: 0x20, 0x0b14: 0x10000, 0x0acc: 0x01000000 | (int(t * 3e6) % 400000), 0x012c: 0x0, 0x0b20: 0x10000}
    return {0x0008: 0x000ccfa0, 0x0b14: 0x9e0, 0x0acc: 0x01000000 | (int(t * 3e6) % 400000), 0x012c: 0x20000000, 0x0b20: 0x10000}


def rd(name):
    if name == "regs":
        EDM.advance()
        s2 = f"0x{status2_val():08x}"
        sg = sig_regs()
        lines = ["sgxfive regs 1", "state loaded 1 live 1 sw_events 0 bif_faults 0", f"reg 0x0008 0x{sg[0x0008]:08x}",
                 f"reg 0x0118 {s2}", f"reg 0x012c 0x{sg[0x012c]:08x}", "reg 0x0c04 0x00000000", "reg 0x0c08 0x00000000",
                 f"reg 0x0144 0x{EDM.stamp(time.monotonic()):08x}", f"reg 0x0acc 0x{sg[0x0acc]:08x}",
                 f"reg 0x0b14 0x{sg[0x0b14]:08x}", f"reg 0x0b20 0x{sg[0x0b20]:08x}",
                 f"hostctl 0x30 0x{EDM.ticks:08x}", f"ccbctl 0x00 0x{EDM.cmds % 256:08x}", "ccbctl 0x04 0x00000000", "end"]
        return "\n".join(lines) + "\n"
    if name == "status":
        return "loaded 1 live 1 sw_events 0 bif_faults 0 ccb_sent 0\n"
    if name == "own_arm":
        return ("off" if EDM.arm_line in ("0", "") else f"armed {EDM.arm_line}") + "\n"
    with open(f"{D}/{name}") as f:
        return f.read()


def wr(name, text):
    trace(f"wr {name} {text if isinstance(text, str) else '<bytes>'}")
    if name == "own_code":
        EDM.has_code = True
        data = text if isinstance(text, bytes) else text.encode()
        info = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bins", "blobs.json")))
        EDM.which = {v["bytes"]: k for k, v in info.items()}.get(len(data), "start")
        return
    if name == "own_arm":
        EDM.arm_line = text.strip()
        return
    if name == "load":
        EDM.blob = None
        EDM.page = [0] * L.PAGE_DWORDS
        EDM.page[0] = L.MAGIC
        return
    if name == "boot":
        EDM.boot("reload")
        return
    if name == "reset":
        EDM.arm_line = "0"
        EDM.boot("reset")
        try:
            n = int(open(os.path.join(MOCK, "reset_count")).read())
        except (OSError, ValueError):
            n = 0
        with open(os.path.join(MOCK, "reset_count"), "w") as f:
            f.write(str(n + 1))
        return
    with open(f"{D}/{name}", "w") as f:
        f.write(text if isinstance(text, str) else text.decode())


def sh(cmd, check=True):
    if cmd.startswith("modinfo"):
        return "MOCKSRCV\n"
    if cmd.startswith("uname"):
        return "7.3.0-mock\n"
    if cmd.startswith("sha256sum"):
        return "0" * 64 + "  /lib/firmware/sgx545_ukernel.fw\n"
    if cmd.startswith("journalctl"):
        extra = ["[2.0] gma500: sgxfive: job 9 hung, recovering"] if "latebad" in SC else []
        log = full_log()
        starts = [i for i, ln in enumerate(log) if " preflight " in ln]
        return "\n".join((log[starts[-1]:] if starts else log) + extra) + "\n"
    if " fill " in cmd:                      # the gate tool's fill, as the runner runs it (E536's form)
        trace(f"fill {current_job()}")
        EDM.advance()
        EDM.perturb("fill")
        return "" if "fillfail" in SC else "diff: 0 of 2048 pixels\n"
    if cmd.strip() == "dmesg":
        return "\n".join(full_log()) + "\n"
    return ""


def full_log():
    try:
        out = open(KMSG).read().splitlines()
    except OSError:
        out = []
    job = current_job()
    paged = bool(job)            # (the alias jobs read no ring page: the job's case marker is what triggers the log line)
    if paged and f"fatal@{job}" in SC:
        out.append("[1.0] watchdog: BUG: soft lockup - CPU#0 stuck for 22s!")
    if paged and f"badlog@{job}" in SC:
        out.append("[1.0] gma500: sgxfive: job 7 hung, recovering")
    return out


def dmesg_len():
    return len(full_log())


def dmesg_new(n0):
    return full_log()[n0:]


class Res:
    def __init__(self):
        pass

    def r(self, dword, n=1):
        EDM.advance()
        if dword in (L.WR, L.RD) and f"boom@{current_job()}" in SC:
            raise RuntimeError("mock: an unexpected error while reading the page")
        return EDM.page[dword:dword + n]

    def w(self, dword, vals):
        EDM.advance()
        if isinstance(vals, int):
            vals = [vals]
        if dword < 1:
            raise OSError("dword 0 is the kernel's")
        EDM.page[dword:dword + len(vals)] = [v & 0xFFFFFFFF for v in vals]

    def page(self):
        trace(f"page {current_job()}")
        if f"boom@{current_job()}" in SC:
            raise RuntimeError("mock: an unexpected error while reading the page")
        return self.r(0, L.PAGE_DWORDS)

    def close(self):
        pass


def regs():
    out, hc = {}, {}
    for line in rd("regs").splitlines():
        m = re.match(r"reg (0x[0-9a-f]+) (0x[0-9a-f]+)$", line)
        if m:
            out[int(m.group(1), 16)] = int(m.group(2), 16)
        m = re.match(r"hostctl (0x[0-9a-f]+) (0x[0-9a-f]+)$", line)
        if m:
            hc[int(m.group(1), 16) // 4] = int(m.group(2), 16)
    return out, hc


def alive(window=3, gap=0.02):
    seen = []
    for _ in range(window):
        seen.append(regs()[1][12])
        time.sleep(gap)
    return {"ticks": seen, "advancing": all(b != a for a, b in zip(seen, seen[1:]))}


def tick_rate(ms=300):
    return 997.4 if EDM.alive else 0.0


def health():
    s2 = status2_val()
    return {"event_status2": s2, "bif_int_stat": 0, "faults_status": 0, "ok": s2 == 0x400 and "unhealthy" not in SC}


def miscinfo():
    """One GETMISCINFO: the kernel logs one answer line."""
    t0 = time.monotonic()
    EDM.advance()
    EDM.cmds += 1
    klog(IDENT)
    return {"ms": (time.monotonic() - t0) * 1000, "lines": 1, "text": "MISCINFO ok"}


def cmd_arm(a):
    """The landed cmd_arm's statements in the landed order (the mock's primitives do the work)."""
    trace(f"arm {a['blob']} {a.get('arm')}")
    wr("own_arm", "0")
    with open(a["blob"], "rb") as f:
        data = f.read()
    wr("own_code", data)
    if a.get("arm"):
        wr("own_arm", a["arm"])
    wr("load", "1")
    wr("boot", "1")
    out = {"own_arm": rd("own_arm").strip(), "alive": alive(), "rate_hz": tick_rate(), "misc": miscinfo(), "health": health()}
    ok = os.path.exists(a["blob"]) and "armfail" not in SC and out["alive"]["advancing"]
    out.update({"ok": ok, "magic": EDM.page[0], "log_bad": []})
    emit(out)


def cmd_reset(a):
    trace("reset")
    wr("reset", "1")
    out = {"own_arm": "off", "misc": miscinfo(), "health": health()}
    out["ok"] = bool(out["health"]["ok"])           # the landed cmd_reset: alive, health (0x400 again) and own_arm off
    emit(out)


def cmd_gate(a):
    trace("gate")
    emit({"ok": "gatefail" not in SC, "fill": "diff: 0 of 2048", "tri": "diff: 0 of 4096"})


def hang_dump(outdir, tag):
    trace("dump")
    os.makedirs(outdir, exist_ok=True)
    with open(f"{outdir}/{tag}-status.txt", "w") as f:
        f.write(rd("status"))
    with open(f"{outdir}/{tag}-own_res.json", "w") as f:
        f.write(json.dumps(EDM.page))
    with open(f"{outdir}/{tag}-regs.txt", "w") as f:
        f.write(rd("regs"))
