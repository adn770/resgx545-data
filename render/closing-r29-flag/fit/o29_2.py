#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fit/o29_2.py: O29-2 (closing29/plan/rank-round29.md section 1, Q163; the fold's record E1113).
What decides a block-2 VDM_STATE1 bits 11:9 = 1 job (v = 1 in block 2)? Standard library only.
Every input is read at the data commit given (default: session.toml [freeze] data) with
`git show`, never the working tree:

  vdm/state-units (E545's 11.31 sweeps, scripts units, risky, grid in run order; output.txt rc,
      kernel.log case markers, `hung, recovering` and `SGX reset:` lines; c = 0 at each script's
      start, as E1021),
  vdm/verification-1141ta/.../vdm-series-b-all (E701's six series; a row without `noreset` follows
      the harness's reset; kernel.log markers and hung lines),
  render/closing-r13-flag/out/20261113-220930/f3 (E1035; the kit's class column; tables/f3.txt's
      knobs for noreset).

Fit set: every block-2 v = 1 job of E545 and E701 (15 jobs). Held-out set: E1035's three
(f3-v1c0, f3-v1c2, f3-v1c5). c is E700's M1 counter (a completed job adds the sum of v - 2 over
its blocks, g(1) = -1, g(0) = 0, c not below 0; a hang or a reset sets c = 0), teacher-forced.

