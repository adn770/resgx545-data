# SPDX-License-Identifier: MIT
"""kmock.py: the part of the R4-events mock laptop that is the session's own: the kicker word, the count byte K of the events under three
readings, what an unbumped kick does under three readings, kick_no_bump, the kicker file, the tasks ring_exit2 (a tick or a kick pass acted
on, ACT 4) and ring_skip3p (the slot 3 end-of-render pass skipped once, ended with the phase end), the fill of e3p as files the fake tool
leaves for the simulated EDM, kregnow clears of CR_EVENT_STATUS.  Nothing here is a model of the hardware: MOCK_SCENARIO switches (comma
separated) make every outcome the scorers must handle:
  stage kb2   default: the count is the commands the EDM consumed (H-CNT) and an unbumped kick is PENDING (H-PEND: no kick entry, the ticks after
              it read pa2 0x...74, USE0_SERV_EVENT bit 16 clear; the next ordinary kick delivers both, two entries, ccbctl 4 4)
              kb_latch (the count is the kicker word as latched at a served kick: H-LATCH)   kb_hwc (a count of CR_EVENT_KICK writes: H-HWC)
              noevent (an unbumped kick raises nothing: H-NOEVENT: pa2 0x...70, bit 16 set, Q4 one entry, ccbctl 4 3)
              late (the unbumped kick is delivered late, inside the ring: H-LATE)   g0_late (the call's kick comes too late: G0P has no
              3 ticks after it: the stage must stop)   nokick_entry (G0P has no kick entry: the timing control fails, the stage must stop)
  stage kp    default H-PHAS-ANY (a kick pass or a tick pass ended with the phase end keeps the tick; the kick is not read: read = write - 1)
              kp_more (the kick pass stops the tick: H-KICK-MORE)   fk_stop (the plain tick pass stops: a control stops)   e0_busy (E0 acts)
              kp_both (KP and, if it runs, KP-r2 stop: the second stop ends the stage)
  stage e3p   default H-PHAS-ANY + H-LEVEL + H-W (the skipped pass keeps the tick, the fill is held, bit 18 holds, CLEAR clears the bits written)
              e3p_more (the skipped pass stops the tick: H-SLOT3-MORE)   e3p_pulse (bit 18 never reads 1)   c_all   c_none (CLEAR clears
              everything / nothing)   no_slot3 (the end-of-render event never comes)   fill_fail (the fake tool's fill fails at once: B0 fails)
"""
import os
import time

import r4layout as L

MOCK = os.environ.get("MOCK_DIR", "")
SC = set(os.environ.get("MOCK_SCENARIO", "").split(","))
K_BLOBS = ("ring_exit2", "ring_skip3p")
BIT18 = 0x40000
CALL_LATENCY = 0.0045        # the mock's own overhead added, the kick lands about 6.5 ms after the call's stamp (E816 G0: 6.70 ms)


def path(n):
    return os.path.join(MOCK, n)


def read_int(n, default=0):
    try:
        return int(open(path(n)).read().strip(), 0)
    except (OSError, ValueError):
        return default


def write(n, v):
    """The mock's files: debugfs knobs live in dbg/, the rest (the fill's files) in the mock directory."""
    p = path("dbg/" + n) if n in ("kick_no_bump", "hold_recovery") else path(n)
    with open(p, "w") as f:
        f.write(str(v))


# ---- the count byte --------------------------------------------------------------------------------------------------------------
def init(e):
    e.W, e.kicks, e.latched, e.no_bump = 0, 0, 0, False
    e.ext_status = 0
    e.pend = False                # an unbumped kick left an event pending (H-PEND): the ticks read pa2 ...74
    e.pend_entry = None           # K of the pending kick (delivered with the next ordinary kick)
    e.late = None                 # (time, K): H-LATE's kick entry
    e.fill_seen = False
    e.q = 0                       # kick passes seen (g0_late)


def k_of(e):
    if "kb_latch" in SC:
        return e.latched & 0xFF
    if "kb_hwc" in SC:
        return e.kicks & 0xFF
    return e.ccb_r & 0xFF          # default H-CNT: the commands the EDM consumed


def boot_reset(e):
    e.W, e.kicks, e.latched, e.no_bump = 0, 0, 0, False
    e.ext_status, e.pend, e.pend_entry, e.late = 0, False, None, None
    e.fill_seen = False
    e.q = 0
    for f in ("fill_start", "fill_done", "e3p_armed"):
        try:
            os.remove(path(f))
        except OSError:
            pass
    write("kick_no_bump", "N")
    write("hold_recovery", "N")


# ---- the debugfs files -------------------------------------------------------------------------------------------------------------
def rd(e, name):
    if name == "kicker":
        return f"kicker {e.W} ccbctl {e.cmds % 256} {e.ccb_r % 256} kicks {e.kicks}\n"
    if name == "kregnow":
        return "0x0814 0x00000000\n0x0a78 0x00000000\n0x0098 0x00000000\n0x0740 0x00000000\n0x0c00 0x00000010\n0x0c04 0x00000000\n"
    return None


def wr(e, name, text):
    """True if handled."""
    if name not in ("kicker", "kick_no_bump", "kregnow", "hold_recovery"):
        return False
    t = text if isinstance(text, str) else text.decode()
    if name == "kicker":
        if not t.startswith("="):
            raise OSError(22, "invalid")
        v = int(t[1:], 0)
        if v > 255:
            raise OSError(22, "invalid")
        e.W = v
        return True
    if name == "kick_no_bump":
        e.no_bump = t.strip() in ("Y", "y", "1")
        write("kick_no_bump", "Y" if e.no_bump else "N")
        return True
    if name == "kregnow":
        off, _, val = t.partition("=")
        off, val = int(off, 16), int(val, 0)
        if off != 0x0134 or val not in L.E3P_CLEAR_VALUES:
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
        return
    was = e.ext_status
    e.ext_status &= ~v
    if was & BIT18 and not e.ext_status & BIT18 and e.alive:
        write("fill_done", "acknowledged")


