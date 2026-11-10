# SPDX-License-Identifier: MIT
"""A fake of the landed fwtask_run.py for the R1-events mock tests: the same names, a simulated EDM behind them.

The page, the ticks (997.46 Hz), CR_TIMER (24.9366 MHz), the four PDS #13 slots (E146's dispatch), our task ring_e1 (arm
through own_code, own_arm, load, boot as the landed cmd_arm writes them), the command counter of the kernel's CCB (the byte
pa1[31:24] of every event, the host's write offset ccbctl[0]; +1 for each GETMISCINFO and each (0, 8) entry of a client job:
boot's GETMISCINFO makes it 1) and the client jobs (written by tests/fake_tool.py to MOCK_DIR/events) are simulated lazily, in
time order, whenever the runner touches the page or the registers.  Nothing here is a model of the hardware: it is the
protocol the runner and the scorer must handle, with switches (MOCK_SCENARIO, comma separated) that make every gate and
every stop rule fire:
  jitter           tick stamps off the 25000 grid         armfail / gatefail   the arm / the gate is not healthy / exact
  k_sat            the count byte saturates at 255 (Q290's H-SAT)   k_fw2   the byte starts at 2 whatever the host sent
  k5_timeout       the 100th kick of a burst times out (the kernel's 500 ms read)
  h_raise (default) / h_thresh / h_never   which jobs raise bit 19 (Q033): raise jobs only / every job that reaches thr0 / none
  d_big4           the big jobs make four partial renders (slot 3's 12 rungs fill: drops)
  fatal@JOB badlog@JOB boom@JOB   a watchdog line / a "hung" line in the kernel log, an exception reading the page in JOB
  knob_stuck       render_pb_pages / hold_recovery ignore writes      ringfull   dmesg shows only its last 5 lines
  latebad          journalctl -k has a "hung, recovering" line no job slice saw      unhealthy   health() is not ok
  t_iter / t_instr (default) / t_time   which Q082 model the fake `probe` follows (tests/fake_tool.py)
  pre_dirty        the job's pre read of CR_EVENT_STATUS2 is 0x440 (the reset did not clear it)
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
import r1layout as L  # noqa: E402

GATE_TOOL = os.path.join(os.environ.get("MOCK_HOME", MOCK), "sgxfive-test")   # the landed gate's /home/jtorra/...
BAD_LOG = re.compile(r"\b(hung|recovering|BUG|Oops)\b|\bfault\b|page fault", re.I)
PERIOD = L.TICK_UNITS / L.TIMER_HZ        # 25000 CR_TIMER units a tick, 997.46 Hz
KMSG = os.environ.get("R1_KMSG", os.path.join(MOCK, "kmsg"))
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


def raised_words(kind):
    """The (slot-less) event groups of a fake client job: each entry a (bit, is_command) of pa1[23:0]; ('b19',) = bit 19."""
    parts = kind.split(":")
    if parts[0] == "big":
        P, nparts, raised = int(parts[1], 0), int(parts[2]), parts[3] == "1"
        if "d_big4" in SC and nparts:
            nparts = 4
        grp = [(8, 1), (21, 0), (10, 0), (4, 0), (22, 0), (9, 0), (4, 0), (22, 0)]
        b19 = "h_thresh" in SC or ("h_never" not in SC and raised)      # default: h_raise
        out = []
        for i in range(nparts):
            out += grp
            if b19 and i == 0:
                out.append((19, 0))
        out += [(8, 1)] * 5
        return out
    table = {"fill": [(8, 1), (4, 0), (8, 1)], "copy": [(8, 1), (4, 0), (8, 1)],
             "tri64": [(8, 1), (9, 0), (4, 0), (22, 0)] + [(8, 1)] * 5,
             "partial": [(8, 1), (21, 0), (10, 0), (4, 0), (22, 0), (9, 0), (4, 0), (22, 0)] * 2 + [(8, 1)] * 5}
    return table.get(kind, [(8, 1), (4, 0), (8, 1)])


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
        self.cmds = 2                     # commands the kernel's CCB took since boot (stock boot: 1 + the runner's read)
        self.processed_events = 0

    @property
    def K(self):
        c = self.cmds % 256
        if "k_sat" in SC:
            c = min(self.cmds, 255)
        return 2 if "k_fw2" in SC else c

    def bump(self, n=1):
        self.cmds += n

    def stamp(self, t):
        x = (t - self.t0) * L.TIMER_HZ
        if "jitter" in SC:
            x += ((int(t * 1e4) * 7919) % 3000) - 1500
        return (int(x) + 0x10000000) & 0xFFFFFFFF

    def pa2_event(self, t):
        since = (t - self.t0) % PERIOD
        return 0x01000000 | max(1, 400000 - int(since * 16 * L.TIMER_HZ))

    def task(self, slot, pa, t):
        p = self.page
        w = p[L.WINDOW]
        log = w == 2 or (w == 1 and not L.is_plain_tick(pa[0], pa[1]))
        if self.blob == "ring_e1" and log:
            base = L.RING_BASE[slot]
            for j in range(L.RUNGS[slot]):
                o = base + L.RUNG * j
                if p[o] == 0:
                    p[o:o + 5] = [1, pa[0], pa[1], pa[2], self.stamp(t)]
                    break
            else:
                p[L.DROP + slot] += 1

    def advance(self):
        now = time.monotonic()
        evs = []
        if self.alive:
            k = int((now - self.t0) / PERIOD)
            for i in range(self.last + 1, k + 1):
                evs.append((self.t0 + i * PERIOD, 0, "tick", None))
            self.last = max(self.last, k)
        try:
            lines = open(os.path.join(MOCK, "events")).read().splitlines()
        except OSError:
            lines = []
        for ln in lines[self.processed_events:]:
            t, kind = ln.split()
            t = float(t)
            for bit, is_cmd in raised_words(kind):
                evs.append((t, 0, "job", (bit, is_cmd)))
                t += 30e-6
        self.processed_events = len(lines)
        for t, _, kind, arg in sorted(evs, key=lambda e: e[0]):
            if kind == "tick":
                if self.blob and self.alive:
                    self.task(0, (L.TICK_PA0, (self.K << 24), L.PA2_CONST), t)
                if self.alive:
                    self.ticks += 1
            else:
                bit, is_cmd = arg
                pa1 = (self.K << 24) | (1 << bit)
                slot = L.pds_slot(0, 1 << bit)
                if self.blob:
                    self.task(slot, (0, pa1, self.pa2_event(t)), t)
                if is_cmd:
                    self.bump()

    def boot(self):
        self.page = [0] * L.PAGE_DWORDS
        self.page[0] = L.MAGIC
        self.cmds = 0
        self.alive = True
        self.bump()                        # sgxfive_boot's GETMISCINFO (sgxfive_ident_ask)
        klog(IDENT)
        self.t0 = time.monotonic()
        self.last = 0
        self.blob = "ring_e1" if self.arm_line not in ("0", "") and self.has_code else None
        with open(STATUS2, "w") as f:
            f.write("0x440\n" if "pre_dirty" in SC else "0x400\n")


EDM = Edm()


# ---- the landed names -----------------------------------------------------------------------
def emit(obj):
    print(json.dumps(obj, sort_keys=True))
    sys.stdout.flush()


def rd(name):
    if name == "regs":
        EDM.advance()
        s2 = f"0x{status2_val():08x}"
        lines = ["sgxfive regs 1", "state loaded 1 live 1 sw_events 0 bif_faults 0",
                 f"reg 0x0118 {s2}", "reg 0x012c 0x20000000", "reg 0x0c04 0x00000000", "reg 0x0c08 0x00000000",
                 f"reg 0x0144 0x{EDM.stamp(time.monotonic()):08x}", f"reg 0x0b14 0x{0x10000 | (EDM.ticks + 3) & 0xFFFF:08x}",
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
    if name in ("render_pb_pages", "hold_recovery") and "knob_stuck" in SC and text not in ("N", "0x422"):
        return                                # the write of the job's value is ignored (its restore lands)
    if name == "own_code":
        EDM.has_code = True
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
        EDM.boot()
        return
    if name == "reset":
        EDM.arm_line = "0"
        EDM.boot()
        try:
            n = int(open(os.path.join(MOCK, "reset_count")).read())
        except (OSError, ValueError):
            n = 0
        with open(os.path.join(MOCK, "reset_count"), "w") as f:
            f.write(str(n + 1))
        return
    if name == "render_pb_pages":
        text = f"0x{int(text, 0):08x}"
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
        starts = [i for i, ln in enumerate(log) if " preflight " in ln]        # journalctl -k --since the stage's start
        return "\n".join((log[starts[-1]:] if starts else log) + extra) + "\n"
    if cmd.strip() == "dmesg":
        return "\n".join(dmesg_lines()) + "\n"
    return ""


def dmesg_lines():
    out = full_log()
    return (["[0.0] older line"] * 5 + out)[-5:] if "ringfull" in SC else out


def full_log():
    try:
        out = open(KMSG).read().splitlines()
    except OSError:
        out = []
    job = current_job()
    try:
        paged = any(ln.endswith(f" page {job}") for ln in open(TRACE).read().splitlines())
    except OSError:
        paged = False
    if paged and f"fatal@{job}" in SC:
        out.append("[1.0] watchdog: BUG: soft lockup - CPU#0 stuck for 22s!")
    if paged and f"badlog@{job}" in SC:
        out.append("[1.0] gma500: sgxfive: job 7 hung, recovering")
    return out


def dmesg_len():
    return len(dmesg_lines())


def dmesg_new(n0):
    return dmesg_lines()[n0:]


class Res:
    def __init__(self):
        pass

    def r(self, dword, n=1):
        EDM.advance()
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
    return 997.4


def health():
    s2 = status2_val()
    return {"event_status2": s2, "bif_int_stat": 0, "faults_status": 0, "ok": s2 == 0x400 and "unhealthy" not in SC}


def miscinfo():
    """One GETMISCINFO: the kick is one event (pa0 0, pa1 (K << 24) | 0x100, pa2 EVENT_TIMER) carrying the value before its
    bump; the kernel logs one answer line (sgxfive_ident_ask)."""
    t0 = time.monotonic()
    EDM.advance()
    try:
        n = int(open(os.path.join(MOCK, "kick_n")).read())
    except (OSError, ValueError):
        n = 0
    with open(os.path.join(MOCK, "kick_n"), "w") as f:
        f.write(str(n + 1))
    if "k5_timeout" in SC and n % 1000 == 99:
        time.sleep(0.01)
        raise TimeoutError(110, "Connection timed out")
    if EDM.blob:
        EDM.task(0, (0, (EDM.K << 24) | L.KICK_LOW, EDM.pa2_event(t0)), t0)
    EDM.bump()
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
    out = {"own_arm": rd("own_arm").strip(), "alive": alive(), "rate_hz": tick_rate(), "misc": miscinfo(),
           "health": health()}
    ok = os.path.exists(a["blob"]) and "armfail" not in SC
    if "armdirty" in SC:
        EDM.page[L.CMD] = 5
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
    os.makedirs(outdir, exist_ok=True)
    with open(f"{outdir}/{tag}-own_res.json", "w") as f:
        f.write(json.dumps(EDM.page))