Deciders (each a function of the job's inputs and the history only):
  D-C        a lookup on c fitted on the fit set (majority; a tie or an unseen c: hang)
  D-BITS     a lookup on block 2's bits 7:0 fitted on the fit set (same rule)
  D-M3       hang iff c = 0 (E701's post hoc M3 clause)
  D-PREVADD  completes iff the job right before (no reset between) completed with a non-zero add
             (formed on the fit set alone)
  H-PREV16   completes iff the job right before (no reset between) completed with a block at
             v 1 or 6 (formed AFTER E1035 was read: post hoc on all 18; E545's own V16 reading,
             moved one job back) [infer]
  H-ALWAYS   every block-2 v = 1 job hangs (E1035 3 of 3 on module B60AB0B4; the completions are
             all on earlier modules, E545 7ED723C2, E701 B21FDA82)

Freeze rule (R29-2 a): h2 is built only if a decider fits E1035's 3 of 3 and E701's c = 8
completion (vs-B2-v1-at-8-02); the best such decider is frozen with its rivals, and h2's rows are
placed where they part (gen/make.py, H2_ROWS).

  python3 fit/o29_2.py [DATA_COMMIT]
"""
import os
import re
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("RESGX545_DATA_REPO", "/Users/jtorra/src/resgx545-data")
SU = "vdm/state-units"
SB = "vdm/verification-1141ta/out-hw/p1141ta-dumps/vdm-series-b-all"
R13 = "render/closing-r13-flag"
R13F3 = R13 + "/out/20261113-220930/f3"
DEFAULT_B2 = 0x0a022405          # block 2's VDM_STATE1 as the tool writes it (state-units' grid rows)
HELD = ("f3-v1c0", "f3-v1c2", "f3-v1c5")


def show(commit, path):
    return subprocess.run(["git", "-C", DATA, "show", f"{commit}:{path}"], check=True,
                          capture_output=True).stdout.decode(errors="replace")


def job_input(args):
    """(v1, v2, block 2's bits 7:0) of an E700-stream probe or E413's `tri --poke vdm:1^=` job."""
    v = {1: 2, 9: 2}
    bits = DEFAULT_B2 & 0xFF
    for word, op, val in re.findall(r"(?:--vdm |--poke vdm:)(\d+)(\^?)=(0x[0-9a-fA-F]+)", args):
        w, x = int(word), int(val, 16)
        if op:
            v[w] = (2 ^ (x >> 9)) & 7
        else:
            v[w] = (x >> 9) & 7
            if w == 9:
                bits = x & 0xFF
    return v[1], v[9], bits


def add(v1, v2):
    g = {0: 0, 1: -1}
    return sum(g.get(v, v - 2) for v in (v1, v2))


def sections(log):
    """{case: (hung, resets)} from a kernel log with `resgx545 case NAME` markers."""
    out, cur = {}, None
    for ln in log.splitlines():
        m = re.search(r"resgx545 case (\S+) ", ln)
        if m:
            cur = m.group(1)
            out[cur] = [False, 0]
            continue
        if ln.startswith("## script"):
            cur = None
        if cur:
            out[cur][0] |= "hung, recovering" in ln
            out[cur][1] += "SGX reset:" in ln
    return out


def jobs(commit):
    """[(source, sequence, name, v1, v2, bits, reset_before, end)] in run order."""
    rows = []
    # E545: three scripts, c = 0 at each start; a reset only after a hang or at a script's end
    su = [ln.split("\t") for ln in show(commit, f"{SU}/cases.tsv").splitlines()[1:] if ln]
    rc, cur = {}, None
    for ln in show(commit, f"{SU}/output.txt").splitlines():
        m = re.match(r"== (\S+) set=", ln)
        cur = m.group(1) if m else cur
        m = re.match(r"\s+rc (\d+)", ln)
        if m and cur:
            rc[cur] = int(m.group(1))
    sec = sections(show(commit, f"{SU}/kernel.log"))
    prev_script, prev_reset = None, True
    for f in su:
        name, script, args = f[0], f[1], f[5]
        hung, resets = sec.get(name, (False, 0))
        end = "hang" if hung else "ok" if rc.get(name) == 0 else "void"
        first = script != prev_script
        rows.append(("E545", script, name, *job_input(args), first or prev_reset, end))
        prev_script, prev_reset = script, bool(hung or resets)
    # E701: series-b, a reset before every row without noreset
    sec = sections(show(commit, f"{SB}/kernel.log"))
    for ln in show(commit, f"{SB}/cases.tsv").splitlines()[1:]:
        f = ln.split("\t")
        name, knobs, args = f[0], f[5], f[7]
        end = "hang" if sec.get(name, (False, 0))[0] else "ok"
        rows.append(("E701", name.rsplit("-", 1)[0], name, *job_input(args), "noreset" not in knobs, end))
    # E1035: r13-flag f3 (the kit resets before every row without noreset)
    tab = {}
    for ln in show(commit, f"{R13}/tables/f3.txt").splitlines():
        if ln and not ln.startswith("#"):
            p = ln.split("|", 5)
            tab[p[0]] = p
    lines = show(commit, f"{R13F3}/cases.tsv").splitlines()
    head = lines[0].split("\t")
    for ln in lines[1:]:
        f = dict(zip(head, ln.split("\t")))
        p = tab[f["name"]]
        rows.append(("E1035", "r13-f3", f["name"], *job_input(p[5]), "noreset" not in p[3].split(),
                     f["class"]))
    return rows


def v1_rows(rows):
    """The block-2 v = 1 jobs with c (M1) before and the job before them."""
    out, c, prev = [], 0, None
    for src, seq, name, v1, v2, bits, reset, end in rows:
        if reset:
            c, prev = 0, None
        if v2 == 1 and v1 == 2:
            out.append(dict(src=src, name=name, c=c, bits=bits, prev=prev, end=end))
        if end == "hang":
            c, prev = 0, None
        elif end == "ok":
            prev = (v1, v2, add(v1, v2))
            c = max(c + add(v1, v2), 0)
        else:
            prev = None
    return out


def lookup(fit, key):
    tab = {}
    for r in fit:
        tab.setdefault(r[key], []).append(r["end"] == "hang")
    return {k: sum(v) * 2 >= len(v) for k, v in tab.items()}


def deciders(fit):
    tc, tb = lookup(fit, "c"), lookup(fit, "bits")
    return {
        "D-C": lambda r: tc.get(r["c"], True),
        "D-BITS": lambda r: tb.get(r["bits"], True),
        "D-M3": lambda r: r["c"] == 0,
        "D-PREVADD": lambda r: not (r["prev"] and r["prev"][2] != 0),
        "H-PREV16": lambda r: not (r["prev"] and ({1, 6} & set(r["prev"][:2]))),
        "H-ALWAYS": lambda r: True,
    }


def main(argv):
    cfg = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
    commit = argv[1] if len(argv) > 1 else cfg["freeze"]["data"][:9]
    v1 = v1_rows(jobs(commit))
    fit = [r for r in v1 if r["src"] != "E1035"]
    held = [r for r in v1 if r["src"] == "E1035"]
    assert [r["name"] for r in held] == list(HELD), [r["name"] for r in held]
    print(f"O29-2 on data {commit}: {len(fit)} fit jobs (E545, E701), {len(held)} held out (E1035)")
    print("jobs (source name c bits prev(v1,v2,add) end):")
    for r in v1:
        print(f"  {r['src']:5} {r['name']:20} c={r['c']} bits={r['bits']} prev={r['prev']} {r['end']}")
    d = deciders(fit)
    e8 = next(r for r in fit if r["name"] == "vs-B2-v1-at-8-02")
    ok = []
    for n, f in d.items():
        rf = sum(f(r) == (r["end"] == "hang") for r in fit)
        rh = sum(f(r) == (r["end"] == "hang") for r in held)
        c8 = f(e8) == (e8["end"] == "hang")
        print(f"{n}: fit {rf} of {len(fit)}, held out {rh} of {len(held)}, E701's c = 8 completion "
              f"{'right' if c8 else 'wrong'}")
        if rh == len(held) and c8:
            ok.append((rf + rh, n))
    best = max(ok)[1] if ok else None
    print(f"rule: a decider fits E1035's 3 of 3 and E701's c = 8 completion: "
          + (f"yes, {best} (h2 is built; post hoc: formed with E1035 read)" if best else "no (h2 is not built)"))
    print("frozen: H-PREV16 against D-PREVADD (the fit set's own form) and H-ALWAYS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
