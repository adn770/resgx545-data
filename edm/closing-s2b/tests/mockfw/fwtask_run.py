# SPDX-License-Identifier: MIT
"""A fake of the landed fwtask_run.py for the S2 mock tests: the same names, a simulated EDM behind them.

The page, the ticks (997.46 Hz), CR_TIMER (24.9366 MHz), the four PDS #13 slots, our four tasks (ring_e1, ring_hold,
pa_read, pa_write) and the client jobs (written by tests/fake_tool.py to MOCK_DIR/events) are simulated lazily, in
time order, whenever the runner touches the page or the registers.  Nothing here is a model of the hardware: it is
the protocol the runner and the scorer must handle, with switches (MOCK_SCENARIO, comma separated) that make every
gate and every stop rule fire:
  h2            job words in the same-position reading (default: the reversed reading)
  noise         window 1 logs a plain tick with an extra bit (the quiet control fails)
  sa66bad       sa66 is not pa2's word (the E2a gate stays closed)
  noalias       pa3/pa4 do not follow sa67/sa68
  tickstop_on_write  the tick stops after the first sa67 write
  nohold        the slow loop takes no time (the knob does not act)
  never_done    the hold never ends (state stays busy)
  jitter        tick stamps off the 25000 grid
  lost          ticks during a hold are lost (default, S2b: run 3's queue, three latched + one pending, the rest
                dropped); all: every tick held is queued; lost_in_e5c: lost only for the e5c control (ctl90)
  kick_lost     a kick during a hold is lost (miscinfo answers "no MISCINFO_READY")
  fatal@JOB     a watchdog line in the kernel log during JOB;  badlog@JOB: a "hung" line
  knob_stuck    render_pb_pages ignores writes
  armfail       the arm is not healthy;  gatefail: the gate after the stage is not exact
  (review fixes)
  armdirty      the page's CMD reads 5 after the arm
  boom@JOB      reading the page in JOB raises RuntimeError (a non-Stop exception after the arm)
  ringfull      dmesg shows only its last 5 lines (a full ring buffer: a line count stays constant)
  latebad       journalctl -k (the stage's kernel.log) has a "hung, recovering" line no job slice saw
  restore_bad   a write of sa67/sa68 back to its read value lands as another value
  ctl_nosa67    cmd 1 of the job "ctl" leaves area A's sa67 dword unwritten (INITFILL)
  misdispatch   a fill's words are logged by slot 1 (the dispatch control must fail)
  sa66bad_ctl   sa66 reads wrong in the job "ctl" only
  nohold_noevents  the no-hold triangles raise no event
  kick_lost     now also: the miscinfo read raises TimeoutError, as the kernel's seq_file read does
  (S2 run 1, always on) every event's pa1[31:24] is a count K (2 after the arm, +1 a kick); the kick's words are
  pa0 0, pa1 (K << 24) | 0x100, pa2 EVENT_TIMER (0x01, 400000 core clocks counting down from the last tick)
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
import s2layout as L  # noqa: E402

GATE_TOOL = os.path.join(os.environ.get("MOCK_HOME", MOCK), "sgxfive-test")   # the landed gate's /home/jtorra/...
BAD_LOG = re.compile(r"\b(hung|recovering|BUG|Oops)\b|\bfault\b|page fault", re.I)
PERIOD = L.TICK_UNITS / L.TIMER_HZ        # 25000 CR_TIMER units a tick (S2 run 3), 997.46 Hz
KMSG = os.environ.get("S2_KMSG", os.path.join(MOCK, "kmsg"))
TRACE = os.path.join(MOCK, "trace")


class Stop(Exception):
    pass


def trace(s):
    with open(TRACE, "a") as f:
        f.write(f"{time.monotonic():.6f} {s}\n")


def at(flag):
    """True if flag@JOB names the job of the last case marker."""
    job = current_job()
    return any(s == f"{flag}@{job}" for s in SC)


def current_job():
    try:
        lines = [ln for ln in open(KMSG).read().splitlines() if " case " in ln]
    except OSError:
        return ""
    return lines[-1].split(" case ")[1].split()[0] if lines else ""


class Edm:
    def __init__(self):
        self.page = [0] * L.PAGE_DWORDS
        self.page[0] = L.MAGIC
        self.blob = None
        self.t0 = time.monotonic()
        self.last = 0                     # index of the last tick processed
        self.ticks = 0x9d0                # HostCtl dword 12
        self.alive = True
        self.busy_until = None
        self.pending = []                 # events held during a hold
        self.sa = {64: 2, 65: 0x02000000, 66: 0x12345678 if "sa66bad" in SC else L.PA2_CONST, 67: 0x67, 68: 0x68,
                   0: 0x0BA5E000}
        self.processed_events = 0
        self.wrote = False
        self.K = 2                        # pa1[31:24]: 2 after the arm, +1 a kick (S2 run 1)

    def kick_words(self, t):
        """S2 run 1: the kick is pa0 0, pa1 (K << 24) | 0x100, pa2 EVENT_TIMER at t (0x01, 400000 core clocks down
        from the last tick); K goes up by one."""
        since = (t - self.t0) % PERIOD
        low = max(1, 400000 - int(since * 16 * L.TIMER_HZ))
        w = (0, (self.K << 24) | 0x100, 0x01000000 | low)
        self.K += 1
        return w

    def stamp(self, t):
        x = (t - self.t0) * L.TIMER_HZ
        if "jitter" in SC:
            x += ((int(t * 1e4) * 7919) % 3000) - 1500
        return (int(x) + 0x10000000) & 0xFFFFFFFF

    # ---- delivery -------------------------------------------------------------------
    def model(self):
        """S2b mock: the queue run 3 showed (three ticks latched on arrival with pa2 0x01061a74, a fourth pending and
        latched when the drain begins, the rest dropped); 'lost' and 'all' make the cap prediction fail."""
        if "lost" in SC or ("lost_in_e5c" in SC and current_job().startswith("ctl90")):
            return "lost"
        return "all" if "all" in SC else "cap"

    def deliver(self, slot, pa, t, kind):
        if self.busy_until is not None and t < self.busy_until:
            ticks = sum(1 for _, _, k in self.pending if k in ("tick", "tick4"))
            if kind == "tick":
                m = self.model()
                if m == "all" or (m == "cap" and ticks < 3):
                    self.pending.append((slot, (pa[0], pa[1], L.TICKS_QUEUED_PA2), "tick"))
                elif m == "cap" and ticks == 3:
                    self.pending.append((slot, pa, "tick4"))
            elif kind == "kick" and "kick_lost" in SC:
                pass
            else:
                self.pending.append((slot, pa, kind))
            return
        self.task(slot, pa, t)

    def finish_hold(self):
        t = self.busy_until
        self.busy_until = None
        p = self.page
        p[L.HOLD_EXIT] = self.stamp(t)
        p[L.ECHO] = p[L.RUNID]
        p[L.CMD] = 0
        p[L.STATE] = 2
        pend, self.pending = self.pending, []
        first = t + 103 / L.TIMER_HZ                       # run 3: the drain at +103, +240, +380, +530 units
        last_tick = self.t0 + int((t - self.t0) / PERIOD) * PERIOD
        for i, (slot, pa, kind) in enumerate(pend):
            if kind == "tick4":                              # latched when the drain began
                since = (first - last_tick) * 16 * L.TIMER_HZ
                pa = (pa[0], pa[1], 0x01000000 | max(1, L.EVT_RELOAD - int(round(since))))
            self.task(slot, pa, t + (103 + 140 * i) / L.TIMER_HZ)

    def task(self, slot, pa, t):
        p = self.page
        b = self.blob
        if b in ("ring_e1", "ring_hold"):
            if b == "ring_hold":
                p[L.PASS + slot] += 1
                if p[L.STATE] == 1:
                    p[L.OVL + slot] = 1
            w = p[L.WINDOW]
            log = w == 2 or (w == 1 and not L.is_plain_tick(pa[0], pa[1]))
            if log:
                base = L.RING_BASE[slot]
                for j in range(L.RUNGS[slot]):
                    o = base + L.RUNG * j
                    if p[o] == 0:
                        p[o:o + 5] = [1, pa[0], pa[1], pa[2], self.stamp(t)]
                        break
                else:
                    p[L.DROP + slot] += 1
            if b == "ring_hold" and slot == 0 and p[L.CMD] == 1:
                n = p[L.N_ITER]
                # run 3: the loop starts about 66 units after the tick's pass and lasts 1.5 n + 15 units
                entry = t + 66 / L.TIMER_HZ
                dur = 0 if "nohold" in SC else L.hold_units_of(n) / L.TIMER_HZ
                p[L.STATE] = 1
                p[L.HOLD_ENTRY] = self.stamp(entry)
                self.busy_until = entry + (1e6 if "never_done" in SC else dur)
                with open(os.path.join(MOCK, "busy"), "w") as f:
                    f.write(str(self.busy_until))
        elif b in ("pa_read", "pa_write") and slot == 0:
            cmd = p[L.CMD]
            alias = "noalias" not in SC
            job = current_job()
            sa66 = 0x12345678 if "sa66bad_ctl" in SC and job == "ctl" else self.sa[66]
            pa_all = list(pa) + [self.sa[67] if alias else 0x33, self.sa[68] if alias else 0x44]
            area = pa_all + [self.sa[64], self.sa[65], sa66, self.sa[67], self.sa[68], self.sa[0], self.stamp(t)]
            if cmd == 1:
                if "ctl_nosa67" in SC and job == "ctl":
                    area[8] = L.INITFILL
                p[L.AREA_A:L.AREA_A + 12] = area
                p[L.ECHO], p[L.CMD], p[L.STATE] = p[L.RUNID], 9, 2
            elif cmd == 9:
                p[L.AREA_B:L.AREA_B + 12] = area
                p[L.CMD], p[L.STATE] = 0, 3
            elif cmd in (2, 3) and b == "pa_write":
                p[L.AREA_A:L.AREA_A + 12] = area
                n = 67 if cmd == 2 else 68
                self.sa[n] = p[L.MARK]
                if "restore_bad" in SC and current_job().startswith("restore"):
                    self.sa[n] = p[L.MARK] ^ 0x1000
                c = L.AREA_C + 2 * (cmd - 2)
                p[c] = self.sa[n] if alias else pa_all[3 + cmd - 2]
                p[c + 1] = self.sa[n]
                p[L.ECHO], p[L.CMD], p[L.STATE] = p[L.RUNID], 9, 2
                if "tickstop_on_write" in SC:
                    self.alive = False

    def advance(self):
        now = time.monotonic()
        evs = []
        if self.alive:
            k = int((now - self.t0) / PERIOD)
            for i in range(self.last + 1, k + 1):
                pa1 = (self.K << 24) | (0x40 if "noise" in SC and i % 5 == 0 else 0)
                evs.append((self.t0 + i * PERIOD, 0, (L.TICK_PA0, pa1, L.PA2_CONST), "tick"))
            self.last = max(self.last, k)
        try:
            lines = open(os.path.join(MOCK, "events")).read().splitlines()
        except OSError:
            lines = []
        for ln in lines[self.processed_events:]:
            t, kind = ln.split()
            t = float(t)
            if "nohold_noevents" in SC and current_job().startswith("tri-nohold"):
                continue
            for pa in job_words(kind):
                pa = (pa[0], pa[1] | (self.K << 24), pa[2])        # every event carries the count byte (run 1)
                slot = 1 if "misdispatch" in SC and kind == "fill" else L.pds_slot(pa[0], pa[1])
                evs.append((t, slot, pa, "job"))
                t += 30e-6
        self.processed_events = len(lines)
        for t, slot, pa, kind in sorted(evs):
            if self.busy_until is not None and t >= self.busy_until:
                self.finish_hold()
            if self.blob and self.alive:
                self.deliver(slot, pa, t, kind)
            if kind == "tick" and self.alive:
                self.ticks += 1
        if self.busy_until is not None and now >= self.busy_until:
            self.finish_hold()


def job_words(kind):
    """The event words a fake client job raises: the reversed reading (H1) unless h2."""
    st = {"fill": [[18]], "copy": [[14]], "tri64": [[18, 0], [6], [14]], "tri256n3": [[18, 0], [6], [14], [13]],
          "partial": [[18, 0], [6], [14], [13], [1]]}[kind]
    out = []
    for group in st:
        pa1 = 0
        for b in group:
            pa1 |= 1 << (b if "h2" in SC else 22 - b)
        out.append((0, pa1, L.PA2_CONST))
    return out


EDM = Edm()


# ---- the landed names -----------------------------------------------------------------------
def emit(obj):
    print(json.dumps(obj, sort_keys=True))
    sys.stdout.flush()


def rd(name):
    with open(f"{D}/{name}") as f:
        return f.read()


def wr(name, text):
    trace(f"wr {name} {text}")
    if name in ("render_pb_pages", "hold_recovery") and "knob_stuck" in SC and text not in ("N", "0x422"):
        return                                # the write of the job's value is ignored (its restore lands)
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
        return "\n".join(full_log() + extra) + "\n"
    if cmd.strip() == "dmesg":
        return "\n".join(dmesg_lines()) + "\n"
    return ""


def dmesg_lines():
    """What dmesg shows: with ringfull only the last 5 lines (the buffer full: its length no longer grows)."""
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
    if paged and any(s == f"fatal@{job}" for s in SC):     # appears after the job ran, so it is new for the job
        out.append("[1.0] watchdog: BUG: soft lockup - CPU#0 stuck for 22s!")
    if paged and any(s == f"badlog@{job}" for s in SC):
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
    EDM.advance()
    return {0x118: 0x400, 0xc04: 0, 0xb14: 0x10000 | (EDM.ticks + 3) & 0xFFFF,
            0x144: EDM.stamp(time.monotonic())}, {12: EDM.ticks}


def alive(window=3, gap=0.02):
    seen = []
    for _ in range(window):
        seen.append(regs()[1][12])
        time.sleep(gap)
    return {"ticks": seen, "advancing": all(b != a for a, b in zip(seen, seen[1:]))}


def health():
    return {"event_status2": 0x400, "bif_int_stat": 0, "faults_status": 0, "ok": "unhealthy" not in SC}


def miscinfo():
    t0 = time.monotonic()
    EDM.advance()
    with open(os.path.join(MOCK, "events_kick"), "a") as f:
        f.write(f"{t0}\n")
    EDM.deliver(0, EDM.kick_words(t0), t0, "kick")
    text = "MISCINFO ok"
    if EDM.busy_until is not None and t0 < EDM.busy_until:
        if "kick_lost" in SC:
            time.sleep(0.05)
            # the kernel's seq_file read returns -ETIMEDOUT: Python raises, the printed text is lost
            raise TimeoutError(110, "Connection timed out")
        else:
            time.sleep(max(0, EDM.busy_until - time.monotonic()) + 0.0002)
    EDM.advance()
    return {"ms": (time.monotonic() - t0) * 1000, "lines": 1, "text": text}


def cmd_arm(a):
    trace(f"arm {a['blob']} {a.get('arm')}")
    EDM.advance()
    EDM.blob = os.path.basename(a["blob"]).rsplit(".", 1)[0]
    EDM.K = 2                             # a load and boot, then the arm's own miscinfo read (run 1: K = 2)
    ok = os.path.exists(a["blob"]) and "armfail" not in SC
    if "armdirty" in SC:
        EDM.page[L.CMD] = 5
    emit({"ok": ok, "rate_hz": 997.4, "magic": L.MAGIC, "alive": {"advancing": True}, "health": health(),
          "log_bad": []})


def cmd_reset(a):
    trace("reset")
    EDM.blob = None
    EDM.busy_until = None
    EDM.alive = True
    EDM.page = [0] * L.PAGE_DWORDS
    EDM.page[0] = L.MAGIC
    emit({"ok": True, "own_arm": "off"})


def cmd_gate(a):
    trace("gate")
    emit({"ok": "gatefail" not in SC, "fill": "diff: 0 of 2048", "tri": "diff: 0 of 4096"})


def hang_dump(outdir, tag):
    os.makedirs(outdir, exist_ok=True)
    with open(f"{outdir}/{tag}-own_res.json", "w") as f:
        f.write(json.dumps(EDM.page))
