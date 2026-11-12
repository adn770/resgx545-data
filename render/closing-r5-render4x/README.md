# r5-render4x (Q292's cause and onset at 4x, reruns of round 4's o and t): prepared, NOT run

Built 2026-11-12, offline. Nothing here touched the laptop, cachix or a git repository.
Read `PREFLIGHT.md` before running. Plan:
`/Users/jtorra/src/scratch/resgx545/closing5/render4x/exp-render4x-r5.md`, every decision (a)
(`closing5/DECISIONS-R5.md` R5-3, R5-4, R5-6): stages s0, t, o, m, l, x, d; 37 jobs; H-TPC's four
variants frozen against the seven size rules; fault limits m 4, l 5, x 3, d 1, o 1, t 1 with
strict health after each fault; no kernel change, no reboot.

## What runs, in order (`stages.txt`)

| stage | jobs | what | predicted | fault limit |
|---|---|---|---|---|
| s0 | 3 | round 4's controls (E827 ctl-u-1024-n1, E828 j1r, E824 h8) | all pass | 1 |
| t | 9 | Q293 again, dump names fixed: t6, t3b, t4b controls; t1-t4 replicate E847; t3c, t4c (0x80) held out | H-PAD: zero dword before the format word | 1 |
| o | 11 | H-ENOSPC4: o1, o2 default triangle at its measured need 19 (P 0x35, 0x34); o3 control; o4, o5 replicates; o6-o9 held out (640 x 480 at 76, 512 x 384 at 49); o10, o11 the 1x full pair (explore, need 49 [model]) | no fault anywhere | 1 |
| m | 5 | H-TPC: the same size with more room (m0 1024x768 on 2048x2048; m1, m2, m3 1280x1024 on 1280x1040, 2048x2048, 2048x1024; m4 2048x1536 on 4096x4096) | m3 faults, the rest complete | 4 |
| l | 5 | onset: 2048x240, 256x1536, 768x2048, 1280x768, 1024x1024 | H-TPC: l4, l5 fault | 5 |
| x | 3 | which H-TPC variant (explore; runs only if m held H-TPC): 1024x512, 1184x768, 1024x800 | TPC-d-rgn: all complete | 3 |
| d | 1 | E845's 1280x1024 held, render_param and render_tadata read in the hold (explore, last) | fault with E845's word; 321 scene pages; headers zero below 0xa000 | 1 |

37 tool jobs plus the health pair at each stage's begin and end and after each fault. Predicted
fault-class events (TPC-d-rgn): 4 (m3, l4, l5, d), all 3D side (BIF_INT_STAT 0x0100, BIF_FAULT
0x10000011). The limits allow 15 (s0 1 + t 1 + o 1 + m 4 + l 5 + x 3 + d 1); the worst case
the frozen rules allow is 10 (K-OR: m1-m4, l1-l5, d; x is gated off when m fails H-TPC).
**Expected time about 25 minutes on the laptop; plan 45.** Every job is a reset, the knob writes,
the tool and the gzip of its dumps; m4 (3.1 Mpixel, a 2.2 MB TA data dump) is the largest.

## Hypotheses and verdicts (`score/score_r.py`, frozen)

- **Q293 (t)**: the dword CR_TE_AA bits 31:30 insert is zero and sits right before the object's
  format word (line at 9, point at 11), at 0x80 as at 0x40 (H-PAD; H-FIELD: non-zero). The
  empty image at 0x80 is predicted [infer] and reported.
- **H-ENOSPC4 (o)**: an overflowing 4x scene ends in -ENOSPC with no BIF line (E846 post hoc),
  held out on 640 x 480 and 512 x 384 one page each side of their kept twins' need. Refuted by a
  fault in o4, o5, o7 or o9. Control that can fail: o1/o2 (the page rule one page apart on a
  measured need). If o10/o11 measure 49, E846 needs an appended correction (exp 1.6).
