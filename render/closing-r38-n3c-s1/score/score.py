#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: the scorer of r38-n3c-s1 (closing29/n3c/design.md §2.1, N3c session S1: rows R1 n0
and R2 th). Every verdict rule comes from kit/scorekit.py, the kept files are read through
kit/kitscore.py (byte copies of the frozen resgx545 commit, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW, CONTROL and OUTCOME lines, then SUMMARY and RULE
                                       lines (exit 0); STAGE own, tim or post
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Stage own, row n0 (R1), the readings from the kept files:
  the page   NAME.own_res.json (fwtask_run.py page, after the job whatever its end), else the
             runner's stop dump NAME.stop0-own_res.json; X0 = dword 70, M4 = dwords 80-81,
             state = dword 2
  Δtick      the record's `ticks` (NAME.txt: HostCtl dword 12 from the command write to 30 ms
             after the window, which ends at done or at timeout_ms)
  gate       NAME.gate.json's ok (the kit's health gate after an ok end): `ok` or absent
  end        `<25|nodone` holds when the record is not done or its ticks are below 25
Outcomes (predictions/own.tsv): N0-OK (X0, M4 and the run id, state 2, Δtick >= 25, the gate
ok) and N0-STOP (Δtick < 25 or no done). Controls, every one can fail: PG page dword 0 =
0x4e574f53; E0 slot 1 = M1 and the run id, cmd 0; T0 snap0's 0x0acc running (bit 24 set, bits
23:0 at most 400000); B BIF_FAULT (0x0c08) 0 in snap9 (else FAULT, its own outcome).
  N3c-R1 RULE: OUTCOME       every control passed and exactly one outcome holds
  N3c-R1 RULE: FAULT         B FAILED
  N3c-R1 RULE: CANNOT TELL   anything else

Stage tim, row th (R2), the readings from NAME.txt (t30's text, then regtimeline's) and
NAME.snap9.regs:
  rows       the stored `tl T V` lines of 0x0acc (regtimeline stores a sample only when it
             differs from the one before: a running count changes every sample)
  the change the first stored sample that is not a running count (bit 24 set and bits 23:0 at
             most 400000); `pre` the samples before it (all of them when there is none)
  tl         `0xV` holds when the change is V and no stored sample after it differs from V;
             `running` holds when there is no change; else FAILED
  snap9      0x0acc in NAME.snap9.regs (right after the job, before any reset): `running` or 0xV
  scratch    the eight tim reads of the program, scratch +0x008 to +0x014 and +0x028 to +0x034
             (tim after 0 to 64 nops, as the recorded run printed them): 0xV when every one is V
  ivl        regtimeline's TOTAL / samples in ns (E1133's reading; LEAD 0.005 and TOTAL 0.06)
Outcomes (predictions/tim.tsv): V0-HOLDS (tl, snap9 and scratch 0x00abcde0) and V0-NOT (tl and
snap9 running, scratch 0x00abcde0). Controls: ivl inside E1133's bounds (2500..5000 ns) and pre
running (at least one stored sample, every one a running count).
  N3c-R2 RULE: OUTCOME       every control passed and exactly one outcome holds
  N3c-R2 RULE: CANNOT TELL   anything else (scratch not 0x00abcde0: the program did not run;
                             another constant; a control FAILED or unread)

Stage post: diff 0 of the health pair's triangle and fill (controls)."""
import json
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

