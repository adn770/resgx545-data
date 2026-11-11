# SPDX-License-Identifier: MIT
"""kmock.py: the part of the R3k mock laptop that is new in the kernel batch: the kicker word and the three hypotheses about the count byte K
(H-KW default, kb_latch, kb_hwc), kick_no_bump, the kicker file, kregnow clears of STATUS2 / EVENT_STATUS, the tasks ring_exit, ring_timer,
pa_write2, strclr, ring_skip3, the loop fill and the fill of e3b as files the fake tool leaves for the simulated EDM.  Nothing here is a model
of the hardware: MOCK_SCENARIO switches (comma separated) make every outcome the scorers must handle:
  R4b fr     ctx5 (FCF stops only after five acted passes since the boot: a block reproduces four: every FCF keeps, H-NOREP by
              context)  ctx_first (FCF stops only under the stage's first arm: block 1 stops, blocks 2 and 3 keep: mixed by context)
              default H-REP (every FCF stops; cont4, FB, FPH keep: as E817)  fcf_keep (every FCF keeps)  fcf_keepN (the N-th FCF keeps)
              fb_stopN (the N-th FB-shaped pass stops: 1 FB, 2 FK1, 3 FK2, 4 FK3)  fph_stop (FPH stops)
  stage f     default H-BOTH (cont4 and the exact replica keep the tick, cfi alone and phas alone stop it)  f_cfi  f_phas  f_any  f_place (the
              replica stops)  f_before (cont4 stops)
  stage t     default H-NOTIMER (ACT 7 keeps the tick, ACT 8 stops it)   t_timer (ACT 8 keeps it)   t_stops (ACT 7 stops it)
  stage kb    default H-KW (K = the kicker word)   kb_latch (K = the word as it was at the last kick)   kb_hwc (K = the count of kicks)
  stage e2b   default H-D (a pa write lands in the alias)   pa_lost   pa_private
  stage e3h/a default H-W (a CLEAR2 write clears the bits written)   c2_all   c2_none   loop_nolatch   kregnow_refused
  stage e3b   default H-STOP3 + H-LEVEL + H-W (the skipped pass stops the tick, bit 18 holds, CLEAR clears the bits written)   e3b_free (the tick
              goes on)   e3b_pulse (bit 18 never reads 1)   c_all   c_none (CLEAR clears everything / nothing)
  k0          tool_diff (the geometry job's picture differs)   defaults_bad (kick_no_bump reads Y)
"""
import gzip
import json
import os
import time

import r4blayout as L

MOCK = os.environ.get("MOCK_DIR", "")
SC = set(os.environ.get("MOCK_SCENARIO", "").split(","))
K_BLOBS = ("ring_exit", "ring_timer", "pa_write2", "strclr", "ring_skip3")
BIT18, BIT29 = 0x40000, 0x20000000


def path(n):
    return os.path.join(MOCK, n)


def read_int(n, default=0):
    try:
        return int(open(path(n)).read().strip(), 0)
    except (OSError, ValueError):
        return default


def write(n, v):
    """The mock's files: debugfs knobs live in dbg/, the rest (status2, the fill's files) in the mock directory."""
    p = path("dbg/" + n) if n in ("kick_no_bump", "hold_recovery") else path(n)
    with open(p, "w") as f:
        f.write(str(v))


# ---- the count byte --------------------------------------------------------------------------------------------------------------
def init(e):
    e.W, e.kicks, e.latched, e.no_bump = 0, 0, 0, False
    e.ext_status, e.bit29_back = 0, None
    e.regs = {"pa2": 0x01061A70, "pa3": 0x04000004, "pa4": 0x00030001, "sa66": 0x01061A70, "sa67": 0x04000004, "sa68": 0x00030001}
    e.fill_seen = False


def k_of(e):
    if "kb_latch" in SC:
        return e.latched & 0xFF
    if "kb_hwc" in SC:
        return e.kicks & 0xFF
    return e.W & 0xFF


def bump(e, n=1):
    for _ in range(n):
        e.cmds += 1
        e.kicks += 1
        if e.no_bump:
            e.no_bump = False
            write("kick_no_bump", "N")
        else:
            e.W += 1
        e.latched = e.W


