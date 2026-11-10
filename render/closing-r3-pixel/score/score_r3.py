#!/usr/bin/env python3
"""score_r3.py: score one R3-pixel stage from its kept files, the loop gate, and the verdict over a session.

  score_r3.py STAGE KEPTDIR        STAGE p-c3 q-f0 q-f1a q-f1b q-t q-v; KEPTDIR = out/ATT/STAGE (copied from the laptop's ~/r3p-out)
  score_r3.py gate STAGE ROOT...   exit 0 open (q-f0's relative loop proved itself), 1 closed, 3 abs and rel loops disagree on the bit
                                   (STAGE q-f1a, q-f1b, q-t; ROOTs: this attempt's out dir, then earlier ones, newest first)
  score_r3.py verdict ROOT...      the two-order q-f1 verdict, q-t, q-v and Q276 from the newest kept dirs
Refuses to run unless `run/freeze_r3.sh verify` passes.  Prints the per-job table and one `SUMMARY:` line.  Run with the scratch venv:
  PYTHONDONTWRITEBYTECODE=1 .../pixel-faults/.venv/bin/python score/score_r3.py q-t out/ATT/q-t
Rules (as R1/R2): a job with no output, an rc that is not a result of the tool, a failed pre-read, a missing dump or a skipped class is
NODATA, tested before any match; a failing control makes what it controls `cannot tell` (Q276: its group only); held-out and replicate
rows are tallied apart from repeats; every scorer ends with one `SUMMARY:` line.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import pathlib  # noqa: E402
import subprocess  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3lib as L  # noqa: E402
import score_c3  # noqa: E402
import score_f  # noqa: E402
import score_t  # noqa: E402
import score_v  # noqa: E402

STAGES = ["p-c3", "q-f0", "q-f1a", "q-f1b", "q-t", "q-v"]


def preds_of(stage):
    return L.load_preds(stage=stage)


def run_stage(stage, d):
    """(text, result) for one stage directory."""
    k = L.Kept(d)
    p = preds_of(stage)
    if stage == "p-c3":
        return score_c3.score_p_c3(k, p)
    if stage == "q-f0":
        return score_f.score_f0(k, p)
    if stage in ("q-f1a", "q-f1b"):
        return score_f.score_f1(k, p, stage[-1])
    if stage == "q-t":
        return score_t.score_t(k, p)
    if stage == "q-v":
        return score_v.score_v(k, p)
    raise SystemExit(f"unknown stage {stage}")


def newest(roots, stage):
    """The first root (newest first) with a kept `stage` directory that has a cases.tsv."""
    for r in roots:
        d = pathlib.Path(r) / stage
        if (d / "cases.tsv").exists():
            return d
    return None


def gate(stage, roots):
    d = newest(roots, "q-f0")
    if d is None:
        print(f"gate {stage}: CLOSED: q-f0 has not run (no kept q-f0 directory in {roots})")
        return 1
    state, msg, _ = score_f.f0_state(L.Kept(d))
    print(f"gate {stage}: {state.upper()}: {msg} (from {d}; rerun: run/r3.sh --only q-f0)")
    return {"open": 0, "edge": 0, "closed": 1, "disagree": 3}[state]


def verdict(roots):
    lines = []
    da, db = newest(roots, "q-f1a"), newest(roots, "q-f1b")
    if da and db:
        a, b = score_f.f1_collect(L.Kept(da)), score_f.f1_collect(L.Kept(db))
        ls, v, unexpl, _ = score_f.f1_verdict(a, b)
        lines.append("Q082 pixel side (q-f1, two orders):")
        lines += ["  " + x for x in ls]
        lines.append("Q082-F: " + "; ".join(f"{h} {t}" for h, t in v.items()) + ("; BOTH H-MA AND H-WD REFUTED (unexplained)" if unexpl else ""))
    else:
        lines.append("Q082-F: q-f1a and q-f1b have not both run (gate closed or not reached)")
    for st, label in (("q-t", "Q082-T"), ("q-v", "Q082-V"), ("p-c3", "Q276")):
        d = newest(roots, st)
        if d is None:
            lines.append(f"{label}: {st} did not run")
            continue
        text, _ = run_stage(st, d)
        s = [x for x in text.splitlines() if x.startswith("SUMMARY:")]
        lines.append(f"{label}: " + (s[-1][len('SUMMARY: '):] if s else "no SUMMARY"))
    print("\n".join(lines))
    return 0


def main(a):
    if a and a[0] == "gate" and len(a) >= 3:
        return gate(a[1], a[2:])
    if a and a[0] == "verdict" and len(a) >= 2:
        return verdict(a[1:])
    if len(a) != 2 or a[0] not in STAGES:
        print(__doc__)
        return 2
    stage, d = a
    r = subprocess.run([str(HERE.parent / "run" / "freeze_r3.sh"), "verify"], capture_output=True, text=True)
    if r.returncode:
        print("REFUSING: the frozen files do not verify:\n" + r.stdout + r.stderr)
        return 3
    try:
        text, _ = run_stage(stage, d)
        print(text)
    except SystemExit as e:
        print(f"REFUSING: {e}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
