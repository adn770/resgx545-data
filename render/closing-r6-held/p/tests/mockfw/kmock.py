# SPDX-License-Identifier: MIT
"""kmock.py: the part of the R5-events mock laptop that is the session's own: the timer_clock knob (the period of the next boot), the task
ring_skip3p (the slot 3 end-of-render pass skipped once when the HOST's flag is set in the page, ended with the phase end), the fill as
files the fake tool leaves for the simulated EDM, the 3D lockup check of R-6 as the mock's default world, kregnow clears of
CR_EVENT_STATUS.  Every outcome follows from what the runner WROTE (the knob, the page's skip flag, the CLEAR values, the miscinfo, the
tool's argv), never from a job's name.  Nothing here is a model of the hardware: MOCK_SCENARIO switches (comma separated) make every
outcome the scorers must handle:
  default     H-HWR + H-TICKS + H-LEVEL + H-W + H-STATE: a skipped end-of-render pass leaves the check armed; the 20th slot 0 pass after
              the fill's kick stops the tick with the marks (dword 3 + 1, dword 8 = 1, sw_events + 1, TA3DCtl 57 = 0, 58 = 0xaac267c2);
              bit 18 holds until the host clears it; the host's CLEAR clears the bits written; a clear of bit 18 does not disarm
  time_stop   the stop comes 19.3 ms after the kick whatever the clock (H-TIME)
  ignore_clock the boot ignores timer_clock (25000 units a tick at every clock: the gap controls must void h2 and h3)
  nomark      the stop comes at 20 but without the marks (H-NOMARK: the runner's stop rule ends the session)
  ack18       a host clear of bit 18 before the stop disarms the check (H-ACK18: the tick stays alive in h3)
  phas_any    the skipped pass keeps the tick (no stop at all)
  pulse       bit 18 never reads 1   c_all  c_none (CLEAR clears everything / nothing)
  no_slot3    the end-of-render event never comes   fill_fail (the fake tool's fill fails at once: B0 fails)
  b0_stop     a fill without the skip stops the tick too (a control stops: the stage ends)
  sticky_marks the reset does not rebuild HostCtl (dword 3 and 8 survive it: the arm_marks control must fail)
r6-held part P, the debugfs peek (dbg/peek, the line the r6-kernel prints; 0 at an idle EDM, 2 written by the lockup path: H-R6):
  peek_nowrite  the lockup leaves 0x0694 as it was (H-IDLE)        peek_idle_two  0x0694 reads 2 already at the arm (cannot tell)
  peek_sticky   the reset leaves 0x0694 at 2 (H-RESET refuted)      peek_badfmt    the file prints `reg 0x0694 skip` (the format control)
  peek_enodev   the file cannot be read (the kernel's -ENODEV: the preflight refuses)
"""
import os

import r5layout as L

MOCK = os.environ.get("MOCK_DIR", "")
SC = set(os.environ.get("MOCK_SCENARIO", "").split(","))
K_BLOBS = ("ring_skip3p",)
BIT18 = L.BIT18
SIG3D = 0xAAC267C2
CALL_LATENCY = 0.0045
KNOBS = ("kick_no_bump", "hold_recovery", "timer_clock")


def path(n):
    return os.path.join(MOCK, n)


def read_int(n, default=0):
    try:
        return int(open(path(n)).read().strip(), 0)
    except (OSError, ValueError):
        return default


def write(n, v):
    """The mock's files: debugfs knobs live in dbg/, the rest (the fill's files) in the mock directory."""
    p = path("dbg/" + n) if n in KNOBS else path(n)
    with open(p, "w") as f:
        f.write(str(v))


def clock_knob():
    return read_int("dbg/timer_clock", 0)


PEEK_IDLE = 0


def peek_write(e):
    """The r6-kernel's debugfs peek as a file the runner's `cat` reads: `reg 0x0694 0x%08x` of the mock's CR_DPM_TASK_STATE."""
    p = path("dbg/peek")
    if "peek_enodev" in SC:
        if os.path.exists(p) and not os.access(p, os.W_OK):
            return
        with open(p, "w") as f:
            f.write("")
        os.chmod(p, 0)
        return
    with open(p, "w") as f:
        f.write("reg 0x0694 skip\n" if "peek_badfmt" in SC else f"reg 0x0694 0x{e.dpm:08x}\n")


def init(e):
    e.ext_status = 0
    e.fill_seen = False
    e.armed3d = False             # sa9 bit 0 of R-6: set by the fill's 3D kick, cleared by the closed end-of-render handler
    e.kick_t = None
    e.after_kick = 0              # slot 0 passes after the fill's kick while armed
    e.hc3, e.hc8, e.sw, e.ta57, e.ta58 = 0, 0, 0, 0, 0
    e.dpm = 2 if "peek_idle_two" in SC else PEEK_IDLE
    peek_write(e)


