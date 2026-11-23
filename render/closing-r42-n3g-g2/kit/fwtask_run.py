#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""Runs on the laptop (as root, python3 stdlib only): the experiment cycles of phase 11.29 on the
debugfs files of the fork's debug group. The host tool is the watchdog: nothing here lets a
hung EDM go unnoticed (the kernel has no liveness watchdog). Each subcommand prints one JSON
object; the Mac side (run_stage.py) decides what to do next and keeps the data.

Never writes a clock-gate register: the only register writes are `kreg` writes to 0x0814 and
0x0a78 (REGS_WRITABLE below), by name in this file, and the kernel's kreg list refuses the rest.
"""
import glob
import json
import os
import random
import re
import subprocess
import sys
import time

D = "/sys/kernel/debug/dri/0/sgx"
REGS_WRITABLE = {0x0814: "CR_REG_0814", 0x0a78: "CR_PDS_REG_0A78"}
DENY_NAMES = ("CR_CLKGATECTL", "CR_CLKGATECTL2", "CR_CLKGATESTATUS", "CR_CLKGATEOVERRIDE")
PAGE = 4096
CMD, STATE, RUNID, OVERLAP, ECHO = 1, 2, 3, 4, 5
INITFILL = 0xdeadc0de
RESULTS = 0x40
LOG = 16
DONE_MS = 100
BAD_LOG = re.compile(r"\b(hung|recovering|BUG|Oops)\b|\bfault\b|page fault", re.I)
# the module's informational line after a reset (fork 36f3d278); exactly this format, nothing broader
RESET_INFO = re.compile(r"\] SGX reset: after the fault clear BIF_FAULT 0x[0-9a-f]+ BIF_INT_STAT 0x[0-9a-f]+$")
KMSG = os.environ.get("FWTASK_KMSG", "/dev/kmsg")
NO_MARKER = "(kernel log marker not found: the whole buffer follows)"


def is_bad_log(line):
    return bool(BAD_LOG.search(line)) and not RESET_INFO.search(line)


class Stop(Exception):
    pass


LOG_WHOLE = False      # set by dmesg_new when its marker was missing; emit() flags every result then


def emit(obj):
    if LOG_WHOLE:
        obj = dict(obj, log_whole_buffer=True)
    print(json.dumps(obj, sort_keys=True))
    sys.stdout.flush()


def rd(name):
    with open(f"{D}/{name}") as f:
        return f.read()


def wr(name, text):
    fd = os.open(f"{D}/{name}", os.O_WRONLY)
    try:
        os.write(fd, text.encode() if isinstance(text, str) else text)
    finally:
        os.close(fd)


def sh(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode:
        raise Stop(f"{cmd}: rc {r.returncode}: {r.stderr.strip()[:200]}")
    return r.stdout


class Res:
    """own_res: dword reads and writes at offsets of the results page."""

    def __init__(self):
        self.fd = os.open(f"{D}/own_res", os.O_RDWR)

    def r(self, dword, n=1):
        b = os.pread(self.fd, 4 * n, 4 * dword)
        return list(int.from_bytes(b[i:i + 4], "little") for i in range(0, len(b), 4))

    def w(self, dword, vals):
        if isinstance(vals, int):
            vals = [vals]
        os.pwrite(self.fd, b"".join(v.to_bytes(4, "little") for v in vals), 4 * dword)

    def page(self):
        return self.r(0, PAGE // 4)

    def close(self):
        os.close(self.fd)


def regs():
    """regs file: {offset: value} and HostCtl dwords."""
    out, hc = {}, {}
    for line in rd("regs").splitlines():
        m = re.match(r"reg (0x[0-9a-f]+) (0x[0-9a-f]+)$", line)
        if m:
            out[int(m.group(1), 16)] = int(m.group(2), 16)
        m = re.match(r"hostctl (0x[0-9a-f]+) (0x[0-9a-f]+)$", line)
        if m:
            hc[int(m.group(1), 16) // 4] = int(m.group(2), 16)
    return out, hc


def kreg_all():
    out = {}
    for line in rd("kreg").splitlines():
        a, b = line.split()
        out[int(a, 16)] = int(b, 16)
    return out


def kreg_write(off, val):
    if off not in REGS_WRITABLE:
        raise Stop(f"refusing to write register 0x{off:04x}")
    wr("kreg", f"0x{off:04x}=0x{val:x}")


def dmesg_len():
    """Write a unique marker line to the kernel log and return it (the token dmesg_new takes).  Not a
    line count: a full ring buffer keeps its line count constant (seen on the laptop, 2026-11-10)."""
    global LOG_WHOLE
    LOG_WHOLE = False
    marker = f"resgx545 fwtask mark {os.getpid()} {time.time_ns()}"
    try:
        # O_APPEND without a seek: Python's "a" mode seeks, which /dev/kmsg refuses with EINVAL
        fd = os.open(KMSG, os.O_WRONLY | os.O_APPEND)
        try:
            os.write(fd, (marker + "\n").encode())
        finally:
            os.close(fd)
    except OSError:
        return None
    return marker


def dmesg_new(marker):
    """The lines after the last occurrence of the marker; when it is not found (or none could be
    written) the whole buffer, led by a line that says so, never an empty list."""
    lines = sh("dmesg").splitlines()
    at = max((i for i, ln in enumerate(lines) if marker and marker in ln), default=None)
    if at is None:
        global LOG_WHOLE
        LOG_WHOLE = True
        return [NO_MARKER] + lines
    return lines[at + 1:]


def alive(window=3, gap=0.02):
    """HostCtl dword 12 must advance across three reads, USE0_SERV_EVENT must move."""
    seen = []
    for _ in range(window):
        r, hc = regs()
        seen.append((hc.get(12), r.get(0xb14)))
        time.sleep(gap)
    ticks = [s[0] for s in seen]
    ev = [s[1] for s in seen]
    ok = all(b != a for a, b in zip(ticks, ticks[1:]))
    return {"ticks": ticks, "serv_event": ev, "advancing": ok, "serv_moves": len(set(ev)) > 1}


def tick_rate(ms=300):
    r0, h0 = regs()
    t0 = time.monotonic()
    time.sleep(ms / 1000)
    r1, h1 = regs()
    t1 = time.monotonic()
    d = (h1[12] - h0[12]) & 0xffffffff
    return d / (t1 - t0)


def health():
    """EVENT_STATUS2 == 0x400, no BIF fault bits, HostCtl AssertFail (dword 4?) zero, faults 0."""
    r, hc = regs()
    st = rd("status").split()
    faults = int(st[st.index("bif_faults") + 1])
    return {"event_status2": r.get(0x118), "bif_int_stat": r.get(0xc04), "bif_fault": r.get(0xc08),
            "faults_status": faults,
            "ok": r.get(0x118) == 0x400 and (r.get(0xc04, 0) & 0xffff) == 0 and faults == 0}


def health_tool():
    """The health tool: FWTASK_HEALTH_TOOL (the session kit passes its session's pinned tool),
    else the laptop's own build in its home."""
    return os.environ.get("FWTASK_HEALTH_TOOL") or "/home/jtorra/sgxfive-test"


# the gate's orders (round 41, N3f K2): the fill first (the default), or the triangle first
GATE_ORDERS = ("fill,tri", "tri,fill")
# the kernel's devcoredump class (round 41, N3f K3): a recovery reset's error state is
# DEVCD/devcdN/data until it is written to (or five minutes pass), one per device at a time
DEVCD = os.environ.get("FWTASK_DEVCD", "/sys/class/devcoredump")


def devcd_free(path):
    """A write to a devcoredump's data frees it (the kernel's devcoredump)."""
    fd = os.open(path, os.O_WRONLY)
    try:
        os.write(fd, b"1")
    finally:
        os.close(fd)


def devcd_take(path):
    """Every pending devcoredump (DEVCD/devcd*/data, by name): its text saved to `path`, each led by
    a `==== devcdN ====` line, then freed; "devcd: none pending" when there is none. Their names."""
    names = sorted(os.path.basename(os.path.dirname(p))
                   for p in glob.glob(os.path.join(DEVCD, "devcd*", "data")))
    out = []
    for n in names:
        p = os.path.join(DEVCD, n, "data")
        try:
            with open(p, errors="replace") as f:
                text = f.read()
        except OSError as e:        # a dump that went away is itself a result
            text = f"error {e}\n"
        out.append(f"==== {n} ====\n{text}")
        try:
            devcd_free(p)
        except OSError as e:
            out.append(f"(not freed: {e})\n")
    with open(path, "w") as f:
        f.write("".join(out) if out else "devcd: none pending\n")
    return names


def gate(order="fill,tri", outdir=None):
    """fill and triangle on the render node, exact; the stock firmware (own_arm 0). `order` runs the
    triangle first when "tri,fill". With `outdir` (round 41, N3f K2 and K3): each tool's whole
    output (its job: line and stderr) is OUTDIR/gate-fill.txt and gate-tri.txt, every devcoredump
    pending before the tools is saved to devcd-pre.txt and freed, and the one pending after them
    to devcd.txt."""
    if order not in GATE_ORDERS:
        raise ValueError(f"gate order {order!r} is not one of {', '.join(GATE_ORDERS)}")
    t = health_tool()
    out = {"order": order}
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        out["devcd_pre"] = devcd_take(os.path.join(outdir, "devcd-pre.txt"))
    full = {}
    for name in order.split(","):
        full[name] = sh(f"{t} {name} 2>&1", check=False)
        if outdir:
            with open(os.path.join(outdir, f"gate-{name}.txt"), "w") as f:
                f.write(full[name])
    if outdir:
        out["devcd"] = devcd_take(os.path.join(outdir, "devcd.txt"))
    fill = [ln for ln in full["fill"].splitlines() if ln.startswith("diff") or "FAIL" in ln][:3]
    tri = [ln for ln in full["tri"].splitlines()
           if ln.startswith(("diff", "tri 64x64")) or "FAIL" in ln][:4]
    out["fill"], out["tri"] = "\n".join(fill).strip(), "\n".join(tri).strip()
    out["ok"] = ("diff: 0 of 2048" in out["fill"] and "diff: 0 of 4096" in out["tri"]
                 and "FAIL" not in out["fill"] + out["tri"])
    return out


def miscinfo():
    t0 = time.monotonic()
    s = rd("miscinfo")
    return {"ms": (time.monotonic() - t0) * 1000, "lines": len(s.splitlines()), "text": s[:300]}


def boot_up(n0):
    wr("boot", "1")
    time.sleep(0.05)
    a = alive()
    if not (a["advancing"] and health()["ok"]):
        raise Stop("boot: no ticks or unhealthy")
    return a


def cmd_status(_):
    r, hc = regs()
    emit({"status": rd("status").strip(), "own_arm": rd("own_arm").strip() if os.path.exists(f"{D}/own_arm") else None,
          "kreg": {hex(k): hex(v) for k, v in kreg_all().items()}, "alive": alive(), "health": health()})


def cmd_stock(a):
    """stage 1: the deploy check, unarmed: boot state, miscinfo, fill, triangle, faults."""
    n0 = dmesg_len()
    out = {"own_arm": rd("own_arm").strip(), "alive": alive(), "rate_hz": tick_rate(),
           "misc": miscinfo(), "health": health(), "gate": gate()}
    out["log_bad"] = [ln for ln in dmesg_new(n0) if is_bad_log(ln)]
    out["ok"] = (out["alive"]["advancing"] and 900 <= out["rate_hz"] <= 1100 and out["health"]["ok"]
                 and out["gate"]["ok"] and not out["log_bad"] and out["own_arm"].startswith("off"))
    emit(out)


def cmd_arm(a):
    """write own_code, own_arm, load, boot; check ticks, miscinfo and the log."""
    n0 = dmesg_len()
    wr("own_arm", "0")
    with open(a["blob"], "rb") as f:
        data = f.read()
    wr("own_code", data)
    if a.get("arm"):
        wr("own_arm", a["arm"])
    wr("load", "1")
    wr("boot", "1")
    time.sleep(0.1)
    out = {"own_arm": rd("own_arm").strip(), "alive": alive(), "rate_hz": tick_rate(),
           "misc": miscinfo(), "health": health()}
    out["log_bad"] = [ln for ln in dmesg_new(n0) if is_bad_log(ln)]
    out["log"] = [ln for ln in dmesg_new(n0) if "own" in ln]
    res = Res()
    out["magic"] = res.r(0)[0]
    res.close()
    out["ok"] = (out["alive"]["advancing"] and 900 <= out["rate_hz"] <= 1100 and out["health"]["ok"]
                 and not out["log_bad"] and out["magic"] == 0x4e574f53)
    emit(out)


def cmd_reset(a):
    n0 = dmesg_len()
    wr("reset", "1")
    time.sleep(0.2)
    out = {"own_arm": rd("own_arm").strip(), "alive": alive(), "rate_hz": tick_rate(),
           "misc": miscinfo(), "health": health(), "log": dmesg_new(n0)[-6:]}
    out["ok"] = out["alive"]["advancing"] and out["health"]["ok"] and out["own_arm"].startswith("off")
    emit(out)


def cmd_gate(a):
    """{order, outdir} both optional (gate()); another order: ok false, rc 2."""
    try:
        emit(gate(**{k: a[k] for k in ("order", "outdir") if k in a}))
    except ValueError as e:
        emit({"ok": False, "error": str(e)})
        return 2


KICKS = ("miscinfo",)       # a job's kick: the one host command read right after its cmd write
BIF_REGS = (0xc04, 0xc08)   # BIF_INT_STAT, BIF_FAULT: K5's words around each job (round 42)


def bif_read():
    """K5 (round 42, N3g §4): ([BIF_INT_STAT, BIF_FAULT], the HostCtl dwords) of one read of the
    debugfs regs file, or ({"error": why}, None) when it fails: printed only, never a stop."""
    try:
        r, hc = regs()
    except OSError as e:
        return {"error": str(e)}, None
    return [r.get(o) for o in BIF_REGS], hc


def one_cmd(res, n, params, runid, regs_to_set, timeout_ms=DONE_MS, initfill=True, ticks=False,
            extra=(), kick=None):
    """One experiment: initfill, set registers, params, cmd; poll state. Returns the record.
    extra: the other result slots (command numbers) the task fills, initfilled and read too.
    kick "miscinfo" (round 39, N3d K): right after the cmd write, K0 (HostCtl dword 12, cmd and
    the job's slot), then one read of debugfs miscinfo (a GETMISCINFO kick: a non-tick EDM pass,
    E746), its reply or error kept; the poll and its timeout start after it. K5 (round 42, N3g
    §4): the record's bif keeps [BIF_INT_STAT, BIF_FAULT] read right before the cmd write (the
    read ticks takes tk0 from) and right after the poll, {pre, post}; nothing is written."""
    if kick is not None and kick not in KICKS:
        raise ValueError(f"kick {kick!r} is not one of {', '.join(KICKS)}")
    base = RESULTS + 4 * n
    if initfill:
        res.w(base, [INITFILL] * 4)
        for s in extra:
            res.w(RESULTS + 4 * s, [INITFILL] * 4)
    res.w(OVERLAP, 0)
    for off, val in regs_to_set.items():
        kreg_write(int(off), val)
    for k, v in params.items():
        res.w(int(k), v)
    res.w(STATE, 0)
    res.w(RUNID, runid)
    bif_pre, hc0 = bif_read()
    tk0 = (hc0 if hc0 is not None else regs()[1]).get(12) if ticks else None
    t0 = time.monotonic()
    res.w(CMD, n)                      # last: the task sees complete parameters
    k0 = kicked = None
    if kick:
        k0 = {"tick": regs()[1].get(12), "cmd": res.r(CMD)[0], "slot": res.r(base, 4),
              "ms": (time.monotonic() - t0) * 1000}
        try:
            kicked = {"kind": kick, "reply": miscinfo()}
        except OSError as e:            # no MISCINFO_READY (the kernel gives up at 500 ms)
            kicked = {"kind": kick, "reply": {"error": str(e)}}
    tp = time.monotonic()               # the poll's start: the cmd write, or the kick's end
    done = False
    while (time.monotonic() - tp) * 1000 < timeout_ms:
        if res.r(STATE)[0] == 2:
            done = True
            break
    ms = (time.monotonic() - t0) * 1000
    bif_post = bif_read()[0]
    out = {"done": done, "ms": ms, "slot": res.r(base, 4), "echo": res.r(ECHO)[0],
           "cmd_after": res.r(CMD)[0], "overlap": res.r(OVERLAP)[0],
           "bif": {"pre": bif_pre, "post": bif_post}}
    if extra:
        out["slots"] = {str(s): res.r(RESULTS + 4 * s, 4) for s in extra}
    if kick:
        out["k0"], out["kick"] = k0, kicked
    if ticks:
        time.sleep(0.03)
        tk1 = regs()[1].get(12)
        dt = (time.monotonic() - t0) * 1000
        out["ticks"] = (tk1 - tk0) & 0xffffffff
        if kick:
            out["ticks_from_kick"] = (tk1 - k0["tick"]) & 0xffffffff
        out["ticks_expected"] = dt * 0.997
        out["window_ms"] = dt
    return out


def hang_dump(outdir, tag):
    os.makedirs(outdir, exist_ok=True)
    for name in ("regs", "status"):
        try:
            open(f"{outdir}/{tag}-{name}.txt", "w").write(rd(name))
        except Exception as e:      # a dead debugfs file is itself a result
            open(f"{outdir}/{tag}-{name}.txt", "w").write(f"error {e}\n")
    try:
        r = Res()
        open(f"{outdir}/{tag}-own_res.json", "w").write(json.dumps(r.page()))
        r.close()
    except Exception as e:
        open(f"{outdir}/{tag}-own_res.json", "w").write(f"error {e}\n")
    open(f"{outdir}/{tag}-dmesg.txt", "w").write(sh("dmesg | tail -60", check=False))


SLEEP_MAX_MS = 60000


def sleep_before(ms):
    """A job's sleep_ms (round 41, N3f K1: row LC's heal read): one fixed sleep before the job,
    {ms, the HostCtl dword 12 count over it}; None without one."""
    if not ms:
        return None
    t0 = regs()[1].get(12)
    time.sleep(ms / 1000)
    t1 = regs()[1].get(12)
    return {"ms": ms, "ticks": None if t0 is None or t1 is None else (t1 - t0) & 0xffffffff}


def cmd_run(a):
    """A list of experiments: each {n, params, regs, repeat}; stops at the first trigger. A job's
    sleep_ms sleeps before it (sleep_before), its slots are extra result slots (one_cmd)."""
    outdir, name = a["outdir"], a["name"]
    n0 = dmesg_len()
    res = Res()
    keep = {off: kreg_all()[off] for off in REGS_WRITABLE}
    rng = random.Random(a.get("seed", 1))
    jobs = list(a["jobs"])
    if a.get("shuffle"):
        rng.shuffle(jobs)
    records, stop = [], None
    resets = 0
    for i, j in enumerate(jobs):
        sl = j.get("sleep_ms", 0)
        if type(sl) is not int or not 0 <= sl <= SLEEP_MAX_MS:
            stop = f"job {i}: sleep_ms {sl!r} is not a whole number of ms, 0 to {SLEEP_MAX_MS}"
            break
    for i, j in enumerate(jobs if stop is None else ()):
        try:
            slept = sleep_before(j.get("sleep_ms", 0))
            rec = one_cmd(res, j["n"], j.get("params", {}), j.get("runid", i + 1), j.get("regs", {}),
                          j.get("timeout_ms", DONE_MS), ticks=j.get("ticks", False),
                          extra=j.get("slots", ()), kick=j.get("kick"))
            rec["job"] = j
            if slept:
                rec["slept"] = slept
            # host-side proof that a str landed: the register itself, then restore
            now = kreg_all()
            rec["H"] = {hex(k): now[k] for k in REGS_WRITABLE}
            for off, v in keep.items():
                if now[off] != v:
                    kreg_write(off, v)
            back = kreg_all()
            rec["restored"] = all(back[o] == v for o, v in keep.items())
            records.append(rec)
            if not rec["done"]:
                raise Stop(f"no done within {j.get('timeout_ms', DONE_MS)} ms (job {i})")
            if not rec["restored"]:
                raise Stop("register not restored")
            if (i % a.get("check_every", 10)) == 9:
                al = alive()
                h = health()
                bad = [ln for ln in dmesg_new(n0) if is_bad_log(ln)]
                if not al["advancing"]:
                    raise Stop("tick not advancing")
                if not h["ok"]:
                    raise Stop(f"unhealthy {h}")
                if bad:
                    raise Stop(f"kernel log: {bad[:2]}")
        except Stop as e:
            stop = str(e)
            hang_dump(outdir, f"stop{i}")
            break
    res.close()
    out = {"name": name, "records": records, "stop": stop, "n_jobs": len(jobs), "ran": len(records)}
    if stop:
        # the tick after a stop: a frozen one is a hung firmware, and the kit classes a job by the
        # word `hung` in its output (r36-n3 stopped with the tick frozen and was classed a failure)
        try:
            out["alive_at_stop"] = alive()
        except Exception as e:      # a dead debugfs file is itself a result
            out["alive_at_stop"] = {"error": str(e)}
        if out["alive_at_stop"].get("advancing") is False:
            out["stop"] = stop + "; firmware hung: the tick stopped"
    else:
        out["alive"] = alive()
        out["health"] = health()
        out["log_bad"] = [ln for ln in dmesg_new(n0) if is_bad_log(ln)]
        out["kreg_after"] = {hex(k): hex(v) for k, v in kreg_all().items()}
    emit(out)
    return 1 if stop else 0


def wait_cmd_clear(res, ms=DONE_MS):
    t0 = time.monotonic()
    while (time.monotonic() - t0) * 1000 < ms:
        if res.r(CMD)[0] == 0:
            return True
    return False


def state_slots(res):
    return {n: res.r(RESULTS + 4 * n, 4) for n in (2, 3, 4, 5)}


def cmd_pair(a):
    """Item 12 and Q124. Task 1 (cmd 1) writes sa, r, i, p and pclink and arms cmd 2 for the next
    event, ending without the closed task; task 2 (cmd 2) reads. `rounds`: 'first' (the pair),
    'again' (cmd 2 once more, after `gap_ms` of closed ticks), 'fill' (a client fill between)."""
    n0 = dmesg_len()
    res = Res()
    out = {"rounds": []}
    stop = None
    for rd_ in a["rounds"]:
        kind = rd_["kind"]
        for n in (2, 3, 4, 5):
            res.w(RESULTS + 4 * n, [INITFILL] * 4)
        entry = {"kind": kind}
        if kind == "first":
            res.w(STATE, 0)
            res.w(RUNID, rd_.get("runid", 7))
            t0 = time.monotonic()
            res.w(CMD, 1)
            ok1 = False
            while (time.monotonic() - t0) * 1000 < DONE_MS:
                if res.r(STATE)[0] == 2:
                    ok1 = True
                    break
            entry["task1_done"] = ok1
            entry["cmd_after_task1"] = res.r(CMD)[0]
            ok2 = wait_cmd_clear(res)
            entry["task2_done"] = ok2
        else:
            time.sleep(rd_.get("gap_ms", 0) / 1000)
            if kind == "fill":
                entry["fill"] = sh(health_tool() + " fill 2>&1 | grep -E '^diff|FAIL' | head -2", check=False).strip()
            res.w(STATE, 0)
            res.w(CMD, 2)
            entry["task2_done"] = wait_cmd_clear(res)
        entry["slots"] = state_slots(res)
        entry["alive"] = alive()
        out["rounds"].append(entry)
        if not entry["alive"]["advancing"] or not entry.get("task2_done", True):
            stop = f"round {kind}: not alive or no task 2"
            hang_dump(a["outdir"], f"pair-{kind}")
            break
    out["stop"] = stop
    out["log_bad"] = [ln for ln in dmesg_new(n0) if is_bad_log(ln)]
    out["health"] = health()
    res.close()
    emit(out)
    return 1 if stop else 0


RD_SLOTS = (10, 11, 12, 13)          # the reader's result slots (state2.s)
PARAM_SA = 32


def read_slots(res):
    return {n: res.r(RESULTS + 4 * n, 4) for n in RD_SLOTS}


def wait_state(res, want, ms=DONE_MS):
    t0 = time.monotonic()
    while (time.monotonic() - t0) * 1000 < ms:
        if res.r(STATE)[0] == want:
            return (time.monotonic() - t0) * 1000
    return None


def cmd_tailpair(a):
    """Item 12 and Q124 with a writer that tail-calls the closed task (state2.s). `rounds` is a
    list of {kind, ...}: control (reader only, cmd 9), write (cmd 1 with the markers `vals` and
    the predicate flags `pflags`, then the reader the writer arms runs at the next event), gap
    (cmd 9 after gap_ms of closed ticks), fill (a client fill, then cmd 9). Stops at the first
    trigger: no done, tick not advancing, an unhealthy status, a bad log line."""
    n0 = dmesg_len()
    res = Res()
    out = {"rounds": []}
    stop = None
    for k, rd_ in enumerate(a["rounds"]):
        kind = rd_["kind"]
        entry = {"kind": kind, "k": k}
        for n in RD_SLOTS:
            res.w(RESULTS + 4 * n, [INITFILL] * 4)
        res.w(RUNID, rd_.get("runid", 100 + k))
        try:
            if kind == "write":
                res.w(PARAM_SA, rd_["vals"])
                res.w(PARAM_SA + 9, rd_["pflags"])
                if rd_.get("extra"):
                    res.w(PARAM_SA + 13, rd_["extra"])
                res.w(STATE, 0)
                tk0 = regs()[1].get(12)
                t0 = time.monotonic()
                res.w(CMD, rd_.get("cmd", 1))
                entry["writer_ms"] = wait_state(res, 2)
                if entry["writer_ms"] is None:
                    raise Stop("no done from the writer within %d ms" % DONE_MS)
                entry["reader_cleared"] = wait_cmd_clear(res)
                entry["since_ms"] = (time.monotonic() - t0) * 1000
                entry["ticks_during"] = (regs()[1].get(12) - tk0) & 0xffffffff
                if not entry["reader_cleared"]:
                    raise Stop("the next event did not run the reader within %d ms" % DONE_MS)
            else:
                if kind == "gap":
                    time.sleep(rd_.get("gap_ms", 1200) / 1000)
                if kind == "fill":
                    entry["fill"] = sh(health_tool() + " fill 2>&1 | grep -E '^diff|FAIL' | head -2",
                                       check=False).strip()
                res.w(STATE, 0)
                t0 = time.monotonic()
                res.w(CMD, 9)
                entry["reader_cleared"] = wait_cmd_clear(res)
                entry["since_ms"] = (time.monotonic() - t0) * 1000
                if not entry["reader_cleared"]:
                    raise Stop("%s: reader not done within %d ms" % (kind, DONE_MS))
            entry["slots"] = read_slots(res)
            entry["alive"] = alive()
            entry["rate_hz"] = tick_rate(100)
            entry["health"] = health()
            out["rounds"].append(entry)
            if not entry["alive"]["advancing"]:
                raise Stop("tick not advancing after round %d (%s)" % (k, kind))
            if not entry["health"]["ok"]:
                raise Stop("unhealthy after round %d: %s" % (k, entry["health"]))
            bad = [ln for ln in dmesg_new(n0) if is_bad_log(ln)]
            if bad:
                raise Stop("kernel log: %s" % bad[:2])
        except Stop as e:
            stop = str(e)
            entry["stopped"] = stop
            if entry not in out["rounds"]:
                out["rounds"].append(entry)
            hang_dump(a["outdir"], "tailpair-stop%d" % k)
            break
    out["stop"] = stop
    out["log_bad"] = [ln for ln in dmesg_new(n0) if is_bad_log(ln)]
    out["health"] = health()
    res.close()
    emit(out)
    return 1 if stop else 0


def cmd_events(a):
    """Q033: clear the log, cause the event (`trigger` miscinfo or fill), read the log."""
    n0 = dmesg_len()
    res = Res()
    res.w(LOG, [0] * 16)
    quiet = None
    if a.get("quiet_ms"):
        time.sleep(a["quiet_ms"] / 1000)
        quiet = res.r(LOG, 16)
        res.w(LOG, [0] * 16)
    if a["trigger"] == "miscinfo":
        trig = miscinfo()
    elif a["trigger"] == "tri":
        trig = {"tri": sh(health_tool() + " tri 2>&1 | grep -E '^diff|FAIL' | head -2", check=False).strip()}
    else:
        trig = {"fill": sh(health_tool() + " fill 2>&1 | grep -E '^diff|FAIL' | head -2", check=False).strip()}
    time.sleep(0.05)
    log = res.r(LOG, 16)
    res.close()
    out = {"log": log, "quiet_log": quiet, "trigger": trig, "alive": alive(), "health": health(),
           "log_bad": [ln for ln in dmesg_new(n0) if is_bad_log(ln)]}
    out["hit_slots"] = [k for k in range(4) if log[4 * k] == 1]
    emit(out)


def cmd_page(a):
    r = Res()
    p = r.page()
    r.close()
    emit({"page": p})


def cmd_wait_clear(a):
    r = Res()
    r.w(int(a["dword"]), a["vals"])
    r.close()
    emit({"ok": True})


def cmd_sleep_ticks(a):
    t0 = time.monotonic()
    r0, h0 = regs()
    time.sleep(a["ms"] / 1000)
    r1, h1 = regs()
    emit({"ticks": (h1[12] - h0[12]) & 0xffffffff, "s": time.monotonic() - t0})


def main():
    a = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    c = sys.argv[1]
    fn = {"status": cmd_status, "stock": cmd_stock, "arm": cmd_arm, "reset": cmd_reset,
          "gate": cmd_gate, "run": cmd_run, "page": cmd_page, "write": cmd_wait_clear,
          "ticks": cmd_sleep_ticks, "pair": cmd_pair, "events": cmd_events, "tailpair": cmd_tailpair}[c]
    sys.exit(fn(a) or 0)


if __name__ == "__main__":
    main()
