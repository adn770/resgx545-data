# R3K-regress preflight: jobs, time, controls, stops, risks, deviations

Prepared 2026-11-10.  Nothing ran on the laptop.  Frozen: `FROZEN.sha256` (generators, scorers,
runner scripts, env,
tables, predictions, the old values the generator reads, the staged programs, the pins and the
landed tool source),
`PREDICTIONS.sha256`.  Refreeze (`run/freeze_k.sh freeze`) only after regenerating and never after
the first job.

## 1. What was found while building (read this before the numbers)

1. **K2's k-pb0 job is not E728's job.**  E728 (isp E728, p1141tex `msaa-b-te29.sh`) ran ONE render
   (`tri --tri-full ... --poke cmd:1=TE --poke cmd:13=0x80000002 ...`; "mode 2" is only the
   `cmd:13` word).  K2's rows add
   `-n 2 --geometry 1`: render 1 geometry only, render 2 closes the scene.  The tool prints render
   1 as green on 0xff203040
   and render 2 as red (0xffff0000) on 0xff000080 (kept output: k-pb0 `diff: ... first (1, 1)
   0xff000080 expected 0xffff0000`
   against E728's `0xff203040 expected 0xff00ff00`; the tool source has the same two colour
   pairs).  So the target hash can
   not equal E728's even on the old module [infer: the k-pb0 shape was never run on the old
   module; the colour evidence is
   the kept outputs and the tool source].  The parameter buffer differs too (dword 26 0x04000004
   is the next render's
   stream, not 0 or the twin's); TA data sha256 of K2's d0 equals E728's TE 0x40 TA data
   (8ec0ebc7...), that is checked in
   `tests/test_gen.py`.  This is why `rg-pb` runs both shapes.
2. **The fork diff gives no suspect for the image.**  `git diff 3702e0aa..8fc748b0` (10 commits):
   new debugfs files
   (`kicker`, `kick_no_bump`, `render_rgn_arrays`, kregnow rows, `par` kpoke space), firmware-task
   acceptance, two reset log
   lines, `sgxfive_kicker_zero` in the reset.  The render path with defaults is unchanged:
   `sgx_render_tadata_layout(...,
   arrays = 1)` is the old layout (KUnit pins it), `par` maps the parameter buffer only while a
   par poke is armed.
3. **No knob restores "the old behaviour"**: the only knob on a render path is
   `render_rgn_arrays`, whose default 1 already
   IS the old layout, and the session never writes it (the brief: only if it matters; it does not,
   so no `rgn` row exists).
4. **Tool confound**: E728's values come from `~/sgxfive-test-1138b`; this session uses the pinned
   `~/sgxfive-test-r1`.
   `rg-ctl` (old values from runs of r1 itself) bounds it: if every `rg-ctl` row passes and only
   an E728-shape row differs,
   the difference is module or 1138b-vs-r1 [infer; K0's k0t already reproduced one L1 geometry job
   and one L2 pixel job
   exactly, so the pinned tool and the new module agree on those].

## 2. Jobs and time

| stage | jobs | what |
|---|---|---|
| rg-ctl | 23 | 11 tri/geometry rows (1024x768 x7 incl. `-n 2/3/4 --geometry`, 640x480, 1280x1024, 512x384, 2048x1536), 7 green fills (8x8 to 256x256), 2 g-dd probes (64x64, dumps), 3 r2-a-safe tri rows (TE 0x20 at 544x400 max, TE 0xe0 at 256x160 and 320x128) |
| rg-pb | 13 | 9 E728-shape rows (TE 0x20 and 0xe0 controls, TE 0x40 x3 at 64x64, 0x80, 0xc0, mode 0, 128x128) then 4 K2-shape rows (TE 0x40 x3, TE 0x60) |

36 jobs (the brief: under about 45).  Time: a reset (3 s) before every job, the tool 0.2 to 3.5 s,
dumps kept; about 6 s a
job, health at the start and end of each stage and after it: rg-ctl about 4 minutes, rg-pb about
3, staging 1, driver health
1: **about 9 minutes**; plan 20 (health retries).  No SSH was run while preparing it, so these are
from the old sessions'
figures (r3k-pixel PREFLIGHT section 1), not measured.

## 3. Controls, held out, models (frozen in `predictions/`, decided in `score/score_rg.py`)

Labels (tallied apart): `control` = rows whose value the new module already reproduced (K0 k0t:
`ctl-dd-p1`, `ctl-green-16x16`)
or E728's own controls (`pb-e20-m2-64`, `pb-ee0-m2-64`: TE 0x20/0xe0 give the full image, hash
0xd0530839d87ea325);
`heldout` = old-module value frozen, new-module result unseen (21 + 7 rows); `replicate` =
`pb-e40-m2-64b/c`, `pb-n40-b/c`.

