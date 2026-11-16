# r34-ev preflight (the lead, before staging)

1. **Safe class**: `#limit 0` in every stage, no expectfault, no kreg, no register write; the one
   knob is debugfs `render_pb_pages` (0x82, 0xe2, 0x1c2, 0x2b6, 0x422; restored to 0x422 after
   every job and by the trap); regtimeline reads 0x012c, 0x0118, 0x0660, 0x0748 through /dev/mem.
2. The laptop runs module 7CE8E38EDB97FC5EA4F6C90 (N1), loaded = installed. If another module is
   booted (N3), the srcversion is stale: re-scaffold, do not edit.
3. The overflow probe form ran 18 of 18 rows without a fault on E0CC4027 and B60AB0B4 (E1032,
   E1057) but not yet on 7CE8E38E: N1 adds the vm_pde_* knobs (default off) and nothing on the
   render path [infer]. Check `cat /sys/kernel/debug/dri/0/sgx/render_pb_pages` reads 0x422 (the
   kit's knob check does it too).
4. `~/sgxfive-test-t10` (9bedc2d6...), `~/sgxfive-test-t30` (b5ea288d...), `~/regtimeline`
   (079f6359...) on the laptop (the stage checks them). Nothing is built.
5. No build or other GPU session at the same time: the calibrations measure the interval of the
   quiet laptop. `~/scratch/r34e` is this session's alone; at least 300 MB free on `~`.
6. Time: 42 jobs, about 15 to 25 minutes, 40 at most. Order e0, e1, e2c, e2, d0, d1; a gated
   stage whose calibration did not open is skipped (gate-STAGE.txt says why). A stop: report it,
   do not rerun blindly, do not reboot.
7. Records: E1137 (e0, e1, e2c, e2: Q111), E1138 (d0, d1: Q036).
