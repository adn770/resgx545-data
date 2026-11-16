# Round 29: the kit word `kreg:OFF=V` (Q024), design

Morning list item 2 (handover r27 item 3; R27-6, round 22's I2 T-kregword, round 18's
unlock survey I2). Branch `r29-kreg` off resgx545 main c057181, worktree
`closing29/kreg/wt`. Nothing touches the laptop until the user approves (section 8).

## 1. What changes, and the rule it moves

The kit's header says "no register write of ours" (`tools/closing/kit/run_stage.sh`; `lib_kit.sh`
allows only `reset 1` and declared knobs), `session.py` refuses `--kreg` (`FORBID_OPTIONS`) and
any `kreg` in the laptop files (`FORBID`). E396 wrote 0x0a78 with debugfs `kreg` from a probe
script outside the kit, so Q024 could not be continued in a kit session (round 27, section 3).

The rule becomes: **no register write of ours, except one `kreg:OFF=V` word per row in a stage
declared flagged, to a register on the kit's frozen allow-list, with the read-back, restore and
trap below.** `--kreg` (the tool option) stays refused everywhere; `kregnow` stays refused
everywhere; hooks still may not write anything.

## 2. The fork's interface (read only, linux-sgx branch resgx545 456404fcffe5)

- `sgxfive_debug.c` `sgxfive_kreg_write`: debugfs `dri/N/sgx/kreg`, one line `OFFSET=VALUE`
  (or `OFFSET^=VALUE`, a flip; the kit never uses it). Refused `-EPERM` for a register off
  `sgxfive_kreg_allowed`, `-ENODEV` unless the firmware is live, `-EBUSY` while a render-node
  job is queued; under the device lock; every write logged
  (`sgxfive: kreg 0x%04x: old -> new, reads x`). "The value stays until the next write or the
  next reset of the SGX."
- Reading `kreg` prints every allowed register, `0xOFFS 0xVALUE` a line (`0x%08x`).
- `sgxfive_kpoke.c` `sgxfive_kreg_allowed`: 0x0418, 0x04dc, 0x04e8, 0x0520, 0x0800, 0x0810,
  0x0814, 0x0818, 0x0a78, 0x0abc. The 0x0810-0x0abc range is never reached by the EDM firmware
  (the kernel's comment, from `sgxfive_regdump_regs`).

## 3. The word

Exact syntax, in the knobs column of a table row:

    kreg:0x0a78=0xV

- OFF: `0x` and exactly four lower-case hex digits; V: `0x` and 1 to 8 lower-case hex digits.
  No flip form (`^=`), no decimal, no upper case. One kreg word a row.
- session.toml declares the register and the values its rows may use:

      [kregs]
      "0x0a78" = { values = ["0x00", "0x01", ..., "0x3f"] }

  and the stage: `[stages] k1 = { alarm = 7200, class = "flagged", on_stop = "end" }`.
  No `default` key: the default is the kit's.

**Allow-list (frozen in the kit, tested equal on both sides):** `KREG_ALLOWED` in
`kit/session.py` and `KIT_KREGS` in `kit/run_stage.sh`:

| register | default (restored) | values | why |
|---|---|---|---|
| 0x0a78 (CR_PDS_REG_0A78) | 0x2c (the firmware's, E141) | 0x00-0x3f | E045 drew all 64 exactly |

0x0a78 alone. The other nine of the kernel's list (0x0818 for Q001, 0x0810 for Q111, BIF list
registers for Q076) are not added: each would need its own value range, a reason it cannot wedge
the core, and the user's OK; adding one is a kit change with its test (section 7).

## 4. What the runner does

Guard (Mac, `session.py guard`, so freeze and mock too) and runner (laptop, rc 7, nothing runs)
both refuse: a kreg word in a stage that is not `class = "flagged"`; a register not on the
allow-list or not in `[kregs]`; a value not declared or above the register's largest; two kreg
words in a row; kreg with `expectfault`. The guard also refuses a flagged stage before a safe
one, an unknown class, a `[kregs]` default, and any `kreg`/`kreg_set`/`kregs_restore` in
`run/hooks.sh`; in the kit's own files only the one write and one read line pass.

Per row, in order:

1. reset (unless `noreset`), the `dbg:` knobs;
2. **pre-check**: the register reads its default (else rc 19, no write, no job);
3. **write before the job**: `OFF=V` to debugfs `kreg` (`sudo -n timeout -k 5 20 tee`);
4. **read-back**: the write's status 0 and `kreg` reads V by value (`same_value`), else
   `## STOP: kreg OFF does not read back V before NAME`, rc 19, the job never runs; then the
   kernel-log mark `kreg NAME OFF=V`;
5. snap, the job, snap, slice, keep, classify (a fault or hang is unexpected: rc 4 stop);
6. **restore after the job**: the default written and read back; if not, a reset and once more,
   else rc 19; mark `kreg-restored NAME`;
7. **trap**: at every exit once any kreg was written (rc 3 and rc 6, the frozen stops, included)
   the default is written again and read back (`exit kregs restored`); after the trap's reset
   (not on a fatal stop) it reads the register once more and logs a mismatch.

The preflight checks debugfs `kreg` exists and every declared register reads its default (read
only). A safe stage never writes a declared register, not even in its trap (tested). The kit does
not lean on the reset to put 0x0a78 back: whether the SGX reset restores 0x2c is not shown
[infer], so the fake laptop keeps the value across a reset and the restore is explicit.

## 5. Q024's session (for the builder, after approval)

Q024 (pds, low, E045, E141, E396): "does CR_PDS_REG_0A78 change timing". E396: six values,
five shuffled runs each, medians within 0.3 percent (67274-67469 us); open are the other 58
values and a load with many small triangles.

**Session r29-kreg (prefix `r29k`), tool t10 (`tri --width 256 --height 256 -n 6` prints each
render's `tri 256x256 #i: T us`; the reading is the mean of renders 2-6, as E141/E396).**

| stage | class | rows | jobs |
|---|---|---|---|
| s0 | safe | c0 control, 8 references | 9 |
| k1 | flagged, `on_stop = "end"`, `#limit 0` | 128 values, 16 controls, end control | 145 |
| k2 | flagged, `#limit 0` | second load, 8 values x 3 runs | 24 |

- s0: c0 an exact 64x64 triangle (`reads:diff`); 8 reference rows at the reset value, no write.
- k1: the 64 values x 2 passes, each pass its own frozen seeded shuffle; a `kreg:0x0a78=0x2c`
  control every 8th row (16); an end control, an exact 64x64 triangle with no write
  (`reads:diff`).
- k2: 0x00, 0x01, 0x08, 0x20, 0x2c, 0x3f and k1's two farthest values, 3 runs each.

About 178 jobs; at ~25 s a job (reset wait, snaps, keeps) about 75 minutes [infer: round 27's
"~1.5 h at three jobs a value"]. k2 needs a frozen form for "many small triangles": t10's
`--vertices N` (copies of the triangle, up to 1500) is the candidate; the builder must confirm on
the library mock that it is timed and replays, else k2 is dropped and Q024 narrows only.

**Frozen prediction (H0, the negative):** for every value, both passes' times lie within
plus or minus 1.0 percent of the median of k1's sixteen 0x2c controls. The bound is three times
E396's spread and below E141's two excursions (2.6 and 5.5 percent), so it would have caught
them. Fit vs held-out: pass A names any value outside the bound; pass B (held out, its own
shuffle) must repeat it in the same direction for a dependence. A value outside on one pass only
is noise by the frozen rule.

**Controls that can fail:** k1's 0x2c write rows against s0's no-write references (within 1
percent, else the write path itself perturbs and the stage cannot tell); the controls' own spread
(interquartile range at most 0.5 percent of their median, else too noisy to read 1 percent:
cannot tell, no retirement); the end exact-triangle control (`reads:diff`); the runner's per-row
read-back.

**What retires it (a bounded negative):** no value of 0x00-0x3f outside the bound on both passes
at 256x256, the controls' premises held, and k2 within the same bound: then Q024 retires as
"CR_PDS_REG_0A78 does not change a render's time by more than 1 percent at any of its 64 values
on the two loads". A value outside on both passes is a finding (Q024 stays open, narrowed to
that value). Without k2, Q024 narrows (the many-triangles clause stays). Records from the
lead's numbers (E1114 onward if R29's E1108-E1113 hold).

