# r10-x preflight (the lead, before staging)

1. The laptop runs module B60AB0B475DD1E8972419B5 (fork 2a650d74, booted 03:11), loaded and
   installed (the kit's preflight checks both), with the debugfs knob `render_rgn_arrays` at 0
   (win0 writes 1 before each of its rows, the runner restores 0 after each and by its trap). If
   the laptop rebooted (stock Arch), stop: scaffold again.
2. `~/sgxfive-test-rgn4` is sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a
   (the kit's stage checks it); no other tool is used. The probe programs are `bins/*.bin`
   (staged, sha256-checked; byte copies of published bins).
3. `~/scratch/r10x/` does not exist or holds no attempt of this session; at least 300 MiB free on
   `~` (the kept files are a few MiB: depth dumps of 18 to 32 pages, gzipped).
4. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED), then
   `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again (it verifies the freeze).
5. Order in the sitting: after the seeds' sessions (rank-round10.md section 2; they may need
   t10), in one sitting on B60AB0B4.
6. `python3 kit/session.py stage .`, then `python3 kit/session.py run .` with its log outside this
   directory (`closing10/logs/run-r10x.log`). A 24 (a tri row without `job: ok`, a probe row
   without its pixel rows) goes on to the next stage by itself; anything else waits for the lead.
7. No fault is planned. A fault or hang anywhere stops the session (4): the kernel's recovery,
   then strict health; a failed recovery (`SGX recovery failed: -110`) is the lead's. A 4 at win0's
   first row with `failed: Invalid argument` is the module refusing the TE words with the knob
   set (README.md deviation 5): win0 is then dropped, nothing else is lost. No reboot, no unload,
   no register write.
