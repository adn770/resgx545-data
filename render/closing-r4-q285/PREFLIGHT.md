# R4-A preflight: jobs, time, module, controls, stops, risks, deviations

Prepared 2026-11-11. Nothing ran on the laptop.

The freeze is `FROZEN.sha256` (39 files) with `FROZEN.commits`, and `PREDICTIONS.sha256`.
Both were written before any job. Refreeze (`run/freeze_k.sh freeze`, then
`gen/frozen_commits.py`) only after regenerating, and never after the first job.

## 1. Jobs and time

| stage | jobs | rows |
|---|---|---|
| a-pb0 | 3 | pb-d0-te40, pb-p0-te60, pb-p1-te40 (controls) |
| a-pb | 5 | pb-p2-own11 (control), p3a, p3b, p4a, p4b (held out and replicates) |

There are 8 jobs, K2's count (k-pb0 3 and k-pb 5).

The time is estimated from R3K-regress's figures (36 jobs in about 5 minutes), not measured.
Each job takes:
- a reset (3 s);
- two knob writes;
- the tool (about 0.3 s for two 64 x 64 renders);
- a 4.6 MB dump gzipped.

That is about 6 s a job. Each stage also has a begin and end health (a fill and a triangle,
about 10 s), and the driver's health after each stage takes about 10 s. Staging takes about
1 minute.

**Total about 4 minutes; plan 15.** A hang in p4 adds the 20 s wait and a recovery.

## 2. Module, tool, knob

- **The preflight** (`lib_k.sh`) checks:
  - `modinfo -F srcversion gma500_gfx` = loaded = **99CD90DA26E3AFF9C450517** (`k.env`);
  - the debugfs files `reset hold_recovery regs render_param render_tadata render_pb_pages
    alias_skip render_rgn_arrays kpoke` exist (`sudo -n test -e`);
  - the defaults: hold_recovery N, render_pb_pages 0x422, alias_skip 0, **render_rgn_arrays 0**;
  - the tool's sha256 is e6951558....

  Any failure exits with rc 1, and nothing is touched.
- **The fresh-boot load** (a health fill and a triangle) runs at the start of every stage.
  There is no EDM stage here.
- **Knob `rgn:1` on every row.** After the job's reset the runner writes 1, reads it back
  (rc 19 if it is not 1) and logs `resgx545 r4a rgn NAME 1`.
- **After every job** it writes 0 and reads it back (rc 19).
- **The exit trap** writes 0 at every exit once the preflight has passed, fatal stops included.
- **The driver** reads the knob after each stage and stops with rc 42 if it is not 0.
- **The tool's flag.** Without the knob the module would refuse these jobs (-EINVAL). The
  rgn4 tool's mock models this: `tests/mock_all.py` shows all 8 rows refused without the flag
  and accepted with `--aa4`.

  The fake kernel of `tests/run_mock.sh` checks this rule too: a table without `rgn:1` stops at
  the first row with rc 4.
- **The par pokes** are written by the tool (debugfs `kpoke`, before render 2), never by the
  runner. After each job the runner reads debugfs `kpoke` and keeps it, and the scorer requires
  it to be empty for p2. A reset before every job and after the last job disarms anything left.
  The fork's `sgxfive_debug_reset()` clears `kpokes.n`.

## 3. Controls: how each passes and fails

