# r45-n3j-n5 fold notes (folder, 2026-11-25)

- **The module.** srcversion EC553F41FD8324BB6BF1764, linux fork r45-kernel b1089172b2e7 (r42-kernel
  plus the crumbz and landq images; its stub twin r45-red 7e3d392bc612), built on cachix 2026-11-24
  (closing29/kernel39c/deliver/b1089172b2e7/manifest: the series check 16 PASS, the module with the
  laptop's config, warnings 0; closing29/r45-n3j-fork-logs/cachix-wait.log; the series pass
  closing29/kernel39c/r45-kernel-check.pass). The fork's KUnit suite on the Mac shim: 48 of 48
  (closing29/r45-n3j-fork-logs/shim-r45-green-fork.log; r45-red 45 of 48, shim-r45-red-fork.log),
  and with the round's own suite 50 of 50 (shim-r45-green.log; r45-red 46 of 50, shim-r45-red.log; a
  wrong row fails, 49 of 50, shim-r45-neg.log). Installed beside the old module and initramfs, kept
  as .079DD0D1 (closing29/r45-n3j-z-logs/install.log).
- **The laptop event (unexplained, recorded as seen; not a row).** After the first one-shot boot
  onto EC553F41 (2026-11-25, about 01:31, closing29/r45-n3j-z-logs/boot.log: the one-shot entry and
  `gma500_gfx.sgx_render=1`), the post-boot routine's ssh session opened, and the laptop then hung
  hard: a black screen, the ssh session reset (closing29/r45-n3j-z-logs/postboot.log: `Connection
  reset by peer`), no oops or panic in the journal, and no netconsole output, since netconsole was
  not yet armed at that point of the routine. The user rebooted it to the stock entry. A second
  one-shot boot (closing29/r45-n3j-z-logs/boot2.log: srcversion EC553F41 loaded) then ran the
  routine one step at a time, cleanly: the boot's KUnit suite gma500_sgxfive_owntask 48 of 48
  (boot2-dmesg0.log), test-session.sh armed the panic sysctls and netconsole
  (step1-test-session.log), a stock fill ok (step2-fill.log, the firmware answered after 144 us) and
  a triangle ok (step3-tri.log); then N5 and N6. A line `clocksource: Watchdog remote CPU 1 read
  timed out` appeared about 30 s after the second boot (boot2-dmesg0.log); the user reports the same
  kind of line on the first boot too, which no kept log holds. What hung the laptop is not known: no
  cause is claimed. Every N5 and N6 stage ran on the second boot.
- One attempt, out/20261125-092017 (09:20:17), the fifth session of round 45
  (closing29/r45-n3j-z-logs/runone-N5.out, run rc 0). Session N5 of closing29/n3j/design.md (section
  9, the rebuild rows; decision E (c)). Kit: resgx545 cf20aa87 (branch r45-n3j-z: K9 and the kit's
  `pds=crumbz|landq`), the blob emitsb_sbc43s, `form=sbc43` (sideband 0xc43) at fw14.
- Every stage was scored by the driver (out/20261125-092017/score-*.txt) and rescored by hand with
  the frozen scorer (fold/reproduce-STAGE-20261125-092017.out): the same bytes for all fourteen, and
  the same bytes as closing29/r45-n3j-z-logs/score-r45-n3j-n5-STAGE.txt. SV passed in every stage
  (EC553F41 installed and loaded).
- Plants wj, wk, wl, wm, wn, wo, wp (row W, image mark): every control passed; `RULE: W-QUIET,
  W-SA1, W-SA13` in each; every prediction held (W-FAULT failed as predicted). wj is the build
  control: W on the new module as on 079DD0D1. KC begin 10, end 2, as expected.
- Reads (image crumbz: crumb3 without its two douta, so it writes no attribute), each right after
  its plant; PLANT, DR, DK, SV and (from zt on) ZN passed in each; Z-QUIET held and Z-FAULT failed
  as predicted in each; the -AOTHER and ZN-OTHER outcomes read failed:
  - zn (none): (V0, M1, V2). `RULE: Z-QUIET, ZN-SAME`. Every prediction held. KC 2.
  - zt (tri): (0, 0x02400000, 0x01027817). `RULE: Z-QUIET, ZT-SA1, ZT-TRIPLE`. Every prediction held
    (ZT-ONE failed as predicted). KC 8.
  - zft (fill,tri): (0, 0x04400000, 0x010201bd). `RULE: Z-QUIET, ZFT-SA1, ZFT-TRIPLE`. Every
    prediction held. KC 10.
  - zf (fill): (2, M1, 0x0100c73d). `RULE: Z-QUIET, ZF-DRAW, ZF-SA1`. Every prediction held
    (ZF-TICK1, ZF-PLANT failed as predicted). KC 4.
  - zff (fill,fill): (2, M1, 0x0100a2e2). `RULE: Z-QUIET, ZFF-DRAW, ZFF-SA1`. Every prediction held.
    KC 6.
  - ztf (tri,fill): (2, 0x02400000, 0x01051f7e). `RULE: Z-QUIET, ZTF-DRAW, ZTF-SA1`. Every
    prediction held (ZTF-TRIPLE failed as predicted). KC 10.
  - ztt (tri,tri): (0, 0x08400000, 0x01044282). `RULE: Z-QUIET, ZTT-LAST, ZTT-TRIPLE`. Every
    prediction held (ZTT-FIRST, ZTT-ONE failed as predicted). KC 14.
- Every read: job 1 done, K5 BIF_FAULT 0 before and after, snap9 0; sa13 = pa1 = M13. Kernel "events
  seen" at each arm (printed): plants 3, zn 0, zt 2, zft 3, zf 1, zff 2, ztf 3, ztt 4.
- Post sa3-sa31 and pa0-pa15 (printed): equal in every stage from wk on; wj and zn differ from them
  at sa3-sa11 only. Against N2-N4 (the earlier boot), sa12, sa14-sa28, sa30 and pa0, pa2-pa15 hold
  other words after the new boot (sa15 0x4d2817d1 for 0x01555620, sa19 0x03c3cda4 for 0x03c3cdac,
  ...), printed, not scored.
- Health after the session ok (closing29/r45-n3j-z-logs/health-r45-n3j-n5.log).
- [post hoc, infer] With nothing written by the image, sa0 and sa2 read what the draws left: 2 and a
  timer word when the last draw was a fill (zf, zff, ztf), 0 and a timer word when it was a triangle
  (zt, zft, ztt); sa1 kept the plant after fills only and took the last triangle's word (R-DRAW
  held, R-TICK fails). Each Z row repeats its N1-N4 twin's sa1.
- Records: E1218 (wj), E1219 (zn), E1220 (wk), E1221 (zt), E1222 (wl), E1223 (zft), E1224 (wm),
  E1225 (zf), E1226 (wn), E1227 (zff), E1228 (wo), E1229 (ztf), E1230 (wp), E1231 (ztt).
