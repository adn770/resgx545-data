# SPDX-License-Identifier: MIT
"""r5common.py: what the scorer of R5-events shares (R4-events' r4common.py with value ranges): the readings of a ring job, the row engine (a measured quantity against every
frozen row of its job, with the control gate), and the verdict of a family of hypotheses.  Standard library only; every verdict word
(held, FAILED, cannot tell, mixed, the gate, the headline) comes from scorekit (resgx545 5a13042 tools/closing/scorekit.py, byte for byte).

States: a row is held (True), FAILED (False) or cannot tell (None).  A void job is cannot tell and never a pass.  A control that is not a
pass (FAILED or cannot tell alike) gates every non-control row of its job: they become cannot tell (the row says why).  The stage-level
gate (kb2: G0P's timing control; kp: E0 and FK; e3p: B0) gates every row of the other rows the same way.
"""
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "gen"))
import scorekit as K  # noqa: E402
import scorelib as C  # noqa: E402
import r5layout as L  # noqa: E402


def yn(b):
    return "yes" if b else "no"


def unique(vals):
    """The one value of a list, 'mixed' if it has more than one, None if it is empty."""
    s = sorted(set(vals))
    return None if not s else s[0] if len(s) == 1 else "mixed"


def read_page(page, page2, stamp):
    """([events], why): the merged events of a page from the window stamp on, or why it cannot be read."""
    if not isinstance(page, list) or len(page) != L.PAGE_DWORDS:
        return None, "no page, or a truncated page"
    if page[0] != L.MAGIC:
        return None, "the page header is not the kernel's magic"
    if not isinstance(page2, list) or len(page2) != L.PAGE_DWORDS or page2[L.RING_BASE[0]:L.RING_END] != page[L.RING_BASE[0]:L.RING_END]:
        return None, "no second page, or the ring changed after the window closed (window 0 did not take)"
    try:
        r = C.ring(page)
    except ValueError as e:
        return None, f"corrupt ring: {e}"
    return C.from_stamp(C.merged(r), stamp), None


def void_job(S, name, rec, classes):
    """Why a job's record must not be read (None: it may).  "not run ..." is no void job: the stage's stop rule ended it before the job (exit
    8: a stopped row is never replicated, a stop ended the stage) or the runner recorded the job as skipped; such a job has no rows."""
    if rec is None:
        sr = S.stagerec or {}
        if sr.get("exit") == 8 and name not in sr.get("jobs_run", []):
            return "not run (the stage was ended by its stop rule: exit 8)"
        return "no record kept"
    if rec.get("class") == "skipped":
        return "not run (" + str(rec.get("note", "")).strip() + ")"
    if rec.get("class") not in classes:
        return f"class {rec.get('class')}"
    if rec.get("rc") is None:
        return "no rc recorded"
    return None


# ---- the row engine ----------------------------------------------------------------------------------------------------------------
def match(value, got):
    """A frozen value against a measured one: equal as text, or `a..b` an integer range (H-TIME's +-1)."""
    if ".." in value and value.replace("..", "").lstrip("-").isdigit():
        a, b = (int(x) for x in value.split(".."))
        try:
            return a <= int(got) <= b
        except (TypeError, ValueError):
            return False
    return str(got) == value


def tally_job(S, n, qvals, gate_why=None):
    """Every frozen row of job n against the measured quantities `qvals` ({quantity: text or None}).  Control rows are evaluated first;
    if any is not a pass, or `gate_why` is given, every other row is cannot tell with the reason.  Returns (controls pass, reason)."""
    preds = [pr for pr in S.preds if pr["case"] == n]
    ctl = {}
    for pr in preds:
        if pr["set"] == "control":
            got = qvals.get(pr["quantity"])
            ok = None if got is None else match(pr["value"], got)
            ctl[pr["quantity"]] = ok if ctl.get(pr["quantity"]) is not False else False
    g = K.gate(ctl) if ctl else K.Gate(ok=True)
    why = gate_why or ("" if g.ok else "control not a pass: " + "; ".join(g.problems))
    for pr in preds:
        got = qvals.get(pr["quantity"])
        ok = None if got is None else match(pr["value"], got)
        note = ""
        if pr["set"] != "control" and why:
            ok, note = None, why
        elif got is None:
            note = (S.why_none.get((n, pr["quantity"])) if hasattr(S, "why_none") else None) or "not measurable"
        S.t.add(n, pr["quantity"], pr["model"], pr["set"], ok, note)
    return g.ok and not gate_why, why


def family_verdict(S, table, family):
    """{hypothesis: 'consistent (n row groups)' | 'REFUTED' | 'mixed' | 'cannot tell'} for the hypotheses of `family` (model-name
    prefixes), from the non-control rows of S.t: rows of one (job row, quantity) combine as replicates (scorekit.combine); any group
    refuted decides against the hypothesis, any mixed leaves it mixed, any cannot tell leaves it undecided, all held makes it consistent."""
    row_of = {j["name"]: j["row"] for j in table["jobs"]}
    out = {}
    for h in family:
        groups = {}
        for case, q, model, kind, ok, _note in S.t.rows:
            if kind == "control" or not model.startswith(h):
                continue
            groups.setdefault((row_of.get(case), q), []).append(ok)
        states = [K.combine(v) for v in groups.values()]
        if not states:
            out[h] = "cannot tell"
        elif "refuted" in states:
            out[h] = "REFUTED"
        elif "mixed" in states:
            out[h] = "mixed"
        elif "cannot tell" in states:
            out[h] = "cannot tell"
        else:
            out[h] = f"consistent ({len(states)} row groups)"
    return out


def controls_state(S):
    """{'job.quantity': True/False/None} over every control row of the tally (not a pass if any row of it is not)."""
    ctl = {}
    for case, q, _model, kind, ok, _note in S.t.rows:
        if kind == "control":
            key = f"{case}.{q}"
            ctl[key] = ok if ctl.get(key) is not False else False
    return ctl


def controls_line(S):
    """The controls' state and how many non-control rows decided, by scorekit (gate, tally).  The hypotheses of a stage exclude each other, so
    some non-control rows are FAILED in any world: no single claim is printed here; the family verdicts are the stage's result."""
    ctl = controls_state(S)
    g = K.gate(ctl)
    t = K.tally([ok for _c, _q, _m, kind, ok, _n in S.t.rows if kind != "control"])
    if g.ok:
        return f"every control PASS ({len(ctl)}); {t.decided} of {t.total} non-control rows decided"
    return f"controls not all PASS ({len(g.problems)} of {len(ctl)}: " + "; ".join(g.problems[:3]) + f"); {t.decided} of {t.total} non-control rows decided"


def sig_class_of(samples):
    """'idle', 'busy' or None from signature samples (the scorelib reading)."""
    sg = C.score_sig(samples)
    if sg["class"] == "unreadable":
        return None
    return "busy" if sg["class"] == "busy" else "idle"


def serv_bit16(samples):
    """'set', 'clear', 'mixed' or None from USE0_SERV_EVENT (0x0b14) bit 16 over the samples."""
    bits = []
    for sm in samples or []:
        if not isinstance(sm, dict) or "error" in sm:
            continue
        v = (sm.get("regs") or {}).get(hex(L.REG_SERV_EVENT))
        if v is not None:
            bits.append("set" if v >> L.SERV_EMPTY_BIT & 1 else "clear")
    return unique(bits)
