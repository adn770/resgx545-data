# r6-render4x stage B (set B): the r6-kernel tail room, prepared, NOT run

Built 2026-11-12, offline, as the session's **second freeze** (`FROZEN-B.sha256`,
`PREDICTIONS-B.sha256`, `FREEZE-B.txt`) beside stage A's, whose files are byte for byte the ones
stage A ran with (`FROZEN.sha256` 5fbd64f7...). Plan:
`/Users/jtorra/src/scratch/resgx545/closing6/render4x/exp-render4x-r6.md` section 4, decisions R6-3 (a),
R6-4 (a), the plan's 2 (a), 3 (a), 6 (a). Module: linux fork branch r6-kernel at 3f0b3e74
(`/Volumes/linux/linux-sgx-r6`, read only; 56f8b932 the tail room, `gen/layout_b.py` transcribes it),
built by the lead: srcversion **41E2F5C756F96D20F7109A4**, sha256 8a32dada..., vermagic
7.3.0-resgx545 SMP preempt mod_unload 686, frozen in `run-b/k.env`. Tool: `~/sgxfive-test-rgn4`
(e6951558..., no uAPI change). Read `PREFLIGHT-B.md` before running.

**Disclosed:** set B was frozen after stage A ran (out/20261112-144822: H-TPM held 11 of 11, h1 and
h2 lost exactly their frozen sets, TPM-y-rgn the only surviving variant). B's predictions use
H-TPM as stage A left it on the new layout; nothing was fitted on stage A's files.

## What runs, in order (`stages-B.txt`)

| stage | jobs | what | predicted | fault limit |
|---|---|---|---|---|
| s0b | 4 | r5's three controls with the r6-kernel's TA-data sizes (4x 1024 x 768: 0x2a000, was 0x1e000), the 1x full 1024 x 768 (TA data as before, r5 o10) | pass | 1 |
| b | 9 | b9 1024 x 768 control; b1-b8 the eight own-maximum cells that faulted on rgn4 (1280x1024, 1184x768, 1024x800, 2048x240, 768x2048, 2048x1536, 1280x768, 1024x1024), automatic room | all complete, 0 wrong, 0 headers off | 2 |
| k | 5 | `render_tail_room` one page apart: k1 0x4000 at 1280x1024 (the old layout), k5 0x4000 at 1024x768, k2 0xb000, k4 0x3000 at 1024x768, k3 0xa000 held | k1, k4, k3 fault; k3 loses the frozen 171 offsets 0xd000-0xd7f8 | 4 |
| r | 3 | r2 2048 x 2032 (1017 pages), r1 4096 x 960, r3 4096 x 1152 (r1, r3 without dumps) | r1, r2 complete; r3 -ENOSPC, no fault | 1 |

**21 jobs** (the plan's section 4 table counts 20; its rows are 21), 3 predicted faults. **About 20
minutes on the laptop; plan 40.**

## Verdicts (`score/score_b.py`, frozen; helpers imported unchanged from set A's `score_r.py`)

- **H-ROOM (b)**: b1-b8 complete with 0 wrong (and 0 headers off the rule from the new td.rgn,
  reported). Controls s0b, b9.
- **H-TPM knob (k)**: k2 completes, k4 faults, k3 faults with its lost set equal to the frozen
  one (by header position from td.rgn 0xd000). Controls k1 (must fault: else the knob does not do
  what it says) and k5 (completes at the limit).
- **r**: r2, r1 complete with 0 wrong, r3 overflows without a fault [explore: the 4096-wide residue].

## Stops

b9 faulting stops b (rc 4); the 2nd fault of b1-b8 with rows left stops b (rc 15); k takes up to 4
fault-class events; any fault in r stops it (rc 4); any fault not E845's word rc 18. The knob
`render_tail_room`: written after each row's reset (0 or the row's `room:0xNNNN`), read back (rc 19),
back to 0 after the job and by the exit trap, required 0 at the preflight and at the stage's end.
Preflight: srcversion installed = loaded = 41E2F5C756F96D20F7109A4 (the rgn4 module is refused),
debugfs `render_tail_room` present, the rest as stage A (`PREFLIGHT-B.md`).

## Commands (laptop files under `~/scratch/r6x`; B's runner in `~/scratch/r6x/run/run-b/`)

```
cd /Users/jtorra/src/scratch/resgx545/closing6/r6-render4x
bash tests/run_all.sh                       # offline: ALL TESTS: PASS (sets A and B)
run-b/guard_b.sh && run/freeze_k.sh verify B
SGX_DRY_RUN=1 run/stage_k.sh --set B && SGX_DRY_RUN=1 run/k.sh --set B
run/stage_k.sh --set B                      # after the one-shot boot and the srcversion check
run/k.sh --set B
$PY score/score_b.py verdict out/ATT
```

## Files of set B

`sets/B.env`, `stages-B.txt`, `run-b/` (`lib_k.sh`, `run_stage.sh`: set A's with the
`render_tail_room` knob; `k.env`: the new module; `guard_b.sh`), `gen/rgen_b.py`, `gen/layout_b.py`,
`gen/data/{twins-B.tsv,sources-B.lst}`, `tables/{s0b,b,k,r}.txt`, `predictions/{s0b,b,k,kh,r}.tsv`,
`TABLES-B.md`, `score/score_b.py`, `tests/test_b.py` and `tests/run_mock.sh` section 8. B pins,
unchanged, the set A files it uses (drivers, scorer and generator helpers). No firmware-derived
file: everything is publishable.

## Deviations

1. 21 jobs, not 20 (the plan's table has 4 + 9 + 5 + 3 rows).
2. s0b's 4x controls freeze the r6-kernel's TA-data size (the change under test) as a control
   quantity; the image, hash and pages are the kept ones.
3. b's limit 2 (the plan: "a fault in b1-b8 after the first stops"); k's limit 4 (3 predicted).
