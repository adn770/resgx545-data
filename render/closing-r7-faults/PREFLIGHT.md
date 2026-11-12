# r7-faults PREFLIGHT (the lead, before staging)

r7-faults runs LAST of round 7's sessions on module 41E2F5C7 (after r7-geo, r7-rp and r7-dpm's stages on that boot), because
its rows can leave the boot unusable. Nothing in it reboots, unloads or rebuilds anything.

## Before the boot (Mac)

1. `bash tests/run_all.sh` prints `RUN_ALL PASSED`.
2. `run/freeze_f.sh verify` passes; `FREEZE.txt` names the hashes; `FROZEN.commits` pins resgx545 files at main 1c64f3a
   (`git -C ~/src/resgx545 show <commit>:<path> | shasum -a 256`); data at 830641e6. The scorer refuses to score if the freeze
   does not verify.
3. The module is the one frozen: srcversion **41E2F5C756F96D20F7109A4** (`run/f.env` SRCV_EXPECT), fork `r6-kernel` 3f0b3e74,
   the module r6-held ran on. If the laptop has rebooted since 15:37 on 2026-11-12, a one-shot boot of the installed module needs
   the user's OK (R7-2). If the loaded build differs (e.g. 37EC97AB already booted for r7-dpm's s-k), STOP: r7-faults does not
   run on another module without a new build of this session.
4. Stage order (R7-2): r7-faults is staged and run after every other session's last stage on 41E2F5C7, and before the one-shot
   boot of 37EC97AB for r7-dpm's s-k.

## On the boot

5. `test-session.sh` health ok; gma500 srcversion loaded = installed = 41E2F5C7... (initramfs).
6. The runner's own preflight, before it touches anything: firmware hash printed; srcversion loaded = installed = expected;
   debugfs `reset hold_recovery regs render_pb_pages alias_skip render_rgn_arrays render_tail_room peek bif_flush kregnow`
   present; `peek` prints `reg 0x0694 0x........` (identity only); `kregnow` lists 0x0c00; the tool `~/sgxfive-test-rgn4` sha256
   e6951558...; knobs at their defaults (`hold_recovery` N, `render_pb_pages` 0x422, `alias_skip` 0, `render_rgn_arrays` 0,
   `render_tail_room` 0); at least 300 MiB free on ~; the ledger `~/scratch/r7f/run/minus110.ledger` below 16.
7. The earlier sessions' traps must have left those defaults; the preflight refuses to start otherwise (rc 1, nothing touched).
8. Laptop files: `~/scratch/r7f/` only (`stage/` the staged tree, `out/` the kept stages, `run/` the ledger), work directories
   `~/scratch/tmp/r7f.XXXXXX` removed by the runner. Nothing in /tmp. The ledger is the session's -110 budget across attempts:
   never delete it between attempts of this session.

## End state (what the lead does after the session)

The session's worst cases and what they leave:

- **rc 0 or rc 25 (the budget):** every cell ended with an exact health pair; the knobs are at their defaults. The boot is
  usable; the next step is r7-dpm's one-shot boot of 37EC97AB anyway (R7-4), which also clears anything the -110s left.
- **rc 24 inside a stage (its rule):** the driver ran health and went on; the same as above.
- **rc 26 (a dead boot: the second boot of a recovery failed, or "SGX boot: BIF fault during reset"):** never seen (54 of 54
  second boots came up, E901). The runner wrote the two knobs back and did **no** reset. The GPU is likely unusable for the rest
  of the boot. Do not reset by hand; read `runner.log`, the kept `NAME.row.dmesg` and `kernel.log`, tell the user, and ask for a
  reboot (the next reboot returns to stock Arch, or the one-shot boot of 37EC97AB if r7-dpm's s-k is next).
- **rc 17 (a cell's third triangle failed) and rc 10 (a held fault still latched after two resets):** the knobs are restored,
  no further reset. The lead decides: a debugfs reset by hand, or a reboot with the user's OK, as for rc 26.
- **rc 16 / rc 5 (health failed after a cell or a hang):** the usual recovery ran; the session stopped. The lead runs
  `test-session.sh`; if it fails, the reboot path above.
- **rc 44 (a stage's premise: a control with no reading, e.g. no held job faulted so no boot to read) and rc 43 (a scorer
  input not kept):** the stage ran to its end with health ok; the session stops so the lead reads why before anything else runs.
- **rc 18 (the laptop stopped answering a BIF write or a regs read, E317):** nothing more was touched; the laptop may need a
  power cycle: ask the user.
- Never from the runner or the driver: a reboot, a module unload, a GRUB change, a build.

## Checked offline (2026-11-12, read only)

- The fork at 3f0b3e74 keeps `kregnow` with E826's BIF rows (`sgxfive_kregnow_bif_allowed`: idle or a held recovery) and its
  log line `kregnow 0x0c00: OLD -> NEW, reads R, BIF_INT_STAT I BIF_FAULT F`; `0x0c00^=0x10` is the flip form E826 used.
- The kernel's boot strings the runner reads (`SGX boot: no INIT_COMPLETE after 500 ms`, `SGX recovery failed: -110`, `SGX boot:
  BIF fault during reset`, `job N hung, recovering`) are the fork's at 3f0b3e74 (`sgxfive.c`, `sgxfive_sched.c`).
- The fork's TA-data layout (`sgx_render.c` at 3f0b3e74) gives every kept fault page (`tests/test_gen.py`); the probe tool
  `~/sgxfive-test-rgn4` (4623753) prints `scratch +0x000 0x...` or `scratch unchanged` and exits 3 when a probe job failed.
- `tools/usse-asm/usse-asm` (as built on the Mac, untracked) assembles l0 and l4 to E088's kept programs byte for byte.
