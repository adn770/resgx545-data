# r14-dpm preflight (the lead, before staging)

1. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74), loaded = installed. After a
   reboot to stock Arch this freeze cannot run: re-scaffold with that module's srcversion (a
   freeze is never rewritten).
2. `~/sgxfive-test-t10` sha256 9bedc2d6... and `~/regtimeline` sha256 079f6359... are present (the
   kit's stage checks both). Nothing is built for this session.
3. debugfs `render_pb_pages` exists and reads 0x422 (its default; the kit restores it after every
   job and by its exit trap). It is the only debugfs file written besides `reset`.
4. `~/scratch/r14d` is free on the laptop (prefix r14d, this session's only).
5. At least 300 MB free on `~`.
6. python3 >= 3.10 on the laptop (the kit's premise check).
7. Time: 10 jobs, about 7 to 10 s each under regtimeline (about 2 minutes) plus the kit's preflight
   and health; about 7 minutes in all. One stage, no gate.
8. Stops: any fault, hang, -110, failed health, an rc 3 without the overflow line: the stage and
   the session stop (rc 4); a PR 0 row whose sampling period is over 1000 ns (`short` 0) stops the
   stage (rc 24; the premise of R-PULSE); an unread control stops the session (rc 25).
9. First row is a PR 0 control: it must read `clr` and `short`. If regtimeline over one register
   does not print its block (or the period is long), stop and report; the period is the point of
   the session (about 0.46 us a sample expected, 7.5 us with 16 registers in r13-dpm).
10. Order in the sitting (DECISIONS-R14): after r14-tex and r14-zls, before r14-isp.
