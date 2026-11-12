# r6-misc preflight (read before staging)

**Freeze 2 (after attempt 20261112-144153): rerun q287 only.** README.md "Attempt 1 and freeze 2".
`run/freeze_m.sh verify S6`, `run/stage_m.sh S6` (the fixed runner must be restaged), then
`run/m.sh S6 --only q287` (a new attempt directory). New stop: rc 23, a file a scorer reads (the
output, a depth dump) was not written or not kept.

## 1. Before anything: what must be true

- The laptop is on the rgn4 boot as it stands: kernel 7.3.0-resgx545, gma500 srcversion
  **99CD90DA26E3AFF9C450517** loaded = installed (handover 2026-11-12-r5, "State"); stock firmware;
  knobs at their defaults (hold_recovery N, render_pb_pages 0x422, alias_skip 0,
  render_rgn_arrays 0). The runner checks all of this read-only and refuses otherwise.
- `~/sgxfive-test-rgn4` has sha256 e6951558... (`TOOL.sha256`).
- Session order (DECISIONS-R6 R6-2 a): r6-pixel, r6-dpm, **r6-misc**, then r6-render4x stage A
  (last before the reboot). No reboot is needed or allowed here.
- At least 200 MB free on the laptop's `~` (the runner checks before every job), and
  `~/scratch/r6m/` absent or holding only earlier attempts of this session.
- The build host (cachix) is reachable from the Mac for one userspace build.

## 2. The lead's commands (Mac)

```
export SGX_TARGET_HOST=jtorra@10.42.0.2            # or the LAN address; as for the other sessions
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
cd ~/src/scratch/resgx545/closing6/r6-misc
export PYTHONDONTWRITEBYTECODE=1
PY=~/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
bash tests/run_all.sh                    # offline, all must pass (about 5 minutes)
lead/build_tool6.sh                      # cachix: t6 from resgx545 d9b2969, prints "sha256 S6"
run/freeze_m.sh tool6 S6                 # fills the TOOL6.sha256 slot (once)
run/freeze_m.sh verify S6
SGX_DRY_RUN=1 run/stage_m.sh S6          # prints the commands
run/stage_m.sh S6                        # copies to ~/scratch/r6m, checks t4, t6 and every file
run/m.sh S6                              # the session (stops: section 5)
$PY score/score_m.py verdict out/ATT S6  # one SUMMARY a stage
```

`run/m.sh S6 --from STAGE` (a new attempt directory) continues after a stop; `--only STAGE...`
reruns stages. The scorers, `m.sh` and `stage_m.sh` refuse without S6 (the freeze's input).

## 3. Safety (checked by run/guard_m.sh and tests/run_mock.sh)

- Debugfs only through `sudo -n`; the only write of the runner is `reset 1` (no knob, no hold, no
  kreg, no BIF or clock-gate register, no firmware `str`, no trc_hazard). The tool writes its own
  kernel pokes (q287: ta:7, rd:1, rd:11..13 as E831; q086: ta:143, 144, 146 as E511); the reset
  before every job and at exit disarms what a job left.
- Kernel-log markers by `sudo -n tee -a /dev/kmsg`; each job's log is the slice after its marker.
- Every `timeout` with `-k`; every ssh and scp bounded (perl alarm); no wait loop.
- Files only under `~/scratch/r6m/` and one `mktemp -d ~/scratch/tmp/r6m.XXXXXX`, job directories
  removed once kept and the mktemp directory at exit; never `/tmp`.
- No reboot, GRUB change, kernel build or compile on the laptop. t6 is built on cachix only.

## 4. Predictions (frozen before any job)

`PREDICTIONS.sha256` and `FROZEN.sha256` were written 2026-11-12 against resgx545 main d9b2969
(`FROZEN.commits`); `TOOL6.sha256` is the slot the lead fills (it does not change either file).
q289: M-OR and M-ADD per row (8 separating rows). q287: rule A and FLOOR stored sets per row
(separating at 7, 11, 19, 23, 35). q086: H-COV (R and U2/U2Q complete, FX and HS fault) and H-ANY.

## 5. Stops and recovery

| rc | meaning |
|---|---|
| 1 | preflight: module, knobs, a tool (t4 always, t6 for q287), a table, runner, FROZEN.sha256 or TOOL6.sha256 that is not the frozen one |
| 3 | a fatal kernel message (no reset) |
| 4 | an unexpected fault, hang or failure (strict health first) |
| 5 | a failed health recovery |
| 6 | a job did not return (no reset) |
| 7 | a knob or tool the session does not allow |
| 12, 13, 14 | registers unreadable / a reset failed / a fault latched before a job |
| 15 | q086: the 3rd fault-class event with rows of a live group left |
| 16 | strict: the first health after a fault failed (recovery done) |
| 17 | q289: the second row without a hash |
| 18 | q086: a fault that is not the 3D-side class (0x0100, 0x100000xx) or a -110 |
| 21 | q287: gateodd, the odd height refused (clean; the driver goes on to q086) |
| 22 | less than 200 MB free on ~ |
| 23 | a file the scorer reads (the output, a `--depth-dump` row's dump) was not written or not kept (freeze 2) |

Driver: 2 usage (no S6), 20 frozen files changed, 30-37 health after a stage, 38 no SUMMARY, 39 the
attempt's stage directory exists, 42 a knob not at its default after a stage. **After any stop:
no reboot, no module unload, no register write. The lead decides.** A refuting outcome is a
result, not a stop.

## 6. Risks

- **q289, q287: low.** 1536 fills of this poke ran clean (E876); E730/E831's 27 depth jobs ran
  clean. New: an odd height on the rgn4 module (the dry 34 x 17 row goes first, gateodd).
- **q086: medium, 3D side.** Up to 3 faults of E511's class (0x90100 at 0x1000001x), each followed
  by strict health; rgn4 recovered 0x90100-class faults in E845 and E848. A TA-side fault or a
  -110 stops the stage.

## 7. After the run

The driver copies each stage to `out/ATT/STAGE` on the Mac; afterwards move the laptop's
`~/scratch/r6m` to `~/scratch/archive/` (HACKING). The fold publishes this directory except
`debug/`.
