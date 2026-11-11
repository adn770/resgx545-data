# D3 b: four region-header arrays for 4x render contexts (2026-11-11)

The user chose option A, a UAPI creation flag (D3 follow-up, 2026-11-11). Everything below is
written and checked on scratch branches. Nothing is landed or pushed, and the laptop has not been
touched.

## Commits

- Linux fork: worktree `/Volumes/linux/linux-sgx-rgn4`, branch `resgx545-r3-rgn4` from
  `8fc748b05494e`. The other branches (`resgx545-r3`, `resgx545`, `sgx545`) are unchanged.
  - commit 11 `92b3b7e9336ed`: drm/gma500: give a render context a 4 MiB TA-data slot
  - commit 12 `a2788bd86537f`: drm/gma500: give 4x render contexts four region-header arrays
    (**tip**, `a2788bd86537fe8de22a37c2b61b9f48408b71a5`)
- resgx545: worktree `closing3/kernel/wt-rgn4`, branch `r3-rgn4` from main `6d1dd97`.
  - `4623753` libsgxfive: create render contexts for 4x targets. It contains the UAPI header
    copy, `sgxfive_render_ctx_create_flags()`, the mock, `sgxfive-test tri --aa4`, the tests and
    the `render_uapi.md` text.

## Slot and heap (commit 11)

- The TA_DATA heap is `0x20000000` + `0x0d000000`, with 32 slots per VM.
- A 4096 x 4096 context needs `0x223000` bytes at four arrays. That is over 2 MiB, so the slot is
  now 4 MiB (`SGXFIVE_RENDER_TD_SLOT = SZ_4M`, `SGX_RENDER_TD_LIMIT = 0x400000`).
- 32 slots now end at `0x28000000`. The slot count, the heap and DEV_QUERY are unchanged.
- One PDE spans 4 MiB, so each slot now has its own page table.
- Only address space grows: the pages a context gets still match its own TA data.
- Slot 0 keeps its address. Slot s ≥ 1 moves to `0x20000000 + s * 4 MiB`.
- 3 MiB would also fit, but those slots would not line up with page tables. Changing the slot
  count or the heap would be a bigger change.
- `sgx_render_tadata_layout_in()` takes the limit as an argument. This keeps -E2BIG tested, since
  no allowed size reaches it any more.
- `tadata_fill` now accepts pages below `0x400`. The old bound was `0x103`.
- New constant `SGX_RENDER_TD_MAX4_SIZE` = `0x223000`.

## UAPI flag and debugfs semantic (commit 12)

### The flag

- `DRM_SGXFIVE_CTX_RENDER_AA_4X` is bit 0. `DRM_SGXFIVE_CTX_FLAGS_MASK` = 1.
- It applies to render contexts only. These are `-EINVAL`:
  - the flag on a transfer context;
  - any unknown bit.
- Automatic mode gives a context made with the flag four arrays, and any other context one.

### The submission check

A job whose `te_aa` sets bit 31 or 30 is refused with `-EINVAL` at submission when the context:
- was created without the flag, and
- had no forced array count at its creation.

### debugfs `render_rgn_arrays`

- 0 is the new default: automatic.
- 1, 2 or 4 force that count on contexts created from now on. A forced count also lets those
  contexts run a TE_AA with bits 31:30 set, so a forced 1 still reproduces E729's fault.
- Any other value is taken as 0.
- Without the debug option the count is always automatic.

### Unchanged

- The ZLS buffer still keeps one array's size. Whether 4x needs more is not known.
- A 1x context is unchanged.

## Tests, and that they failed first

### Fork

KUnit cases were added for:
- the limit argument and its exact bound;
- 4096 x 4096 at four arrays (`0x223000`), which does not fit in 2 MiB;
- the slot: 4 MiB, page-table aligned, slot 3 at `0x20c00000`;
- `tadata_fill` pages `0x103`, `0x222`, `0x3ff` accepted and `0x400` refused;
- `sgx_render_rgn_arrays()` (automatic and forced);
- `sgx_render_te_aa_ms()`;
- `sgxfive_render_check()` with and without the permission;
- the flag rules in `sgxfive_ctx_check_args()`;
- the debugfs reading.

All existing 1x cases are unchanged and still run at one array.

The tests were committed alone on top of `8fc748b0` as a temporary commit `3486cd731904`, not on
the branch, and checked on cachix. The build failed with 47 errors per config: the new symbols
were undefined. Log: `rgn4-work/run-rgn4-red.log`, `rgn4-work/red-{off,on}-build.log`.

### resgx545

- `test_uapi` did not build (`rgn4-work/red-userspace-c.txt`).
- `tests/test_cli_aa4.py` failed 6 of 7 cases on the old tool
  (`rgn4-work/red-userspace-cli.txt`). The seventh is the "without the option nothing changes"
  guard, which is meant to pass.
- A new case `aa4()` in `test_render_job.c`.

## Check results

### Cachix series check

The check ran from `BASE 3702e0aa3e827` to `TIP a2788bd86537f` with
`closing3/kernel/recheck-rgn4.sh`, which uses:
- its own clone, `~/src/linux-sgx-resgx545-rgn4`;
- its own work directory, `~/src/linux-sgx-resgx545-rgn4-check` (a copy of the r3 one);
- its own pass file, `closing3/kernel/rgn4-check.pass`.

