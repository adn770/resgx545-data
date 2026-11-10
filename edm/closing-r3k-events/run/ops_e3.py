# SPDX-License-Identifier: MIT
"""ops_e3.py: the clear-register ops of the R3k runner: `clear_host` (stage e3h), `clear_fw` (stage e3a), `skip3` (stage e3b).  A mixin.

Q166, E3a (stages e3h, e3a): the latch STATUS2 bit 6 (E431, E769: set by a loop of 56 iterations, held through later jobs, never
acknowledged by the firmware).  A round = reset, then the five steps of r3layout.E3_STEPS: the loop fill through the pinned tool
(`probe loop-b16-i56.bin`), wait 1 s, CLEAR2 = bit 15 (a zero bit), CLEAR2 = bit 6, the loop fill again; STATUS2 is read after each step.
e3h writes CLEAR2 by the host (debugfs `kregnow 0x0114=V`, a write-only row of the new module); e3a by the task (strclr.s command 1:
`str #69, rV`, V from the page) with the stock tail calls otherwise.  Only the two values of r3layout.CLEAR2_BITS are ever written.

Q111, E3b (stage e3b, LAST): ring_skip3 armed, hold_recovery Y (b1: the state stays for the host's writes), the host's skip flag (b1: 1,
b0: 0), one fill through the tool in the background; STATUS (reg 0x12c) and STATUS2 read as fast as the debugfs allows for 50 ms; the tick
checked (a skipped end-of-render handler may stop the EDM: H-STOP3; the signature is then taken BEFORE any write); then CLEAR (0x0134) by
the host: bit 15 (a zero bit), bit 18, and after a stop bit 29 (TIMER, the one unacknowledged bit of a stop), each read after; b2 does the
same two values by the task (`str #77`).  hold_recovery is put back to N (read back) before the tool is collected and the stage resets.
"""
import json
import os
import pathlib
import subprocess
import time

import r3layout as L
import fwtask_run as FR
from r3common import Stop