def boot_reset(e):
    write("acted_since_boot", 0)
    write("boots", read_int("boots") + 1)
    e.W, e.kicks, e.latched, e.no_bump = 0, 0, 0, False
    e.ext_status, e.bit29_back = 0, None
    e.fill_seen = False
    for f in ("fill_start", "fill_done", "e3b_armed"):
        try:
            os.remove(path(f))
        except OSError:
            pass
    write("kick_no_bump", "Y" if "defaults_bad" in SC else "N")
    write("hold_recovery", "N")
    e.regs.update({"pa2": 0x01061A70, "pa3": 0x04000004, "pa4": 0x00030001, "sa66": 0x01061A70, "sa67": 0x04000004, "sa68": 0x00030001})


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
        if not e.alive and False:
            raise OSError(16, "busy")
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
        if "kregnow_refused" in SC:
            raise OSError(1, "not permitted")
        off, _, val = t.partition("=")
        off, val = int(off, 16), int(val, 0)
        if off == 0x0114:
            clear2(e, val)
        elif off == 0x0134:
            clear(e, val)
        else:
            raise OSError(1, "not permitted")
        return True
    if name == "hold_recovery":
        write("hold_recovery", t.strip())
        if t.strip() == "N" and os.path.exists(path("fill_start")) and not os.path.exists(path("fill_done")):
            write("fill_done", "recovered")           # the watchdog's recovery of the held job
        return True
    return False


def clear2(e, v):
    s2 = read_int("status2", 0x400)
    if "c2_all" in SC:
        s2 = 0x400
    elif "c2_none" in SC:
        pass
    else:
        s2 &= ~v | 0x400                        # the bits written, never the idle level
    write("status2", f"0x{s2:x}")


def clear(e, v):
    if "c_none" in SC:
        return
    if "c_all" in SC:
        e.ext_status &= ~BIT18
        e.ext_status &= ~BIT29
        if os.path.exists(path("fill_start")) and not os.path.exists(path("fill_done")) and not e.stalled_by:
            write("fill_done", "cleared")
        return
    was = e.ext_status
    e.ext_status &= ~v
    if v & BIT29 and was & BIT29:
        e.bit29_back = time.monotonic() + 0.002
    if was & BIT18 and not e.ext_status & BIT18 and e.alive:
        write("fill_done", "acknowledged")


def status_ext(e):
    """Extra bits of CR_EVENT_STATUS (0x012c) at this moment."""
    if e.bit29_back is not None and time.monotonic() >= e.bit29_back:
        e.ext_status |= BIT29
        e.bit29_back = None
    return e.ext_status


# ---- time: the fill's events -------------------------------------------------------------------------------------------------------
def advance(e, now):
    """The fill of e3b (a file the fake tool leaves): (0, 8) the command, then (3, 4) the end of render 36 us later."""
    if e.fill_seen or not os.path.exists(path("fill_start")):
        return
    t0 = read_int("fill_start_t", 0) / 1e6
    if not e.alive or now < t0:
        return
    e.fill_seen = True
    t = now
    K = k_of(e)
    ev = (0, (K << 24) | L.KICK_LOW, e.pa2_event(t))
    if e.blob == "ring_skip3":
        if e.ring_logs(ev):
            e.log(0, ev, t)
        e.page[L.PASS] += 1
        pa = (0, (k_of(e) << 24) | L.SKIP3_WORD_BIT, e.pa2_event(t + 36 / 1e6))
        ran = skip3_pass(e, t + 36 / 1e6, pa, 3)
        if ran:
            write("fill_done", "completed")


# ---- the tasks -----------------------------------------------------------------------------------------------------------------------
def act_pass(e, t, pa, slot):
    """ring_exit.s / ring_timer.s: the S2 ring and, in slot 0, window 2, the acted tick pass."""
    p = e.page
    if slot == 0:
        p[L.A_PASS] += 1
    flag, acted = 1, False
    if slot == 0 and p[L.WINDOW] == 2 and p[L.COUNT] > 0 and p[L.KIND] == 1 and L.is_plain_tick(pa[0], pa[1]):
        acted = True
        act = p[L.ACT]
        p[L.COUNT] -= 1
        p[L.ACTED] += 1
        p[L.ACT_SEEN] = act
        flag = L.TAIL_FLAG if act in L.ACT_ENDS_TAIL else L.SKIP_FLAG
    if e.ring_logs(pa):
        e.log(slot, pa, t, flag)
    if not acted:
        return True
    act = p[L.ACT]
    prior = read_int("acted_since_boot")              # R4b context worlds: acted passes since the last boot (reset or arm)
    write("acted_since_boot", prior + 1)
    if act == L.ACT_CONT4:
        stops = "f_before" in SC
    elif act == L.ACT_BOTH:
        n = read_int("both_count") + 1                 # R4b: the n-th acted FB pass (FB, FK1, FK2, FK3): fb_stopN stops that one
        write("both_count", n)
        stops = "f_place" in SC or f"fb_stop{n}" in SC
    elif act == L.ACT_CFI:
        stops = not ("f_cfi" in SC or "f_any" in SC)
        n = read_int("cfi_count") + 1                  # R4b: the n-th acted cfi pass of the stage (fcf_keepN: that one keeps the tick)
        write("cfi_count", n)
        if "fcf_keep" in SC or f"fcf_keep{n}" in SC:
            stops = False
        if "ctx5" in SC:                               # the stop needs five acted passes since the boot: a block has four before fcfN
            stops = prior >= 5
        if "ctx_first" in SC:                          # the stop needs the stage's first arm (nothing after it was reset): block 1 only
            stops = read_int("boots") <= 2
    elif act == L.ACT_PHAS:
        stops = "fph_stop" in SC                       # R4b: E817's world (H-PHAS: the phas end keeps the tick); fph_stop: it stops
    elif act == L.ACT_STR_TAIL:
        stops = "t_stops" in SC
    else:                                           # ACT_STR_END
        stops = "t_timer" not in SC
    if stops and (e.stops_seen == 0 or "second_stop" in SC or True):
        e.stops_seen += 1
        e.stall(t, f"act {act}", 0, 0)
    return False


