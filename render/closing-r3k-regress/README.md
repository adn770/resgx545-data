# R3K-regress (module-regression session): prepared, NOT run

Built overnight 2026-11-10/11 by `regress-build`; nothing here touched the laptop, cachix or a git
repo.
The laptop's gma500 module changed from srcversion B21FDA82BD5E5CB5A627E3B (rounds 1-2, L1-L3) to
230E0EF50FFFD606C53AE3C (fork `resgx545` at 8fc748b0).  K2 stage k-pb0 then froze a target hash of
0x8ea26cdfee74a325 where E728 had 0xfc5ff15e0434a325.  This session asks one question: did the
module
change any image, or is that difference an artefact of K2's job shape?  Read `PREFLIGHT.md` first.

## What it is

A copy of the framework of `closing3/r3k-pixel` (runner `run_stage.sh`, `lib_k.sh`, driver `k.sh`,
gates,
freeze, guard, mock tests), reduced to plain jobs: no held job, no BIF row, no knob write at all
(the runner
writes only debugfs `reset`).  Two stages, 36 jobs:

- `rg-ctl` (23 jobs): rows taken from closing sessions that passed on the old module (E773 g-u1
  tri and
  geometry jobs, E806 green fills, E798 g-dd probes, E763/E788 r2-a-safe TE 0x20/0xe0 jobs), each
  with its OLD
  kept value frozen as the prediction (record and kept file in the last column of
  `predictions/rg-ctl.tsv`).
- `rg-pb` (13 jobs): the k-pb0 diagnosis.  E728's own job shape (ONE render, TE 0x40/0x80/0xc0,
  mode 0 and 2,
  64x64 and 128x128, TE 0x40 three times) with E728's values (H-OLD); K2's shape (`-n 2 --geometry
  1`) three
  times with K2's k-pb0 value (H-NEW).  Runs only if every `rg-ctl` row ran with class ok (the
  gate).

Laptop directories `~/r3kreg-run`, `~/r3kreg-stage`, `~/r3kreg-out` (no other session's).

## Layout

- `tables/` (`rg-ctl.txt`, `rg-pb.txt`; `TABLES.md` is the readable view with every frozen
  prediction),
  `predictions/*.tsv` (case, quantity, value, model, set, source), `gen/rgen.py` (+
  `gen/data/old_values.tsv`:
  the values extracted once from the records by `rgen.py extract`), `score/score_rg.py` (+
  `rlib.py`, `klib.py`),
  `run/` (`run_stage.sh`, `lib_k.sh`, `k.env`, `k.sh`, `stage_k.sh`, `freeze_k.sh`, `guard_k.sh`,
  `lib_check.sh`),
  `bins/` (pix_green, dd-p1, dd-p2 programs, frozen by sha256), `tests/`, `FROZEN.sha256`,
  `PREDICTIONS.sha256`.
- Tests: `tests/run_all.sh` = PASS (test_gen 27, test_scorers_rg 31, mock_all 36 of 36, run_mock
  128, guard clean).

## Commands the lead runs (home LAN)

```
export SGX_TARGET_HOST=jtorra@192.168.12.234
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHONDONTWRITEBYTECODE=1
export PY=/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python   # ABSOLUTE
cd /Users/jtorra/src/scratch/resgx545/closing3/overnight/r3k-regress
bash tests/run_all.sh                       # offline, must say ALL TESTS: PASS
run/guard_k.sh && run/freeze_k.sh verify
SGX_DRY_RUN=1 run/stage_k.sh                # prints the commands
run/stage_k.sh                              # copies, compares, checks the tool hash
run/k.sh                                    # the session (stops: PREFLIGHT.md section 6)
$PY score/score_rg.py verdict out/ATT       # both SUMMARY lines from the kept stages
```

`run/k.sh --only STAGE` (a new attempt directory) reruns one stage; `run/k.sh --from STAGE`
continues after a
stop.  `PY` is used by `k.sh` too (its default is the same absolute path); never a relative path.
There is no
gate file anywhere: the gate of `rg-pb` is computed from the kept `rg-ctl` directory (this
attempt, then
earlier ones).  It writes no knob, so it leaves every default as it found it; the module must be
the new one (the preflight checks
srcversion), so run it in the same boot as the K sessions.
