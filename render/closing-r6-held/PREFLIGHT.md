# r6-held PREFLIGHT (the lead, before staging)

Part H (this directory) and part P (`p/PREFLIGHT.md`, its own checks) run on the same boot, P first.

## Before the boot (Mac)

1. `bash tests/run_all.sh` prints `RUN_ALL PASSED` (part H's tests, then `p/tests/run_all.sh`).
2. `run/freeze_h.sh verify` and `p`'s verify pass; `FREEZE.txt` names the hashes; `FROZEN.commits`
   pins resgx545 files at main d9b2969 (check with `git -C ~/src/resgx545 show <commit>:<path> |
   shasum -a 256`). The scorer refuses to score if the freeze does not verify.
3. The new module is the one frozen: srcversion **41E2F5C756F96D20F7109A4** (`run/h.env`
   SRCV_EXPECT), built from fork `r6-kernel` 3f0b3e74 (series check passed,
   `closing6/kernel/r6-check.pass`). If the installed build differs, STOP: refreeze is a new
   session build, not an edit.

## On the boot (one-shot test boot with `boot-test-kernel.sh`, no GRUB change; the user's OK)

4. `test-session.sh` health ok; gma500 srcversion loaded = installed = 41E2F5C7... (initramfs).
5. The runner's own preflight checks, before it touches anything: firmware hash printed; srcversion
   loaded = installed = expected; debugfs `reset hold_recovery regs render_pb_pages alias_skip
   render_rgn_arrays render_tail_room peek bif_flush` present; `cat peek` prints `reg 0x0694
   0x........`; the tool `~/sgxfive-test-rgn4` sha256 e6951558...; knobs at their defaults
   (`hold_recovery` N, `render_pb_pages` 0x422, `alias_skip` 0, `render_rgn_arrays` 0,
   `render_tail_room` 0); at least 300 MiB free on ~.
6. If r6-render4x stage B ran first on this boot: its trap restores `render_tail_room` 0; part H's
   preflight refuses to start otherwise (rc 1, nothing touched).
7. Laptop files: `~/scratch/r6h/` only (`run/`, `out/`; part P under `~/scratch/r6h/p/`), work
   directories `~/scratch/tmp/r6h.XXXXXX` (and P's own form) removed by the runners. Nothing in /tmp.

## Recovery plan (what a stop leaves)

- rc 17 (a cell's third triangle failed) and rc 10 (a held fault latched after two resets): the
  runner does NOT reset again; knobs are restored. The lead reads `runner.log` and the kept slices
  and decides (a debugfs reset by hand, or a reboot with the user's OK; the next reboot returns to
  stock Arch).
- rc 22 (two cells in a row with a -110): the kernel recovered by its second reset each time (E848);
  the stage stops after the second cell's health; remaining cells are cannot tell.
- rc 23 in s0 (bif_flush taken with nothing held): the K2 gate does not behave as the fork's tests
  say: no q row runs. rc 23 in q (a held flush refused): the K2 rows of that cell are void.
- Any other stop: health ran (or rc 5 says it failed); no reboot, no module unload, no register
  write; `run/h.sh --from STAGE` is a new attempt directory.

## Checked offline (2026-11-12, read only)

- The series adds no UAPI: `git -C /Volumes/linux/linux-sgx-r6 diff a2788bd8 3f0b3e74 -- include/uapi`
  is empty, so ~/sgxfive-test-rgn4 (e6951558, built from 4623753) talks to the new module as to rgn4.
- The new module's regs table still reads 0x0c00, 0x0c04 and 0x0c08 (`sgxfive_regdump.c` at 3f0b3e74),
  and 0x0694 stays `skip` there (only `peek` reads it).
- The tail-room commit leaves a 1x context's layout byte for byte (its message and KUnit): E848's jobs
  (no `--aa4`) fault where they did.
