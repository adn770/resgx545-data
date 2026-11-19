#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: the scorer of r40-s-sb, r40-s-s2 and r40-s-pass (Q128, the split of r39-n3d-z's Z-DONE;
closing29/n3d/design.md §3, N3d; STEP below says which: SB = Z with s2 0, S2 = Z with our old
emit word, SP = Z from the timer pass, no kick). Built on r39-n3d-z's scorer. Every verdict rule comes from kit/scorekit.py, the kept files
are read through kit/kitscore.py (byte copies of the frozen resgx545 commit, pinned in
FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY and RULE lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Stage own has one row (c1-a). Its readings (§3), from the kept files:
  the page   NAME.own_res.json (fwtask_run.py page, after the job whatever its end), else the
             runner's stop dump NAME.stop0-own_res.json; X0 = dword 70, S1 = dword 84, M4 =
             dwords 80-81, state = dword 2; `fill` is the host's 0xdeadc0de
  K0         (SB, S2: the kick) the record's k0 (NAME.txt): cmd and slot 1 (dword 0 read) between
             the command write and the kick
  Δtick      printed, never scored: the record's `ticks_from_kick` (SB, S2: HostCtl dword 12 from
             K0 to 30 ms after the window) and `ticks` (from the command write)
  alive      the record's alive_at_stop.advancing (NAME.txt: the tick after a runner stop)
  T          0x0acc in NAME.snap9.regs and in the stop dump NAME.stop0-regs.txt (about 0.3 s
             apart; one read after an ok end). `running`: every read has bit 24 set and bits 23:0
             at most 400000, and two reads differ; a constant: every read equals it; else (two
             unequal reads while not running, or equal reads while running) cannot tell
Each frozen outcome (predictions/own.tsv, model = the outcome) holds when every one of its
quantities matches, FAILED when one does not; the row's outcome is the one that holds. None
holding (T any other value, a combination the table lacks) is CANNOT TELL.