- **H-TPC (m)** [infer]: at 4x the TA's tail-pointer extent of the doubled grid runs over the
  region headers of the context's layout; held if m1, m2, m4 complete with 0 wrong and m3 faults
  (every size rule predicts m1, m2, m4 fault). m0 is the gate control (a fault there stops m).
- **Q292 onset (m, l, x)**: eleven rules, each prediction computed from the row's argv
  (`gen/rules.py`): TPC-d-rgn, TPC-d-state, TPC-rs-rgn, TPC-rb-rgn, K-W, K-H, K-OR, K-AND,
  K-TPM, K-P, K-AREA. The verdict names the rules no decided row contradicts. A threshold rule
  (K-TPM, K-P, K-AREA) is a family that survives while some threshold fits; the session's cells
  cannot separate these three (see Deviations).
- **d**: replication of E845's fault (a completion voids l and m) and, if the held dumps were
  read (not error text), which variant's extent the zeroed headers fit.

## Round 4's two slips: impossible by construction, and the dry runs that show it

- **o2's control (default triangle frozen with the full triangle's need)**: every frozen need comes
  from a kept TWIN of the row's own argv (`gen/twins.py`, `gen/data/twins.tsv`); a control with no
  twin or a [model] need fails the build. `tests/test_twin.py` checks every row's command against
  the plan row typed independently (triangle, mode, size, maximum, P, TE word, knobs) and fails
  round 4's o table at o2 (97 frozen, its 6 twins say 19). `tests/mock_all.py` runs every command
  through the pinned tool's own `--mock` and compares the triangle counts with the twin's; round
  4's o2 command fails there too.
- **t's scorer (looked for NAME.tri.* where a probe writes NAME.PROG.*)**: the scorer finds a dump
  by the verb of the argv that ran (`rlib.dump_stem`); a row that asked for a dump, completed and
  has none is a READER-MISS (never a silent NODATA); `insertion()` refuses a missing side. Every
  row freezes its dump name (`dump_param`), checked against R4-G's real directories.
- **The mock answers by argv**: `tests/worlds.py` never sees a case name; it decides from the
  argv and the fake debugfs knobs (render_pb_pages, render_rgn_arrays, hold_recovery), replays the
  real kept outputs and dumps of the argv's twin, and names probe dumps as the tool does.
- **Replays on round 4's kept files** (`tests/test_replay.py`, published
  `resgx545-data/render/closing-r4-render4x`): t3b, t4b PASS, t3 held at 9, t4 held at 11, t1, t2
  held, t6 PASS, "4 of 6 rows decided"; r4's o3, o4, o5 (matched by argv and P, not by name) PASS,
  held, held; files it must fail on fail (r4's o4 as an o3 control; a point against the line
  baseline). Round 4's own frozen scorer on the correctly named mock prints NODATA for t3b and t4b
  (`tests/test_scorers_r.py`), kept as the regression.
- **The gate across attempts** (r4 scored o and t with s0 NODATA after `--from`): the driver writes
  `out/ATT/gate-STAGE.txt` naming the directory that holds s0 (and m, for x); the stage scorer
  reads s0 there. Tested on r4's two real attempt directories and in the mock with two attempts.

## Stops

- s0, t, o: the first fault, hang or unexplained failure ends the stage (rc 4) after strict health.
- m, l, x, d: a fault with E845's word is a measured hypothesis; the stage ends when its limit is
  reached with rows left (rc 15). m0 has no hypothesis knob: a fault there ends m (rc 4).
- Any fault whose BIF_INT_STAT bits 15:0 are not 0x0100 or whose BIF_FAULT is not 0x10000011
  (a TA-side fault, another word) or a "recovery failed: -110": rc 18. A hang: rc 4.
- Strict health after every fault-class event: the first fill and triangle must draw, else the
  recovery runs and the stage stops (rc 16). Fatal kernel line rc 3, freeze rc 6.
