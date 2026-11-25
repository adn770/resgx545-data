# r46-n3k-b5 fold notes (folder, 2026-11-25)

- **The module.** srcversion 10BBF3BFBD51D559106589F, linux fork r46-kernel c5094783eb88 (r45-kernel
  plus the landr and landp images; its stub twin r46-red 142e4d813806), built on cachix 2026-11-25
  (closing29/kernel39c/deliver/c5094783eb88/manifest: the series check 18 PASS, the module with the
  laptop's config, warnings 0; closing29/r46-n3k-fork-logs/cachix-wait.log; the series pass
  closing29/kernel39c/r46-kernel-check.pass). The fork's KUnit suite on the Mac shim: 51 of 51
  (closing29/r46-n3k-fork-logs/shim-r46-green-fork.log; r46-red 48 of 51, shim-r46-red-fork.log),
  and with the round's own suite 54 of 54 (shim-r46-green.log; r46-red 50 of 54, shim-r46-red.log; a
  wrong row fails, 53 of 54, shim-r46-neg.log). Installed beside the old module and initramfs, kept
  as .EC553F41 (closing29/r46-n3k-logs/install.log); one one-shot boot
  (closing29/r46-n3k-logs/boot.log), the boot's KUnit suites with no failure, gma500_sgxfive_owntask
  51 of 51 (closing29/r46-n3k-logs/postboot.log), test-session.sh arming netconsole to the Mac and
  the panic sysctls (step1-test-session.log), a stock fill and triangle ok (step2-fill.log,
  step3-tri.log). Every session of round 46 ran on that one boot (decision F (b)).
- **Boot note (not a row).** The boot's KUnit run logged a lockdep splat, `INFO: trying to register
  non-static key`, in sgxfive_debug_test_hold_recovery (the test fixture's spinlock, reached through
  sgxfive_hostirq_reset; closing29/r46-n3k-logs/netconsole-r46.log, about line 1044), and lockdep
  then turned itself off for the rest of the boot. The same splat is in the netconsole logs of
  rounds 35 and 44, so it predates this build; no session reads lockdep. A candidate fix of the
  fork's test fixture, not made here.
- One attempt, out/20261125-150329 (15:03:30), the first session of round 46
  (closing29/r46-n3k-logs/runone-B5.out, run rc 0). Row B5 of closing29/n3k/design.md section 10.1
  (decision B (b): rebuilt on today's kit with an after-read). Kit: resgx545 eaee04a4 (branch
  r46-n3k). Blob emitsb_sb043s (emitsb_sbc43s with only the sideband changed, 0x043), crumb3 at
  fw14, `form=sb043`.
- Stage b5: rc 0, scored by the driver (score-b5.txt) and rescored by hand
  (fold/reproduce-b5-20261125-150329.out): the same bytes, and the same bytes as
  closing29/r46-n3k-logs/score-r46-n3k-b5-b5.txt. `Q128-N3K-B5 RULE: B5-DONE, B5-GATE, B5-HID,
  B5-QUIET, B5-RUN, B5-SAME`; every control passed; every prediction held.
- Readings (printed): job 1 DONE, 10 ticks; post sa0-sa31 = pre; job 2 done on its GETMISCINFO kick,
  its after-read = pre = post; the gate's fill and triangle exact; K5 BIF_FAULT 0 everywhere; KC 10
  and 10. Post pa0-pa15: no V0 or V2 (landing NONE); pa1 M13, pa12 and pa14 Ma and Mb, the other pa
  the words round 45's N5 and N6 left in sa12-sa27 (r45-n3j-n5's and -n6's surveys).
- [post hoc, infer] B5's pa look like words of earlier runs kept through the boot; whether crumb3's
  douta with 0x043 land nowhere (as 0x843) is not told by one read.
- Health after the session: fill ok, triangle ok (closing29/r46-n3k-logs/health-r46-n3k-b5.log).
- Records: E1234 (b5).
