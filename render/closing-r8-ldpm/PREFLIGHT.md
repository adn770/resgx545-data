# r8-ldpm preflight (the lead, before staging)

1. The laptop runs module 37EC97AB0CB37213C42FCCC (fork 664fd0d0), loaded = installed; the round 8
   kernel (R8-5) is NOT booted yet. If it is, this freeze cannot run: re-scaffold with that
   module's srcversion (a freeze is never rewritten).
2. `~/sgxfive-test-rgn4` sha256 e6951558... and `~/regtimeline` sha256 079f6359... are present
   (the preflight refuses another build). Nothing is built for this session.
3. debugfs `render_pb_pages` exists and reads 0x422 (its default; the kit restores it after every
   job and by its exit trap). It is the only debugfs file written besides `reset`.
4. `~/scratch/r8l` is free on the laptop: the plan named L1's prefix `r8d` and L2's `r8l`; this
   session uses `r8l` as the build prompt gave it. If r8-lgeo also takes `r8l`, run them apart
   (attempt directories differ, but archive one before the other) or re-scaffold one.
5. At least 600 MB free on `~` (dumps up to 4.6 MB raw a job, 43 dumped jobs).
6. python3 >= 3.10 on the laptop (the kit's premise check).
7. Time: about 30 minutes; a0 first (gate), then sp, m6, v, f9, k, u.
8. Stops: any fault, hang, -110, failed health, unexpected rc: the stage and the session stop;
   a control off stops its stage (rc 24) and, in a0, every later stage stays closed.