- Knobs not reading back rc 19; driver rc 42 if a knob is not at its default after a stage.
- Any stop ends the session (the driver exits); after a stop: no reboot, no module unload, no
  register write. The lead decides (`run/k.sh --from STAGE` is a new attempt).

## Layout and commands

`gen/rgen.py` writes `tables/`, `predictions/`, `TABLES.md`, `stages.txt`, `bins/` (the line and
point programs, equal to R4-G's published ones), `gen/data/` (twins, the rule fit, the source
list). `gen/rules.py` the eleven rules, `gen/twins.py` the scene twins, `gen/pbmodel.py` the page
model and layout, `gen/rlib.py` readers (dump names, the header rule). `score/score_r.py` the
scorer (`score/scorekit.py` byte for byte main's). `run/`: `run_stage.sh` and `lib_k.sh` run on the
laptop; `k.sh` the driver; `stage_k.sh` stages; `freeze_k.sh`, `guard_k.sh` the freeze and the
session's own static guard. `tests/run_all.sh` runs every offline test (exits 0).

Laptop directories: `~/r5x-run`, `~/r5x-stage` (the two programs), `~/r5x-out`. Prefix `~/r5x-`.

```
export SGX_TARGET_HOST=jtorra@192.168.12.234
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHONDONTWRITEBYTECODE=1
export PY=/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
cd /Users/jtorra/src/scratch/resgx545/closing5/r5-render4x
bash tests/run_all.sh                 # offline: ALL TESTS: PASS
run/guard_k.sh && run/freeze_k.sh verify
SGX_DRY_RUN=1 run/stage_k.sh && SGX_DRY_RUN=1 run/k.sh
run/stage_k.sh                        # copies, compares, checks the tool hash
run/k.sh                              # the session, stage by stage (gates, scores, health)
$PY score/score_r.py verdict out/ATT  # the SUMMARY lines (several ATT after a --from)
```

## Deviations from the plan

1. **K-TPM, K-P and K-AREA are not separated** by the planned cells (the plan's own l table gives
   them one column in l1-l3; l4 and l5 are "no threshold" for K-P and K-AREA). The scorer treats a
   threshold rule as a family and names the survivors together; the rule worlds show it (a K-P or
   K-AREA world leaves both, a K-TPM world all three). Every other rule is named alone.
2. **The fault limit is the number of events a stage may take**: the stage stops at the limit
   only with rows left (round 4 stopped on the LIMIT-th event). So K-OR's five faults in l and
   the K rules' four in m end those stages normally, as the plan's limits intend.
3. **Row d's command** has no `--dump-render`, `--regs` or `--pixels`: a held fault loses the
   context, the registers come from the debugfs snapshots and the dumps from the hold.
4. **All faults get strict health** (R5-4 a), the unexpected ones of s0, t, o included; a fault
   that is not E845's word stops with rc 18 (new).
5. **The header rule for a maximum larger than the target** (grid of the target, base `td.rgn`
   of the maximum) is [infer]: no such dump was kept. It is reported per completed row (with the
   scene pages and the TA-data size), never a rule's verdict.
6. **The name census on real files** uses R4-G's kept o, t and s0 directories (this runner and
   this tool); the 11.31 line and point sessions kept their dumps under another runner's names
   (`NAME.param.bin.gz`), so they serve only as the baselines' records.
7. **H-ENOSPC4's headline counts o4 and o5** with o6-o9 (scorekit rows); the lines label o4, o5
   as replicates of E846 and o6-o9 as held out.

## Publishable

Everything here is our own: generators, scorers, runners, tests, tables, the twins table (read
from published datasets), the rule fit (our fork's layout formula) and the two programs (built
from `probes/ta/p1131-progs.toml`). **No firmware-derived file**: nothing goes to data-private.
`debug/` is scratch (the mock tool build, test work directories) and is not part of the session.
