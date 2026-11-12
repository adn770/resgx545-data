# SPDX-License-Identifier: MIT
"""ops_h.py: the `hjob` op of the R5-events runner (stages h1, h2, h3).  A mixin of Runner.  R4-events' ops_e3p.py (E836, E837) with the
clock knob, the status dumps and the early clears added.

One job: timer_clock written and read back (the job's clock: 0, 800000 or 1600000), a debugfs reset and the arm of ring_skip3p (R4's bytes),
the arm's status dump (HostCtl dword 6 = the clock, dwords 3 and 8, TA3DCtl 57 and 58), hold_recovery Y in B1P / B1E (the state stays for
the host; B0 runs with N), the host's skip flag (1 in B1P / B1E, 0 in B0), one `fill` through the pinned tool in the background.  The bounded
wait (2 ms steps, at most H_SLOT3_WAIT_S) for the slot 3 entry in the page, then:
  clears "early" (h3's B1E): one STATUS read, the host's CLEAR (`kregnow 0x0134=`) of bit 15, reads 1 and 3 ms after it, of bit 18, reads 1
           and 3 ms after it, then ONE `miscinfo` (the kernel's command and kick together: never a bare kick); then the watch;
  otherwise the watch at once.
The watch: STATUS (0x012c) and STATUS2 read as fast as the debugfs reads go for the row's watch_ms (50, 100 or 150 ms).  The tick checked
(a stop is signed FIRST: the signature twice and the landed dumps, stop-NAME-status.txt with the lockup marks); then, in h1's B1P (clears
"late"), the host's CLEAR of bit 15 (reads 1 and 3 ms) then bit 18 (reads 1, 3 and 20 ms); then P3 if the tick stopped; a status dump
after the watch (every job); the stop's explanation for the runner's stop rule (the marks and the fill's kick entry).  Nothing else is
written: no bit 29, no CLEAR2, no firmware `str`.  hold_recovery is put back to N (read back) before the tool is collected; each B1P / B1E
that kept the tick (held by design) ends with the debugfs reset, the gate and the health (post_hjob; handle_stop does it after a stop).
"""
import re
import subprocess
import time

import r5layout as L
import fwtask_run as FR
from r3common import Stop

NOT_ANSWERED = re.compile(r"timeout|timed out|no MISCINFO|not ready", re.I)