- `rg-ctl`: one model OLD; PASS needs every quantity equal (rc, echo, target hash, diff and first
  wrong pixel, last
  `tri` line counts, renders ok, geometry-only renders, probe o0/tri/triangle lines, TA data and
  parameter-buffer sha256 where a
  dump was kept).  Summary: controls and held-out PASS counts apart, the failing rows named with
  the differing quantity.
- `rg-pb`: E728-shape rows have H-OLD (E728's rc, hash, diff, first pixel, tri line, dump sha256s,
  dwords 0-2 and 11-26).  K2-shape
  rows have H-NEW (K2's k-pb0 values) and H-OLD (E728's hash, diff, dwords 11-26) as the
  alternative.  Verdicts:
  - **H-SHAPE**: 7 of 7 E728-shape rows as H-OLD, both E728 controls PASS and 3 of 3 K2-shape rows
    as H-NEW: the module did not
    change E728's image; k-pb0's value is reproducible and belongs to the job shape.
  - K2 value not reproducible: E728-shape rows reproduce E728 but the K2-shape rows are not H-NEW.
  - **H-MOD**: the E728-shape TE 0x40/0x80/0xc0 rows are stable run to run, differ from E728, the
    TE 0x20/0xe0 controls reproduce
    E728: the module (or the tool) changed the image; the value found is printed.
  - not reproducible (the three TE 0x40 runs disagree), a general difference (the controls fail
    too), cannot tell (NODATA or a
    fault-class row).
- Never a verdict (NODATA): no `cases.tsv` row, rc 2/124/125-127/128+, a class that is not a
  result, a fault latched before the
  job (snap 0), tool output or dumps missing.  A fault-class row is FAULT, never PASS.

## 4. Tool, module, pins

Tool `~/sgxfive-test-r1` sha256 bf4f8be2... (`TOOL.sha256`, `k.env`); a mismatch: stop and ask,
nothing is rebuilt.  Preflight
(`lib_k.sh`): kernel and firmware printed; `modinfo -F srcversion` = loaded =
**230E0EF50FFFD606C53AE3C**; debugfs files `reset
hold_recovery regs render_param render_tadata render_pb_pages alias_skip render_rgn_arrays kregnow
kpoke kicker` exist (read-only
`test -e` through `sudo -n`); defaults hold_recovery N, render_pb_pages 0x422, alias_skip 0,
render_rgn_arrays 1.  Any failure:
rc 1, nothing touched.  The knobs are read again before every job (rc 19 if another value).
Kernel-log markers
(`resgx545 r3kreg ...`, `resgx545 case NAME RUN`) go through `sudo -n tee -a /dev/kmsg` (an append
write; the guard refuses a
non-append form).  The brief asks for `os.open O_WRONLY|O_APPEND`: the runner is a shell script,
`tee -a` opens the file O_WRONLY|O_APPEND.

## 5. Staged programs

`bins/pix_green.bin` (dae26442...), `dd-p1__0.bin` (9a3b552c...), `dd-p2__0.bin` (69c37a28...):
copies of the closing sessions'
frozen programs (r3-pixel, r3-geo), frozen again here by sha256; the runner refuses any other bytes.

## 6. Stops and recovery

**Stop rule: any fault-class event (BIF fault, hang, timeout) or unexplained failure ends the
stage at once** (no hypothesis
group, no allowance): reset, health check, exit 4.  Runner exit codes (`run_stage.sh` header): 1
preflight / frozen mismatch /
table or tri row not as frozen, 3 fatal kernel message, 4 unexpected hang, fault or failure, 5
failed health recovery, 6 a job did
not return, 7 a forbidden knob or rt in a table or a dbg_write of another name, 8 missing program,
12 registers unreadable, 13 reset
failed, 14 fault latched before a job, 19 a knob not at its default.  Driver (`k.sh`): 20 frozen
files changed, 30-37 health after a
stage, 38 no scorer SUMMARY, 39 attempt directory exists, 42 render_rgn_arrays not 1 after a
stage.  After a stop the driver prints
the knobs it can read.  No reboot, no module unload, no register write, no knob write: **the lead
decides** after any stop; a wrong
image is a result, not a stop (an image mismatch does not close the `rg-pb` gate).