## 6. Risks

- **Wedging the core.** 0x0a78's function is unknown. Against: E045 drew all 64 values exactly,
  E396 made 30 writes and 30 restores cleanly, the kernel's comment says the EDM firmware never
  reaches 0x0810-0x0abc, and `tools/fwtask/fwtask_run.py` writes it too. For: a value could stall
  the PDS so a render hangs; the kernel's recovery then runs and the row stops the stage (no
  `expectfault` with kreg). A hang the kernel does not recover (rc 3, rc 6) leaves the trap's
  write; if that fails too the laptop needs the user (a power cycle; no reboot from the kit).
- **The write lands while the firmware is not live** (right after a reset): `-ENODEV`, the
  read-back fails, rc 19 before any job. Harmless, but it ends k1; s0's reset timings show the
  3 s wait suffices for jobs, not for kreg [infer].
- **A kept value leaks into the next row**: the explicit restore and the pre-check of the next
  row (default before the write) stop it; the reset is not relied on.
- **Timing noise** (a slow render, as E396's one 0x01 run): the two-pass rule and the controls'
  spread premise, not a stop.

## 7. Stop rules

- rc 7: a kreg word outside a flagged stage, off the allow-list or undeclared (nothing runs).
- rc 19: the register not at its default before the write, a failed write or read-back (the job
  never runs), or not back at its default after the job and a reset.
- rc 4: any fault or hang in a kreg row (never a reading); then reset and strict health.
- `on_stop = "end"` on k1: its rc 24 (a hook's reason) ends the session; k2 runs only after k1
  ended 0.
- Session hook (k1, k2): stop (rc 24) on a render time above twice s0's reference median or a
  missing `renders ok` line (a wedge symptom, not timing noise).
- Any unplanned fault or failed recovery: stop, the user decides.

## 8. Implementation (branch r29-kreg) and what the user approves

Implemented test first: `kit/session.py` (`KREG_ALLOWED`, `STAGE_CLASSES`, `[kregs]`, guard,
session.env `KREGS`, `KREG_<off>_VALUES`, `FLAGGED_STAGES`, mock), `kit/run_stage.sh` (header,
`KIT_KREGS`, table check, write/restore), `kit/lib_kit.sh` (`kreg_read`, `kreg_write`,
`kreg_set`, `kregs_restore`, preflight, trap), `kit/fake/sudo` (kreg, world token `kregstuck`),
the template session.toml, HACKING "Session kit", tests in `tools/closing/test_kit.py`.

For the user:

1. The rule change (section 1): flagged-stage kreg to 0x0a78 only.
2. Merging r29-kreg into main (no laptop change; staged kits copy from a named commit).
3. Q024's session (section 5): about 178 jobs, about 75 minutes, flagged, no planned faults; the
   1 percent bound and the two-pass rule as frozen above; k2 only if the builder finds a form.
