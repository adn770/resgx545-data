# C3 preflight (prepared 2026-11-10, not run)

Everything is under `~/src/scratch/resgx545/closing3/r3x-c3/`. The landed tree, the data, the
linux fork and the past session directories were read, not changed. The laptop was not contacted.
Nothing is committed. Frozen: `FROZEN.sha256` (every generator, scorer, runner, script, table,
blob, source, prediction, test and what they import from the landed tree), `PREDICTIONS.sha256`
(1 file), `LAPTOP.sha256` (the files as laid out on the laptop in `~/r3xc3/`).

Checks that pass (dated run at the end of this file): `tests/run_all.sh` (sim_c3.py,
test_scorer.py, test_guard.py, run_mock.py, guard_c3.sh); `run/freeze_c3.sh verify`.

## 1. Offline readings behind the rows

- **The re-arm reload is a debugfs action, not a module reload** (fork, branch resgx545,
  `sgxfive.c`, `sgxfive_debug.c`). `cmd_arm` writes `own_arm 0`, `own_code` (the verifier accepts
  the blob; it is kept in kernel memory and disarmed), `own_arm` (the line), `load` and `boot`.
  `load` calls `sgxfive_unload` when loaded (a power-off request, a halt, the unmaps) and then
  `sgxfive_load`; `boot` runs the boot sequence. `reset` is `sgxfive_recover(MANUAL)`: halt,
  stock buffers rebuilt, `own_arm` cleared (`sgxfive_debug_reset`), boot. So L (reload, no reset)
  and R (reset then reload) are two different paths into the same boot sequence; R cannot be
  "reset and read" because after a reset only the stock firmware runs, so every R job re-arms
  (R = reset + reload; the L job isolates the reload). This is E536's confound, split in two.
- **What our task may write.** R2-1 b allows sa63, sa64, sa65. Q158's text names sa100, sa127, sa20
  and i0, r20 as markers: sa100, sa127 and sa20 are NOT writable by our task, so they are READ
  only (the reader stores sa63, sa64, sa65, sa100, sa127, sa20, sa24). The sa marker is sa63
  (E791 A1: written and read back at the next entry and 1200 ms later, 3 of 3, the tick kept).
  What C3 can settle for Q158's sa part: sa63's persistence across fill, reload and reset, and
  whether sa100/sa127/sa20/sa24 change over those perturbations. If sa100/sa127 read 0 at S0
  (a boot since E536) their "persistence" is not informative; the scorer says so. S0 also
  reports i0, i1, r20, r21, p and pclink as found (the start state after the stage's own arm).
  The preflight keeps `/proc/uptime` and the boot id to read S0 with.
- **What the controls already say (E536, E537, E792).** After a reset and a reload E536's controls
  read i0, i1, sa100, sa127 as E533's writer left them (survived), sa20/sa24/sa64 not, r20 = 0,
  r21 = 0x1000 ("what fills leave"); E537's control, after a reload that followed three fills,
  read r21 = 0x3000 again, so r21 survived THAT reload. The sketch's "r20, r21 do not survive" and
  that reading disagree, so both are frozen: H-KEEP (i, sa63 survive, r gone) and H-ALL (r
  survives too); a world where nothing survives fails both (E536's controls already refute it).
- **p2/p3 (Q124).** E792: after every writer p2 p3 read 1 1, in A0 (no writer, first after the
  arm) 0 0; a writer that set them (E536, A1-A5) or did not (A6, after A5) both gave 1 1. The
  writer here sets p0..p3 from per-job flags: (0,0,1,1) E536's, (0,1,0,0) and (1,0,1,0). H-KEEP:
  the next entry has p2 p3 as left (reads the flags). H-SET: it has 1 1 whatever was left (only
  the jobs with a 0 in p2 or p3 discriminate: n2, n3, f2, f3, l2, l3, r2, r3). p0 reads 1 (E792,
  19 of 19), p1 reads the writer's p1 (19 of 19), pclink 0x98 (sa64 is not written here).
- **The tick bit clause of Q124** (the closed task's path depends on the tick bit alone) is not
  touched: no sa64 write (E792 wrote 0 and 2 only). C3 does not close it.
- **Stop risk.** One new combination: sa63 + r20, r21, i0, i1 + p flags in one writer pass
  (E536 wrote all of those plus sa100, sa127, sa20, sa24 and kept the tick; E791 A1 and A6 each
  kept it). E537's stop had sa63 and sa65 and no predicates. Stop budget 0: the first stop ends the
  stage (signature read twice before the reset, E537's four elements scored, reset, gate, exit 8).

## 2. Rows, labels and controls

13 jobs, ordered by risk: S0, N x3 (1200 ms), F x3 (one client fill), L x3 (reload), R x3
(reset and reload). Each job: rd0 (host reader, before the writer), the writer, rdA (the reader
it armed, at the next event), the perturbation, rdB (host reader). 247 frozen rows (24 control,
38 fit, 49 held out, 136 replicate). Controls that can fail: `a_markers` (the writer's markers at
the next event, every job: a failure makes that job's rdB rows cannot-tell) and `carry` (a job's
rd0 equals the previous job's last reading). Fit: E536's next-event, 1200 ms and fill readings
and E792's pclink/p0/p1. Held out: p2 p3 (H-KEEP vs H-SET), sa63 after a fill, the counter step
of r21 per fill (+0x1000), every row of L and R. Void: no record, a class that is not a result,
a writer that did not run, an sa63 read-back that differs from what was written. Cannot tell:
a reader not run with the tick kept, a failed control.

## 3. Limits kept

No clock-gate register, no `str` in the task, no trc, no register or knob write, no kreg/kpoke:
the runner's debugfs writes are own_code, own_arm, load, boot, reset and the page (guard_c3.sh
checks the text, guard_blobs.py the assembled code, the runner checks its table at preflight).
Preflight: srcversion loaded = installed, the pinned tool, own_code/own_arm/own_res/load/boot/
reset/regs/status/miscinfo present, the gate tool present. Tool messages are searched in the
whole job log and the stage's kernel.log; the driver runs health at the stage's end and after
any stop. Laptop directory `~/r3xc3` (and `~/r3xc3-out`).

## 4. Dated run (2026-11-10, Mac, offline)

`tests/run_all.sh`: sim_c3.py 24 ok (every command path of the blob in sgx-sim), test_scorer.py
58 ok, test_guard.py 30 ok, run_mock.py 11 tests / 84 ok (about 3 minutes), guard_c3.sh clean:
"run_all: all passed" (log in `debug/runall.log`). Freeze made on that code state, then
`run/freeze_c3.sh verify`: "files verified" (40 files, 1 predictions file). Hash prefixes:
FROZEN 30f4d9d7c5f7aeab, PREDICTIONS b1d9d8b5a79b7919, LAPTOP f5f3b563ae74c682, blob
f728519f8196c06c. The scorer and sim worlds were written before the scorer; the blob was
assembled and verified before its sim test (a small deviation from strict order).
Expected laptop time: about 2 to 3 minutes (13 jobs; 3 reload and 3 reset arms of about 1 s,
3 gaps of 1.2 s), plus the driver's health run.

## Refreeze 2026-11-10 (lead, before the first job)

Main moved to 7aaa017 (r3-kernel landed) after this session was frozen, changing
`tools/fwtask/fwtask.py` and `regs.toml`. The blob was rebuilt with the verifier at 927bea4 (the
laptop's running kernel's rows) and at 7aaa017: both give f728519f..., the frozen blob. Only
FROZEN.sha256 was regenerated (old kept as FROZEN.pre-l3b-refreeze.sha256); PREDICTIONS.sha256 is
unchanged.