Result: **`series check passed: 24 PASS for 12 commits`**.
- Every commit is W=1 clean with debug off and on.
- Commit 11: KUnit 107/107 off, 188/188 on.
- Commit 12: 108/108 off, 190/190 on.
- Log: `closing3/kernel/run-rgn4.log`.

The round 3 pass file and log in the fork's git dir were not touched.

### resgx545 `tools/check.sh`

- Full run, as briefed: **19 steps, all passed**.
  - pytest: 3003 passed, 157 skipped.
  - libsgxfive: 387 passed, 2 skipped.
  - guard `--tree`: 0 findings.
  - Log: `rgn4-work/check-sh.log`.
- Staged guard (`guard.py --staged`): 0 findings. The pre-commit check passed.
- The tests that need the fork were rerun with `RESGX545_LINUX=/Volumes/linux/linux-sgx-rgn4`:
  - `tools/fwtask` and `test_gen_tri_progs`: 289 passed.
  - `tools/sweep`: 147 passed.
  - One earlier sweep run in that set had 18 transient failures. They did not repeat in two
    reruns, and the full run passed.

## For landing (not done here)

- `tools/sweep/kernel_masks.toml`: `cmd:1` (te_aa) is now validated (bits 31:30), not passed
  through. Update it, the `VALIDATED` list in `test_sweep.py` and the `fork` pin when the series
  lands.
- The IGT fork's copy of `dev.c` and `sgxfive.h` is now stale. `test_vendored` skips without
  `RESGX545_IGT`; re-sync at landing.
- The fork snapshots in `tools/rewrite/forks/linux`, as for round 3.

## Behaviour change the laptop check must cover

E827's row `ctl-a1-256x160-tee0` is a 4x poke job on a context without the flag at the default
setting. On the new module that job is **refused with -EINVAL**. This is by design: before, it
completed only because the target is small. To reproduce its old value it now needs
`render_rgn_arrays` set to 1. With `--aa4` it gets four arrays, a different TA data and different
dump hashes.

## Laptop check proposal

Setup:
- The module is built from fork tip `a2788bd86537f`, with the debug option on and
  `LOCALVERSION=` as in series-r3.md.
- The tool is built from resgx545 `4623753`.
- Before each job, write debugfs `reset`, then set `render_rgn_arrays` as listed. Afterwards
  write 0 back and read it back.
- `S4X` is E824's word set:
  `--poke cmd:1=0xe0000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26`.

Jobs:

1. **4x, automatic** (`render_rgn_arrays` 0):
   `sgxfive-test tri --tri-full --keep-going --wait-ms 20000 --width 288 --height 144 --max-width 288 --max-height 144 --aa4 $S4X --dump-render $W/a1`
   - Expect: the tool prints the "made for 4x targets" line.
   - Expect: it completes with 0 of 41472 wrong.
   - Expect: the TA data dump is `0x8000` bytes, E824 h1's value.
2. **The same size forced to 1** (`render_rgn_arrays` 1, `hold_recovery` Y as E824's c1):
   `sgxfive-test tri --tri-full --keep-going --wait-ms 20000 --width 288 --height 144 --max-width 288 --max-height 144 $S4X`
   - Expect E729's fault: BIF_INT_STAT `0x90004`, page `0x20006`.
   - Then read the fault, write `reset` and run the health check, as c1 did.
   - E824 saw two failed health triangles after such a fault before one passed.
3. **Refusal without the flag** (`render_rgn_arrays` 0): the line of job 2.
   - Expect `-EINVAL` at submission, nothing run and no fault.
4. **4096 x 4096 4x, automatic** (`render_rgn_arrays` 0):
   `sgxfive-test tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --width 4096 --height 4096 --aa4 $S4X --dump-render $W/a4096`
   - Expect: creation succeeds and the TA data dump is `0x223000` bytes.
   - The render's outcome has not been measured.
     - The tool accepts this size.
     - The mock renders it with 0 wrong.
     - The default PB of 0x422 pages takes 4096 x 4096 at 1x.
     - Whether 4x overflows the PB, or needs a larger ZLS, is the open question. Run it last.
5. **1x control** (`render_rgn_arrays` 0), E827 row `ctl-u-1024-n1`:
   `sgxfive-test tri --width 1024 --height 768 -n 1 --keep-going --keep-overflow --wait-ms 20000`
   - Expect E827's values: rc 0, echo `1024x768`, target hash `0xc9e301d225fe2325`, diff 0 of
     786432, triangle counts `207456 triangle, 578976 background, 0 other`, renders ok 1.
6. *(Optional)* **E827's 4x row under forced 1** (`render_rgn_arrays` 1), row
   `ctl-a1-256x160-tee0`:
   `sgxfive-test tri --tri-full --keep-going --wait-ms 20000 --width 256 --height 160 --max-width 256 --max-height 160 $S4X --dump-render $W/a1tee0`
   - Expect E827's values: target hash `0x845a011c4fbf2325`, 0 of 40960 wrong, TA data `0x6000`
     bytes with sha256 `eaa6c96c...4372992`.
   - This shows that a forced 1 gives the old layout byte for byte.

Order: 5, 1, 3, 6, 2 (fault, held), 4 (large) last.