REQUIRED = {"own": (".txt", ".own_res.json", ".gate.json", ".snap0.regs", ".snap9.regs",
                    "cases.tsv", "void.tsv", "readings.tsv"),
            "tim": (".txt", ".snap0.regs", ".snap9.regs", "cases.tsv", "void.tsv",
                    "readings.tsv"),
            "post": (".txt", "cases.tsv", "void.tsv", "readings.tsv")}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none (own's stop ends)
FILL = 0xDEADC0DE
X0, M4 = 0x5A5A3303, 0x5A5A3302
X0_AT, SLOT4 = 0x46, 0x50
TIM, BIF, SERV = 0x0ACC, 0x0C08, 0x0B14
TIM_RUN, TIM_MAX = 1 << 24, 400000
SCRATCH_TIM = (0x008, 0x00C, 0x010, 0x014, 0x028, 0x02C, 0x030, 0x034)
CTLS = {"PG": ("res:0x0",), "E0": ("res:0x44", "res:0x45", "res:0x1"), "T0": ("snap0:0x0acc",),
        "B": ("snap9:0x0c08",)}
WHAT = {"N0-OK": "the stop needs the emit (expected)",
        "N0-STOP": "our path stops the tick without any emit",
        "V0-HOLDS": "the host sees the PDS write (expected)",
        "V0-NOT": "a PDS tim is not the host's 0x0acc"}


def state_word(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def producible(row):
    if row["tool"] in ("owntask", "rt"):
        return set()
    return {"diff"} if row["args"].split()[:1] in (["tri"], ["fill"]) else set()


def reading(text):
    for ln in text.splitlines():
        if ln.startswith("diff: "):
            return {"diff": ln.split()[1]}
    return {}


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n, r in cases.items():
        K.text(d, n + ".txt")
        if stage in ("own", "tim"):
            K.text(d, n + ".snap0.regs")
            K.text(d, n + ".snap9.regs")
        if stage == "own":
            K.own_res(d, n)
            if r["class"] == "ok":
                K.text(d, n + ".gate.json")


def regs_of(text):
    """{offset: value} of `reg 0xOOOO 0xV` lines and {("hostctl", i): v} of `hostctl 0xOO 0xV`."""
    out = {}
    for m in re.finditer(r"^(reg|hostctl|ta3dctl) (0x[0-9a-f]+) (0x[0-9a-f]{8})$", text or "",
                         re.M):
        k = int(m.group(2), 16)
        out[k if m.group(1) == "reg" else (m.group(1), k // 4)] = int(m.group(3), 16)
    return out


def running(v):
    return v is not None and bool(v & TIM_RUN) and (v & 0xFFFFFF) <= TIM_MAX


def all_of(states):
    states = list(states)
    if any(s is False for s in states):
        return False
    return None if any(s is None for s in states) else True


def hexs(v):
    return "?" if v is None else f"0x{v:08x}"


def outcome_lines(n, ctl, hyp):
    return ([f"CONTROL {n}:{k}: {state_word(s)}" for k, s in ctl.items()]
            + [f"OUTCOME {n} {m}: {'held' if s else 'FAILED' if s is False else 'cannot tell'}"
               for m, s in hyp.items()])


def rule_of(tag, ctl, hyp, fault=False):
    held = [m for m, s in hyp.items() if s is True]
    if fault:
        return (f"N3c-{tag} RULE: FAULT: BIF_FAULT is not 0 after the job: its own outcome (the "
                "kept files are the reading)")
    if all(s is True for s in ctl.values()) and len(held) == 1:
        return f"N3c-{tag} RULE: {held[0]}: {WHAT[held[0]]}"
    why = [f"control {k} {state_word(s)}" for k, s in ctl.items() if s is not True]
    if len(held) != 1:
        why.append("no frozen outcome holds" if not held else f"{len(held)} outcomes hold")
    return f"N3c-{tag} RULE: CANNOT TELL ({'; '.join(why)})"


# ---- own (R1) ---------------------------------------------------------------------------------
def page_of(d, n):
    """(the page, where) of the row: own_res.json, else the stop dump; (None, None)."""
    p = K.own_res(d, n)
    if p is not None:
        return p, "own_res.json"
    p = K.own_json(d, n, ".stop0-own_res.json")
    p = p.get("page") if isinstance(p, dict) else p
    if isinstance(p, list) and len(p) == K.OWN_PAGE and all(isinstance(x, int) for x in p):
        return p, "stop0-own_res.json"
    return None, None


def record_of(d, n):
    try:
        return json.loads(K.text(d, n + ".txt"))["records"][0]
    except (ValueError, KeyError, IndexError, TypeError):
        return {}


def gate_of(d, n):
    g = K.own_json(d, n, ".gate.json")
    return None if not isinstance(g, dict) else bool(g.get("ok"))


def own_readings(d, n):
    page, where = page_of(d, n)
    snaps = {k: regs_of(K.text(d, f"{n}.{k}")) for k in ("snap0.regs", "snap9.regs",
                                                          "stop0-regs.txt")}
    rec = record_of(d, n)
    return dict(page=page, where=where, snaps=snaps, ticks=rec.get("ticks"),
                window_ms=rec.get("window_ms"), done=rec.get("done"), gate=gate_of(d, n))


def own_value(spec, q, r):
    """A frozen value against the reading of quantity q: True, False or None."""
    page = r["page"]
    if q == "end":                      # `<25|nodone`
        if r["done"] is False:
            return True
        if r["done"] is None or r["ticks"] is None:
            return None
        return r["ticks"] < int(spec.split("|")[0][1:])
    if q == "gate":
        return None if r["gate"] is None else (spec == "ok") == r["gate"]
    if q == "ticks":
        got = r["ticks"]
    elif q.startswith(("snap0:", "snap9:")):
        got = r["snaps"][q[:5] + ".regs"].get(int(q[6:], 16))
    else:
        got = None if page is None else page[K.res_index(q)]
    if got is None:
        return None
    if spec == "running":
        return running(got)
    if spec == "@runid":
        return got == page[3]
    if spec.startswith(">="):
        return got >= int(spec[2:])
    return got == int(spec, 16)


def signature(r):
    """USE0_SERV_EVENT bit 16 and count minus HostCtl dword 12, per snapshot (printed only)."""
    out = []
    for k in ("snap0.regs", "snap9.regs", "stop0-regs.txt"):
        s = r["snaps"][k]
        ev, tk = s.get(SERV), s.get(("hostctl", 12))
        if ev is None:
            continue
        out.append(f"{k.split('.')[0]}: bit 16 {ev >> 16 & 1}, count - tick "
                   + ("?" if tk is None else str((ev & 0xFFFF) - (tk & 0xFFFF))))
    return "SIGNATURE (printed, not scored): " + ("; ".join(out) or "no USE0_SERV_EVENT read")


def score_own(d):
    """(lines, ctl {row:key: state}, hyp {row: {outcome: state}}, rule lines)."""
    preds = K.predictions(KP, "own")
    cases = K.rows(d, "cases.tsv")
    lines, ctl_all, hyp_all, rl = [], {}, {}, []
    for t in K.table(KP, "own"):
        n = t["name"]
        if n not in cases and K.own_res(d, n) is None:
            continue
        q = preds.get(n, {})
        r = own_readings(d, n)
        if r["page"] is None or n not in cases:
            lines.append(f"ROW {n}: no results page kept: cannot tell")
            ctl_all.update({f"{n}:{k}": None for k in CTLS})
            continue
        models = sorted({m for mv in q.values() for m in mv if m != "CTL"})
        hyp = {m: all_of(own_value(mv[m], k, r) for k, mv in q.items() if m in mv)
               for m in models}
        ctl = {c: all_of(own_value(q[k]["CTL"], k, r) for k in ks) for c, ks in CTLS.items()}
        p = r["page"]
        t9 = r["snaps"]["snap9.regs"].get(TIM)
        lines.append(f"ROW {n}: page {r['where']}; run id {p[3]}; X0 {hexs(p[X0_AT])}; M4 "
                     f"{hexs(p[SLOT4])} {hexs(p[SLOT4 + 1])}; state {p[2]}; done {r['done']}; "
                     f"ticks {r['ticks']} (window "
                     f"{'?' if r['window_ms'] is None else '%.1f' % r['window_ms']} ms); gate "
                     f"{'?' if r['gate'] is None else 'ok' if r['gate'] else 'not ok'}; T9 "
                     f"{hexs(t9)}")
        lines += outcome_lines(n, ctl, hyp)
        ctl_all.update({f"{n}:{k}": s for k, s in ctl.items()})
        hyp_all[n] = hyp
        rl.append(rule_of("R1", ctl, hyp, fault=ctl.get("B") is False))
        rl.append(f"X0 qualifier: {hexs(p[X0_AT])}" + (" (the task stored past cmd 0)"
                                                        if p[X0_AT] == X0 else ""))
        rl.append(signature(r))
    if not rl:
        rl = ["N3c-R1 RULE: CANNOT TELL (no row kept)"]
    lines.append("SUMMARY: own: controls: " + ("every control passed" if SK.gate(ctl_all).ok
                                               else "; ".join(SK.gate(ctl_all).problems)))
    return lines, ctl_all, hyp_all, rl


# ---- tim (R2) ---------------------------------------------------------------------------------
def timeline(text):
    """(header {samples, seconds, rc}, [(t, value of 0x0acc)]) of the job's text, or (None, [])."""
    head, rows, col = None, [], None
    for ln in (text or "").splitlines():
        if ln.startswith("timeline: regs"):
            if head is not None:
                break
            w = ln.split()
            i = w.index("samples")
            regs = w[2:i]
            col = regs.index("0x0acc") if "0x0acc" in regs else None
            head = dict(samples=int(w[i + 1]), seconds=float(w[i + 3]), rc=int(w[i + 9]),
                        nregs=len(regs))
        elif ln.startswith("tl ") and head is not None and col is not None:
            w = ln.split()
            if len(w) != head["nregs"] + 2:
                break
            rows.append((int(w[1]), int(w[2 + col], 16)))
    return head, rows


def scratch(text):
    """{offset: value} of `probe NAME: scratch +0xOOO 0xV` lines."""
    return {int(m.group(1), 16): int(m.group(2), 16) for m in
            re.finditer(r"^probe \S+: scratch \+(0x[0-9a-f]+) (0x[0-9a-f]{8})$", text or "", re.M)}


def tim_readings(d, n):
    text = K.text(d, n + ".txt")
    head, rows = timeline(text)
    change = next((i for i, (_, v) in enumerate(rows) if not running(v)), None)
    pre = rows if change is None else rows[:change]
    ivl = None
    if head and head["seconds"] > 0 and head["samples"] > 0:
        ivl = int(head["seconds"] * 1e9 / head["samples"])
    sc = scratch(text)
    tims = [sc.get(o) for o in SCRATCH_TIM]
    return dict(head=head, rows=rows, change=change, pre=pre, ivl=ivl, tims=tims,
                snap9=regs_of(K.text(d, n + ".snap9.regs")).get(TIM))


def tim_value(spec, q, r):
    if q == "tl":
        if not r["rows"]:
            return None
        if r["change"] is None:
            return spec == "running"
        after = {v for _, v in r["rows"][r["change"]:]}
        return spec != "running" and after == {int(spec, 16)}
    if q == "snap9:0x0acc":
        v = r["snap9"]
        if v is None:
            return None
        return running(v) if spec == "running" else v == int(spec, 16)
    if q == "scratch":
        if any(x is None for x in r["tims"]):
            return None
        return all(x == int(spec, 16) for x in r["tims"])
    if q == "ivl":
        return SK.ivl_control(r["ivl"], spec, {})
    if q == "pre":
        return None if not r["rows"] else bool(r["pre"]) and all(running(v) for _, v in r["pre"])
    raise ValueError(f"unknown quantity {q}")


def score_tim(d):
    """(lines, ctl {row:key: state}, hyp {row: {outcome: state}}, rule lines)."""
    preds = K.predictions(KP, "tim")
    cases = K.rows(d, "cases.tsv")
    lines, ctl_all, hyp_all, rl = [], {}, {}, []
    for t in K.table(KP, "tim"):
        n = t["name"]
        if n not in cases:
            continue
        q = preds.get(n, {})
        r = tim_readings(d, n)
        models = sorted({m for mv in q.values() for m in mv if m != "CTL"})
        hyp = {m: all_of(tim_value(mv[m], k, r) for k, mv in q.items() if m in mv)
               for m in models}
        ctl = {k: tim_value(mv["CTL"], k, r) for k, mv in q.items() if "CTL" in mv}
        ch = None if r["change"] is None else r["rows"][r["change"]]
        h = r["head"] or {}
        lines.append(
            f"ROW {n}: class {cases[n]['class']}; timeline {len(r['rows'])} stored of "
            f"{h.get('samples', '?')} samples, rc {h.get('rc', '?')}, ivl {r['ivl']} ns; change "
            + ("none" if ch is None else f"at {ch[0]} ns to {hexs(ch[1])} "
               f"({len(r['rows']) - r['change'] - 1} stored after it)")
            + f"; pre {len(r['pre'])} samples; snap9 0x0acc {hexs(r['snap9'])}; scratch tim "
            + " ".join(hexs(x) for x in r["tims"]))
        lines += outcome_lines(n, ctl, hyp)
        ctl_all.update({f"{n}:{k}": s for k, s in ctl.items()})
        hyp_all[n] = hyp
        rl.append(rule_of("R2", ctl, hyp))
        if any(x is not None for x in r["tims"]) and not all(x == 0x00ABCDE0 for x in r["tims"]):
            rl.append("NOTE: scratch tim is not 0x00abcde0 throughout: the program did not run "
                      "as recorded")
    if not rl:
        rl = ["N3c-R2 RULE: CANNOT TELL (no row kept)"]
    lines.append("SUMMARY: tim: controls: " + ("every control passed" if SK.gate(ctl_all).ok
                                               else "; ".join(SK.gate(ctl_all).problems)))
    return lines, ctl_all, hyp_all, rl


# ---- post ---------------------------------------------------------------------------------------
def score_post(d):
    preds = K.predictions(KP, "post")
    cases = K.rows(d, "cases.tsv")
    controls, lines = {}, []
    for r in K.table(KP, "post"):
        n = r["name"]
        got = reading(K.text(d, n + ".txt")).get("diff") if n in cases and \
            cases[n]["class"] == "ok" else None
        want = preds.get(n, {}).get("diff", {})
        state = None if got is None or not want else got in want.values()
        controls[n] = state
        lines.append(f"CONTROL {n}: diff {got} (frozen {sorted(want.values())}): "
                     f"{state_word(state)}")
    g = SK.gate(controls)
    lines.append("SUMMARY: post: " + ("the stock firmware drew the triangle and the fill exactly "
                                      "after the tim stage" if g.ok else
                                      "controls FAILED or cannot tell: " + "; ".join(g.problems)))
    return lines, controls


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in ("own", "tim"):
        lines, _, _, rl = (score_own if argv[1] == "own" else score_tim)(argv[2])
        print("\n".join(lines + rl))
        return 0
    if len(argv) >= 3 and argv[1] == "post":
        print("\n".join(score_post(argv[2])[0]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