class HOps:
    def check_hjob(self, j, spec, row):
        n = j["name"]
        if j.get("skip") != spec["skip"] or j.get("watch_ms") != spec["watch_ms"] or j.get("slot3_wait_s") != L.H_SLOT3_WAIT_S:
            raise Stop(7, f"{n}: skip flag, watch or wait time outside the allow-list")
        if j.get("timer_clock") != spec["timer_clock"] or j["timer_clock"] not in L.CLOCKS:
            raise Stop(7, f"{n}: timer_clock {j.get('timer_clock')} is not row {row}'s")
        if j.get("clears") != spec["clears"] or j.get("miscinfo_after_clears") != spec["miscinfo_after_clears"]:
            raise Stop(7, f"{n}: the clears are not row {row}'s")
        if j.get("clear_values") != list(L.H_CLEAR_VALUES):
            raise Stop(7, f"{n}: the CLEAR values are not the frozen ones")
        want_ms = L.H_READ_MS_EARLY if j["clears"] == "early" else L.H_READ_MS_LATE
        if j.get("read_ms") != {k: list(v) for k, v in want_ms.items()}:
            raise Stop(7, f"{n}: the read times are not the frozen ones")
        if j["skip"] and j.get("hold_recovery") != "Y":
            raise Stop(7, f"{n}: B1P / B1E run with hold_recovery Y")
        if not j["skip"] and j.get("hold_recovery") != "N":
            raise Stop(7, f"{n}: B0 runs with hold_recovery N")
        if bool(j.get("may_stop")) != bool(spec["may_stop"]):
            raise Stop(7, f"{n}: may_stop is not row {row}'s")

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

    def clears(self, j, rec):
        for key, v in (("bit15", j["clear_values"][0]), ("bit18", j["clear_values"][1])):
            self.clear_write(v, rec, key, j["read_ms"][key])

    def misc_after_clears(self, rec):
        """h3: ONE miscinfo after the clears (the EDM running: answered, its kick entry in the ring with ticks after it)."""
        t = time.monotonic()
        try:
            m = FR.miscinfo()
            m["answered"] = m.get("ms", 0) < L.P3_MS and not NOT_ANSWERED.search(str(m.get("text", "")))
        except OSError as e:
            m = {"ms": (time.monotonic() - t) * 1000, "errno": e.errno, "text": f"no completion (the read failed: {e})", "answered": False}
        m["t_ms"] = round((t - self.t0_mono) * 1000, 2)
        rec["misc"] = m

    def explain(self, j, rec):
        """The runner's stop rule: a stop is explained when its status dump carries the lockup marks (dword 3 above the arm's, dword 8
        bit 0) and the fill's kick entry is in the ring (the count is readable).  Recorded in the job."""
        try:
            st = (self.out / f"stop-{j['name']}-status.txt").read_text()
        except OSError as e:
            st = ""
            rec["explained_why"] = f"no stop status dump ({e})"
        m = L.parse_marks(st)
        base = ((rec.get("marks_arm") or {}).get("hc") or {}).get(L.HC_LOCKUPS, 0)
        page = None
        try:
            page = self.cur_res.page() if self.cur_res is not None else None
        except Exception as e:
            rec["explained_why"] = f"no page ({e!r})"
        cnt, info, why = L.count_after_kick(page) if page else (None, {}, "no page")
        rec["marks_stop"] = m
        rec["count_at_stop"] = {"count": cnt, "info": info, "why": why}
        marked = L.is_marked(m, base)
        rec["explained"] = bool(marked and cnt is not None)
        if not rec["explained"]:
            rec["explained_why"] = rec.get("explained_why") or (f"marks {marked}, count {cnt} ({why})")

    def hjob_job(self, j, rec):
        rec["clock"] = j["timer_clock"]
        self.set_clock(j["timer_clock"], rec)
        self.pre_reset_arm(j, rec)
        rec["status_arm"] = FR.rd("status")
        rec["marks_arm"] = L.parse_marks(rec["status_arm"])
        rec["status2_pre"] = self.reg(L.REG_STATUS2_OFF)
        res = FR.Res()
        self.cur_res = res
        proc = None
        try:
            self.ring_clear(res)
            res.w(L.SKIP3, j["skip"])
            rec["knobs"] = {"hold_recovery": self.knob("hold_recovery", j["hold_recovery"]), "timer_clock": rec["timer_clock_read"]}
            rec["tick_pre"] = FR.alive()
            t0 = time.monotonic()
            self.ring_open(res, 2, rec)
            proc = subprocess.Popen([self.tool, "fill"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True)
            # the slot 3 entry in the page (bounded: 2 ms steps)
            tw0 = time.monotonic()
            seen = False
            for _ in range(int(j["slot3_wait_s"] * 500)):
                if res.r(L.RING_BASE[3])[0]:
                    seen = True
                    break
                time.sleep(0.002)
            rec["slot3_seen"], rec["slot3_wait_ms"] = seen, round((time.monotonic() - tw0) * 1000, 2)
            rec["clears"] = {}
            if j["clears"] == "early":
                r = FR.regs()[0]
                rec["status_before_clears"] = {"status": r.get(L.REG_EVENT_STATUS), "status2": r.get(L.REG_STATUS2_OFF),
                                               "t_ms": round((time.monotonic() - self.t0_mono) * 1000, 2)}
                self.clears(j, rec)
                if j["miscinfo_after_clears"]:
                    self.misc_after_clears(rec)
            watch = []
            tw = time.monotonic()
            for _ in range(4000):                       # as fast as the debugfs reads go, for the watch time
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
            self.check_tick(rec, "after-watch")
            stopped = bool(rec.get("stopped"))
            if stopped:
                self.explain(j, rec)
            if j["clears"] == "late":
                self.clears(j, rec)
            if stopped:
                self.probe_p3(rec)
            rec["status_post"] = FR.rd("status")
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
                    o, _ = proc.communicate(timeout=L.TOOL_WAIT_S)
                    rec["tool_rc"] = proc.returncode
                except subprocess.TimeoutExpired:
                    proc.kill()
                    o, _ = proc.communicate()
                    rec["tool_rc"] = "timeout"
                rec["tool_out"] = (o or "")[-600:]

    def classify_hjob(self, j, rec):
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

    def post_hjob(self, j, rec):
        if not j["skip"]:
            return
        # a B1P / B1E that kept the tick is held by design: its fill was killed at the end of the job; the recovery is the debugfs
        # reset, the gate and the health
        if not self.end(f"{j['name']}-recovery"):
            s = Stop(5, f"{j['name']}: the recovery after the held job (reset, gate, health) is not exact")
            s.ended = True
            raise s
