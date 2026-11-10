# SPDX-License-Identifier: MIT
"""A fake of the landed fwtask_run.py for the R3-events mock tests: the same names, a simulated EDM behind them.

The page, the ticks (997.46 Hz), CR_TIMER (24.9366 MHz), HostCtl dword 12, the kernel's command counter K (the byte pa1[31:24] of
every event; +1 for each GETMISCINFO and each xfer_sync kick), and our three tasks as the protocol the runner and the scorer must
handle: alias.s (stage a: the commands, the reader at the next event, the sa/r/i/p/pclink state), ring_skip.s (stage b: window,
SKIP, flag-3 rungs, no closed task on a skipped pass), ring_hold.blob (stage k7: the hold, the queue behind it, the kicks).  The
events are simulated lazily, in time order, whenever the runner touches the page or the registers.  Nothing here is a model of the
hardware: switches (MOCK_SCENARIO, comma separated) make every outcome and every stop rule fire:
  stage a   a_stop_a1 / a_stop_a6 / a_stop_a4 / a_stop_a3   the tick stops after that row's writer (H-63, H-P11, ...)
            a_alias                A4's sa64 write sends the closed task down the other path (next entry pclink 6, p1 0, d12 -1)
            a_noreader             the reader armed by the writer never runs (the tick is kept)
            a_writefail            the sa63 write does not take (read-back differs)
            a_sa63_persists        sa63 survives the debugfs reset (it does not by default)
            a_second_stop          the stop repeats in the same row after the re-arm (a second stop)
            a_a0_differs           the control reads another pclink
  stage b   b_stop                 a skipped pass stops the tick (H-STOP)     b_offgrid   the pass after a skip comes at +2 ticks
  stage k7  k7_merge               the second kick is merged: one entry and the xfer read times out   k7_each (default)
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
import r3layout as L  # noqa: E402

GATE_TOOL = os.path.join(os.environ.get("MOCK_HOME", MOCK), "sgxfive-test")   # the landed gate's /home/jtorra/...
BAD_LOG = re.compile(r"\b(hung|recovering|BUG|Oops)\b|\bfault\b|page fault", re.I)
PERIOD = L.TICK_UNITS / L.TIMER_HZ        # 25000 CR_TIMER units a tick, 997.46 Hz
KMSG = os.environ.get("R3_KMSG", os.path.join(MOCK, "kmsg"))
TRACE = os.path.join(MOCK, "trace")
STATUS2 = os.path.join(MOCK, "status2")
IDENT = "[1.0] gma500 0000:00:02.0: [drm] SGX firmware: core 545 rev 0x1000d, DDK 1.7.17 build 862890, answered after 179 us"
STOP_CMD = {"a_stop_a1": 1, "a_stop_a3": 3, "a_stop_a4": 4, "a_stop_a6": 6}


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
        self.cmds = 2                     # commands the kernel's CCB took since boot
        self.sa63 = 0
        self.persist63 = 0
        self.ent = {"pclink": 0x98, "p": (1, 1, 0, 0)}     # what the next entry sees
        self.regs_ri = [0, 0x3000, 0xB5000020, 0xB5000021]
        self.stops_seen = 0
        self.stop_pending = False
        self.hold_end = None              # time the hold ends (ring_hold)
        self.queue = []                   # events queued behind the hold: (time, kind, K)
        self.t_stop = None
        self.row_stopped = {}
        self.which = None
        self.drop_next = False

    @property
    def K(self):
        return self.cmds % 256

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

    # ---- ring plumbing (S2's ring, flag 1 logged, 3 skipped) -----------------------------------
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

    # ---- the tasks -------------------------------------------------------------------------------
    def tick_pass(self, t, pa=None, slot=0):
        """One pass of the armed task at time t.  Returns True if the closed task ran (the tick was handled)."""
        pa = pa or (L.TICK_PA0, self.K << 24, 0x01061A70)
        if self.blob == "alias":
            return self.alias_pass(t, pa)
        if self.blob == "ring_skip":
            return self.skip_pass(t, pa, slot)
        if self.blob == "ring_hold":
            return self.hold_pass(t, pa, slot)
        return True

    def alias_pass(self, t, pa):
        p = self.page
        p[L.A_PASS] += 1
        cmd = p[L.CMD]
        e = self.ent
        if cmd == 0:
            self.ent = {"pclink": 0x98, "p": (0, e["p"][1], e["p"][2], e["p"][3])}
            return True
        if cmd == L.CMD_READ:
            rd = [e["pclink"], *e["p"], self.regs_ri[0], self.regs_ri[1], self.regs_ri[2], self.regs_ri[3],
                  2, self.K << 24, self.sa63, pa[0], pa[1], pa[2], p[L.A_PASS]]
            p[L.RD:L.RD + 16] = rd
            p[L.ECHO] = p[L.RUNID]
            p[L.CMD] = 0
            p[L.STATE] = L.STATE_DONE
            self.ent = {"pclink": 0x98, "p": (1, 1, 0, 0)}
            return True
        if cmd == L.CMD_A6:
            self.regs_ri = list(p[L.A_RI:L.A_RI + 4])
        before63 = self.sa63
        if cmd in (L.CMD_A1, L.CMD_RESTORE63):
            self.sa63 = p[L.A_M]
            rb = self.sa63 ^ (1 if "a_writefail" in SC and cmd == L.CMD_A1 else 0)
        elif cmd == L.CMD_A3:
            rb = p[L.A_M]
        elif cmd == L.CMD_A2:
            rb = self.K << 24
        elif cmd == L.CMD_A4:
            rb = pa[0] & ~2
        elif cmd == L.CMD_A5:
            rb = pa[0]
        else:
            rb = 0
        if cmd in (L.CMD_A1, L.CMD_A2, L.CMD_A3, L.CMD_A4, L.CMD_A5, L.CMD_RESTORE63):
            written = {L.CMD_A1: p[L.A_M], L.CMD_A2: self.K << 24, L.CMD_A3: p[L.A_M], L.CMD_A4: pa[0] & ~2, L.CMD_A5: pa[0],
                       L.CMD_RESTORE63: p[L.A_M]}[cmd]
            rb2 = (self.K << 24) if cmd == L.CMD_A3 else 0
            p[L.WR:L.WR + 9] = [pa[0], pa[1], pa[2], before63, 2, self.K << 24, written, rb, rb2]
        elif cmd == L.CMD_A6:
            p[L.WR:L.WR + 3] = list(pa)
        p[L.ECHO] = p[L.RUNID]
        p[L.WR_DONE] = p[L.RUNID]
        p[L.CMD] = 0 if "a_noreader" in SC else L.CMD_READ
        p[L.STATE] = L.STATE_DONE
        stop_cmd = [c for k, c in STOP_CMD.items() if k in SC]
        if cmd in stop_cmd and (self.stops_seen == 0 or "a_second_stop" in SC):
            self.stops_seen += 1
            self.alive = False
            self.t_stop = t
            return False
        if cmd == L.CMD_A4 and "a_alias" in SC:
            self.ent = {"pclink": 6, "p": (1, 0, 1, 1)}
            self.skipped_handlers = getattr(self, "skipped_handlers", 0) + 1
            return False                  # the closed task did not count this tick
        self.ent = {"pclink": 0x98, "p": (1, 1, 1, 1) if cmd == L.CMD_A6 else (1, 1, 0, 0)}
        return True

    def skip_pass(self, t, pa, slot):
        p = self.page
        if slot == 0:
            p[L.A_PASS] += 1
        if self.ring_logs(pa):
            flag = 1
            skipping = (slot == 0 and p[L.WINDOW] == 2 and p[L.SKIP] > 0 and L.is_plain_tick(pa[0], pa[1]))
            if skipping:
                flag = L.SKIP_FLAG
            self.log(slot, pa, t, flag)
        else:
            skipping = False
        if skipping:
            p[L.SKIP] -= 1
            p[L.SKIPPED] += 1
            if "b_stop" in SC and (self.stops_seen == 0 or "a_second_stop" in SC):
                self.stops_seen += 1
                self.alive = False
                self.t_stop = t
            elif "b_offgrid" in SC:
                self.drop_next = True
            return False
        return True

    def hold_pass(self, t, pa, slot):
        p = self.page
        p[L.PASS + slot] += 1
        if self.ring_logs(pa):
            self.log(slot, pa, t)
        if slot == 0 and p[L.CMD] == 1:
            n = p[L.N_ITER]
            p[L.STATE] = L.STATE_BUSY
            p[L.HOLD_ENTRY] = self.stamp(t + 67 / L.TIMER_HZ)
            dur = L.hold_units_of(n) / L.TIMER_HZ
            self.hold_end = t + 67 / L.TIMER_HZ + dur
            p[L.HOLD_EXIT] = self.stamp(self.hold_end)
        return True

    # ---- time ------------------------------------------------------------------------------------
    def flush_hold(self):
        """The hold's exit: the queued events run back to back 140 units apart, then the task ends done."""
        p = self.page
        t = self.hold_end
        p[L.ECHO] = p[L.RUNID]
        p[L.CMD] = 0
        p[L.STATE] = L.STATE_DONE
        self.hold_end = None
        step = 140 / L.TIMER_HZ
        i = 0
        for (_, kind, K) in self.queue:
            i += 1
            tt = t + i * step
            if kind == "tick":
                self.log(0, (L.TICK_PA0, K << 24, 0x01061A74), tt)
                self.ticks += 1
            else:
                self.log(0, (0, (K << 24) | L.KICK_LOW, self.pa2_event(tt)), tt)
        self.queue = []

    def advance(self):
        now = time.monotonic()
        if not self.alive:
            return
        k = int((now - self.t0) / PERIOD)
        for i in range(self.last + 1, k + 1):
            t = self.t0 + i * PERIOD
            self.last = i
            if self.hold_end is not None and t >= self.hold_end:
                self.flush_hold()
            if self.hold_end is not None:                  # behind the hold: at most four ticks queue (S2 run 3)
                if sum(1 for q in self.queue if q[1] == "tick") < 4:
                    self.queue.append((t, "tick", self.K))
                continue
            if self.drop_next:
                self.drop_next = False
                continue
            if self.blob:
                ran = self.tick_pass(t)
                if not self.alive:
                    return
                if ran is False:                           # the closed task did not run: HostCtl dword 12 does not count it
                    continue
            self.ticks += 1
        if self.hold_end is not None and now >= self.hold_end:
            self.flush_hold()

    def kick_event(self, t, K):
        """A host kick: pa0 0, pa1 (K << 24) | 0x100 with the value before its bump."""
        if self.hold_end is not None and t < self.hold_end:
            if "k7_merge" in SC and any(q[1] == "kick" for q in self.queue):
                return
            self.queue.append((t, "kick", K))
        elif self.blob in ("ring_skip", "ring_hold"):
            pa = (0, (K << 24) | L.KICK_LOW, self.pa2_event(t))
            if self.ring_logs(pa):
                self.log(0, pa, t)

    def boot(self):
        self.page = [0] * L.PAGE_DWORDS
        self.page[0] = L.MAGIC
        self.cmds = 0
        self.alive = True
        self.bump()                        # sgxfive_boot's GETMISCINFO (sgxfive_ident_ask)
        klog(IDENT)
        self.t0 = time.monotonic()
        self.last = 0
        self.hold_end = None
        self.queue = []
        self.ent = {"pclink": 0x98, "p": (1, 1, 0, 0)}
        self.blob = None
        if self.arm_line not in ("0", "") and self.has_code:
            self.blob = self.which
        if "a_sa63_persists" not in SC:
            self.sa63 = 0
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
    if name == "xfer_sync":
        return xfer_sync()
    with open(f"{D}/{name}") as f:
        return f.read()


