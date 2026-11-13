# r10-dpm preflight (the lead, before staging)

1. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74), loaded = installed. After a
   reboot to stock Arch this freeze cannot run: re-scaffold with that module's srcversion (a
   freeze is never rewritten).
2. `~/sgxfive-test-rgn4` sha256 e6951558... and `~/regtimeline` sha256 079f6359... are present (the
   kit's stage checks both). Nothing is built for this session.
3. debugfs `render_pb_pages` exists and reads 0x422 (its default; the kit restores it after every
   job and by its exit trap). It is the only debugfs file written besides `reset`.
4. `~/scratch/r10d` is free on the laptop (prefix r10d, this session's only).
5. At least 300 MB free on `~` (two dumped a0 jobs, up to 3 MB each raw).
6. python3 >= 3.10 on the laptop (the kit's premise check).
7. Time: 17 jobs, about 7 s each under regtimeline (about 2 minutes) plus the kit's preflight and
   health; about 5 minutes in all. One stage, no gate.
8. Stops: any fault, hang, -110, failed health, an rc 3 without the overflow line: the stage and
   the session stop (rc 4); an a0 control off stops the stage (rc 24); an unread control stops the
   session (rc 25). The replicates never stop a stage.
9. Order in the sitting (DECISIONS-R10): after S10-tex and S10-geo, before S10-zls.
