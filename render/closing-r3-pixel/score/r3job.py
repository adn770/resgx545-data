# SPDX-License-Identifier: MIT
"""One kept job of an R3-pixel stage as a record: void reason, STATUS2 before and after, the loop proof line, the burst of the
regtimeline.  Rules common to every scorer: a job with no output, an rc that is not a result of the tool, a skipped class, a
failed pre-read (STATUS2 not 0x400 after the reset) or a missing after-read is VOID, tested before any match."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import r3lib as L  # noqa: E402


def job(k, name, mark=None, count=None):
    """mark / count: the proof the row expects (o0 = mark on count of count pixels).  Returns a dict:
    void (reason or None), cls, pre, post, bit6, bit7, o0, proof (None = no expectation, True/False), B, t6, t7."""
    c = k.case(name)
    r = dict(name=name, cls=c.get("class", ""), void=None, pre=None, post=None, bit6=None, bit7=None, o0=None, proof=None,
             B=None, t6=None, t7=None, stale=False, txt="")
    v = k.void(name)
    if v:
        r["void"] = v
        return r
    txt = k.out(name)
    r["txt"] = txt
    if c.get("class") not in ("ok", None, ""):
        r["void"] = f"class {c.get('class')}"
        return r
    r["pre"] = L.status2(L.regs_file(k, name, "pre"))
    r["post"] = L.status2(L.regs_file(k, name, "after"))
    if r["pre"] is None or r["post"] is None:
        r["void"] = "no STATUS2 read (pre or after)"
        return r
    if r["pre"] != 0x400:
        r["void"] = f"STATUS2 before the job was {r['pre']:#x}, not 0x400"
        return r
    r["bit6"], r["bit7"] = bool(r["post"] & 0x40), bool(r["post"] & 0x80)
    r["o0"] = L.parse_o0(txt)
    if mark is not None:
        o = r["o0"]
        r["proof"] = bool(o and o[0] == "same" and o[1] == mark and o[2] == count and o[3] == count)
    b = L.burst(txt)
    if b:
        r.update(B=b["B"], t6=b["t6"], t7=b["t7"], stale=b["stale"])
    return r
