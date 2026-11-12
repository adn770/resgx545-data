#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen_r5.py (r6-held part P): write the table and the frozen predictions part P runs from, in this directory (closing6/r6-held/p/).
R5-events' generator (closing5/r5-events/gen/gen_r5.py) cut to one stage, p1 (E855's h1 job: B0, B1P x2), with the peek rows of
CR_DPM_TASK_STATE added and the rgn4 kernel's `cannot tell` row (R6-DPM) dropped.  The blob is R4-events' ring_skip3p (byte for byte,
E836: sha256 in r5layout.SKIP3P_SHA); nothing is assembled here.

The predictions start from landed text only (no data-private reading is cited): E855 (3 of 3 held-out stops with the lockup marks after
20 slot 0 passes, bit 18 a level, the host's clears H-W; its R-6 [RE] row: the lockup path writes CR_DPM_TASK_STATE = 2 before a poll of
EVENT_STATUS bit 6, which the rgn4 kernel could not read), E836, E837, E849, E084.

  tables/p1.json   the job table;   predictions/p1.tsv   the frozen predictions (case quantity value model set)
  bins/blobs.json  the blob's facts (R4's entry for ring_skip3p, copied)

Run with the scratch venv:  .../pixel-faults/.venv/bin/python gen/gen_r5.py   (then run/freeze_p.sh freeze)
"""
import hashlib
import json
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R5 = HERE.parent
sys.path.insert(0, str(HERE))
import r5layout as L  # noqa: E402

STAGES = L.STAGES
SPEC = L.ROW_SPEC
BLOB_INFO = {"arm": "slots=0xf entry=0,1,2,3", "bytes": 5464, "cont4": False, "entries": [0, 245, 379, 513], "insns": 668, "ldr": ["#81"],
             "pa_writes": [], "patches": 12, "sa_writes": [], "sha256": L.SKIP3P_SHA, "str": [],
             "note": "byte-identical to closing4/r4-events/bins/ring_skip3p.blob (E836); its blobs.json entry copied"}

# where each prediction comes from (cited in the model text; [infer] where the reading is ours and not measured)
R6 = "E855 (R-6's reading as E855 lands it)"
S0 = "E855 (S0, as E855 lands it)"
H_HWR = f"H-HWR (the firmware's 3D lockup check: {R6} (i)-(ii), {S0}; b1p's marks E849)"
H_NOMARK = "H-NOMARK (another cause: b1p's marks were incidental)"


def build_blobs():
    blob = (R5 / "bins" / "ring_skip3p.blob").read_bytes()
    assert hashlib.sha256(blob).hexdigest() == L.SKIP3P_SHA, "ring_skip3p.blob is not R4-events' bytes"
    info = {"ring_skip3p": BLOB_INFO}
    (R5 / "bins" / "blobs.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    return info


# ---- tables ----------------------------------------------------------------------------------------------------------------
def jobs_of(stage):
    jobs = []
    for row in L.ROW_ORDER[stage]:
        spec = SPEC[stage][row]
        for k in range(spec["reps"]):
            j = {"name": L.rep_name(row, k), "set": spec["label"], "row": row,
                 "runid": 0x7600 + 0x100 * STAGES.index(stage) + len(jobs) + 1}
            j.update(make_hjob(spec))
            jobs.append(j)
    return jobs


def make_hjob(spec):
    early = spec["clears"] == "early"
    return {"op": "hjob", "skip": spec["skip"], "timer_clock": spec["timer_clock"], "watch_ms": spec["watch_ms"], "clears": spec["clears"],
            "miscinfo_after_clears": spec["miscinfo_after_clears"], "clear_values": list(L.H_CLEAR_VALUES),
            "read_ms": {k: list(v) for k, v in (L.H_READ_MS_EARLY if early else L.H_READ_MS_LATE).items()},
            "slot3_wait_s": L.H_SLOT3_WAIT_S, "hold_recovery": "Y" if spec["skip"] else "N", "may_stop": spec["may_stop"]}


def table(stage):
    info = L.STAGE_INFO[stage]
    return {"stage": stage, "blob": info["blob"], "arm": info["arm"], "stop_budget": info["budget"], "per_job_reset": info["per_job_reset"],
            "jobs": jobs_of(stage), "needs": info["gate"], "session": L.SESSION}


# ---- predictions (frozen before the first job; `case quantity value model set`) --------------------------------------------
def add(P, n, q, v, model, s):
    P.append((n, q, str(v), model, s))


def gap_text(clock):
    return f"{L.gap_units(clock)}+-{L.GAP_TOL[clock]}"


def common(P, j):
    """Every job: the design echoed back (what the runner applied) and the clock it ran at: controls that can fail."""
    n, c = j["name"], j["timer_clock"]
    add(P, n, "skipped", j["skip"], "control (the design: the host's flag, the task's count)", "control")
    add(P, n, "slot3_logged", "yes", "control (the slot 3 end-of-render entry is in the page before the watch starts)", "control")
    add(P, n, "hold_recovery_after", "N", "control (put back and read back)", "control")
    add(P, n, "timer_clock_read", L.knob_text(c), "control (the knob written before the job's reset, read back)", "control")
    add(P, n, "arm_dword6", L.eff_clock(c), "control (HostCtl dword 6 in the arm's status dump = the knob, 400000 for 0: E084)", "control")
    add(P, n, "arm_marks", "0 0", "control (HostCtl dwords 3 and 8 in the arm's status dump: the reset rebuilds every firmware buffer, "
        "fork a2788bd8 sgx_fw.c sgx_fw_build; 0 in the 22 other kept stops, E849)", "control")
    add(P, n, "peek_format", "ok", "control (every peek read of the job prints the one line `reg 0x0694 0x%08x`: the arm read, and after "
        "the watch (B0) or the stop's, the clears' and the recovery's (B1P))", "control")
    gm = "E084 (dword 6 / 16 CR_TIMER units a tick)" if c in (0, 800000) else "E084's rule at a clock it did not measure (B0B is its measurement)"
    add(P, n, "tick_gap", gap_text(c), f"control ({gm}; a job whose gap is not its clock's is void)", "control")


def marks_rows(P, n, s, stage):
    """The lockup marks of a B1P / B1E stop, from its status dump taken at the signature (before any clear)."""
    hw, nm = H_HWR, H_NOMARK
    if stage == "h3":
        hw = f"H-STATE (the arm is firmware state, sa9 bit 0, which no host write to EVENT_HOST_CLEAR touches: {R6} (i), (iii))"
        nm = "H-ACK18 (the unacknowledged bit 18 keeps the check armed: the clears end it)"
    add(P, n, "tick_alive", "no", hw, s)
    add(P, n, "tick_alive", "no" if stage != "h3" else "yes", nm, s)
    add(P, n, "lockups", 1, hw.split(" (")[0] + " (HostCtl dword 3 at the stop minus at the arm: +1, R-6 (i); E849)", s)
    add(P, n, "lockups", 0, nm.split(" (")[0], s)
    add(P, n, "iflags", 1, hw.split(" (")[0] + " (HostCtl dword 8 = 1, InterruptFlags bit 0: the HWR request, R-6 (i); E849)", s)
    add(P, n, "iflags", 0, nm.split(" (")[0], s)
    if stage == "h3":
        add(P, n, "sig_event_status", f"0x{L.STOP_STATUS_H3:08x}", "H-STATE (the stop's EVENT_STATUS after the host cleared bit 18: bit 29 alone)", s)
        return
    add(P, n, "sw_events", 1, "H-HWR (the kernel counted one SW_EVENT: the lockup path writes EVENT_STATUS bit 14, R-6 (i); E849)", s)
    add(P, n, "sw_events", 0, "H-NOMARK", s)
    add(P, n, "dword9", 0, "H-HWR (InterruptClearFlags: the lockup path does not write it)", s)
    add(P, n, "dword57", 0, "H-HWR (TA3DCtl dword 57 zeroed by the 20th tick's sample, R-6 (i); b1p 0, E849)", s)
    add(P, n, "dword58", "nonzero", "H-HWR (TA3DCtl dword 58 = the register signature stored at ticks 10 and 20, R-6 (i); b1p 0xaac267c2, E849)", s)
    add(P, n, "dword58", "0", "H-NOMARK", s)
    add(P, n, "dword14", 0, "H-HWR (HostCtl dword 14: the assert routine at 0x0 did not run, 0 in every stop but E813's)", s)
    add(P, n, "ccb", "3 3", "H-HWR (the CCB offsets at the stop: boot, arm and fill commands read, b1p 3 3)", s)
    add(P, n, "status_bit6", "clear", f"H-HWR (EVENT_STATUS bit 6 DPM_STATE_CLEAR clear: the lockup path polls it with no exit, {R6} (ii), {S0})", s)
    peek_rows(P, n, s)
    add(P, n, "ta3d_dword28", 0, f"H-HWR [infer] (TA3DCtl dword 28, the 3D render context of the render kick, 0: the fill's 3D kick is the "
        "second of R-6's two 3D kicks, which also sets sa9 bit 2, so the lockup path skips the context's dword 13 bit 11 (R-6); b1p 0, bif_faults 0)", s)
    add(P, n, "p3_answered", "no", f"H-HWR (the EDM waits for DPM_STATE_CLEAR under lock #0: a miscinfo is not read, {R6} (ii); E836 P3)", s)


PEEK_SRC = ("debugfs peek of fork r6-kernel db7faabc (one read of 0x0694 under the device lock), read before any write after the stop's "
            "signature")


def peek_rows(P, n, s):
    """Q111's row (E855: cannot tell on rgn4).  Decided only where the same job's arm read is not 2 (else both rows cannot tell)."""
    add(P, n, "peek_stop", f"0x{L.PEEK_DPM_LOCKUP:08x}", f"H-R6 (CR_DPM_TASK_STATE = 2 at the lockup stop: the lockup path writes it before "
        f"its poll of EVENT_STATUS bit 6, E855's [RE] row; {PEEK_SRC})", s)
    add(P, n, "peek_stop_eq_arm", "no", "H-R6 (the stop's read differs from the arm's: decided only when the arm read is not 2)", s)
    add(P, n, "peek_stop_eq_arm", "yes", "H-IDLE (the stop leaves 0x0694 as the idle EDM had it at the arm: nothing on the lockup path writes it)", s)
    add(P, n, "peek_recovered_eq_arm", "yes", "H-RESET [infer] (the reset, gate and health after the stop give 0x0694 back its idle value, "
        "the arm's read: the reset rebuilds the firmware's state, sgx_fw_build)", s)


def preds_stage(stage, t):
    P = []
    for j in t["jobs"]:
        n, row, s, c = j["name"], j["row"], j["set"], j["timer_clock"]
        common(P, j)
        if not j["skip"]:
            m = "control (E823 B0 3 of 3, E836 b0: the fill without the skip)"
            for q, v in (("tool_ok", "yes"), ("tick_alive", "yes"), ("end_render_entries", 1), ("bit18_in_watch", "never")):
                add(P, n, q, v, m, "control")
            add(P, n, "post_marks", "0 0", "control (HostCtl dwords 3 and 8 in a status dump after the watch: no lockup without the skip)", "control")
            continue
        add(P, n, "fill_returned_in_watch", "no", "both (the closed slot 3 handler is not called: the job is held, E836)", s)
        add(P, n, "end_render_entries", 1, "H-ONCE (the event is not re-fired, E836)", s)
        marks_rows(P, n, s, stage)
        # the count: H-TICKS (R-6 (i): dword 57 + 1 a tick against HostCtl dword 5 = 10, the compare on tick 20) and H-TIME (about 19.3 ms)
        add(P, n, "ticks_after_kick", L.LOCKUP_TICKS, f"H-TICKS (the stop on the 20th tick after the fill's kick, {R6} (i), {S0}; b1p 20, E849)", s)
        if stage == "h2":
            t_ms = 19.3                      # E849 / O1: the last pass entered about 19.3 ms after the kick
            mid = round(t_ms * L.CORE_HZ / L.eff_clock(c) / 1000)
            add(P, n, "ticks_after_kick", f"{mid - 1}..{mid + 1}", f"H-TIME (the stop about 19.3 ms after the kick whatever the tick: {mid} +-1 ticks at {c}; "
                "no mechanism in the code, R-6)", s)
        if stage in ("h1", "h2", "p1"):
            add(P, n, "bit18_in_watch", "all", "H-LEVEL (bit 18 holds until acknowledged: E837, E823 48 ms)", s)
            add(P, n, "bit18_in_watch", "never", "H-PULSE", s)
        if stage in ("h1", "p1"):
            for mm, v in (("H-W", "1"), ("H-ALL", "0"), ("H-NONE", "1")):
                add(P, n, "bit18_after_bit15", v, mm + " (the bits written are the bits cleared: E837 fit)" if mm == "H-W" else mm, s)
            for mm, v in (("H-W", "0"), ("H-ALL", "0"), ("H-NONE", "1")):
                add(P, n, "bit18_after_bit18", v, mm + " (the bits written are the bits cleared: E837 fit)" if mm == "H-W" else mm, s)
        if stage == "h3":
            add(P, n, "misc_answered", "yes", "control (the miscinfo after the clears is answered: the EDM was running at the clears)", "control")
            add(P, n, "misc_kick_in_ring", "yes", "control (its kick entry is in the slot 0 ring with a tick after it)", "control")
            add(P, n, "bit18_before_clears", "1", "H-LEVEL (bit 18 set at the slot 3 entry of a skipped pass, E837)", s)
            for mm, v in (("H-W", "1"), ("H-ALL", "0"), ("H-NONE", "1")):
                add(P, n, "bit18_after_bit15", v, mm + " (on a running EDM: the bits written are the bits cleared)" if mm == "H-W" else mm, s)
            for mm, v in (("H-W", "0"), ("H-ALL", "0"), ("H-NONE", "1")):
                add(P, n, "bit18_after_bit18", v, mm + " (on a running EDM: the bits written are the bits cleared)" if mm == "H-W" else mm, s)
    return P


FAMILIES = {"p1": [("H-HWR", "H-NOMARK"), ("H-TICKS",), ("H-LEVEL", "H-PULSE"), ("H-W", "H-ALL", "H-NONE"), ("H-R6", "H-IDLE"),
                   ("H-RESET",)]}


# ---- writing -------------------------------------------------------------------------------------------------------------
def write_preds(stage, rows):
    out = ["case\tquantity\tvalue\tmodel\tset"] + ["\t".join(r) for r in rows]
    (R5 / "predictions" / f"{stage}.tsv").write_text("\n".join(out) + "\n")


def brief(j):
    skip = {"name", "set", "row", "runid", "op", "read_ms", "clear_values"}
    return ", ".join(f"{k}={v}" for k, v in j.items() if k not in skip and v not in (None, [], False))


def tables_md(info, tabs):
    L_ = ["# r6-held part P job table (generated by gen/gen_r5.py; the JSON in tables/ is what runs)", "",
          "| blob | insns | bytes | sha256 | arm | sa writes | pa writes | str | ldr | cont4 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, i in info.items():
        L_.append(f"| {n} | {i['insns']} | {i['bytes']} | {i['sha256'][:16]}... | `{i['arm']}` | none | none | none | {', '.join(i['ldr'])} | no |")
    L_ += [""]
    for st in STAGES:
        t = tabs[st]
        L_ += [f"## stage {st}: blob {t['blob']}, needs {t['needs']}, stop budget {t['stop_budget']} (a stop past it ends the stage), "
               f"reset + arm each job: {t['per_job_reset']}", "",
               "| job | set | row | parameters |", "|---|---|---|---|"]
        for j in t["jobs"]:
            L_.append(f"| {j['name']} | {j['set']} | {j['row']} | {brief(j)} |")
        L_.append("")
    (R5 / "TABLES.md").write_text("\n".join(L_) + "\n")


def main():
    info = build_blobs()
    tabs = {st: table(st) for st in STAGES}
    (R5 / "tables").mkdir(exist_ok=True)
    (R5 / "predictions").mkdir(exist_ok=True)
    for st in STAGES:
        (R5 / "tables" / f"{st}.json").write_text(json.dumps(tabs[st], indent=1, sort_keys=True) + "\n")
        write_preds(st, preds_stage(st, tabs[st]))
    (R5 / "stages.txt").write_text("\n".join(f"{st} {L.STAGE_INFO[st]['alarm']}" for st in STAGES) + "\n")
    tables_md(info, tabs)
    print("wrote tables", ", ".join(STAGES), "; jobs", {st: len(tabs[st]["jobs"]) for st in STAGES}, "total",
          sum(len(t["jobs"]) for t in tabs.values()))


if __name__ == "__main__":
    main()
