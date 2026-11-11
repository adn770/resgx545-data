# SPDX-License-Identifier: MIT
"""ops_kicker2.py: the `kicker2` op of the R4-events runner (stage kb2 = Q290 rows G0P, Q2P, Q3P, Q4).  A mixin of Runner.

E819's stage kb opened the window, waited 1 ms, made the write, waited 5 ms and called `miscinfo`: the 16-rung ring was full 11 ms before
the kick.  Here the order changes and nothing else: per job a debugfs reset + arm of ring_hold (K = 2 after the arm, E768), the ring cleared,
the writes made BEFORE the window opens (Q2P: `kicker =0x42`; Q3P and Q4: `kick_no_bump` Y; G0P: none), then the window (window 2: every pass
is logged with its count byte K = pa1[31:24] and its pa2), `miscinfo` called 1 ms later (the kernel's own command and kick together; never
a bare kick), so that, by E816 G0's timing (the kick entry came 6.70 ms after the call's stamp), the kick's write falls about 8 ms after the
first ring entry with about 7 ticks before it and 6 after.  After a call that timed out (Q3P, Q4: the kernel's 500 ms) the signature is
read twice, 30 ms apart (USE0_SERV_EVENT bit 16).  Q4 then clears the ring and runs a second window with one ordinary `miscinfo`.
The kicker file is read before, after the writes, after the call and at the end (`kicker W ccbctl WOFF ROFF kicks N`).  G0P is the stage's
timing control: after each G0P job, if the page has not one kick entry with at least 3 ticks after it, the stage stops (exit 8): the
timing design is wrong again and Q2P, Q3P and Q4 would be void.
"""
import re
import time

import r4layout as L
import fwtask_run as FR
from r3common import Stop


