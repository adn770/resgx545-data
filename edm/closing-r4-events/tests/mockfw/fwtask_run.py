# SPDX-License-Identifier: MIT
"""A fake of the landed fwtask_run.py for the R4b mock tests (a copy of R3k-events' fake, moved to the API of the landed file at
resgx545 6421c1c: dmesg_len() writes a kmsg marker and returns it, dmesg_new(marker) returns the lines after it, is_bad_log() leaves the
reset's info line out; and the R4b switches nofw (the firmware is not running until the first reset or arm) and those of kmock.py).

The page, the ticks (997.46 Hz), CR_TIMER (24.9366 MHz), HostCtl dwords 12 (served ticks) and 14 (the assert word), the kernel's
command counter K = the CCB write offset (the byte pa1[31:24] of every event; +1 for each GETMISCINFO) and the EDM's read offset, and
our three tasks as the protocol the runner and the scorer must handle: ring_hold.blob (stage h: the hold, the queue behind it, the
signature inside it), alias2.s (stages c and d: the commands, the reader at the next event, the sa/r/i/p/pclink state, cmd 10, 11, 12),
ring_end.s (stage e: window, KIND, ACT, COUNT, flags 3 and 4, own end, tail call to slot 2).  The events are simulated lazily, in time
order, whenever the runner touches the page or the registers.  Nothing here is a model of the hardware: switches (MOCK_SCENARIO,
comma separated) make every outcome and every stop rule fire:
  stage h   h_rearm              the signature inside the hold is an idle EDM's (H-REARM); default: a running task's (H-NOTENDED)
            h_stop               the hold of H1 stops the tick (a surprise)
  stage c   c_stop_cN            the tick stops after the writer of the row CN (N 1..5) (a surprise)    c_second_stop  the same row again
            c_c5_free            C5's sa64 write does not take the other path (the closed task counts the ticks)
  stage e   e_body               X1 stops the tick (H-BODY; B3 stops too)    e_tickonly   B3 keeps the tick (H-TICKONLY)
            default (H-EXIT): X1 and X20 keep the tick, B3 stops it
  stage d   d_handler            a word with bit 4, 7 or 10 stops it (D1 and D3 stop, D2 keeps it; no assert mark)   d_once  nothing stops
            default (H-CCB): a word with bit 8 stops it with read = write + 1 and dword 14 = 0xad002600 (D2, D3, D4)
  probes    p3_answers           a miscinfo into a stopped EDM is answered (H-REARM)
  stop signature (any stop)   sig_pending (idle, events queued)   sig_empty (idle, nothing queued)   default: E537's busy values
  general   jitter  armfail  gatefail  unhealthy  pre_dirty  fatal@JOB  badlog@JOB  boom@JOB  latebad  a_sa63_persists  toolbad
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
import r4layout as L  # noqa: E402
import kmock  # noqa: E402

GATE_TOOL = os.path.join(os.environ.get("MOCK_HOME", MOCK), "sgxfive-test")   # the landed gate's /home/jtorra/...
BAD_LOG = re.compile(r"\b(hung|recovering|BUG|Oops)\b|\bfault\b|page fault", re.I)
RESET_INFO = re.compile(r"\] SGX reset: after the fault clear BIF_FAULT 0x[0-9a-f]+ BIF_INT_STAT 0x[0-9a-f]+$")
NO_MARKER = "(kernel log marker not found: the whole buffer follows)"
LOG_WHOLE = False


def is_bad_log(line):
    return bool(BAD_LOG.search(line)) and not RESET_INFO.search(line)
PERIOD = L.TICK_UNITS / L.TIMER_HZ        # 25000 CR_TIMER units a tick, 997.46 Hz
KMSG = os.environ.get("R3_KMSG", os.path.join(MOCK, "kmsg"))
TRACE = os.path.join(MOCK, "trace")
STATUS2 = os.path.join(MOCK, "status2")
IDENT = "[1.0] gma500 0000:00:02.0: [drm] SGX firmware: core 545 rev 0x1000d, DDK 1.7.17 build 862890, answered after 179 us"
STOP_ROW = {f"c_stop_c{n}": n for n in range(1, 6)}
HANDLER_BITS = 0x10 | 0x80 | 0x400        # pa1 bits 4, 7, 10: handlers with no job (H-HANDLER)
BIT8 = 0x100


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
        self.ticks = 0x9d0                # HostCtl dword 12: ticks the closed task served
        self.dw14 = 0                     # HostCtl dword 14: the assert word of the routine at 0x0
        self.alive = True
        self.cmds = 2                     # the kernel's CCB write offset
        self.ccb_r = 2                    # the EDM's read offset
        self.sa63 = 0
        self.ent = {"pclink": 0x98, "p": (1, 1, 0, 0)}     # what the next entry sees
        self.regs_ri = [0, 0x3000, 0xB5000020, 0xB5000021]
        self.stops_seen = 0
        self.hold_end = None              # time the hold ends (ring_hold)
        self.queue = []                   # events queued behind the hold: (time, kind, K)
        self.t_stop = None
        self.which = None
        self.stalled_by = None
        self.held_pass = False
        self.row_stops = {}
        kmock.init(self)

    @property
    def K(self):
        return kmock.k_of(self)

    def bump(self, n=1):
        kmock.bump(self, n)

    def stamp(self, t):
        x = (t - self.t0) * L.TIMER_HZ
        if "jitter" in SC:
            x += ((int(t * 1e4) * 7919) % 3000) - 1500
        return (int(x) + 0x10000000) & 0xFFFFFFFF

    def pa2_event(self, t):
        since = (t - self.t0) % PERIOD
        return 0x01000000 | max(1, 400000 - int(since * 16 * L.TIMER_HZ))

    def stall(self, t, why, r_off=0, dw14=0):
        """The tick stops: no further event until the reset.  r_off: read offset - write offset at the stop."""
        self.alive = False
        self.t_stop = t
        self.stalled_by = why
        self.ccb_r = self.cmds + r_off
        self.dw14 = dw14

    # ---- ring plumbing (S2's ring, flag 1 logged, 3 own end, 4 tail) ---------------------------
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
        """One pass of the armed task at time t.  Returns True if the closed task ran (the tick was served), False if not."""
        pa = pa or (L.TICK_PA0, self.K << 24, 0x01061A74 if self.pend else 0x01061A70)
        if self.blob == "alias2":
            return self.alias_pass(t, pa)
        if self.blob in kmock.K_BLOBS:
            return kmock.pass_(self, t, pa, slot)
        if self.blob == "ring_hold":
            return self.hold_pass(t, pa, slot)
        return True

    def word_stops(self, word):
        """Does this sa65 word, left in place for the closed task, stop the tick?  (marks as the world says)"""
        if "d_once" in SC:
            return None
        if "d_handler" in SC:
            return (0, 0) if word & HANDLER_BITS & 0xFFFFFF else None
        return (1, L.ASSERT_WORD) if word & BIT8 else None       # default H-CCB: bit 8 alone

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
        if cmd == L.CMD_RESTORE63:
            self.sa63 = p[L.A_M]
            p[L.WR:L.WR + 9] = [pa[0], pa[1], pa[2], 0, 2, self.K << 24, p[L.A_M], p[L.A_M], 0]
            self.writer_done(p, arm=True)
            return True
        if cmd in (L.CMD_WORD65, L.CMD_E537):
            word = p[L.W65]
            p[L.WR:L.WR + 9] = [pa[0], pa[1], pa[2], self.sa63, 2, self.K << 24, word, word, 0]
            if cmd == L.CMD_E537:
                p[L.WR_X:L.WR_X + 4] = [p[L.A_M], p[L.A_M], p[L.W64], p[L.W64]]
                self.regs_ri = list(p[L.A_RI:L.A_RI + 4])
            self.writer_done(p, arm=True)
            st = self.word_stops(word)
            if st:
                self.stall(t, f"word {word:#x}", st[0], st[1])
                return False
            self.ent = {"pclink": 0x98, "p": (1, 1, 1, 1) if cmd == L.CMD_E537 else (1, 1, 0, 0)}
            return True
        if cmd == L.CMD_RUN64:
            n = p[L.NPASS]
            if n == 0:
                return True
            v = pa[0] & ~2
            p[L.NPASS] = n - 1
            p[L.WR:L.WR + 9] = [pa[0], pa[1], pa[2], self.sa63, 2, self.K << 24, v, v, 0]
            if n - 1 == 0:
                self.writer_done(p, arm=True)
            if "c_c5_free" in SC:
                self.ent = {"pclink": 0x98, "p": (1, 1, 0, 0)}
                return True
            self.ent = {"pclink": 6, "p": (1, 0, 1, 1)}
            return False                  # the other path: the closed task did not count this tick
        # the A rows' commands are not in this session's tables; any other command is a plain tail call
        return True

    def writer_done(self, p, arm):
        p[L.ECHO] = p[L.RUNID]
        p[L.WR_DONE] = p[L.RUNID]
        p[L.CMD] = L.CMD_READ
        p[L.STATE] = L.STATE_DONE
        row = current_job()
        n = None
        for k, v in STOP_ROW.items():
            if k in SC and row.startswith(f"c{v}") and (self.stops_seen == 0 or "c_second_stop" in SC):
                n = v
        if n:
            self.stops_seen += 1
            self.stall_next = True

    def end_pass(self, t, pa, slot):
        """ring_end.s: the S2 ring, and in slot 0, window 2: the pass of the wanted KIND is acted on while COUNT > 0."""
        p = self.page
        if slot == 0:
            p[L.A_PASS] += 1
        flag = 1
        acted = False
        if slot == 0 and p[L.WINDOW] == 2 and p[L.COUNT] > 0:
            kind, act = p[L.KIND], p[L.ACT]
            tick = L.is_plain_tick(pa[0], pa[1])
            kick = pa[0] == 0 and (pa[1] & L.LOW24) == L.KICK_LOW
            if (kind == 1 and tick) or (kind == 2 and kick):
                acted = True
                p[L.COUNT] -= 1
                p[L.ACTED] += 1
                flag = L.TAIL_FLAG if act == 2 else L.SKIP_FLAG
        if self.ring_logs(pa):
            self.log(slot, pa, t, flag)
        if not acted:
            return True
        act = p[L.ACT]
        kick = pa[0] == 0
        if act == 1:                                  # own end: nop.end, the closed task is not called
            if kick and "e_tickonly" not in SC:
                self.stall(t, "own end on a kick pass", 0, 0)       # B3: the kick (bumped after this) was never read: read = write - 1
            elif not kick and "e_body" in SC:
                self.stall(t, "own end on a tick pass", 0, 0)
            return False
        # act 2: the closed task of slot 2: no group bit: it ends without serving the tick
        if "e_body" in SC and not kick and (self.stops_seen == 0 or "c_second_stop" in SC):
            self.stops_seen += 1
            self.stall(t, "tail call to slot 2", 0, 0)
        return False

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
            self.held_pass = True
            if "h_stop" in SC and self.stops_seen == 0:
                self.stops_seen += 1
                self.stall(t, "hold", 0, 0)
            return False                              # the held pass is served when the hold ends
        return True

    # ---- time ------------------------------------------------------------------------------------
    def flush_hold(self):
        """The hold's exit: the held pass is served, the queued events run back to back 140 units apart, then the task ends done."""
        p = self.page
        t = self.hold_end
        p[L.ECHO] = p[L.RUNID]
        p[L.CMD] = 0
        p[L.STATE] = L.STATE_DONE
        self.hold_end = None
        if self.held_pass:
            self.ticks += 1
            self.held_pass = False
        step = 140 / L.TIMER_HZ
        i = 0
        for (_, kind, K) in self.queue:
            i += 1
            tt = t + i * step
            if kind == "tick":
                self.log(0, (L.TICK_PA0, K << 24, 0x01061A74), tt)
                p[L.PASS] += 1
                self.ticks += 1
            else:
                self.log(0, (0, (K << 24) | L.KICK_LOW, self.pa2_event(tt)), tt)
        self.queue = []

    def advance(self, now=None):
        now = time.monotonic() if now is None else now
        kmock.advance(self, now)
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
            if self.blob:
                ran = self.tick_pass(t)
                if not self.alive:
                    return
                if getattr(self, "stall_next", False):
                    self.stall_next = False
                    self.alive = False
                    self.stalled_by = "writer's word"
                    return
                if ran is False:                           # the closed task did not run: HostCtl dword 12 does not count it
                    continue
            self.ticks += 1
        if self.hold_end is not None and now >= self.hold_end:
            self.flush_hold()

    def kick_event(self, t, K):
        """A host kick (GETMISCINFO): pa0 0, pa1 (K << 24) | 0x100 with the count before.  Returns True if the EDM read the command."""
        if self.hold_end is not None and t < self.hold_end:
            self.cmds += 1
            self.kicks += 1
            self.W += 1
            self.queue.append((t, "kick", K))
            return True
        return kmock.kick(self, t, K)

    def boot(self):
        open(os.path.join(MOCK, "booted"), "w").write("1")
        self.page = [0] * L.PAGE_DWORDS
        self.page[0] = L.MAGIC
        self.cmds = 0
        self.ccb_r = 0
        self.dw14 = 0
        kmock.boot_reset(self)
        self.alive = True
        self.stalled_by = None
        self.stall_next = False
        self.bump()                        # sgxfive_boot's GETMISCINFO (sgxfive_ident_ask)
        self.ccb_r = self.cmds
        klog(IDENT)
        self.t0 = time.monotonic()
        self.last = 0
        self.hold_end = None
        self.held_pass = False
        self.queue = []
        self.ent = {"pclink": 0x98, "p": (1, 1, 0, 0)}
        self.blob = None
        if self.arm_line not in ("0", "") and self.has_code:
            self.blob = self.which
        if "a_sa63_persists" not in SC:
            self.sa63 = 0
        if self.blob == "ring_skip3p":
            open(os.path.join(MOCK, "e3p_armed"), "w").write("1")
        with open(STATUS2, "w") as f:
            f.write("0x440\n" if "pre_dirty" in SC else "0x400\n")


