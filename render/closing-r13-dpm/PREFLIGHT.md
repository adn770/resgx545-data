# r13-dpm preflight (the lead, before staging)

1. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74), loaded = installed. After a
   reboot to stock Arch this freeze cannot run: re-scaffold with that module's srcversion (a
   freeze is never rewritten).
2. `~/sgxfive-test-t10` sha256 9bedc2d6... and `~/regtimeline` sha256 079f6359... are present (the
   kit's stage checks both). Nothing is built for this session.
3. debugfs `render_pb_pages` exists and reads 0x422 (its default; the kit restores it after every
   job and by its exit trap). It is the only debugfs file written besides `reset`.
4. `~/scratch/r13d` is free on the laptop (prefix r13d, this session's only).
5. At least 300 MB free on `~`.
6. python3 >= 3.10 on the laptop (the kit's premise check).
7. Time: 8 jobs, about 7 to 10 s each under regtimeline (about 1.5 minutes) plus the kit's preflight
   and health; about 5 minutes in all. One stage, no gate.
8. Stops: any fault, hang, -110, failed health, an rc 3 without the overflow line: the stage and
   the session stop (rc 4); a PR 0 row reading a partial render stops the stage (rc 24); an unread
   control stops the session (rc 25).
9. First t10 `probe` under regtimeline on B60AB0B4 (r10-dpm ran t4): the first row is a PR 0 control
   that reads nparts 0, knob 0x400 and clr; if it does not read, stop (rc 25) and report.
10. Order in the sitting (DECISIONS-R13): after r13-tex and r13-zls, before r13-isp.