Controls (every row; all can fail; predictions/own.tsv model CTL): PG page dword 0 = 0x4e574f53;
(SB, S2) K0 cmd 1 and slot 1 the fill right before the kick (the ticks did not emit); K1 (E0 in
SP) slot 1 = M1 and the run id, cmd 0 (the gate fired: r37's E0); T0 snap0's 0x0acc running (else the timer was
already stopped: cannot tell); B BIF_FAULT (0x0c08) 0 in snap9 (a fault is its own outcome,
kept, not one of the table's).

RULE (N3d), frozen:
  Q128-STEP OUTCOME     every control passed and exactly one frozen outcome holds: that outcome,
                        printed with its meaning (STEP-RUN for any of T1..DONE) and the X0
                        qualifier
  Q128-STEP FAULT       B FAILED: a BIF fault, its own outcome (the kept files are the reading)
  Q128-STEP CANNOT TELL anything else (a control FAILED or unread, no outcome or two); S1 =
                        0x5a5a3304 with T 0 or 0x200 is printed as its own reading (`S1-EARLY`)
Printed, never scored: the arm's kernel log line (the address the emit names, pds=, pdsat= and
pds2= and form=); (SB, S2) the miscinfo reply; the ticks from the command write to K0; Δtick from the
command write against the window; alive; USE0_SERV_EVENT (0x0b14) bit 16 and its count (bits
15:0) minus HostCtl dword 12 in snap0, snap9 and the stop dump; that T1 stops the tick by design
(the tick says nothing once T1 ran); after an ok end only, pa0-pa3 and sa0-sa3 against snap0's
TA3DCtl dwords 0-3 (one exploratory row of the landing, not N3's rule)."""
import json
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STEP = "SP"
KICK = STEP != "SP"
REQUIRED = {"own": (".txt", ".own_res.json", ".gate.json", ".snap0.regs", ".snap9.regs",
                    "cases.tsv", "void.tsv", "readings.tsv"),
            "post": (".txt", "cases.tsv", "void.tsv", "readings.tsv")}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none (own's stop ends)
FILL = 0xDEADC0DE
S1, T3 = 0x5A5A3304, 0x005A3305
SLOT_PA, SLOT_SA, X0_AT, S1_AT = 0x48, 0x4C, 0x46, 0x54
TIM, BIF, SERV = 0x0ACC, 0x0C08, 0x0B14
TIM_RUN, TIM_MAX = 1 << 24, 400000
CTLS = {"PG": ("res:0x0",), "K0": ("k0:cmd", "k0:slot1"), "K1": ("res:0x44", "res:0x45", "res:0x1"),
        "T0": ("snap0:0x0acc",), "B": ("snap9:0x0c08",)} if KICK else \
    {"PG": ("res:0x0",), "E0": ("res:0x44", "res:0x45", "res:0x1"), "T0": ("snap0:0x0acc",),
     "B": ("snap9:0x0c08",)}
MEANING = {
    "NEVER": "the program never started (T running, S1 fill): {}",
    "T1": "started, stopped at a douta",
    "T2": "stopped at the doutu",
    "T3": "doutu issued, entry 1 never stored (or entry 1 died within its first three "
          "instructions: r37's stated residual)",
    "E1": "entry 1 started, stopped after S1",
    "DONE": "all ran",
}
NEVER = {"SB": "with the kick and #14's word, s2 = 0x00020000 is needed",
         "S2": "with the kick and s2 = 0x00020000, #14's sideband is needed",
         "SP": "with #14's word and s2, the kick pass is needed"}
RUN = {"SB": "SB-RUN: s2 is not needed: #14's sideband with the kick pass suffices",
       "S2": "S2-RUN: the sideband is not needed: s2 with the kick pass suffices",
       "SP": "SP-RUN: the kick pass is not needed: #14's word and s2 suffice on a tick"}
WHAT = {f"{s}-{k}": (v.format(NEVER[s]) if k == "NEVER" else f"{v} ({RUN[s]})")
        for s in NEVER for k, v in MEANING.items()}


def state_word(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def producible(row):
    if row["tool"] == "owntask":
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
        if stage == "own":
            K.own_res(d, n)
            K.text(d, n + ".snap0.regs")
            K.text(d, n + ".snap9.regs")
            if r["class"] == "ok":
                K.text(d, n + ".gate.json")


def regs_of(text):
    """{offset: value} of `reg 0xOOOO 0xV` lines and {"hostctl", i: v} of `hostctl 0xOO 0xV`."""
    out = {}
    for m in re.finditer(r"^(reg|hostctl|ta3dctl) (0x[0-9a-f]+) (0x[0-9a-f]{8})$", text, re.M):
        k = int(m.group(2), 16)
        out[k if m.group(1) == "reg" else (m.group(1), k // 4)] = int(m.group(3), 16)
    return out


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
        r = json.loads(K.text(d, n + ".txt"))
        return r["records"][0]
    except (ValueError, KeyError, IndexError, TypeError):
        return {}


def readings_of(d, n):
    page, where = page_of(d, n)
    snaps = {k: regs_of(K.text(d, f"{n}.{k}")) for k in ("snap0.regs", "snap9.regs",
                                                          "stop0-regs.txt")}
    t = [snaps[k][TIM] for k in ("snap9.regs", "stop0-regs.txt") if TIM in snaps[k]]
    rec = record_of(d, n)
    try:
        alive = json.loads(K.text(d, n + ".txt")).get("alive_at_stop", {}).get("advancing")
    except (ValueError, AttributeError):
        alive = None
    k0 = rec.get("k0") if isinstance(rec.get("k0"), dict) else {}
    slot = k0.get("slot") if isinstance(k0.get("slot"), list) else []
    kick = rec.get("kick") if isinstance(rec.get("kick"), dict) else {}
    return dict(page=page, where=where, snaps=snaps, T=t, ticks=rec.get("ticks"),
                ticks_kick=rec.get("ticks_from_kick"), window_ms=rec.get("window_ms"),
                done=rec.get("done"), alive=alive if isinstance(alive, bool) else None,
                k0={"cmd": k0.get("cmd"), "slot1": slot[0] if slot else None,
                    "tick": k0.get("tick")}, kick=kick.get("reply"))


def running(v):
    return v is not None and bool(v & TIM_RUN) and (v & 0xFFFFFF) <= TIM_MAX


def t_match(spec, reads):
    """T against `running` or a constant: True, False, or None (cannot tell)."""
    if not reads:
        return None
    run = all(running(x) for x in reads)
    differ = len(set(reads)) > 1
    if run and (len(reads) == 1 or differ):
        return spec == "running"
    if not differ and not any(running(x) for x in reads):
        return spec != "running" and reads[0] == int(spec, 16)
    return None


def value_ok(spec, q, r):
    """A frozen value against the reading of quantity q: True, False or None."""
    page = r["page"]
    if q == "T":
        return t_match(spec, r["T"])
    if q == "alive":
        return None if r["alive"] is None else r["alive"] == (spec == "true")
    if q == "ticks":
        got = r["ticks"]
    elif q == "ticks_kick":
        got = r["ticks_kick"]
    elif q.startswith("k0:"):
        got = r["k0"].get(q[3:])
        got = got if isinstance(got, int) else None
    elif q.startswith(("snap0:", "snap9:")):
        got = r["snaps"][q[:5] + ".regs"].get(int(q[6:], 16))
    else:
        i = K.res_index(q)
        got = None if page is None else page[i]
    if got is None:
        return None
    if spec == "any":
        return True
    if spec == "running":
        return running(got)
    if spec == "fill":
        return got == FILL
    if spec == "@runid":
        return got == page[3]
    if spec.startswith(">="):
        return got >= int(spec[2:])
    if re.fullmatch(r"[0-9]+-[0-9]+", spec):
        lo, hi = (int(x) for x in spec.split("-"))
        return lo <= got <= hi
    return got == int(spec, 16)


def all_of(states):
    states = list(states)
    if any(s is False for s in states):
        return False
    return None if any(s is None for s in states) else True


def hexs(v):
    return "?" if v is None else f"0x{v:08x}"


def own_row(d, n, q, ran):
    """(controls {PG, K0, K1, T0, B: state}, {outcome: state}, lines) of one own row."""
    r = readings_of(d, n)
    if r["page"] is None or not ran:
        return ({k: None for k in CTLS}, {}, [f"ROW {n}: no results page kept: cannot tell"], r)
    models = sorted({m for mv in q.values() for m in mv if m != "CTL"})
    hyp = {m: all_of(value_ok(mv[m], k, r) for k, mv in q.items() if m in mv) for m in models}
    ctl = {c: all_of(value_ok(q[k]["CTL"], k, r) for k in ks) for c, ks in CTLS.items()}
    p = r["page"]
    lines = [f"ROW {n}: page {r['where']}; run id {p[3]}; X0 {hexs(p[X0_AT])}; S1 "
             f"{hexs(p[S1_AT])}; M4 {hexs(p[0x50])} {hexs(p[0x51])}; state {p[2]}; T "
             f"{' '.join(hexs(x) for x in r['T']) or '?'}; "
             + (f"K0 cmd {r['k0']['cmd']} slot 1 {hexs(r['k0']['slot1'])}; ticks from the kick "
                f"{r['ticks_kick']}; " if KICK else "") + f"ticks {r['ticks']} "
             f"(window {'?' if r['window_ms'] is None else '%.1f' % r['window_ms']} ms); alive "
             f"{'?' if r['alive'] is None else str(r['alive']).lower()}"]
    lines += [f"CONTROL {n}:{k}: {state_word(s)}" for k, s in ctl.items()]
    lines += [f"OUTCOME {n} {m}: {'held' if s else 'FAILED' if s is False else 'cannot tell'}"
              for m, s in hyp.items()]
    return ctl, hyp, lines, r


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


def landing(r):
    v = {k[1]: x for k, x in r["snaps"]["snap0.regs"].items() if isinstance(k, tuple)
         and k[0] == "ta3dctl"}
    p = r["page"]
    pa, sa = p[SLOT_PA:SLOT_PA + 4], p[SLOT_SA:SLOT_SA + 4]
    yes = {True: "yes", False: "no"}
    return (f"LANDING (one exploratory row, not N3's rule): pa0-pa3 {' '.join(map(hexs, pa))}; "
            f"sa0-sa3 {' '.join(map(hexs, sa))}; V0-V3 {' '.join(hexs(v.get(i)) for i in range(4))}"
            f"; pa0 = V0 {yes.get(pa[0] == v.get(0)) if 0 in v else '?'}, pa2 = V2 "
            f"{yes.get(pa[2] == v.get(2)) if 2 in v else '?'}")


def arm_line(d):
    """The arm's kernel log line (kernel.log of the stage), printed, never scored."""
    for ln in K.text(d, "kernel.log").splitlines():
        m = re.search(r"own task armed: .*?(emit image \S+).*?(pds=\S+)(?: (pdsat=\S+))?"
                      r"(?: (pds2=\S+))?(?: (form=\S+))?", ln)
        if m:
            return "ARM (printed, not scored): " + " ".join(x for x in m.groups() if x)
    return "ARM (printed, not scored): no arm line in kernel.log"


def rule(ctl, hyp, r, d=""):
    """The RULE line and the printed notes."""
    held = [m for m, s in hyp.items() if s is True]
    out = [arm_line(d)]
    if ctl.get("B") is False:
        out.append(f"Q128-{STEP} RULE: FAULT: BIF_FAULT is not 0 after the job: its own outcome "
                   "(the kept files are the reading)")
    elif all(s is True for s in ctl.values()) and len(held) == 1:
        out.append(f"Q128-{STEP} RULE: {held[0]}: {WHAT[held[0]]}")
    else:
        why = [f"control {k} {state_word(s)}" for k, s in ctl.items() if s is not True]
        why += ["no frozen outcome holds" if not held else f"{len(held)} outcomes hold"] \
            if len(held) != 1 else []
        out.append(f"Q128-{STEP} RULE: CANNOT TELL ({'; '.join(why)})")
    p = r["page"]
    if p is not None:
        out.append(f"X0 qualifier: {hexs(p[X0_AT])}"
                   + (" (the issuer went on past the emit)" if p[X0_AT] == 0x5A5A3303 else
                      " (the fill: the issuer did not store past the emit)" if p[X0_AT] == FILL
                      else ""))
        stopped = r["T"] and not any(running(x) for x in r["T"]) and len(set(r["T"])) == 1
        if p[S1_AT] == S1 and stopped and r["T"][0] in (0, 0x200):
            out.append(f"S1-EARLY: S1 is set with T {hexs(r['T'][0])}: its own reading (a doutu "
                       "would block the PDS until its task ends [infer, not expected])")
    out.append("TICK: T1 stops the tick by design: the tick readings say nothing about what "
               f"stopped it whenever T1 ran; only the {STEP}-NEVER row (T running) reads as R4's "
               "M-NEVER")
    win = '?' if r['window_ms'] is None else '%.1f' % r['window_ms']
    if KICK:
        out.append(f"TICK: Δtick {r['ticks_kick']} from the kick (K0) to 30 ms after the window; "
                   f"{r['ticks']} from the command write ({win} ms); "
                   + ("?" if not isinstance(r["ticks"], int) or not isinstance(r["ticks_kick"], int)
                      else str(r["ticks"] - r["ticks_kick"])) + " between the command write and K0")
        out.append("KICK (printed, not scored): miscinfo "
                   + (json.dumps(r["kick"], sort_keys=True)[:300] if r["kick"] is not None
                      else "no reply kept"))
    else:
        out.append(f"TICK: Δtick {r['ticks']} from the command write to 30 ms after the window "
                   f"({win} ms; printed, not scored; no kick in this row)")
    out.append(signature(r))
    if held == [f"{STEP}-DONE"] and p is not None:
        out.append(landing(r))
    return out


def score_own(d):
    """(lines, ctl {row:key: state}, hyp {row: {outcome: state}}, rule lines)."""
    preds = K.predictions(KP, "own")
    cases = K.rows(d, "cases.tsv")
    lines, ctl_all, hyp_all, rl = [], {}, {}, []
    for t in K.table(KP, "own"):
        n = t["name"]
        if n not in cases and K.own_res(d, n) is None:
            continue
        ctl, hyp, ln, r = own_row(d, n, preds.get(n, {}), n in cases)
        lines += ln
        ctl_all.update({f"{n}:{k}": s for k, s in ctl.items()})
        hyp_all[n] = hyp
        if r["page"] is not None and n in cases:
            rl += rule(ctl, hyp, r, d)
    if not rl:
        rl = [f"Q128-{STEP} RULE: CANNOT TELL (no row kept)"]
    lines.append("SUMMARY: own: controls: " + ("every control passed" if SK.gate(ctl_all).ok
                                               else "; ".join(SK.gate(ctl_all).problems)))
    return lines, ctl_all, hyp_all, rl


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
                                      "after the disarm" if g.ok else
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
    if len(argv) >= 3 and argv[1] == "own":
        lines, _, _, rl = score_own(argv[2])
        print("\n".join(lines + rl))
        return 0
    if len(argv) >= 3 and argv[1] == "post":
        print("\n".join(score_post(argv[2])[0]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