EDM = Edm()


# ---- the landed names -----------------------------------------------------------------------
def emit(obj):
    print(json.dumps(obj, sort_keys=True))
    sys.stdout.flush()


def sig_regs():
    """The registers of E537's stop signature (the busy values), the scenario's idle ones, or a running EDM's.  Inside a hold a
    running task looks busy (H-NOTENDED) unless h_rearm."""
    t = time.monotonic()
    if EDM.alive:
        holding = EDM.hold_end is not None and t < EDM.hold_end
        if holding and "h_rearm" not in SC:
            return {0x0008: 0x000ccfa0, 0x0b14: 0x9e0, 0x0acc: 0x01000000 | (int(t * 3e6) % 400000), 0x012c: 0x20000000, 0x0b20: 0x10000}
        return {0x0008: 0x20, 0x0b14: (0 if EDM.pend else 0x10000) | (EDM.ticks + 3) & 0xFFFF, 0x0acc: 0x01000000 | (int(t * 3e6) % 400000),
                0x012c: 0x20000000, 0x0b20: 0x10000}
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
                 f"reg 0x0118 {s2}", f"reg 0x012c 0x{(sg[0x012c] | kmock.status_ext(EDM)):08x}", "reg 0x0c04 0x00000000", "reg 0x0c08 0x00000000",
                 f"reg 0x0144 0x{EDM.stamp(time.monotonic()):08x}", f"reg 0x0acc 0x{sg[0x0acc]:08x}",
                 f"reg 0x0b14 0x{sg[0x0b14]:08x}", f"reg 0x0b20 0x{sg[0x0b20]:08x}",
                 f"hostctl 0x30 0x{EDM.ticks & 0xFFFFFFFF:08x}", f"hostctl 0x38 0x{EDM.dw14:08x}",
                 f"ccbctl 0x00 0x{EDM.cmds % 256:08x}", f"ccbctl 0x04 0x{EDM.ccb_r % 256:08x}", "end"]
        return "\n".join(lines) + "\n"
    if name == "status":
        EDM.advance()
        sg = sig_regs()

        def row(first, dwords):
            return f"[{first:2d}]: " + " ".join(f"{(v >> (8 * i)) & 0xFF:02x}" for v in dwords for i in range(4))
        hc = [0] * 17
        hc[12], hc[14] = EDM.ticks & 0xFFFFFFFF, EDM.dw14
        return "\n".join([f"loaded 1 live 1 sw_events 0 bif_faults 0 ccb_sent {EDM.cmds} deferred 0",
                          f"reg 0x008 = 0x{sg[0x0008]:08x}", f"reg 0x12c = 0x{sg[0x012c]:08x}", f"reg 0xb14 = 0x{sg[0x0b14]:08x}",
                          "hostctl" + row(0, hc[0:8]), "hostctl" + row(8, hc[8:16]), "hostctl" + row(16, hc[16:17]),
                          "ccbctl" + row(0, [EDM.cmds % 256, EDM.ccb_r % 256])]) + "\n"
    if name == "own_arm":
        return ("off" if EDM.arm_line in ("0", "") else f"armed {EDM.arm_line}") + "\n"
    k = kmock.rd(EDM, name)
    if k is not None:
        EDM.advance()
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
        # the module 230E0EF5's two reset lines (fork 36f3d278): the second names "fault" as a word
        klog("gma500 0000:00:02.0: [drm] SGX reset: BIF_FAULT 0x0 BIF_INT_STAT 0x80000 EVENT_STATUS 0x20000000/0x400")
        klog("gma500 0000:00:02.0: [drm] SGX reset: after the fault clear BIF_FAULT 0x0 BIF_INT_STAT 0x80000")
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
        return os.environ.get("MOCK_SRCV", "MOCKSRCV") + "\n"
    if cmd.startswith("uname"):
        return "7.3.0-mock\n"
    if cmd.startswith("sha256sum"):
        return ("0" * 64 if "fw_other" in SC else L.FW_SHA256) + "  /lib/firmware/sgx545_ukernel.fw\n"
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
    paged = bool(job)
    if paged and f"fatal@{job}" in SC:
        out.append("[1.0] watchdog: BUG: soft lockup - CPU#0 stuck for 22s!")
    if paged and f"badlog@{job}" in SC:
        out.append("[1.0] gma500: sgxfive: job 7 hung, recovering")
    return out