def boot_reset(e):
    e.ext_status = 0
    e.fill_seen = False
    e.armed3d = False
    e.kick_t = None
    e.after_kick = 0
    if "sticky_marks" not in SC:
        e.hc3, e.hc8, e.ta57, e.ta58 = 0, 0, 0, 0       # sgx_fw_build rewrites every buffer at the reset
    e.sw = 0                                         # the kernel's sw_events counter is zeroed at every boot
    if "peek_sticky" not in SC:
        e.dpm = 2 if "peek_idle_two" in SC else PEEK_IDLE
    peek_write(e)
    v = clock_knob()
    e.clock = 0 if "ignore_clock" in SC else v
    for f in ("fill_start", "fill_done", "e3p_armed"):
        try:
            os.remove(path(f))
        except OSError:
            pass
    write("hold_recovery", "N")


def rd(e, name):
    if name == "kregnow":
        return "0x0814 0x00000000\n0x0a78 0x00000000\n0x0098 0x00000000\n0x0740 0x00000000\n0x0c00 0x00000010\n0x0c04 0x00000000\n"
    if name == "timer_clock":
        return L.knob_text(clock_knob()) + "\n"
    return None


def wr(e, name, text):
    """True if handled."""
    if name not in ("kick_no_bump", "kregnow", "hold_recovery", "timer_clock"):
        return False
    t = text if isinstance(text, str) else text.decode()
    if name == "timer_clock":
        v = int(t.strip(), 0)                     # the kernel's x32 file takes any u32; the runner and the guard limit the values
        write("timer_clock", L.knob_text(v))
        return True
    if name == "kick_no_bump":
        write("kick_no_bump", t.strip())
        return True
    if name == "kregnow":
        off, _, val = t.partition("=")
        off, val = int(off, 16), int(val, 0)
        if off != 0x0134 or val not in L.H_CLEAR_VALUES:
            raise OSError(1, "not permitted")            # the mock refuses everything the runner must never write
        clear(e, val)
        return True
    if name == "hold_recovery":
        write("hold_recovery", t.strip())
        if t.strip() == "N" and os.path.exists(path("fill_start")) and not os.path.exists(path("fill_done")):
            write("fill_done", "recovered")           # the watchdog's recovery of the held job
        return True
    return False


def clear(e, v):
    if "c_none" in SC:
        return
    if "c_all" in SC:
        e.ext_status &= ~BIT18
    else:
        e.ext_status &= ~v
    if v == BIT18 and "ack18" in SC and e.alive:
        e.armed3d = False                             # H-ACK18: the acknowledgement ends the check


def status_ext(e):
    return e.ext_status


def lockup(e, t):
    """R-6's lockup path: dword 3 + 1, dword 8 |= 1, SW_EVENT (the kernel counts it), then the wait (the tick stops)."""
    if "nomark" not in SC:
        e.hc3 += 1
        e.hc8 |= 1
        e.sw += 1
        e.ta57, e.ta58 = 0, SIG3D
    if "peek_nowrite" not in SC:
        e.dpm = 2                                     # H-R6: CR_DPM_TASK_STATE = 2 before the poll (E855's [RE] row)
        peek_write(e)
    e.stall(t, "lockup", 0, 0)


def tick(e, t):
    """One slot 0 tick pass while the check is armed: the count of R-6 (i), or the time of H-TIME."""
    if not e.armed3d:
        return
    e.after_kick += 1
    e.ta57 = e.after_kick % L.HWR_RATE
    if "time_stop" in SC:
        if t - e.kick_t >= 0.0193:
            lockup(e, t)
        return
    if e.after_kick == L.LOCKUP_TICKS:
        lockup(e, t)


def advance(e, now):
    """The fill of ring_skip3p (a file the fake tool leaves): the kick in slot 0, then the end of render in slot 3, 36 us later."""
    if e.fill_seen or not os.path.exists(path("fill_start")) or not e.alive:
        return
    e.fill_seen = True
    t = now
    ev = (0, (e.K << 24) | L.KICK_LOW, e.pa2_event(t))
    if e.ring_logs(ev):
        e.log(0, ev, t)
    e.page[L.PASS] += 1
    e.armed3d, e.kick_t, e.after_kick = True, t, 0
    e.cmds += 1
    e.ccb_r = e.cmds
    if "no_slot3" in SC:
        return
    pa = (0, (e.K << 24) | L.SKIP3_WORD_BIT, e.pa2_event(t + 36 / 1e6))
    ran = skip3p_pass(e, t + 36 / 1e6, pa, 3)
    if ran:
        if "b0_stop" not in SC:
            e.armed3d = False                         # the closed handler ends the check (R-6 (iii))
        write("fill_done", "completed")


def skip3p_pass(e, t, pa, slot):
    """ring_skip3p.s: the S2 ring; slot 3 skips the first pass of the fill's end of render (flag 3, ended with the phase end)."""
    p = e.page
    if slot == 0:
        p[L.PASS] += 1
    skip = slot == 3 and p[L.SKIP3] and pa[0] == 0 and (pa[1] & L.LOW24) == L.SKIP3_WORD_BIT
    if e.ring_logs(pa):
        e.log(slot, pa, t, L.SKIP_FLAG if skip else 1)
    if skip:
        p[L.SKIP3] = 0
        p[L.SKIPPED] += 1
        if "pulse" not in SC:
            e.ext_status |= BIT18
        if "phas_any" in SC:
            e.armed3d = False
        return False
    return True


def pass_(e, t, pa, slot):
    r = skip3p_pass(e, t, pa, slot)
    if slot == 0 and L.is_plain_tick(pa[0], pa[1]):
        tick(e, t)
    return r
