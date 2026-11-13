#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r8-k2's scorer (Q108, the PTE flags). Every verdict rule comes from kit/scorekit.py,
the kept files are read through kit/kitscore.py (byte copies of resgx545 68b313611d70, pinned in
FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, READ and ROW lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A kept row reads (NAME.txt, the tool's output; NAME.dmesg, its kernel-log slice):
  job      the `job:` line: ok, rejected, faulted, hung, failed
  hash, diff, src (copy --print-addrs), fb (tri's layout line)
  pte      the kernel's `vm_map A +S: PTE flags F` lines: {A: (S, F)}
  faults   the kernel's `BIF fault S at A` lines: [(S, A)]
A knob row's outcome (gen/make.py): exact (job ok, diff 0, the stage's knob-free hash), diff (job
ok, pixels differ), fault (faulted, a fault line's page inside the mapping), and the readings that
match no hypothesis: fault-elsewhere, hang; rejected and other read nothing (cannot tell). Its premise is the PTE line of its
mapping with the frozen flags (`pte`, RO the tool's own); without it the row cannot tell.
A hypothesis holds on a row when the frozen outcome is the one read, FAILS when another was read,
and cannot tell without the premise, a job, or the stage's controls (scorekit.headline)."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import make as G  # noqa: E402

PER_ROW = (".txt", ".dmesg")
REQUIRED = {s: PER_ROW + ("cases.tsv", "void.tsv", "readings.tsv") for s in G.LIMIT}
GATES = {}          # no stage gates another: each stage's own controls gate its rows
# a job the kernel rejected, or one that ended without a job line, read nothing (r8-geo's 23 rows):
# cannot tell, never FAILED; a hang or a fault outside the mapping was read and matches no hypothesis
NOT_READ = ("rejected", "other")
GROUPS = {G.WO: "WRITEONLY", G.CACHED: "CACHECONSISTENT", G.EDMPROT: "EDMPROTECT"}


def producible(row):
    return G.producible(row["args"])


def parse(out, dmesg):
    r = {"pte": {}, "faults": []}
    m = re.search(r"^job: ([a-z]+)", out, re.M)
    if m:
        j = m[1]
        if j == "failed":
            j = "faulted" if re.search(r"^job: failed: job faulted", out, re.M) else \
                "hung" if re.search(r"^job: failed: job hung", out, re.M) else "failed"
        r["job"] = j
    for key, rx in (("hash", r"^target: \d+x\d+ hash (0x[0-9a-f]+)"), ("diff", r"^diff: (\d+) of "),
                    ("src", r"^copy: source at (0x[0-9a-f]+),"), ("fb", r"^layout: fb (0x[0-9a-f]+)"),
                    ("ro", r"^(PASS|FAIL) read-only-faults$")):
        m = re.search(rx, out, re.M)
        if m:
            r[key] = m[1]
    for m in re.finditer(r"vm_map (0x[0-9a-f]+) \+(0x[0-9a-f]+): PTE flags (0x[0-9a-f]+)", dmesg):
        r["pte"][int(m[1], 16)] = (int(m[2], 16), int(m[3], 16))
    for m in re.finditer(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", dmesg):
        r["faults"].append((int(m[1], 16), int(m[2], 16)))
    return r


def read_row(d, n):
    return parse(K.text(d, n + ".txt"), K.text(d, n + ".dmesg"))


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        read_row(d, n)


def ctl_state(name, cmd, want, case, got):
    """A control: PASS when every frozen quantity is read, FAILED when one differs or the job did
    not end as frozen, cannot tell (None) when it did not run."""
    if case is None:
        return None, "did not run"
    probs = []
    if cmd == "isolation":
        if case["class"] != "fault":
            probs.append(f"class {case['class']}, not the frozen fault")
        last = got["faults"][-1] if got["faults"] else None
        rd = {"ro": got.get("ro"), "rostat": f"0x{last[0]:x}" if last else None,
              "ropage": f"0x{last[1] & ~0xfff:08x}" if last else None}
    else:
        if case["class"] != "ok" or case["rc"] != 0:
            probs.append(f"class {case['class']} rc {case['rc']}, not a completed job")
        rd = got
    for q, v in want.items():
        if rd.get(q) != v:
            probs.append(f"{q} {rd.get(q)} (frozen {v})")
    return (False, "; ".join(probs)) if probs else (True, "as frozen")


def outcome(got, case, start, size, ctl_hash):
    j = got.get("job")
    if j == "rejected":
        return "rejected"
    if j == "hung" or case["class"] == "hang":
        return "hang"
    if j == "faulted" or case["class"] == "fault":
        here = [f for f in got["faults"] if start <= (f[1] & ~0xfff) < start + size]
        return "fault" if here else "fault-elsewhere"
    if j == "ok" and got.get("diff") is not None:
        if got["diff"] == "0" and got.get("hash") == ctl_hash:
            return "exact"
        if got["diff"] != "0":
            return "diff"
    return "other"


def verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    controls, lines = {}, []
    ctl_hash = {}
    table = K.table(KP, stage)
    for r in table:
        if r["set"] != "control":
            continue
        n, cmd = r["name"], r["args"].split()[0]
        want = {q: next(iter(m.values())) for q, m in preds[n].items()}
        got = read_row(d, n) if n in cases else {"pte": {}, "faults": []}
        st, why = ctl_state(n, cmd, want, cases.get(n), got)
        controls[n] = st
        if "hash" in want:
            ctl_hash.setdefault(cmd, want["hash"])
        lines.append(f"CONTROL {n}: {'PASS' if st else 'FAILED' if st is False else 'cannot tell'} ({why})")
    rows = {}          # {flag: {hypothesis: [states]}}
    for r in table:
        if r["set"] == "control":
            continue
        n, cmd = r["name"], r["args"].split()[0]
        p = preds[n]
        start, size = (int(x, 16) for x in p["map"]["KNOB"].split("+"))
        pte, access = int(p["pte"]["KNOB"], 16), p["access"]["KNOB"]
        flag = pte & ~G.RO
        hyps = p["outcome"]
        case = cases.get(n)
        if case is None:
            seen, why = None, "did not run (void or not reached)"
        else:
            got = read_row(d, n)
            logged = got["pte"].get(start)
            if logged is None or logged[1] != pte:
                seen, why = None, f"no PTE line 0x{pte:x} at 0x{start:08x} (logged {logged}): the knob's premise"
            else:
                seen = outcome(got, case, start, size, ctl_hash.get(cmd))
                why = (f"job {got.get('job')} hash {got.get('hash')} diff {got.get('diff')}; PTE 0x{start:08x} "
                       f"+0x{logged[0]:x} flags 0x{logged[1]:x}; faults "
                       + (", ".join(f"0x{s:x} at 0x{a:08x}" for s, a in got["faults"]) or "none"))
        matched = [h for h, v in hyps.items() if v == seen]
        lines.append(f"READ {n} ({GROUPS[flag]} on {access} 0x{start:08x}): {seen or 'cannot tell'}; {why}"
                     + ("" if seen in (None,) + NOT_READ or matched else "; matches no frozen hypothesis")
                     + ("; not a reading (the job did not run as built)" if seen in NOT_READ else ""))
        for h, v in hyps.items():
            state = None if seen is None or seen in NOT_READ else seen == v
            rows.setdefault(flag, {}).setdefault(h, []).append((n, state))
            lines.append(f"ROW {n} {h} (frozen {v}): "
                         f"{'held' if state else 'FAILED' if state is False else 'cannot tell'}")
    summ = []
    for flag, hs in rows.items():
        for h, st in hs.items():
            claim = f"Q108 {GROUPS[flag]}, {h}: {G.WHY[h]}"
            summ.append(f"SUMMARY: {stage} {GROUPS[flag]} {h}: " +
                        SK.headline(claim, controls, [s for _, s in st]))
    return controls, rows, lines, summ


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        _, _, lines, summ = verdicts(argv[1], argv[2])
        print("\n".join(lines + summ))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
