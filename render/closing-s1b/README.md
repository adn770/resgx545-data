# S1b of the resgx545 question-closing pass: prepared, NOT run

The frozen follow-up of S1 (`closing/s1/`, run on hardware 2026-11-09), from the S1 analysis's S1b
list (`closing/s1/analysis/README.md`, items 1 to 9; item 10 and the redesigns of item 11 are
not here).  Nothing here touched the laptop; nothing is committed.  Read `PREFLIGHT.md` first.

**Where this lives.** Prepared in the agent worktree
`~/src/resgx545/.claude/worktrees/agent-aed0242cfe8ab4e23/debug/s1b/` (the Write tool refused
`~/src/scratch/resgx545/closing/s1b/`; see PREFLIGHT, inconsistency 1).  Every script finds its
files relative to itself, so the directory can be copied to `closing/s1b/` as it is.  The tool
changes it needs are in the same worktree's `userspace/libsgxfive` (uncommitted).

## Layout (file names kept from S1; every path, marker and tool name inside is S1b's)

- `tables/STAGE.txt`: one job table a stage (`name|set|risk|P|knobs|rt|command`); `TABLES.md`
  is the readable view
- `predictions/STAGE.tsv`: frozen predictions `case quantity value model set`;
  `p-b2-set-*.bits` (E731's region, HT and HV sets), `p-d-A4.tsv` (A4 at each job's own pages)
- `gen/s1gen.py` + `gen/s1b_stages.py`: regenerate tables, predictions, programs (`bins/`);
  `gen/s1pix.py`, `gen/b2model.py` carry the generator fixes
- `score/score_s1.py STAGE out/STAGE`: the scorers (refuse unless the freeze verifies);
  `score_geo.py`, `score_pix.py` carry the scorer fixes and the S1b stage scorers
- `run/stage_s1.sh --src PATH`: copies runner, tables and programs to the laptop and builds the
  tool there from the checkout at PATH (give the worktree until the tool change lands)
- `run/s1.sh [--from STAGE | --only STAGE...]`: the Mac-side driver (verify, one ssh a stage,
  copy, health), every ssh/scp bounded by a perl alarm
- `run/run_stage.sh`, `run/lib_s1.sh`: the laptop-side runner
- `run/freeze_s1.sh [freeze|verify]`, `FROZEN.sha256`, `PREDICTIONS.sha256`: the freeze
- `run/guard_s1.sh`: the forbidden list, wait loops, and debugfs only through `sudo -n`
- `tests/`: `test_fixes.py` (every analysis fix, failing on S1's code), `test_s1b_scorers.py`,
  `test_scorers.py` (S1's readers), `run_mock.sh` (runner end to end on a fake tool),
  `mock_all.py` and `emit_checks.py` (every command and the option words against the worktree
  tool's mock)

Python: `~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python` (numpy; scorers,
generators and tests only).

## Order

`stages.txt` (review order): p-b2, g-e8b, g-e1, g-e3, p-c, g-e5 (no expected fault), then p-d,
p-f, g-e4w.  No pause: every table is frozen before the first job.

**Target host.** There is no `tools/bringup/local.env` for this session: export both before
staging and running (the scripts read them from the environment):

```
export SGX_TARGET_HOST=jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
```

**Tool source.** `TOOLSRC.sha256` (in the freeze) holds the sha256 of every deploy input of the
tool (userspace/libsgxfive without build/, include/uapi, tools/gen_tri_progs.py) as they are in
the agent worktree.  Once that change is committed to main, stage from main; any other content
is refused before anything is copied:

```
run/freeze_s1.sh verify
SGX_DRY_RUN=1 run/stage_s1.sh --src ~/src/resgx545    # prints "deploy inputs match the freeze"
run/stage_s1.sh --src ~/src/resgx545
run/s1.sh                                  # stops at the first non-zero stage or health status
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
$PY score/score_s1.py p-f out/p-f          # one SUMMARY line a stage
```

Tests (offline), always with `export PYTHONDONTWRITEBYTECODE=1` (the scorers import modules of
resgx545-data; a `__pycache__` there breaks the dataset digests; every entry point also sets
`sys.dont_write_bytecode`): `$PY tests/test_review.py`, `$PY tests/test_fixes.py` (and
`CODE=../s1` to see S1's code fail), `$PY tests/test_s1b_scorers.py`, `$PY tests/test_scorers.py`,
`bash tests/run_mock.sh`, `$PY tests/mock_all.py`, `$PY tests/emit_checks.py`.
