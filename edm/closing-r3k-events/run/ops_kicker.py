# SPDX-License-Identifier: MIT
"""ops_kicker.py: the `kicker` op of the R3k runner (stage kb = Q290 rows Q0-Q3, stage k0h row G0).  A mixin of Runner.

Per job: reset + arm ring_hold (K = 2 after the arm, E768), the window open (window 2: every pass is logged with its count byte K =
pa1[31:24]; slot 0's ring has 16 rungs, so the whole job fits in about 12 ticks: 1 ms, the action, 5 ms of ticks, one `miscinfo` (the
kernel's own command and kick together: Q2, Q3, G0; never a bare kick), 5 ms of ticks), `kick_no_bump` set (Q3), `kicker =0x42` written (Q1,
Q2: no command, no kick, no register), the window closed and the page read twice.  The kicker file is read before, after each action and at the end (`kicker W ccbctl WOFF ROFF kicks N`).
"""
import re
import time

import r3layout as L
import fwtask_run as FR
from r3common import Stop


class KickerOps:
    def check_kicker(self, j, spec, row):
        n = j["name"]
        for k in ("set_kicker", "no_bump", "kick"):
            if j.get(k) != spec[k]:
                raise Stop(7, f"{n}: {k} {j.get(k)!r} is not row {row}'s {spec[k]!r}")
        if j.get("set_kicker") not in (None, L.KICKER_WORD):
            raise Stop(7, f"{n}: the kicker word {j.get('set_kicker')} is not the frozen {L.KICKER_WORD:#x}")
        if j.get("window") != 2 or j.get("pre_ms") != 1 or j.get("ticks_ms") != 5 or j.get("post_ms") != 5:
            raise Stop(7, f"{n}: window or times outside the allow-list")

    def kicker_read(self):
        """{"w", "wofs", "rofs", "kicks", "raw"} from the kicker file; w is None if the line is not the kernel's format."""
        text = FR.rd(L.KICKER_FILE)
        m = re.match(L.KICKER_RE, text.strip())
        if not m:
            return {"w": None, "wofs": None, "rofs": None, "kicks": None, "raw": text[:120]}
        return {"w": int(m.group(1)), "wofs": int(m.group(2)), "rofs": int(m.group(3)), "kicks": int(m.group(4)), "raw": text.strip()}

    def kicker_job(self, j, rec):
        self.pre_reset_arm(j, rec)
        res = FR.Res()
        self.cur_res = res
        try:
            self.ring_clear(res)
            rec["kicker_before"] = self.kicker_read()
            rec["no_bump_before"] = FR.rd(L.KICK_NO_BUMP_FILE).strip()
            rec["ccbctl_pre"] = self.ccbctl()
            t0 = time.monotonic()
            self.ring_open(res, j["window"], rec)
            time.sleep(j["pre_ms"] / 1000)
            if j["no_bump"]:
                FR.wr(L.KICK_NO_BUMP_FILE, "Y")
                rec["no_bump_set"] = FR.rd(L.KICK_NO_BUMP_FILE).strip()
            if j["set_kicker"] is not None:
                rec["stamp_before_set"] = self.reg(L.REG_TIMER)
                try:
                    FR.wr(L.KICKER_FILE, f"={j['set_kicker']}")
                    rec["set_ok"] = True
                except OSError as e:
                    rec["set_ok"], rec["set_errno"] = False, e.errno
                rec["stamp_after_set"] = self.reg(L.REG_TIMER)
                rec["kicker_after_set"] = self.kicker_read()
            time.sleep(j["ticks_ms"] / 1000)
            if j["kick"]:
                rec["stamp_before_kick"] = self.reg(L.REG_TIMER)
                self.kick(rec)
                rec["stamp_after_kick"] = self.reg(L.REG_TIMER)
                rec["kicker_after_kick"] = self.kicker_read()
            time.sleep(j["post_ms"] / 1000)
            rec["kicker_after"] = self.kicker_read()
            rec["no_bump_after"] = FR.rd(L.KICK_NO_BUMP_FILE).strip()
            self.ring_close(res, rec, t0)
            rec["bracket"] = None
        finally:
            res.close()
        self.check_tick(rec, "after-window")

    def classify_kicker(self, j, rec):
        if j["set_kicker"] is not None and rec.get("set_ok") is not True:
            rec["class"], rec["note"] = "void", rec["note"] + " the kicker write was refused"
            return True
        if rec.get("kicker_after", {}).get("w") is None and rec.get("rc") == 0:
            rec["class"], rec["note"] = "void", rec["note"] + " the kicker file did not read in the kernel's format"
            return True
        return False
