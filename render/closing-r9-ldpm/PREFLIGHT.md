# r9-ldpm preflight (the lead, before staging)

1. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74, the one-shot boot of 03:11),
   loaded = installed. After a reboot to stock Arch this freeze cannot run: re-scaffold with that
   module's srcversion (a freeze is never rewritten).
2. `~/sgxfive-test-rgn4` sha256 e6951558... and `~/regtimeline` sha256 079f6359... are present (the
   kit's stage checks both). Nothing is built for this session.
3. debugfs `render_pb_pages` exists and reads 0x422 (its default; the kit restores it after every
   job and by its exit trap). It is the only debugfs file written besides `reset`.
4. `~/scratch/r9l` is free on the laptop (prefix r9l, this session's only).
5. At least 300 MB free on `~` (four dumped m6b jobs, up to 3 MB each raw).
6. python3 >= 3.10 on the laptop (the kit's premise check).
7. Time: about 9 minutes of jobs (60 jobs, about 7 s each under regtimeline, a little more for the
   dumped and the 2816x2048-sized ones) plus the kit's preflight and health per stage; a0 first
   (gate), then m6b, w, f9b. Stage k2 is not in this session (OD-3: 7 of 20).
8. Stops: any fault, hang, -110, failed health, an rc 3 without the overflow line: the stage and
   the session stop (rc 4); an a0 control off stops a0 (rc 24) and no later stage opens; an f9b
   calibration's need off stops f9b (rc 24). m6b's replicates and w's calibrations never stop a
   stage: the scorer gates their verdicts.