| row | passes | fails |
|---|---|---|
| pb-d0-te40 | every frozen quantity of R3K-regress pb-n40-a; no poke applied | FAIL: gate closed |
| pb-p0-te60 | every frozen quantity of pb-n60 (hash 0xd2bfb75560f4c325, dword 26 0x04000004) | FAIL: gate closed |
| pb-p1-te40 | as d0, and its parameter buffer sha256 equals d0's in this run | FAIL: gate closed |
| pb-p2-own11 | as d0 (sha256 = d0's); applied exactly `par:11=0x00000000`; nothing armed after | FAIL: every row cannot tell |

The frozen quantities are:
- rc, the size echo and the geometry-only line;
- the target hash and the diff text;
- the render 2 line and the `renders ok` line;
- the parameter buffer and TA data sha256 and their sizes;
- dwords 0-63.

A row is NODATA, never a pass, when:
- it has no cases.tsv row;
- its rc is 2, 124-127 or 128 or more;
- its class is not a result;
- its output is missing;
- a dump is missing;
- the kept `kpoke` read is missing (p2);
- there is an overflow message in the output.

The tool's and the kernel's messages are searched in the whole output and in the job's kmsg
slice.

## 4. Fit vs held out

- **Controls:** d0, p0 and p1 are frozen from R3K-regress. p2 is frozen from the same file,
  plus its pokes.
- **Held out:** p3a (the twin's words) and p4a (0xffffffff at dword 11). No value of a poked job
  exists anywhere: k-pb never ran.
- **Replicates:** p3b and p4b.
- **Fit:** none. The hypotheses are K2's, frozen in R3K-pixel's predictions before its run. The
  poke words are K2's. `tests/test_gen.py` checks that p3's words 11-25 are pb-n60's dwords
  11-25.

## 5. Decision rules

The decision is frozen in `score/score_a.py`; README "Hypotheses" gives the table.
- a-pb0 gives PASS, FAIL or NODATA for each control. The gate is scorekit's `gate()`.
- a-pb gives each row's reading, and each pair goes through `combine`. Q285 is printed through
  scorekit's `headline`, with the four controls and the decided-row count.

## 6. Stops and recovery

Runner exit codes (`run_stage.sh` header):

| rc | meaning |
|---|---|
| 1 | preflight, a frozen file mismatch, a table without expectdiff or --keep-going |
| 3 | a fatal kernel message (no reset; the knob restore only) |
| 4 | the first fault, hang or unexplained failure (fault limit 1), after a reset and health |
| 5 | a failed health recovery |
| 6 | a freeze (no reset; the knob restore only) |
| 7 | a forbidden knob or dbg_write |
| 12 | the registers are unreadable |
| 13 | a reset failed |
| 14 | a fault was latched before a job |
| 19 | the knob did not read back |

Driver exit codes (`k.sh`):

| rc | meaning |
|---|---|
| 20 | the frozen files changed |
| 30-37 | health after a stage |
| 38 | no SUMMARY |
| 39 | the attempt directory exists |
| 42 | render_rgn_arrays is not 0 after a stage |
| 142 | the alarm (a freeze) |

After any stop the driver prints the knobs it can read. There is no reboot, no module unload
and no register write. **The lead decides.**

A wrong image is a result, not a stop: an image mismatch never stops a stage.

## 7. Risks

- **a-pb0: low.** R3K-regress ran exactly these jobs 4 times, without the knob, on 230E0EF5.
  The 2026-11-11 rgn4 check ran a 4x one-render job on 99CD90DA at forced 1, and it reproduced
  E827 byte for byte, parameter buffer included.

  **The residual risk** is that something in the two-render path changed between 8fc748b0 and
  a2788bd8. That fork diff is about the TA-data slot and the 4x flag: slot 0 keeps its address,
  and a 1x context keeps its layout. If it happened, the controls fail and the gate closes,
  which is the purpose of the controls.
- **a-pb: medium** (K2's estimate). A garbage dword 11 (p4) may hang the ISP. Then the stage
  stops (rc 4) after a reset and a health check, and p4 cannot tell. p3 writes 16 words of a
  valid twin object.
- **Nothing else is written.** The session writes no clock-gate register, trc_hazard, kreg,
  kregnow, kicker, BIF register, hold_recovery, /dev/mem, boot-loader file or kernel. The
  debugfs writes are only:
  - `reset 1`;
  - `render_rgn_arrays 0|1`, always through `sudo -n` and bounded.

  `run/guard_k.sh` enforces this, and `tests/run_mock.sh` tests it with 23 script injections
  and 12 table lines.

## 8. Deviations from K2 and the brief

1. **Every row gets `rgn:1`**, which K2's rows did not have. The module changed: the default is
   now 0, and it refuses these jobs.
2. **p3's deciding quantity is the picture**, not K2's hash. The hash K2 froze is a one-render
   value: see README, "Records that contradict".
3. **p4 "empty" requires 0 other pixels too.** K2 called any 0-triangle reading empty. Here
   0 triangle with other pixels is read and matches no hypothesis.
4. **The tool is the rgn4 build**, not R3K-regress's r1. The source diff is in the README.
5. **The mock tool for `tests/mock_all.py`** is the worktree build
   `closing3/kernel/wt-rgn4/userspace/libsgxfive/build/sgxfive-test`. Its source
   `sgxfive-test.c` hashes to 4623753's blob. The binary's own build provenance is not pinned.
6. **Freeze pins.**
   - By absolute path, from resgx545: `tools/closing/scorekit.py` (the source of the copy) and
     `tools/bringup/health.sh` (run by `k.sh`). Both are in `FROZEN.commits`.
   - From resgx545-data: the R3K-regress and K2 files, which are not resgx545-tree pins.
   - The tool source of 4623753 is pinned in `TOOLSRC.sha256` by commit, not by path: the
     worktree's path contains a `resgx545` component that `frozen.py` would misread.
7. **A bounded wait for the log tee.** The runner's exit waits for its log tee with a single
   bounded fallback (`TEE_GRACE`, 10 s, then kill). A macOS mock run once left tee without EOF
   and hung the test suite. On Linux, tee ends at EOF first.

## 9. Freeze (2026-11-11, before any job)

- `FROZEN.sha256` 6bed5eeeb62eae5c40dbc4b0fdf20e013ebf5c808aa0ad9170ff131cd89f3ff6 (39 files)
- `PREDICTIONS.sha256` 2959655d948593f19f7e4047df7df9002efd388232d68536a4cda5c7b60b3e51
- `FROZEN.commits` 697fd3c0596fd6d5c74f02c50b8b94991d118013615e63d47ad1c322da365550: scorekit.py
  at eb84f54 and health.sh at 382b7362.