def dmesg_len():
    """As the landed file at 6421c1c: a unique marker line written to the kernel log, returned as the token."""
    global LOG_WHOLE
    LOG_WHOLE = False
    marker = f"resgx545 fwtask mark {os.getpid()} {time.time_ns()}"
    klog(marker)
    return marker


def dmesg_new(marker):
    """As the landed file: the lines after the last occurrence of the marker, else the whole buffer led by NO_MARKER."""
    global LOG_WHOLE
    lines = full_log()
    at = max((i for i, ln in enumerate(lines) if marker and marker in ln), default=None)
    if at is None:
        LOG_WHOLE = True
        trace("dmesg whole buffer")
        return [NO_MARKER] + lines
    return lines[at + 1:]


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
    return 997.4 if EDM.alive else 0.0


def health():
    s2 = status2_val()
    return {"event_status2": s2, "bif_int_stat": 0, "faults_status": 0, "ok": s2 == 0x400 and "unhealthy" not in SC}


def miscinfo():
    """One GETMISCINFO: the call's command reaches the CCB 6.7 ms after the call starts (E816 G0), the kick is one event carrying the count
    before it, the kernel logs one answer line.  The EDM answers if it read the command; a kick it never read (stopped, a pass that ended
    with our own end, an unbumped kick) is the kernel's timeout."""
    t0 = time.monotonic()
    EDM.advance()
    time.sleep(kmock.CALL_LATENCY)
    t1 = time.monotonic()
    EDM.advance(t1)                                  # the ticks up to the kick are served with the count before it, the later ones after
    K = EDM.K
    was_alive = EDM.alive
    if EDM.hold_end is not None and t1 < EDM.hold_end:
        EDM.cmds += 1
        EDM.kicks += 1
        EDM.W += 1
        EDM.queue.append((t1, "kick", K))
        served = True
    else:
        served = kmock.kick(EDM, t1, K)
    if not served and (not was_alive and "p3_answers" in SC):
        served = True
        EDM.ccb_r = EDM.cmds
    if not served:
        time.sleep(0.15)
        EDM.advance()
        raise TimeoutError(110, "Connection timed out")
    klog(IDENT)
    if EDM.hold_end is not None:                       # the answer comes after the hold (S2b: 90 ms)
        time.sleep(max(0.0, EDM.hold_end - time.monotonic()) + 0.002)
        EDM.advance()
    return {"ms": (time.monotonic() - t0) * 1000, "lines": 1, "text": "MISCINFO ok"}


def cmd_arm(a):
    """The landed cmd_arm's statements in the landed order (the mock's primitives do the work)."""
    trace(f"arm {a['blob']} {a.get('arm')}")
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
    ok = os.path.exists(a["blob"]) and "armfail" not in SC
    # the kernel's arm line goes to the log; the landed cmd_arm slices dmesg by a line count, which a full (wrapped) ring buffer
    # keeps constant: on the laptop (2026-11-10, 1880 lines) it returned "log" and "log_bad" empty, as here
    klog(f"[1.0] gma500: sgxfive: own task armed: slots 0xf, trc 0 (0: stock), exit {'0x0' if 'exit0' in SC else '0x1974'} (0: unknown) (debugfs own_arm)")
    if "armbad" in SC:
        klog("[1.0] gma500: sgxfive: job 7 hung, recovering")
    new = dmesg_new(n0)
    out.update({"ok": ok, "magic": EDM.page[0], "log_bad": [ln for ln in new if is_bad_log(ln)], "log": [ln for ln in new if "own" in ln]})
    if "toolbad" in SC:
        print("fwtask: FAIL: something the last line does not show")
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
