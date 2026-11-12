# r7-rp preflight (read before staging)

## 1. Before anything: what must be true

- The laptop is on the test kernel 7.3.0-resgx545 with gma500 srcversion
  **41E2F5C756F96D20F7109A4** (fork 3f0b3e74) loaded = installed (handover 2026-11-12-r6). If it
  has rebooted (stock Arch, no render node), a one-shot boot (`boot-test-kernel.sh`) needs the
  user's OK first, then `test-session.sh` and the srcversion check. Knobs at the defaults:
  hold_recovery N, render_pb_pages 0x422, alias_skip 0, render_rgn_arrays 0, render_tail_room 0.
  The runner checks all of this read-only and refuses otherwise.
- `~/sgxfive-test-rgn4` has sha256 e6951558... (`TOOL.sha256`).
- Session order (DECISIONS-R7 R7-2 a): r7-geo, **r7-rp**, r7-dpm, r7-faults last. r7-rp's only
  expected faults are q086's five (3D side, recoverable), in its last stage.
- At least 200 MB free on the laptop's `~` (checked before every job); `~/scratch/r7r/` absent or
  holding only earlier attempts of this session.
- The build host (cachix) is reachable from the Mac for one userspace build (t7).
- Mac: `debug/tool6-i686/sgxfive-test` (round 6's t6, 97df5c0e..., copied from
  `closing6/r6-misc/debug/tool6-i686`) is present; `run/stage_r7.sh` checks its hash.

## 2. The lead's commands (Mac)

```
export SGX_TARGET_HOST=jtorra@10.42.0.2            # or the LAN address; as for the other sessions
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing7/r7-rp
export PYTHONDONTWRITEBYTECODE=1
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
bash tests/run_all.sh                    # offline, all must pass (about 15 minutes)
lead/build_tool7.sh                      # cachix: t7 from resgx545 main 1c64f3a, prints "sha256 S7"
run/freeze_r7.sh tool7 S7                # fills the TOOL7.sha256 slot (once)
run/freeze_r7.sh verify S7
SGX_DRY_RUN=1 run/stage_r7.sh S7         # prints the commands
run/stage_r7.sh S7                       # copies to ~/scratch/r7r, checks t4, t6, t7, programs, files
run/r7.sh S7                             # the session (stops: section 5)
$PY score/score_r7.py verdict out/ATT S7 # SUMMARY lines per question
```

`run/r7.sh S7 --from STAGE` (a new attempt directory) continues after a stop; `--only STAGE...`
reruns stages. The scorers, `r7.sh` and `stage_r7.sh` refuse without S7 (the freeze's input).
Q139's held-out rows are read only after the fold fits a placement model:
`$PY score/score_dump.py q139-fitdata out/ATT/q139`, fit, hash, commit, then
`$PY score/score_dump.py q139-heldout out/ATT/q139 MODEL_SHA`.

## 3. Safety (checked by run/guard_r7.sh and tests/run_mock.sh)

- Debugfs only through `sudo -n`; the runner writes `reset 1` and, for q293's four rows only,
  `render_rgn_arrays 1` (read back) and `0` after the job and at every exit. No other knob, no
  hold, no kreg, no BIF or clock-gate register, no firmware `str`, no trc_hazard. The tool writes
  its own kernel pokes; the reset before every job and at exit disarms what a job left.
- Kernel-log markers by `sudo -n tee -a /dev/kmsg`; each job's log is the slice after its marker.
- Every `timeout` with `-k`; every ssh and scp bounded (perl alarm); no wait loop.
- Files only under `~/scratch/r7r/` and one `mktemp -d ~/scratch/tmp/r7r.XXXXXX` per stage run,
  job directories removed once kept and the mktemp directory at exit; never `/tmp`.
- No reboot, GRUB change, kernel build or compile on the laptop. t7 is built on cachix only.

## 4. Predictions (frozen before any job)

`PREDICTIONS.sha256` and `FROZEN.sha256` were written 2026-11-12 against resgx545 main 1c64f3a
and data 830641e6 (`FROZEN.commits`); `TOOL7.sha256` is the slot the lead fills (it changes
neither file; no prediction names a tool hash). README.md "Hypotheses" lists every frozen model.

## 5. Stops and recovery

| rc | meaning |
|---|---|
| 1 | preflight: kernel module, knobs (incl. render_tail_room), a tool (t4 always; t6, t7 when a row needs it), a table, runner, program, FROZEN.sha256 or TOOL7.sha256 that is not the frozen one |
| 3 | a fatal kernel message (no reset) |
| 4 | an unexpected fault, hang or failure (strict health first) |
| 5 | a failed health recovery |
| 6 | a job did not return (no reset) |
| 7 | a knob or tool the session does not allow |
| 8 | a staged program missing |
| 12, 13, 14 | registers unreadable / a reset failed / a fault latched before a job |
| 15 | q086: the 6th fault-class event with rows left |
| 16 | strict: the first health after a fault failed (recovery done) |
| 18 | q086: a fault that is not the 3D-side class (0x0100, 0x100000xx) or a -110 |
| 19 | render_rgn_arrays did not read back (q293), or q086's FX bridge completed (E886 needs a correction naming the module) |
| 21 | q287: odd width refused (clean: the even-width rows ran; the driver goes on) |
| 22 | less than 200 MB free on ~ |
| 23 | a file a scorer reads (output, depth dump, render dump) was not written or not kept |

Driver: 2 usage (no S7), 20 frozen files changed, 30-36 health after a stage, 37 a copy failed,
38 no SUMMARY, 39 the attempt's stage directory exists, **40 the s0 gate failed**, 42 a knob not
at its default after a stage. Gate q291g or p7-rdc failing skips q291 or p7-rd (printed `GATE:`)
and the session goes on. After any stop: no reboot, no module unload, no register write; the lead
decides.

## 6. Check before staging

- t7's hash: `lead/build_tool7.sh` prints it; the binary must never reach the laptop except by
  `run/stage_r7.sh`.
- u2 (q293) is frozen on E888's 99CD90DA dump and hash; a mismatch on 41E2F5C7 voids q293's
  controls (a finding).
- x-rd-7's tag (README deviation 3) if the lead wants another unused tag: regenerate and refreeze
  before staging.
