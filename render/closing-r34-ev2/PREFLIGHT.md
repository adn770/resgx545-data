# r34-ev2 preflight (the lead, before staging)

1. **Safe class**: `#limit 0` everywhere, no expectfault, kreg or register write; the one knob is
   debugfs `render_pb_pages` (0x82, 0xe2, 0x1c2, 0x2b6, 0x422; restored to 0x422); regtimeline
   reads 0x012c, 0x0748, 0x0660 through /dev/mem.
2. Module 7CE8E38EDB97FC5EA4F6C90 (N1), loaded = installed. Another booted module: re-scaffold.
3. `~/sgxfive-test-t10` (9bedc2d6...), `~/sgxfive-test-t30` (b5ea288d...), `~/regtimeline`
   (079f6359...) on the laptop. Nothing is built. The forms ran 34 of 34 jobs in r34-ev (E1137).
4. No build or other GPU session at the same time (the calibrations measure the quiet laptop);
   `~/scratch/r34f` is this session's alone; at least 300 MB free on `~`.
5. Time: 61 jobs, about 10 to 15 minutes, 30 at most. Order e0, e1, c0, d1, d1s, p0, p1; exactly
   one of d1 and d1s opens (gate-d1.txt, gate-d1s.txt say why). A stop: report it, do not rerun
   blindly, do not reboot.
6. Records: E1141 (Q036: c0, d1 or d1s, p0, p1), E1142 (Q111: e0, e1).
