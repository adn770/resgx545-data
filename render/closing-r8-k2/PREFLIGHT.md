# r8-k2 preflight (the lead, before staging)

1. The laptop runs the round 8 module: gma500 srcversion B60AB0B475DD1E8972419B5 loaded and
   installed (the kit's preflight checks both), booted by the lead after r8-lgeo (decision R8-5);
   `/sys/kernel/debug/dri/*/sgx/vm_pte_flags` and `vm_pte_addr` exist and read 0 (the preflight
   refuses knobs not at their defaults). If the module is rebuilt, this session is scaffolded
   again with the new srcversion (a freeze is never rewritten).
2. `~/sgxfive-test-rgn4` is sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a
   (the kit's stage checks it); no other tool is used.
3. `~/scratch/r8k/` does not exist or holds no attempt of this session; at least 300 MiB free on
   `~` (the kept files are a few MiB).
4. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED), then
   `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again (it verifies the freeze).
5. `python3 kit/session.py stage .`, then `python3 kit/session.py run .` with its log outside this
   directory (`closing8/logs/run-r8k.log`). A 24 goes on by itself; anything else waits for the
   lead. No reboot, no unload, no register write. After the run (or a stop) the knobs read 0
   (the exit trap restores them; check with `sudo cat .../vm_pte_flags .../vm_pte_addr`).
6. Faults are expected (isolation's three in one job, xf-wo-copy, tri-wo-gen, and up to three
   EDMPROT rows): each is recovered by the kernel, then the kit's reset and strict health; a
   recovery that fails (`SGX recovery failed: -110`) stops the session. The isolation job also
   bans its own file after its third fault (kernel `3 faults within a minute, file banned`): the
   next job is a new process and is not affected (render/client-jobs ran the same).