## 7. Risks

- Low overall: every row is a job class that completed on the old module (E773 at 1024x768 `-n
  1..4`, 640x480, 1280x1024, 2048x1536;
  E806 fills; E798 probes; E763/E788 r2-a-safe) or on this module (K0 two rows; K2 k-pb0 three `-n
  2 --geometry 1` rows, no fault).
- The largest jobs: `ctl-u-2048x1536` (3.1 Mpixel, 3.3 s on record) and `ctl-u-1280x1024`; kept
  `--keep-overflow` as recorded (an
  overflow message would be class fail: stop).
- `ctl-a1`, `ctl-a2` (TE 0xe0, the "4x" rows) were `risky` in r2-pixel because 4x faults occur at
  larger sizes (E729); these two sizes
  completed with 0 wrong in r2-pixel, E788.  The new module's render_rgn_arrays default 1 gives
  the old TA data layout (KUnit pins
  it); one 4x fault would stop the stage (rc 4) after a reset and health, a known-recoverable class.
- Nothing writes a clock-gate register, trc_hazard, kreg, kregnow, kpoke, kicker, a BIF register,
  hold_recovery, render_rgn_arrays,
  /dev/mem, a boot-loader file or a kernel.  The only debugfs write is `reset`, always through
  `sudo -n`; enforced by
  `run/guard_k.sh` and tested with about 45 injections (scripts and tables).

## 8. DEVIATIONS from the brief and from the sources

1. **Rows are not byte-for-byte their records' commands.**  The g-u1 rows drop `--dump-render
   --dump-each --words --regs` (the guard
   forbids the last three; no dump is predicted for them), so no page-need quantity U is
   predicted; E728's rows drop `--pixels` and
   `--regs`; the E806 fills drop the regtimeline (`rt` `-`, no regtimeline in this session).
   `tests/test_gen.py` compares every
   command with its record's after exactly those removals.
2. **Which sessions the controls come from**: r1-pixgeo (g-u1), r3-pixel (q-t fills), r3-geo
   (g-dd), r2-pixel (r2-a-safe), plus E728 and
   K2's k-pb0 for `rg-pb`.  r2-geo, s1, s1b, s3 and the edm sessions were looked at only at the
   level of their table headers: their
   rows need non-default `render_pb_pages` cells, regtimeline or register reads, held jobs or
   faults (excluded by the brief), so
   none was taken [infer from the headers, not row by row].
3. **E728's and K2's values are not in a published `closing-*` directory** (E728:
   `resgx545-data/texture/p1141`, K2: scratch
   `closing3/r3k-pixel/out/20261110-193547`), as the brief asked for `rg-pb`; the source column of
   the predictions cites them.
4. **Tool source drift**: main's `sgxfive-test.c` and `tri_probe.[ch]` differ from the source R1's
   binary was built from
   (`TOOLSRC.sha256`, a listing kept for the record).  The freeze therefore does not compare the
   landed source with `TOOLSRC`
   (R3K-pixel's did); it freezes the landed `sgxfive-test.c` by hash, and `tests/mock_all.py` (36
   of 36 commands accepted) ran
   against the landed build, not the pinned binary.  The pinned binary's own options are bounded
   by the old sessions that ran these
   commands on it (g-u1, q-t, g-dd, r2-a-safe, k-pb0).
5. **No hypothesis groups and no fault allowance**: the fault limit of R3K-pixel (5 a stage,
   groups) is replaced by stop-at-first.
6. **The `rgn` knob rows of the brief were not added**: no knob restores old behaviour for a
   suspect change (section 1, point 3).
7. The three `-n 2 --geometry 1` TE 0x40 rows are the "alternative hypothesis" rows; their
   old-module value does not exist (K2 never
   ran that shape on the old module), so H-OLD there carries only E728's hash/diff/dwords, which
   the colours make unreachable.
8. `os.open` kmsg markers: see section 4 (the runner is shell: `tee -a`).
