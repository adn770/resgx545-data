# r30-pde preflight (the lead, before staging)

1. **Flagged session**, with the user present (closing29/kernel/plan-kernel.md N-4 a, the full
   flagged session, user 2026-11-16): at most 20 planned faults (`#limit`s 6, 4, 6, 4), no
   control expecting one. No kernel build, no clock-gate write, no held reset, no kreg.
2. The module: srcversion 7CE8E38EDB97FC5EA4F6C90 (fork r30-kernel 8bc0877e8603), installed with
   the user's OK and booted (one-shot), **loaded = installed** (the kit's preflight checks it).
   Before the boot, the rollback file `gma500_gfx.ko.E0CC4027` exists (plan-kernel.md 2.4). After
   the boot: the in-module KUnit suites passed (KTAP in kmsg: gma500_sgx_mmu_large 6 of 6,
   gma500_sgxfive_vm and gma500_sgxfive_debug all passed) and health is ok; any failure is a
   rollback, not a run. After a reboot into another kernel this freeze cannot run: re-scaffold.
3. **Run it first after the boot** (no other session between): s0-warm's 4 MiB region (order 10,
   contiguous) is most likely had on an unfragmented machine; the module's pool keeps it.
4. t30: `~/sgxfive-test-t30` built by `bash lead/finish_freeze.sh` (its sha256 in session.toml and
   lead/TOOL30.built) before the freeze; `~/sgxfive-test-t10` sha256 9bedc2d6... for health. The
   kit's stage checks both.
5. debugfs: `reset`, `regs`, `vm_pde_addr`, `vm_pde_size`, `vm_pde_layout`, `vm_large` exist; the
   knobs read 0 before the session and are restored after every job; `vm_large` reads `none`.
6. `~/scratch/r30p` is free on the laptop (prefix r30p, this session's only); at least 300 MB
   free on `~`; python3 >= 3.10. Not while another GPU session or a build runs.
7. Time: 36 jobs, about 10 minutes of jobs, 15 to 20 with staging [infer].
8. Order: s0, f1, f2, f45, f67 (`python3 kit/session.py run .`). Each flagged stage is gated and
   ends the session on its rc 24. A hook_check stop on a changed table or a page outside the
   readings means the GPU wrote where no reading puts it: stop, read kmsg, report to the user;
   do not rerun.
9. Do not reboot on any stop; report to the user (rollback per plan-kernel.md 2.4 only with the
   user). After the run: `python3 score/score.py q109 out/ATT`.
