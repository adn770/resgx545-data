# SPDX-License-Identifier: MIT
"""ops_e2b.py: the `pawrite` op of the R3k runner (stage e2b = Q098's write direction).  A mixin of Runner.

pa_write2.s (one arm for the stage, slots=0x1 entry=0): the host writes the marker (dword 11), the p0..p3 flags (E536's 0, 0, 1, 1) and the
command; the task's pass stores area A (pa0-pa4, sa64-sa68, sa0, CR_TIMER as they stood at entry), does the command's one write (`mov
sa67/sa68` as E748, `mov pa3/pa4/pa2` new), reads the pa and its alias back in the same pass (area C), arms command 9 and tail-calls the
closed task; the next pass (the next tick) stores the same registers in area B.  The runner waits for both, then reads the three areas.
"""
import time

import r3layout as L
import fwtask_run as FR
from r3common import Stop


class PaOps:
    def check_pawrite(self, j, spec, row):
        n = j["name"]
        if j.get("cmd") != spec["cmd"] or j.get("marker") != spec["marker"] or j.get("flags") != [0, 0, 1, 1]:
            raise Stop(7, f"{n}: command, marker or flags are not row {row}'s")
        if sorted(j.get("sa", [])) != sorted(L.PW_SA[spec["cmd"]]) or sorted(j.get("pa", [])) != sorted(L.PW_PA[spec["cmd"]]):
            raise Stop(7, f"{n}: the sa/pa set of command {spec['cmd']} is not the frozen one")
        if any(p in ("pa0", "pa1") for p in j.get("pa", [])):
            raise Stop(7, f"{n}: pa0 and pa1 are never written (R3-K3)")

    def pa_wait(self, res, runid, state, ms):
        """Bounded wait: the writer pass is done when ECHO holds the run id (it stays); the next pass's read is done when STATE is 3
        (the writer leaves STATE 2, the reader 3).  Returns ms or None."""
        t = time.monotonic()
        for _ in range(int(ms / 2) + 1):
            if (state == L.STATE_DONE and res.r(L.ECHO)[0] == runid) or (state == L.STATE_NEXT and res.r(L.STATE)[0] == L.STATE_NEXT):
                return (time.monotonic() - t) * 1000
            time.sleep(0.002)
        return None

    def pawrite_job(self, j, rec):
        res = FR.Res()
        self.cur_res = res
        try:
            self.zero_protocol(res)
            res.w(L.PW_FLAGS, list(j["flags"]))
            if j["marker"] is not None:
                res.w(L.PW_M, j["marker"])
            res.w(L.PW_A, [0] * 12)
            res.w(L.PW_C, [0] * 8)
            res.w(L.PW_B, [0] * 12)
            rec["bracket_pre"] = [res.r(L.A_PASS)[0], FR.regs()[1].get(12), res.r(L.A_PASS)[0]]
            res.w(L.STATE, 0)
            res.w(L.ECHO, 0)
            res.w(L.RUNID, j["runid"])
            res.w(L.CMD, j["cmd"])
            rec["t_cmd_ms"] = 0.0
            rec["writer_ms"] = self.pa_wait(res, j["runid"], L.STATE_DONE, 150)
            rec["next_ms"] = self.pa_wait(res, j["runid"], L.STATE_NEXT, 150) if rec["writer_ms"] is not None else None
            rec["area_a"] = res.r(L.PW_A, 12)
            rec["area_c"] = res.r(L.PW_C, 8)
            rec["area_b"] = res.r(L.PW_B, 12)
            rec["cmd_after"] = res.r(L.CMD)[0]
            rec["rc"] = 0
        finally:
            res.close()
        self.check_tick(rec, "after-pass")

    def classify_pawrite(self, j, rec):
        if rec.get("rc") is None:
            return False
        if rec.get("writer_ms") is None or rec.get("next_ms") is None:
            rec["class"], rec["note"] = "void", rec["note"] + " the task did not answer (writer or next-pass read missing)"
            return True
        return False
