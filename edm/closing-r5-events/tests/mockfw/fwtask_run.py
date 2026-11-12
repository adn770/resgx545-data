# SPDX-License-Identifier: MIT
"""A fake of the landed fwtask_run.py for the R5-events mock tests: R4-events' fake (closing4/r4-events/tests/mockfw/fwtask_run.py) cut to
the one task of this session (ring_skip3p) and given the clock knob, the status file's HostCtl and TA3DCtl rows and the regs file's
`skip` lines.  The API is the landed file's (resgx545 main tools/fwtask/fwtask_run.py): dmesg_len() writes a kmsg marker and returns it,
dmesg_new(marker) returns the lines after it, is_bad_log() leaves the reset's info line out, hang_dump() writes NAME-regs.txt,
NAME-status.txt, NAME-own_res.json and NAME-dmesg.txt.

The page, the ticks (HostCtl dword 6 / 399.0 MHz a tick: timer_clock at the boot, E084), CR_TIMER (24.9375 MHz: dword 6 / 16 units a
tick), HostCtl dwords 3, 5, 6, 8, 12, 14, TA3DCtl 28, 57, 58, the CCB offsets, sw_events.  The events are simulated lazily, in time
order, whenever the runner touches the page or the registers.  Every trace line names the job the kernel log's last case marker names
(`[job]`), so the argv-twin test can read what each job applied.  Switches (MOCK_SCENARIO, comma separated): kmock.py's worlds, and
  general   jitter  armfail  gatefail  unhealthy  nofw  fatal@JOB  badlog@JOB  boom@JOB  latebad  toolbad  p3_answers  sig_empty
  (the @JOB switches inject a failure at a job; no outcome of a hypothesis depends on a job's name)
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
import r5layout as L  # noqa: E402
import kmock  # noqa: E402

GATE_TOOL = os.path.join(os.environ.get("MOCK_HOME", MOCK), "sgxfive-test")   # the landed gate's /home/jtorra/...
BAD_LOG = re.compile(r"\b(hung|recovering|BUG|Oops)\b|\bfault\b|page fault", re.I)
RESET_INFO = re.compile(r"\] SGX reset: after the fault clear BIF_FAULT 0x[0-9a-f]+ BIF_INT_STAT 0x[0-9a-f]+$")
NO_MARKER = "(kernel log marker not found: the whole buffer follows)"
LOG_WHOLE = False
TIMER_HZ = L.CORE_HZ / 16
KMSG = os.environ.get("R3_KMSG", os.path.join(MOCK, "kmsg"))
TRACE = os.path.join(MOCK, "trace")
STATUS2 = os.path.join(MOCK, "status2")
IDENT = "[1.0] gma500 0000:00:02.0: [drm] SGX firmware: core 545 rev 0x1000d, DDK 1.7.17 build 862890, answered after 179 us"
SKIP_REGS = (0x0114, 0x0134, 0x0140, 0x0694, 0x0698, 0x069c)


def is_bad_log(line):
    return bool(BAD_LOG.search(line)) and not RESET_INFO.search(line)


class Stop(Exception):
    pass


def current_job():
    try:
        lines = [ln for ln in open(KMSG).read().splitlines() if " case " in ln or " arm clock-back " in ln]
    except OSError:
        return ""
    if not lines:
        return ""
    ln = lines[-1]
    return "clock-back" if " arm clock-back " in ln else ln.split(" case ")[1].split()[0]


def trace(s):
    with open(TRACE, "a") as f:
        f.write(f"{time.monotonic():.6f} [{current_job()}] {s}\n")


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
        self.last = 0
        self.ticks = 0x9d0
        self.dw14 = 0
        self.alive = True
        self.cmds = 2
        self.ccb_r = 2
        self.clock = 0
        self.stalled_by = None
        self.which = None
        kmock.init(self)

    @property
    def period(self):
        return L.eff_clock(self.clock) / L.CORE_HZ

    @property
    def K(self):
        return self.ccb_r & 0xFF

    def stamp(self, t):
        x = (t - self.t0) * TIMER_HZ
        if "jitter" in SC:
            x += ((int(t * 1e4) * 7919) % 6) - 3
        return (int(x) + 0x10000000) & 0xFFFFFFFF

    def pa2_event(self, t):
        since = (t - self.t0) % self.period
        return 0x01000000 | max(1, L.eff_clock(self.clock) - int(since * L.CORE_HZ))

    def stall(self, t, why, r_off=0, dw14=0):
        self.alive = False
        self.stalled_by = why
        self.ccb_r = self.cmds + r_off
        self.dw14 = dw14

    def log(self, slot, pa, t, flag=1):
        p = self.page
        base = L.RING_BASE[slot]
        for j in range(L.RUNGS[slot]):
            o = base + L.RUNG * j
            if p[o] == 0:
                p[o:o + 5] = [flag, pa[0], pa[1], pa[2], self.stamp(t)]
                return True
        p[L.DROP + slot] += 1
        return False

    def ring_logs(self, pa):
        w = self.page[L.WINDOW]
        return w == 2 or (w == 1 and not L.is_plain_tick(pa[0], pa[1]))

    def advance(self, now=None):
        now = time.monotonic() if now is None else now
        if self.alive:
            self.ticks_until(now)              # the ticks up to now first: the fill's kick (kmock.advance) comes after them
        kmock.advance(self, now)

    def ticks_until(self, now):
        k = int((now - self.t0) / self.period)
        for i in range(self.last + 1, k + 1):
            t = self.t0 + i * self.period
            self.last = i
            if self.blob:
                kmock.pass_(self, t, (L.TICK_PA0, self.K << 24, 0x01061A70), 0)
                if not self.alive:
                    return
            self.ticks += 1

    def boot(self):
        open(os.path.join(MOCK, "booted"), "w").write("1")
        self.page = [0] * L.PAGE_DWORDS
        self.page[0] = L.MAGIC
        self.cmds = 1                      # sgxfive_boot's GETMISCINFO
        self.ccb_r = 1
        self.dw14 = 0
        kmock.boot_reset(self)
        self.alive = True
        self.stalled_by = None
        klog(IDENT)
        self.t0 = time.monotonic()
        self.last = 0
        self.blob = None
        if self.arm_line not in ("0", "") and self.has_code:
            self.blob = self.which
        if self.blob == "ring_skip3p":
            open(os.path.join(MOCK, "e3p_armed"), "w").write("1")
        with open(STATUS2, "w") as f:
            f.write("0x400\n")


EDM = Edm()


def emit(obj):
    print(json.dumps(obj, sort_keys=True))
    sys.stdout.flush()


def sig_regs():
    t = time.monotonic()
    timer = 0x01000000 | (int(t * 3e6) % 400000)
    if EDM.alive:
        return {0x0008: 0x20, 0x0b14: 0x10000 | (EDM.ticks + 3) & 0xFFFF, 0x0acc: timer, 0x012c: 0x20000000, 0x0b20: 0x10000}
    if "sig_empty" in SC:
        return {0x0008: 0x20, 0x0b14: 0x10000, 0x0acc: timer, 0x012c: 0x0, 0x0b20: 0x10000}
    return {0x0008: 0x000ccfa0, 0x0b14: 0x422, 0x0acc: timer, 0x012c: 0x20000000, 0x0b20: 0x10000}


def hostctl():
    hc = [0] * 17
    hc[0], hc[3], hc[5], hc[6], hc[8], hc[12], hc[14] = 1, EDM.hc3, L.HWR_RATE, L.eff_clock(EDM.clock), EDM.hc8, EDM.ticks & 0xFFFFFFFF, EDM.dw14
    return hc


def ta3dctl():
    ta = [0] * 59
    ta[57], ta[58] = EDM.ta57, EDM.ta58
    return ta


def rd(name):
    if name == "regs":
        EDM.advance()
        s2 = f"0x{status2_val():08x}"
        sg = sig_regs()
        lines = ["sgxfive regs 1", f"state loaded 1 live 1 sw_events {EDM.sw} bif_faults 0", f"reg 0x0008 0x{sg[0x0008]:08x}",
                 f"reg 0x0118 {s2}", f"reg 0x012c 0x{(sg[0x012c] | kmock.status_ext(EDM)):08x}", "reg 0x0c04 0x00000000",
                 "reg 0x0c08 0x00000000", f"reg 0x0144 0x{EDM.stamp(time.monotonic()):08x}", f"reg 0x0acc 0x{sg[0x0acc]:08x}",
                 f"reg 0x0b14 0x{sg[0x0b14]:08x}", f"reg 0x0b20 0x{sg[0x0b20]:08x}"]
        lines += [f"reg 0x{o:04x} skip" for o in SKIP_REGS]
        lines += [f"hostctl 0x{4 * i:02x} 0x{v:08x}" for i, v in enumerate(hostctl())]
        lines += [f"ta3dctl 0x{4 * i:02x} 0x{v:08x}" for i, v in enumerate(ta3dctl())]
        lines += [f"ccbctl 0x00 0x{EDM.cmds % 256:08x}", f"ccbctl 0x04 0x{EDM.ccb_r % 256:08x}", "end"]
        return "\n".join(lines) + "\n"
    if name == "status":
        EDM.advance()
        sg = sig_regs()

        def rows(tag, words):
            out = []
            for first in range(0, len(words), 8):
                ws = words[first:first + 8]
                out.append(f"{tag}[{first:2d}]: " + " ".join(f"{(v >> (8 * i)) & 0xFF:02x}" for v in ws for i in range(4)))
            return out
        return "\n".join([f"loaded 1 live 1 sw_events {EDM.sw} bif_faults 0 ccb_sent {EDM.cmds} deferred 0",
                          f"reg 0x008 = 0x{sg[0x0008]:08x}", f"reg 0x12c = 0x{(sg[0x012c] | kmock.status_ext(EDM)):08x}",
                          f"reg 0xb14 = 0x{sg[0x0b14]:08x}"] + rows("hostctl", hostctl()) + rows("ta3dctl", ta3dctl())
                         + rows("ccbctl", [EDM.cmds % 256, EDM.ccb_r % 256])) + "\n"
    if name == "own_arm":
        return ("off" if EDM.arm_line in ("0", "") else f"armed {EDM.arm_line}") + "\n"
    k = kmock.rd(EDM, name)
    if k is not None:
        return k
    with open(f"{D}/{name}") as f:
        return f.read()


def wr(name, text):
    trace(f"wr {name} {text if isinstance(text, str) else '<bytes>'}")
    if kmock.wr(EDM, name, text):
        return
    if name == "own_code":
        EDM.has_code = True
        data = text if isinstance(text, bytes) else text.encode()
        info = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bins", "blobs.json")))
        EDM.which = {v["bytes"]: k for k, v in info.items()}.get(len(data))
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
        klog("gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0x0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/0x400")
        klog("gma500 0000:00:02.0: [drm] SGX reset: after the fault clear BIF_FAULT 0x0 BIF_INT_STAT 0x80000")
        return
    with open(f"{D}/{name}", "w") as f:
        f.write(text if isinstance(text, str) else text.decode())


def sh(cmd, check=True):
    if cmd.startswith("modinfo"):
        return os.environ.get("MOCK_SRCV", "MOCKSRCV") + "\n"
    if cmd.startswith("uname"):
        return "7.3.0-mock\n"
    if cmd.startswith("sha256sum"):
        return L.FW_SHA256 + "  /lib/firmware/sgx545_ukernel.fw\n"
    if cmd.startswith("journalctl"):
        extra = ["[2.0] gma500 0000:00:02.0: [drm] SGX: BIF fault at 0x00000000"] if "latebad" in SC else []
        log = full_log()
        starts = [i for i, ln in enumerate(log) if " preflight " in ln]
        return "\n".join((log[starts[-1]:] if starts else log) + extra) + "\n"
    if cmd.startswith("dmesg"):
        return "\n".join(full_log()) + "\n"
    return ""


def full_log():
    try:
        out = open(KMSG).read().splitlines()
    except OSError:
        out = []
    job = current_job()
    if job and f"fatal@{job}" in SC:
        out.append("[1.0] watchdog: BUG: soft lockup - CPU#0 stuck for 22s!")
    if job and f"badlog@{job}" in SC:
        out.append("[1.0] gma500: sgxfive: job 7 hung, recovering")
    return out


def dmesg_len():
    global LOG_WHOLE
    LOG_WHOLE = False
    marker = f"resgx545 fwtask mark {os.getpid()} {time.time_ns()}"
    klog(marker)
    return marker


def dmesg_new(marker):
    global LOG_WHOLE
    lines = full_log()
    at = max((i for i, ln in enumerate(lines) if marker and marker in ln), default=None)
    if at is None:
        LOG_WHOLE = True
        return [NO_MARKER] + lines
    return lines[at + 1:]


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
        if dword == L.SKIP3:
            trace(f"page skip3 {vals[0]}")
        if dword == L.WINDOW:
            trace(f"page window {vals[0]}")
        EDM.page[dword:dword + len(vals)] = [v & 0xFFFFFFFF for v in vals]

    def page(self):
        if f"boom@{current_job()}" in SC:
            raise RuntimeError("mock: an unexpected error while reading the page")
        return self.r(0, L.PAGE_DWORDS)

    def close(self):
        pass


def regs():
    out, hc, _ = L.parse_regs(rd("regs"))
    return out, hc


def alive(window=3, gap=0.02):
    if "nofw" in SC and not os.path.exists(os.path.join(MOCK, "booted")):
        return {"ticks": [0] * window, "advancing": False}
    seen = []
    for _ in range(window):
        seen.append(regs()[1][12])
        time.sleep(gap)
    return {"ticks": seen, "advancing": all(b != a for a, b in zip(seen, seen[1:]))}


def tick_rate(ms=300):
    return (L.CORE_HZ / L.eff_clock(EDM.clock)) * 0.9997 if EDM.alive else 0.0


def health():
    s2 = status2_val()
    return {"event_status2": s2, "bif_int_stat": 0, "faults_status": 0, "ok": s2 == 0x400 and "unhealthy" not in SC}


def miscinfo():
    """One GETMISCINFO: the kick is one slot 0 event carrying the count before it; a stopped EDM never reads it (the kernel's timeout)."""
    t0 = time.monotonic()
    trace("misc")
    EDM.advance()
    time.sleep(kmock.CALL_LATENCY)
    t1 = time.monotonic()
    EDM.advance(t1)
    EDM.cmds += 1
    if EDM.alive:
        pa = (0, (EDM.K << 24) | L.KICK_LOW, EDM.pa2_event(t1))
        if EDM.blob and EDM.ring_logs(pa):
            EDM.log(0, pa, t1)
        EDM.ccb_r = EDM.cmds
    elif "p3_answers" in SC:
        EDM.ccb_r = EDM.cmds
    else:
        time.sleep(0.15)
        raise TimeoutError(110, "Connection timed out")
    klog(IDENT)
    return {"ms": (time.monotonic() - t0) * 1000, "lines": 1, "text": "MISCINFO ok"}


def cmd_arm(a):
    """The landed cmd_arm's statements in the landed order (the mock's primitives do the work), its `ok` with the landed 900-1100 Hz."""
    trace(f"arm {os.path.basename(a['blob'])} {a.get('arm')}")
    n0 = dmesg_len()
    wr("own_arm", "0")
    with open(a["blob"], "rb") as f:
        data = f.read()
    wr("own_code", data)
    if a.get("arm"):
        wr("own_arm", a["arm"])
    wr("load", "1")
    wr("boot", "1")
    out = {"own_arm": rd("own_arm").strip(), "alive": alive(), "rate_hz": tick_rate(), "misc": miscinfo(), "health": health()}
    klog("[1.0] gma500: sgxfive: own task armed: slots 0xf, trc 0 (0: stock), exit 0x1974 (0: unknown) (debugfs own_arm)")
    new = dmesg_new(n0)
    out.update({"magic": EDM.page[0], "log_bad": [ln for ln in new if is_bad_log(ln)], "log": [ln for ln in new if "own" in ln]})
    out["ok"] = (out["alive"]["advancing"] and 900 <= out["rate_hz"] <= 1100 and out["health"]["ok"] and not out["log_bad"]
                 and out["magic"] == 0x4e574f53 and "armfail" not in SC)
    if "toolbad" in SC:
        print("fwtask: FAIL: something the last line does not show")
    emit(out)


def cmd_reset(a):
    trace("reset")
    wr("reset", "1")
    out = {"own_arm": "off", "misc": miscinfo(), "health": health()}
    out["ok"] = bool(out["health"]["ok"])
    emit(out)


def cmd_gate(a):
    trace("gate")
    emit({"ok": "gatefail" not in SC, "fill": "diff: 0 of 2048", "tri": "diff: 0 of 4096"})


def hang_dump(outdir, tag):
    trace(f"dump {tag}")
    os.makedirs(outdir, exist_ok=True)
    for name in ("regs", "status"):
        with open(f"{outdir}/{tag}-{name}.txt", "w") as f:
            f.write(rd(name))
    with open(f"{outdir}/{tag}-own_res.json", "w") as f:
        f.write(json.dumps(EDM.page))
    with open(f"{outdir}/{tag}-dmesg.txt", "w") as f:
        f.write(sh("dmesg"))
