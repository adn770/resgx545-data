#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r9-faults's scorer (Q108: the PTE flags, stages xf2 and tri2; Q076: alias_skip, stage
bif). Every verdict rule comes from kit/scorekit.py, the kept files are read through
kit/kitscore.py (byte copies of resgx545 f32dfacc8db8, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, READ and ROW lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A kept row reads (NAME.txt, the tool's output; NAME.dmesg, its kernel-log slice):
  job      the first `job:` line: ok, rejected, faulted, hung, overflowed (`scene overflowed the
           parameter buffer, context kept`) or failed
  jobs     every `job:` line, in order; hashes, diffs: every `target:` hash and `diff:` count
  src, fb, ro, renders (tri's last line: Nok, KofNovfM, failedK), dstore (the depth store's
  changed dwords of `depth store #1`)
  pte      the kernel's `vm_map A +S: PTE flags F` lines: {A: (S, F)}
  faults   the kernel's `BIF fault S at A` lines: [(S, A)]
Q108 (gen/make.py): a knob row's outcome is exact (job ok, diff 0, the row's reference hash: the
stage's knob-free control or, for the sizes no control has, the library mock's fill hash, which
equals the laptop's; tri --depth rows: tri-c-depth's own hash as read), diff (job ok, pixels
differ), fault and fault@PAGE (a fault line's page inside the flagged mapping: the first such),
or the readings matching no hypothesis, fault-elsewhere and hang; rejected and other read nothing
(cannot tell). Its premise is the PTE line of its mapping with the frozen flags.
Q076: a row is exact (every render's job ok or overflowed-kept as its control, diff 0 each, the
control's hashes, the count of renders), needed (a fault whose page lies in a buffer the mask
leaves out, the layout of gen/make.py), fault-elsewhere, hang or other.
A hypothesis holds on a row when the frozen outcome is the one read, FAILS when another was read,
and cannot tell without the premise, a job, or the row's controls (scorekit.headline)."""
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
REQUIRED = {s: PER_ROW + ("cases.tsv", "void.tsv", "readings.tsv") for s in G.STAGES}
GATES = {}          # no stage gates another: each stage's own controls gate its rows
NOT_READ = ("rejected", "other")
FLAGS = {G.WO: "WRITEONLY", G.CACHED: "CACHECONSISTENT", G.EDMPROT: "EDMPROTECT",
         G.WO | G.EDMPROT: "WRITEONLY|EDMPROTECT"}
# the reference hash of an exact knob row whose size no knob-free control draws: the library
# mock's fill hash of the tool's source (tests/test_twin.py), which equals the laptop's for the
# default fill (0xb60c6095080bd325, r7-rp's health fill)
REF_HASH = {"fill-low": "0x1b53c7736b16fb25", "fill-64": "0xc3ac149063f58325"}


def producible(row):
    return G.producible(row["args"])


def parse(out, dmesg):
    r = {"pte": {}, "faults": [], "jobs": [], "hashes": [], "diffs": []}
    for m in re.finditer(r"^job: ([a-z]+)(.*)$", out, re.M):
        j = m[1]
        if j == "failed":
            j = "faulted" if m[2].startswith(": job faulted") else \
                "hung" if m[2].startswith(": job hung") else \
                "overflowed" if m[2].startswith(": scene overflowed the parameter buffer, context kept") else "failed"
        r["jobs"].append(j)
    if r["jobs"]:
        r["job"] = r["jobs"][0]
    r["hashes"] = re.findall(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", out, re.M)
    r["diffs"] = re.findall(r"^diff: (\d+) of ", out, re.M)
    if r["hashes"]:
        r["hash"] = r["hashes"][0]
    if len(r["hashes"]) > 1:
        r["hash2"] = r["hashes"][1]
    if r["diffs"]:
        r["diff"] = r["diffs"][0]
    for key, rx in (("src", r"^copy: source at (0x[0-9a-f]+),"), ("fb", r"^layout: fb (0x[0-9a-f]+)"),
                    ("ro", r"^(PASS|FAIL) read-only-faults$"),
                    ("dstore", r"^depth store #1: \d+ dwords, (\d+) changed")):
        m = re.search(rx, out, re.M)
        if m:
            r[key] = m[1]
    m = re.search(r"^tri: (?:(\d+) renders ok|(\d+) of (\d+) renders ok, (\d+) overflowed|FAILED after (\d+) renders?)$",
                  out, re.M)
    if m:
        r["renders"] = f"{m[1]}ok" if m[1] else f"{m[2]}of{m[3]}ovf{m[4]}" if m[2] else f"failed{m[5]}"
    for m in re.finditer(r"vm_map (0x[0-9a-f]+) \+(0x[0-9a-f]+): PTE flags (0x[0-9a-f]+)", dmesg):
        r["pte"][int(m[1], 16)] = (int(m[2], 16), int(m[3], 16))
    for m in re.finditer(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", dmesg):
        r["faults"].append((int(m[1], 16), int(m[2], 16)))
    if r["faults"]:
        s, a = r["faults"][-1]
        r["fstat"], r["fpage"] = f"0x{s:x}", f"0x{a & ~0xfff:08x}"
    return r


def read_row(d, n):
    return parse(K.text(d, n + ".txt"), K.text(d, n + ".dmesg"))


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        read_row(d, n)


def state_word(st):
    return "PASS" if st else "FAILED" if st is False else "cannot tell"


def ctl_state(kind, want, case, got):
    """A control: PASS when every frozen quantity is read, FAILED when one differs or the job did
    not end as frozen, cannot tell (None) when it did not run."""
    if case is None:
        return None, "did not run"
    probs = []
    if kind in ("isolation", "ta3d", "buf0"):
        if case["class"] != "fault":
            probs.append(f"class {case['class']}, not the frozen fault")
        last = got["faults"][-1] if got["faults"] else None
        rd = dict(got, ro=got.get("ro"), rostat=f"0x{last[0]:x}" if last else None,
                  ropage=f"0x{last[1] & ~0xfff:08x}" if last else None)
    else:
        if case["class"] != "ok" or case["rc"] != 0:
            probs.append(f"class {case['class']} rc {case['rc']}, not a completed job")
        rd = got
    for q, v in want.items():
        if rd.get(q) != v:
            probs.append(f"{q} {rd.get(q)} (frozen {v})")
    return (False, "; ".join(probs)) if probs else (True, "as frozen")


def q_outcome(got, case, start, size, ref_hash):
    """(outcome, the fault's page word) of a Q108 knob row."""
    j = got.get("job")
    if j == "rejected":
        return "rejected", None
    if j == "hung" or case["class"] == "hang":
        return "hang", None
    if j == "faulted" or case["class"] == "fault":
        here = [f for f in got["faults"] if start <= (f[1] & ~0xfff) < start + size]
        if not here:
            return "fault-elsewhere", None
        return "fault", f"fault@0x{here[0][1] & ~0xfff:08x}"
    if j == "ok" and got.get("diff") is not None:
        if got["diff"] == "0" and ref_hash is not None and got.get("hash") == ref_hash:
            return "exact", None
        if got["diff"] != "0":
            return "diff", None
    return "other", None


def kind_of(stage, row):
    """The control kind of a table row (gen/make.py's CTL or BCTL key)."""
    if stage == "bif":
        return next(r[4] for r in G.BROWS if r[0] == row["name"])
    return next(r[4] for r in G.QROWS if r[1] == row["name"])


def controls_of(stage, table, preds, cases, d):
    controls, lines, read = {}, [], {}
    for r in table:
        if r["set"] != "control":
            continue
        n = r["name"]
        want = {q: next(iter(m.values())) for q, m in preds[n].items()}
        got = read_row(d, n) if n in cases else {"pte": {}, "faults": []}
        st, why = ctl_state(kind_of(stage, r), want, cases.get(n), got)
        controls[n] = st
        read[n] = got
        lines.append(f"CONTROL {n}: {state_word(st)} ({why})")
    return controls, lines, read


def q_depends(stage, name, cmd, controls):
    """The controls a Q108 row depends on: every control of xf2; in tri2 the plain triangle's,
    and tri-c-depth too for a tri --depth row."""
    if stage == "xf2":
        return dict(controls)
    keep = {"tri-c", "tri-c-end"} | ({"tri-c-depth"} if cmd == "tri-depth" else set())
    return {k: v for k, v in controls.items() if k in keep}


def q_verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, stage)
    controls, lines, ctl_read = controls_of(stage, table, preds, cases, d)
    spec = {r[1]: r for r in G.QROWS}
    rows = {}           # {(group, hypothesis): [(name, state, set)]}
    deps = {}
    for r in table:
        if r["set"] == "control":
            continue
        n = r["name"]
        _, _, sset, _, cmd, mp, flag, groups, _ = spec[n]
        p = preds[n]
        start, size = (int(x, 16) for x in p["map"]["KNOB"].split("+"))
        pte, access = int(p["pte"]["KNOB"], 16), p["access"]["KNOB"]
        if cmd == "tri-depth":
            ref = ctl_read.get("tri-c-depth", {}).get("hash") if controls.get("tri-c-depth") else None
        else:
            ref = REF_HASH.get(cmd) or G.CTL[cmd]["hash"][0]
        case = cases.get(n)
        seen = page = None
        if case is None:
            why = "did not run (void or not reached)"
        else:
            got = read_row(d, n)
            logged = got["pte"].get(start)
            if logged is None or logged[1] != pte:
                why = f"no PTE line 0x{pte:x} at 0x{start:08x} (logged {logged}): the knob's premise"
            else:
                seen, page = q_outcome(got, case, start, size, ref)
                why = (f"job {got.get('job')} hash {got.get('hash')} diff {got.get('diff')}; PTE 0x{start:08x} "
                       f"+0x{logged[0]:x} flags 0x{logged[1]:x}; faults "
                       + (", ".join(f"0x{s:x} at 0x{a:08x}" for s, a in got["faults"]) or "none"))
        deps[n] = q_depends(stage, n, cmd, controls)
        lines.append(f"READ {n} [{sset}] ({FLAGS[flag]} on {access} 0x{start:08x}): "
                     f"{(page or seen) or 'cannot tell'}; {why}"
                     + ("; not a reading (the job did not run as built)" if seen in NOT_READ else ""))
        for g in groups:
            q = ("page:" if g.endswith("PAGE") else "outcome:") + g
            word = (page or seen) if g.endswith("PAGE") else seen
            for h, v in p[q].items():
                state = None if seen is None or seen in NOT_READ else word == v
                rows.setdefault((g, h), []).append((n, state, sset))
                lines.append(f"ROW {n} {g} {h} (frozen {v}): "
                             f"{'held' if state else 'FAILED' if state is False else 'cannot tell'}")
    summ = []
    for (g, h), st in rows.items():
        use = [(n, s) for n, s, sset in st if g not in G.HELDOUT_ONLY or sset == "heldout"]
        if not use:
            continue
        ctl = {}
        for n, _ in use:
            ctl.update(deps[n])
        claim = f"Q108 {g}, {h}: {G.WHY[h]}"
        summ.append(f"SUMMARY: {stage} {g} {h}: " + SK.headline(claim, ctl, [s for _, s in use]))
    return controls, rows, lines, summ


def b_outcome(got, case, mask, ctl_want, n_renders):
    if got.get("job") == "rejected":
        return "rejected"
    if got.get("job") == "hung" or case["class"] == "hang":
        return "hang"
    if got.get("job") == "faulted" or case["class"] == "fault":
        left = [G.buf_range(i) for i in G.buffers(mask)]
        if any(lo <= (a & ~0xfff) < hi for _, a in got["faults"] for lo, hi in left):
            return "needed"
        return "fault-elsewhere"
    if case["class"] != "ok" or not got["jobs"]:
        return "other"
    plain = ctl_want["job"] == "ok"
    want_jobs = ["ok" if plain else "overflowed"] * n_renders
    hashes = [ctl_want["hash"], ctl_want["hash2"]]
    want_hashes = [hashes[i % 2] for i in range(n_renders)]
    want_renders = f"{n_renders}ok" if plain else f"0of{n_renders}ovf{n_renders}"
    if got["jobs"] == want_jobs and got["diffs"] == ["0"] * n_renders and \
            got["hashes"] == want_hashes and got.get("renders") == want_renders:
        return "exact"
    if got["jobs"] == want_jobs and any(x != "0" for x in got["diffs"]):
        return "diff"
    return "other"


def b_verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, stage)
    controls, lines, _ = controls_of(stage, table, preds, cases, d)
    spec = {r[0]: r for r in G.BROWS}
    rows = {}           # {hypothesis: {base name: [states]}}
    deps = {}
    for r in table:
        if r["set"] == "control":
            continue
        n = r["name"]
        _, sset, mask, args, ctl, _ = spec[n]
        p = preds[n]
        cname = p["control"]["KNOB"]
        cwant = {q: next(iter(m.values())) for q, m in preds[cname].items()}
        a = args.split()
        nr = int(a[a.index("-n") + 1])
        case = cases.get(n)
        seen = None
        if case is None:
            why = "did not run (void or not reached)"
        else:
            got = read_row(d, n)
            seen = b_outcome(got, case, mask, cwant, nr)
            why = (f"jobs {','.join(got['jobs']) or '-'}; renders {got.get('renders')}; hashes "
                   f"{','.join(got['hashes']) or '-'}; diffs {','.join(got['diffs']) or '-'}; faults "
                   + (", ".join(f"0x{s:x} at 0x{x:08x}" for s, x in got["faults"]) or "none"))
        keep = {k for k in controls if k != "bif-c-ovf"} | ({"bif-c-ovf"} if ctl == "ovf" else set())
        deps[n] = {k: v for k, v in controls.items() if k in keep}
        left = ",".join(str(i) for i in G.buffers(mask))
        lines.append(f"READ {n} [{sset}] (mask 0x{mask:x}: buffers {left} left out): {seen or 'cannot tell'}; {why}"
                     + ("; not a reading (the job did not run as built)" if seen in NOT_READ else ""))
        base = n[:-3] if sset == "replicate" else n
        for h, v in p["outcome"].items():
            state = None if seen is None or seen in NOT_READ else seen == v
            rows.setdefault(h, {}).setdefault(base, []).append((state, n))
            lines.append(f"ROW {n} {h} (frozen {v}): "
                         f"{'held' if state else 'FAILED' if state is False else 'cannot tell'}")
    summ = []
    for h, by in rows.items():
        states, ctl = [], {}
        for base, reps in by.items():
            if len(reps) > 1:
                c = SK.combine([s for s, _ in reps])
                lines.append(f"REPLICATES {base} {h}: {c} ({', '.join(x for _, x in reps)})")
                states.append(True if c == "held" else False if c == "refuted" else None)
            else:
                states.append(reps[0][0])
            for _, x in reps:
                ctl.update(deps[x])
        claim = f"Q076 alias_skip, {h}: {G.BWHY[h]}"
        summ.append(f"SUMMARY: {stage} {h}: " + SK.headline(claim, ctl, states))
    return controls, rows, lines, summ


def verdicts(stage, d):
    return b_verdicts(stage, d) if stage == "bif" else q_verdicts(stage, d)


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