def status_ext(e):
    """Extra bits of CR_EVENT_STATUS (0x012c) at this moment."""
    return e.ext_status


def bump(e, n=1):
    """The kernel's own commands before the jobs (the boot's GETMISCINFO): one command, one kick, the kicker word bumped."""
    for _ in range(n):
        e.cmds += 1
        e.kicks += 1
        e.W += 1
        e.latched = e.W


# ---- the kick ------------------------------------------------------------------------------------------------------------------------
def kick(e, t, K):
    """One GETMISCINFO's command and kick at time t, K the count before.  Returns True if the EDM read the command (the call is answered)."""
    if not e.alive:
        return False
    pa = (0, (K << 24) | L.KICK_LOW, e.pa2_event(t))
    unbumped = e.no_bump
    e.cmds += 1
    e.kicks += 1
    if unbumped:
        e.no_bump = False
        write("kick_no_bump", "N")
        if "noevent" in SC:
            return False                              # nothing is raised: H-NOEVENT
        if "late" in SC:
            e.late = (t + 0.004, K)                   # H-LATE: delivered inside the ring, never answered
            return False
        e.pend, e.pend_entry = True, K                # H-PEND: an event pending that never reaches our task
        return False
    e.W += 1
    if e.blob != "ring_exit2":
        if e.pend:                                    # the pending kick is delivered with this one: two entries
            e.pend = False
            if e.ring_logs(pa):
                e.log(0, (0, (e.pend_entry << 24) | L.KICK_LOW, e.pa2_event(t)), t)
            e.ccb_r = e.cmds
            e.latched = e.W
        elif e.cmds - e.ccb_r > 1:                    # H-NOEVENT: one command a kick event: the older stays
            e.ccb_r += 1
            e.latched = e.W
        else:
            e.ccb_r = e.cmds
            e.latched = e.W
        e.q += 1
        if e.ring_logs(pa) and not ("nokick_entry" in SC and e.q == 2):       # 1 is the arm's own kick
            e.log(0, pa, t)
        return True
    # ring_exit2: the kick pass is acted on when the host asked for it
    served = act_pass(e, t, pa, 0)
    if served:
        e.ccb_r = e.cmds
        e.latched = e.W
    else:
        e.cmds, e.ccb_r = e.cmds, e.ccb_r             # the closed reader never ran: read = write - 1
    return served


# ---- time: the fill's events ---------------------------------------------------------------------------------------------------------
def advance(e, now):
    """The late kick of H-LATE, and the fill of e3p (a file the fake tool leaves): (0, 8) the command, then (3, 4) the end of render."""
    if e.late is not None and now >= e.late[0] and e.alive:
        tt, K = e.late
        e.late = None
        if e.ring_logs((0, (K << 24) | L.KICK_LOW, 0)):
            e.log(0, (0, (K << 24) | L.KICK_LOW, e.pa2_event(tt)), tt)
    if e.fill_seen or not os.path.exists(path("fill_start")):
        return
    t0 = read_int("fill_start_t", 0) / 1e6
    if not e.alive or now < t0:
        return
    e.fill_seen = True
    t = now
    K = k_of(e)
    ev = (0, (K << 24) | L.KICK_LOW, e.pa2_event(t))
    if e.blob == "ring_skip3p":
        if e.ring_logs(ev):
            e.log(0, ev, t)
        e.page[L.PASS] += 1
        if "no_slot3" in SC:
            return
        pa = (0, (k_of(e) << 24) | L.SKIP3_WORD_BIT, e.pa2_event(t + 36 / 1e6))
        ran = skip3p_pass(e, t + 36 / 1e6, pa, 3)
        if ran:
            write("fill_done", "completed")


# ---- the tasks -----------------------------------------------------------------------------------------------------------------------
def act_pass(e, t, pa, slot):
    """ring_exit2.s: the S2 ring and, in slot 0, window 2, the acted pass (KIND 1 a plain tick, 2 a kick) ended with the phase end (ACT 4)."""
    p = e.page
    if slot == 0:
        p[L.A_PASS] += 1
    tick = L.is_plain_tick(pa[0], pa[1])
    kickp = pa[0] == 0 and (pa[1] & L.LOW24) == L.KICK_LOW
    flag, acted = 1, False
    if slot == 0 and p[L.WINDOW] == 2 and p[L.COUNT] > 0 and ((p[L.KIND] == L.KIND_TICK and tick) or (p[L.KIND] == L.KIND_KICK and kickp)):
        acted = True
        p[L.COUNT] -= 1
        p[L.ACTED] += 1
        p[L.ACT_SEEN] = p[L.ACT]
        flag = L.SKIP_FLAG
    if e.ring_logs(pa):
        e.log(slot, pa, t, flag)
    if not acted:
        return True
    if kickp:
        stops = "kp_more" in SC or ("kp_both" in SC)
    else:
        stops = "fk_stop" in SC
    if stops:
        e.stops_seen += 1
        e.stall(t, "ring_exit2 acted pass", 0, 0)
    return False                                       # ended with the phase end (own end): the closed task is not called


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
        if "e3p_pulse" not in SC:
            e.ext_status |= BIT18
        if "e3p_more" in SC:
            e.stall(t, "skipped end-render pass", 0, 0)
        return False
    return True


def pass_(e, t, pa, slot):
    if e.blob == "ring_exit2":
        return act_pass(e, t, pa, slot)
    return skip3p_pass(e, t, pa, slot)
