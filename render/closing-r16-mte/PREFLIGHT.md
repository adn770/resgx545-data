# r16-mte preflight (the lead, before staging)

1. **SAFE CLASS** (R16-4 a): the fourth session of round 16 (after r16-zls, r16-usse, r16-tex,
   before r16-tw). No planned fault: any fault or hang stops rclip (4) and ends the session; a
   hook stop (24) ends it too (`on_stop = "end"`). The first `--blk-add` ever run.
2. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74), loaded = installed. After a
   reboot to stock Arch this freeze cannot run: re-scaffold (a freeze is never rewritten).
3. `~/sgxfive-test-t10` sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb is
   on the laptop (the kit's stage checks it). Nothing is built for this session.
4. No debugfs knob is written; `reset` and `regs` exist (the kit's preflight).
5. `~/scratch/r16m` is free on the laptop (prefix r16m, this session's only); at least 300 MB free
   on `~`; python3 >= 3.10.
6. Time: 15 jobs, about 5 minutes with staging and preflight.
7. Stops (README.md "Stops"): any fault, hang or hook stop ends the session; a failed recovery: do
   not reboot, report it.
8. Check before staging: README.md "Deviations" 1 (H-TILECLIP's row origin is memory row 0, the
   plan's literal "from the bottom" is the rival H-FLIP) and 4 (the gate stops the session).
