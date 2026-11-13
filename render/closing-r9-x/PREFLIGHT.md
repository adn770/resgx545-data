# r9-x preflight (the lead, before staging)

1. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74, booted 03:11), loaded and
   installed (the kit's preflight checks both). No knob is written by any row; the kit's knob
   check finds none declared. If the laptop rebooted (stock Arch), stop: scaffold again.
2. `~/sgxfive-test-rgn4` is sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a
   (the kit's stage checks it); no other tool is used. The probe programs are `bins/*.bin`
   (staged, sha256-checked).
3. `~/scratch/r9x/` does not exist or holds no attempt of this session; at least 300 MiB free on
   `~` (the kept files are a few MiB: zls dumps up to 91 pages a buffer, gzipped).
4. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED), then
   `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again (it verifies the freeze).
5. Order in the sitting: after the seeds' safe sessions (S9-geo, S9-lgeo, r9-k1), before S9-ldpm
   (DECISIONS-R9.md); stage z2 (Q101) is not part of this session.
6. `python3 kit/session.py stage .`, then `python3 kit/session.py run .` with its log outside this
   directory (`closing9/logs/run-r9x.log`). A 24 (t3 or srgb without pixel rows, a tri row
   without `job: ok`) goes on to the next stage by itself; anything else waits for the lead.
7. No fault is planned. A fault or hang in far (vertices past 2^21 pixels, a new range) stops the
   session (4): the kernel's recovery, then strict health; a failed recovery
   (`SGX recovery failed: -110`) is the lead's. No reboot, no unload, no register write.