class ClearOps:
    # ---- shared ----------------------------------------------------------------------------------
    def check_clear_host(self, j, spec, row):
        self._check_e3(j, spec, row)

    def check_clear_fw(self, j, spec, row):
        self._check_e3(j, spec, row)

    def _check_e3(self, j, spec, row):
        n = j["name"]
        if [tuple(x) for x in j.get("steps", [])] != [tuple(x) for x in L.E3_STEPS] or j.get("prog") != L.LOOP_PROG:
            raise Stop(7, f"{n}: the steps or the loop program are not the frozen ones")
        vals = [x[1] for x in j["steps"] if x[0] == "clear2"]
        if any(v not in L.CLEAR2_BITS for v in vals):
            raise Stop(7, f"{n}: a CLEAR2 value outside bits 15 and 6")

    def check_skip3(self, j, spec, row):
        n = j["name"]
        if j.get("skip") != spec["skip"] or bool(j.get("fw_clear")) != bool(spec.get("fw_clear")) or j.get("watch_ms") != L.E3B_WATCH_MS:
            raise Stop(7, f"{n}: skip flag, route or watch time outside the allow-list")
        if j.get("clear_values") != [L.CLEAR_BITS[0], L.CLEAR_BITS[1]] or j.get("timer_bit") != L.CLEAR_TIMER_BIT:
            raise Stop(7, f"{n}: the CLEAR values are not the frozen ones")
        if j["skip"] and j.get("hold_recovery") != "Y":
            raise Stop(7, f"{n}: b1 and b2 run with hold_recovery Y")
        if not j["skip"] and j.get("hold_recovery") != "N":
            raise Stop(7, f"{n}: b0 runs with hold_recovery N")

    def knob(self, name, val):
        """Write a debugfs knob and read it back (the read-back is what is recorded)."""
        FR.wr(name, val)
        return FR.rd(name).strip()

    def reg(self, off):
        return FR.regs()[0].get(off)

    def status2(self):
        return self.reg(L.REG_STATUS2_OFF)

    def loop_fill(self, rec, key):
        """One loop fill through the pinned tool (stock or armed firmware): the tool's whole output kept in the record's tail."""
        prog = str(pathlib.Path(__file__).resolve().parent.parent / "bins" / "progs" / f"{L.LOOP_PROG}.bin")
        p = subprocess.Popen([self.tool, "probe", prog], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True)
        try:
            o, _ = p.communicate(timeout=60)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            p.kill()
            o, _ = p.communicate()
            rc = "timeout"
        rec.setdefault("tool", {})[key] = {"rc": rc, "tail": (o or "")[-600:], "bad": [ln[:200] for ln in (o or "").splitlines()
                                                                                        if "FAIL" in ln or "Traceback" in ln]}
        if rc == "timeout":
            rec["timeout"] = True
        return rc

    # ---- e3h, e3a --------------------------------------------------------------------------------
    def clear_round(self, j, rec, route):
        self.pre_reset_arm(j, rec)
        rec["status2_pre"] = self.status2()
        rec["route"] = route
        res = FR.Res() if route == "fw" else None
        self.cur_res = res
        steps = []
        try:
            for i, st in enumerate(j["steps"], 1):
                d = {"step": i, "what": st[0], "arg": st[1] if len(st) > 1 else None, "ok": True}
                if st[0] == "fill":
                    d["rc"] = self.loop_fill(rec, f"step{i}")
                elif st[0] == "wait":
                    time.sleep(st[1])
                elif st[0] == "clear2":
                    if route == "host":
                        try:
                            FR.wr("kregnow", f"0x0114=0x{st[1]:x}")
                        except OSError as e:
                            d["ok"], d["errno"] = False, e.errno
                    else:
                        d.update(self.fw_command(res, L.SC_CMD_CLEAR2, st[1], j["runid"] + i))
                    time.sleep(0.005)
                d["status2"] = self.status2()
                steps.append(d)
            rec["steps"] = steps
            rec["rc"] = 0
        finally:
            if res is not None:
                res.close()
        self.check_tick(rec, "after-round")          # a stop is signed here, before anything else runs

    def fw_command(self, res, cmd, value, runid):
        """strclr.s / ring_skip3.s: the value in the page, the run id, the command; wait (bounded) until the task took it (CMD back to 0)."""
        res.w(L.SC_VAL, value)
        res.w(L.ECHO, 0)
        res.w(L.STATE, 0)
        res.w(L.RUNID, runid)
        res.w(L.CMD, cmd)
        t = time.monotonic()
        took = False
        for _ in range(60):
            if res.r(L.CMD)[0] == 0:
                took = True
                break
            time.sleep(0.002)
        return {"ok": took, "task_ms": (time.monotonic() - t) * 1000, "value": value, "cmd_taken": took}

    def clear_host_job(self, j, rec):
        self.clear_round(j, rec, "host")

    def clear_fw_job(self, j, rec):
        self.clear_round(j, rec, "fw")

    def _classify_round(self, j, rec):
        h = rec["health"]
        h_ok = h.get("faults_status", 0) == 0 and ((h.get("bif_int_stat") or 0) & 0xFFFF) == 0
        if rec.get("rc") is None:
            rec["class"] = "void"
        elif not rec["alive"].get("advancing"):
            rec["class"] = "tickstop"
        elif not h_ok or rec["log_bad"] or rec.get("timeout") or any(t["bad"] for t in rec.get("tool", {}).values()):
            rec["class"] = "unhealthy"
        elif any(not s["ok"] for s in rec.get("steps", [])):
            rec["class"] = "void"
            rec["note"] += " a clear write or the task's command did not take"
        else:
            rec["class"] = "ok"
        return True

    classify_clear_host = _classify_round
    classify_clear_fw = _classify_round

    # ---- e3b -------------------------------------------------------------------------------------
    def clear_write(self, route, res, value, runid, rec, key):
        """One CLEAR write by the host (kregnow 0x0134) or the task (str #77), then STATUS and STATUS2 read after 1 and 4 ms."""
        out = {"value": value, "t_ms": round((time.monotonic() - self.t0_mono) * 1000, 2)}
        if route == "host":
            try:
                FR.wr("kregnow", f"0x0134=0x{value:x}")
                out["ok"] = True
            except OSError as e:
                out["ok"], out["errno"] = False, e.errno
        else:
            out.update(self.fw_command(res, L.SC_CMD_CLEAR, value, runid))
        reads = []
        for ms in (1, 3):
            time.sleep(ms / 1000)
            r = FR.regs()[0]
            reads.append({"ms_after": ms, "status": r.get(L.REG_EVENT_STATUS), "status2": r.get(L.REG_STATUS2_OFF)})
        out["reads"] = reads
        rec.setdefault("clears", {})[key] = out
        return out

    def skip3_job(self, j, rec):
        self.pre_reset_arm(j, rec)
        rec["status2_pre"] = self.status2()
        res = FR.Res()
        self.cur_res = res
        proc = None
        route = "fw" if j.get("fw_clear") else "host"
        rec["route"] = route
        try:
            self.ring_clear(res)
            res.w(L.SKIP3, j["skip"])
            rec["knobs"] = {"hold_recovery": self.knob("hold_recovery", j["hold_recovery"])}
            rec["tick_pre"] = FR.alive()
            t0 = time.monotonic()
            self.ring_open(res, 2, rec)
            proc = subprocess.Popen([self.tool, "fill"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True)
            watch = []
            tw = time.monotonic()
            for _ in range(2000):                       # as fast as the debugfs reads go, for the watch time
                ms = (time.monotonic() - tw) * 1000
                r, hc = FR.regs()[0], None
                watch.append([round(ms, 2), r.get(L.REG_EVENT_STATUS), r.get(L.REG_STATUS2_OFF)])
                if ms >= j["watch_ms"]:
                    break
            rec["watch"] = watch
            rec["tool_returned_in_watch"] = proc.poll() is not None
            time.sleep(0.02)
            rec["skipped"] = res.r(L.SKIPPED)[0]
            # the tick after the skip: a stop is signed first (no P3 yet: the writes come before it), then the writes
            rec["no_p3"] = True
            self.check_tick(rec, "after-skip")
            stopped = bool(rec.get("stopped"))
            rec["clears"] = {}
            if j["skip"]:
                for key, v in (("bit15", j["clear_values"][0]), ("bit18", j["clear_values"][1])):
                    self.clear_write(route, res, v, j["runid"] + (1 if key == "bit15" else 2), rec, key)
                if stopped:
                    self.clear_write("host", res, j["timer_bit"], 0, rec, "bit29")
            if stopped:
                self.probe_p3(rec)
            time.sleep(0.01)
            self.ring_close(res, rec, t0)
            rec["rc"] = 0
        finally:
            try:
                rec.setdefault("knobs", {})["hold_recovery_after"] = self.knob("hold_recovery", "N")
            finally:
                res.close()
            if proc is not None:
                try:
                    o, _ = proc.communicate(timeout=6)
                    rec["tool_rc"] = proc.returncode
                except subprocess.TimeoutExpired:
                    proc.kill()
                    o, _ = proc.communicate()
                    rec["tool_rc"] = "timeout"
                rec["tool_out"] = (o or "")[-600:]

    def classify_skip3(self, j, rec):
        if rec.get("rc") is None:
            rec["class"] = "void"
            return True
        if rec.get("knobs", {}).get("hold_recovery_after") != "N":
            rec["class"], rec["note"] = "knob", rec["note"] + " hold_recovery was not put back"
            return True
        if not rec["alive"].get("advancing"):
            rec["class"] = "tickstop"
            return True
        if j["skip"]:
            # the held fault and the watchdog lines are the design: only the tick decides the class (health is read after the reset)
            rec["class"] = "ok"
            return True
        h = rec["health"]
        if not h.get("ok") or rec["log_bad"] or rec.get("tool_rc") != 0:
            rec["class"] = "unhealthy"
        else:
            rec["class"] = "ok"
        return True