def pa_pass(e, t, pa, slot):
    p = e.page
    p[L.A_PASS] += 1
    cmd = p[L.CMD]
    if cmd == 0:
        return True
    K = k_of(e)
    r = e.regs
    cur = {"pa0": 2, "pa1": K << 24, "pa2": 0x01061A70, "pa3": r["pa3"], "pa4": r["pa4"], "sa64": 2, "sa65": K << 24, "sa66": r["sa66"],
           "sa67": r["sa67"], "sa68": r["sa68"], "sa0": 0x32004000, "timer": e.stamp(t)}
    cur["pa2"] = r["pa2"]
    area = [cur[f] for f in L.PW_FIELDS]
    if cmd == 9:
        p[L.PW_B:L.PW_B + 12] = area
        p[L.CMD], p[L.STATE] = 0, L.STATE_NEXT
        return True
    p[L.PW_A:L.PW_A + 12] = area
    if cmd in (2, 3, 4, 5, 6):
        M = p[L.PW_M]
        off, pa_n, sa_n = L.PW_C_OF[cmd]
        if cmd in (2, 3):                                   # E748: an sa write is read back through the pa
            r[sa_n] = M
            r[pa_n] = M
            p[off], p[off + 1] = r[pa_n], r[sa_n]
        else:                                               # the pa write: the three worlds
            if "pa_lost" in SC:
                pass
            elif "pa_private" in SC:
                r[pa_n] = M
            else:
                r[pa_n] = M
                r[sa_n] = M
            p[off], p[off + 1] = r[pa_n], r[sa_n]
    p[L.ECHO] = p[L.RUNID]
    p[L.CMD], p[L.STATE] = 9, L.STATE_DONE
    return True


def strclr_pass(e, t, pa, slot):
    p = e.page
    if slot == 0:
        p[L.A_PASS] += 1
        if p[L.CMD] == L.SC_CMD_CLEAR2:
            clear2(e, p[L.SC_VAL])
            p[L.ECHO] = p[L.RUNID]
            p[L.CMD], p[L.STATE] = 0, L.STATE_DONE
    return True


def skip3_pass(e, t, pa, slot):
    """ring_skip3.s: the S2 ring; slot 3 skips the first pass of the fill's end of render (flag 3, nop.end); slot 0 takes command 2 (str #77)."""
    p = e.page
    if slot == 0:
        p[L.PASS] += 1
    skip = slot == 3 and p[L.SKIP3] and pa[0] == 0 and (pa[1] & L.LOW24) == L.SKIP3_WORD_BIT
    if e.ring_logs(pa):
        e.log(slot, pa, t, L.SKIP_FLAG if skip else 1)
    if slot == 0 and p[L.CMD] == L.SC_CMD_CLEAR:
        clear(e, p[L.SC_VAL])
        p[L.CMD], p[L.STATE] = 0, L.STATE_DONE
    if skip:
        p[L.SKIP3] = 0
        p[L.SKIPPED] += 1
        if "e3b_pulse" not in SC:
            e.ext_status |= BIT18
        if "e3b_free" not in SC:
            e.ext_status |= BIT29
            e.stall(t, "skipped end-render pass", 0, 0)
        return False
    return True


def pass_(e, t, pa, slot):
    b = e.blob
    if b in ("ring_exit", "ring_timer"):
        return act_pass(e, t, pa, slot)
    if b == "pa_write2":
        return pa_pass(e, t, pa, slot)
    if b == "strclr":
        return strclr_pass(e, t, pa, slot)
    return skip3_pass(e, t, pa, slot)


# ---- the fake tool's files ------------------------------------------------------------------------------------------------------------
def fixture(name):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "fixtures", name)


def gunzip(name):
    with gzip.open(fixture(name), "rb") as f:
        return f.read()
