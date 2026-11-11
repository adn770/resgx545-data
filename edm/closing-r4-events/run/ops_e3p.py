# SPDX-License-Identifier: MIT
"""ops_e3p.py: the `skip3p` op of the R4-events runner (stage e3p, LAST).  A mixin of Runner.

Q166 / Q111: ring_skip3p armed (slot 3 skips the fill's end-of-render pass once, B1P, and ends it with the phase end), hold_recovery Y
in B1P (the state stays for the host's writes; B0 runs with N), the host's skip flag (B1P 1, B0 0), one `fill` through the pinned tool in
the background.  The status watch starts only when the page shows the slot 3 entry logged (E823's first read came before the render's end
and voided its frozen rows): a bounded wait on the page (2 ms steps, at most E3P_SLOT3_WAIT_S), then STATUS (reg 0x12c) and STATUS2 read as
fast as the debugfs reads go for 50 ms; the tick checked (a stop is signed FIRST, no P3 yet); then, in B1P, the host's CLEAR by
`kregnow 0x0134=`: bit 15 (a zero bit), read 1 and 3 ms after it, then bit 18, read 1, 3 and 20 ms after it (measured from the write); then P3 if
the tick stopped.  Nothing else is written: no bit 29, no CLEAR2, no firmware `str`.  hold_recovery is put back to N (read back) before the
tool is collected; each B1P (held by design) ends with the debugfs reset, the gate and the health (post_job; handle_stop does it after a stop).
"""
import subprocess
import time

import r4layout as L
import fwtask_run as FR
from r3common import Stop


class Skip3pOps:
    def check_skip3p(self, j, spec, row):
        n = j["name"]
        if j.get("skip") != spec["skip"] or j.get("watch_ms") != L.E3P_WATCH_MS or j.get("slot3_wait_s") != L.E3P_SLOT3_WAIT_S:
            raise Stop(7, f"{n}: skip flag, watch or wait time outside the allow-list")
        if j.get("clear_values") != list(L.E3P_CLEAR_VALUES) or j.get("read_ms") != {k: list(v) for k, v in L.E3P_READ_MS.items()}:
            raise Stop(7, f"{n}: the CLEAR values or the read times are not the frozen ones")
        if j["skip"] and j.get("hold_recovery") != "Y":
            raise Stop(7, f"{n}: B1P runs with hold_recovery Y")
        if not j["skip"] and j.get("hold_recovery") != "N":
            raise Stop(7, f"{n}: B0 runs with hold_recovery N")

    def clear_write(self, value, rec, key, read_ms):
        """One CLEAR write by the host (kregnow 0x0134), then STATUS and STATUS2 read at the given milliseconds after it."""
        out = {"value": value, "t_ms": round((time.monotonic() - self.t0_mono) * 1000, 2)}
        t_w = time.monotonic()
        try:
            FR.wr("kregnow", f"0x0134=0x{value:x}")
            out["ok"] = True
        except OSError as e:
            out["ok"], out["errno"] = False, e.errno
        reads = []
        for ms in read_ms:
            time.sleep(max(0.0, ms / 1000 - (time.monotonic() - t_w)))
            r = FR.regs()[0]
            reads.append({"ms_after": ms, "t_ms": round((time.monotonic() - t_w) * 1000, 2), "status": r.get(L.REG_EVENT_STATUS),
                          "status2": r.get(L.REG_STATUS2_OFF)})
        out["reads"] = reads
        rec.setdefault("clears", {})[key] = out
        return out

    def skip3p_job(self, j, rec):
        self.pre_reset_arm(j, rec)
        rec["status2_pre"] = self.reg(L.REG_STATUS2_OFF)
        res = FR.Res()
        self.cur_res = res
        proc = None
        try:
            self.ring_clear(res)
            res.w(L.SKIP3, j["skip"])
            rec["knobs"] = {"hold_recovery": self.knob("hold_recovery", j["hold_recovery"])}
            rec["tick_pre"] = FR.alive()
            t0 = time.monotonic()
            self.ring_open(res, 2, rec)
            proc = subprocess.Popen([self.tool, "fill"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True)
            # the watch starts when the page shows the slot 3 entry (bounded: 2 ms steps)
            tw0 = time.monotonic()
            seen = False
            for _ in range(int(j["slot3_wait_s"] * 500)):
                if res.r(L.RING_BASE[3])[0]:
                    seen = True
                    break
                time.sleep(0.002)
            rec["slot3_seen"], rec["slot3_wait_ms"] = seen, round((time.monotonic() - tw0) * 1000, 2)
            watch = []
            tw = time.monotonic()
            for _ in range(2000):                       # as fast as the debugfs reads go, for the watch time
                ms = (time.monotonic() - tw) * 1000
                r = FR.regs()[0]
                watch.append([round(ms, 2), r.get(L.REG_EVENT_STATUS), r.get(L.REG_STATUS2_OFF)])
                if ms >= j["watch_ms"]:
                    break
            rec["watch"] = watch
            rec["tool_returned_in_watch"] = proc.poll() is not None
            time.sleep(0.02)
            rec["skipped"] = res.r(L.SKIPPED)[0]
            # the tick after the pass: a stop is signed first (no P3 yet: the writes come before it), then the writes
            rec["no_p3"] = True
            self.check_tick(rec, "after-skip")
            stopped = bool(rec.get("stopped"))
            rec["clears"] = {}
            if j["skip"]:
                for key, v in (("bit15", j["clear_values"][0]), ("bit18", j["clear_values"][1])):
                    self.clear_write(v, rec, key, j["read_ms"][key])
            if stopped:
                self.probe_p3(rec)
            time.sleep(0.01)
            self.ring_close(res, rec, t0)
            rec["rc"] = 0
        finally:
            try:
                rec.setdefault("knobs", {})["hold_recovery_after"] = self.knob("hold_recovery", "N")
                self.knobs_written.pop("hold_recovery", None)
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

    def classify_skip3p(self, j, rec):
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
            # the held job and its watchdog lines are the design: only the tick decides the class (health is read after the reset)
            rec["class"] = "ok"
            return True
        h = rec["health"]
        if not h.get("ok") or rec["log_bad"] or rec.get("tool_rc") != 0:
            rec["class"] = "unhealthy"
        else:
            rec["class"] = "ok"
        return True

    def post_skip3p(self, j, rec):
        if not j["skip"]:
            return
        # B1P is held by design: its fill was killed at the end of the job; the recovery is the debugfs reset, the gate and the health
        if not self.end(f"{j['name']}-recovery"):
            s = Stop(5, f"{j['name']}: the recovery after the held job (reset, gate, health) is not exact")
            s.ended = True
            raise s