def wr(name, text):
    trace(f"wr {name} {text if isinstance(text, str) else '<bytes>'}")
    if name == "own_code":
        EDM.has_code = True
        data = text if isinstance(text, bytes) else text.encode()
        info = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bins", "blobs.json")))
        EDM.which = {v["bytes"]: k for k, v in info.items()}.get(len(data), "ring_hold")
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
    """One GETMISCINFO: the kick is one event carrying the value before its bump; the kernel logs one answer line."""
    t0 = time.monotonic()
    EDM.advance()
    EDM.kick_event(t0, EDM.K)
    EDM.bump()
    klog(IDENT)
    if EDM.hold_end is not None:                       # the answer comes after the hold (S2b: 90 ms)
        time.sleep(max(0.0, EDM.hold_end - time.monotonic()) + 0.002)
        EDM.advance()
    return {"ms": (time.monotonic() - t0) * 1000, "lines": 1, "text": "MISCINFO ok"}


def xfer_sync():
    """The landed xfer_sync: kick 1 now, 50 ms later kick 2, then wait for the SW event; both inside a hold that is long enough."""
    t0 = time.monotonic()
    EDM.advance()
    EDM.kick_event(t0, EDM.K)
    EDM.bump()
    time.sleep(0.05)
    EDM.advance()
    t1 = time.monotonic()
    merged = "k7_merge" in SC and EDM.hold_end is not None
    EDM.kick_event(t1, EDM.K)
    EDM.bump()
    if EDM.hold_end is not None:
        time.sleep(max(0.0, EDM.hold_end - time.monotonic()) + 0.002)
    EDM.advance()
    if merged:
        time.sleep(0.05)
        raise TimeoutError(110, "Connection timed out")
    return "dummy transfer 0: SW_EVENT after 41000 us, completion word already written\nstatus F ok\nsync wait and release correct\n"


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
    ok = os.path.exists(a["blob"]) and "armfail" not in SC
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