class Kicker2Ops:
    def check_kicker2(self, j, spec, row):
        n = j["name"]
        for k in ("set_kicker", "no_bump", "kick", "second_kick"):
            if j.get(k) != spec[k]:
                raise Stop(7, f"{n}: {k} {j.get(k)!r} is not row {row}'s {spec[k]!r}")
        if j.get("set_kicker") not in (None, L.KICKER_WORD):
            raise Stop(7, f"{n}: the kicker word {j.get('set_kicker')} is not the frozen {L.KICKER_WORD:#x}")
        if (j.get("window"), j.get("pre_ms"), j.get("ticks_ms"), j.get("post_ms"), j.get("q4_pre_ms")) != \
                (2, L.KB2_PRE_MS, 0, L.KB2_POST_MS, L.KB2_Q4_PRE_MS):
            raise Stop(7, f"{n}: window or times outside the allow-list")

    def kicker_read(self):
        """{"w", "wofs", "rofs", "kicks", "raw"} from the kicker file; w is None if the line is not the kernel's format."""
        text = FR.rd(L.KICKER_FILE)
        m = re.match(L.KICKER_RE, text.strip())
        if not m:
            return {"w": None, "wofs": None, "rofs": None, "kicks": None, "raw": text[:120]}
        return {"w": int(m.group(1)), "wofs": int(m.group(2)), "rofs": int(m.group(3)), "kicks": int(m.group(4)), "raw": text.strip()}

    def ring_close_key(self, res, rec, t0, key):
        """ring_close for a second window: the page twice (window 0 proof) under page{key}, page2{key}."""
        res.w(L.WINDOW, 0)
        time.sleep(0.003)
        rec["page" + key] = res.page()
        time.sleep(0.010)
        rec["page2" + key] = res.page()

    def kicker2_job(self, j, rec):
        self.pre_reset_arm(j, rec)
        res = FR.Res()
        self.cur_res = res
        try:
            self.ring_clear(res)
            rec["kicker_before"] = self.kicker_read()
            rec["no_bump_before"] = FR.rd(L.KICK_NO_BUMP_FILE).strip()
            rec["ccbctl_pre"] = self.ccbctl()
            # the writes, BEFORE the window opens
            if j["no_bump"]:
                FR.wr(L.KICK_NO_BUMP_FILE, "Y")
                self.knobs_written[L.KICK_NO_BUMP_FILE] = "N"
                rec["no_bump_set"] = FR.rd(L.KICK_NO_BUMP_FILE).strip()
            if j["set_kicker"] is not None:
                try:
                    FR.wr(L.KICKER_FILE, f"={j['set_kicker']}")
                    rec["set_ok"] = True
                except OSError as e:
                    rec["set_ok"], rec["set_errno"] = False, e.errno
                rec["kicker_after_set"] = self.kicker_read()
            t0 = time.monotonic()
            self.ring_open(res, j["window"], rec)
            time.sleep(j["pre_ms"] / 1000)
            rec["stamp_before_kick"] = self.reg(L.REG_TIMER)
            self.kick(rec)
            rec["stamp_after_kick"] = self.reg(L.REG_TIMER)
            rec["kicker_after_kick"] = self.kicker_read()
            if j["no_bump"]:
                rec["sig_after_timeout"] = self.sig_samples(res, n=L.KB2_SIG_N, gap=L.KB2_SIG_GAP)
            time.sleep(j["post_ms"] / 1000)
            rec["kicker_after"] = self.kicker_read()
            rec["no_bump_after"] = FR.rd(L.KICK_NO_BUMP_FILE).strip()
            self.ring_close(res, rec, t0)
            rec["bracket"] = None
            if j["second_kick"]:
                self.second_window(res, j, rec)
        finally:
            res.close()
        self.check_tick(rec, "after-window")

    def second_window(self, res, j, rec):
        """Q4: the ring cleared, a second window, one ordinary `miscinfo` 1 ms after it (the unbumped kick of the first part has been
        sent and timed out: kick_no_bump was one-shot)."""
        q = rec.setdefault("q4", {})
        q["kicker_before"] = self.kicker_read()
        self.ring_clear(res)
        t0 = time.monotonic()
        self.ring_open(res, j["window"], q)
        time.sleep(j["q4_pre_ms"] / 1000)
        q["stamp_before_kick"] = self.reg(L.REG_TIMER)
        self.kick(q)
        q["stamp_after_kick"] = self.reg(L.REG_TIMER)
        time.sleep(j["post_ms"] / 1000)
        q["kicker_after"] = self.kicker_read()
        self.ring_close_key(res, q, t0, "")
        rec["q4_done"] = True

    def classify_kicker2(self, j, rec):
        if j["set_kicker"] is not None and rec.get("set_ok") is not True:
            rec["class"], rec["note"] = "void", rec["note"] + " the kicker write was refused"
            return True
        if rec.get("kicker_after", {}).get("w") is None and rec.get("rc") == 0:
            rec["class"], rec["note"] = "void", rec["note"] + " the kicker file did not read in the kernel's format"
            return True
        if j["second_kick"] and not rec.get("q4_done") and rec.get("rc") == 0:
            rec["class"], rec["note"] = "void", rec["note"] + " the second window did not run"
            return True
        return False

    def timing_of(self, rec):
        """(kick entries, ticks after the first kick entry) of the page's slot 0, rung order = time order (one slot, one task)."""
        es = L.slot_entries(rec["page"], 0)
        kicks = [i for i, e in enumerate(es) if L.is_kick_entry(e)]
        after = sum(1 for e in es[kicks[0] + 1:] if L.is_tick_entry(e)) if kicks else 0
        return len(kicks), after

    def post_kicker2(self, j, rec):
        if j["row"] != "G0P":
            return
        nk, after = self.timing_of(rec)
        rec["timing"] = {"kick_entries": nk, "ticks_after": after}
        print(f"## {j['name']} timing: {nk} kick entries, {after} ticks after it (want 1 and at least {L.KB2_MIN_AFTER})")
        if nk != 1 or after < L.KB2_MIN_AFTER:
            raise Stop(8, f"{j['name']}: the timing control failed ({nk} kick entries, {after} ticks after it): the kick is not in the ring "
                          f"with {L.KB2_MIN_AFTER} ticks after it, so Q2P, Q3P and Q4 would be void (the stage stops)")
