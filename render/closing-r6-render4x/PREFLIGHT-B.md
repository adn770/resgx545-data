# r6-render4x stage B preflight (set B)

Prepared 2026-11-12. Nothing ran on the laptop. Freeze: `FROZEN-B.sha256` + `PREDICTIONS-B.sha256`
(`FREEZE-B.txt`); stage A's `FROZEN.sha256` is unchanged (5fbd64f7...).

## 0. Check before staging (the lead)

- The module of fork branch r6-kernel at 3f0b3e74 is installed and the one-shot boot (user's OK,
  `boot-test-kernel.sh`, no GRUB change) is done: `modinfo -F srcversion gma500_gfx` and
  `/sys/module/gma500_gfx/srcversion` both **41E2F5C756F96D20F7109A4** (`run-b/k.env`; module sha256
  8a32dada935e8a293b7be03c5d1938cc31093fea4b356ed41f9cb476d421576a). The runner refuses any other
  build, the rgn4 module included.
- `/sys/kernel/debug/dri/*/sgx/render_tail_room` exists and reads 0x00000000 (automatic).
- `~/sgxfive-test-rgn4` still hashes to e6951558... (staging checks it).
- At least 300 MiB free on `~`; set A's `~/scratch/r6x` stays (B adds `run/run-b`, `FROZEN-B.sha256`).
- `bash tests/run_all.sh`: ALL TESTS: PASS; `run/freeze_k.sh verify B` passes.

## 1. Jobs, faults, time

| stage | jobs | faults predicted | limit | alarm |
|---|---|---|---|---|
| s0b | 4 | 0 | 1 | 900 s |
| b | 9 | 0 | 2 | 1800 s |
| k | 5 | 3 (k1, k4, k3 held) | 4 | 1500 s |
| r | 3 | 0 (r3 -ENOSPC) | 1 | 1500 s |

21 jobs, 3 predicted 3D-side faults (E845's class). About 20 minutes; plan 40. r1 and r2 check about
4 Mpixel each on the Atom; r1, r3 keep no dumps.

## 2. Knobs and writes

`reset 1`, `render_rgn_arrays 0`, `render_pb_pages 0x422`, `hold_recovery Y|N` (k3 only), and
`render_tail_room` 0 or the row's value (0x4000, 0xb000, 0x3000, 0xa000), each read back
numerically, put back to 0 after the job and by the exit trap; nothing else. No peek, no bif_flush
(not this session's), no kreg/kregnow/kpoke write, no clock-gate register, no reboot or build.

## 3. Controls

| control | passes | fails |
|---|---|---|
| s0b (4 rows) | kept hash, diff, pages; TA data 0x8000 / 0x2a000 (4x), 0x11000 (1x) | set B void (the module is not the change) |
| b9 | 1024 x 768 completes | b stops (rc 4) |
| k1 | 0x4000 at 1280 x 1024 faults (the rgn4 layout) | the knob is not what it says: k void |
| k5 | 0x4000 at 1024 x 768 completes at the limit | no k claim |

## 4. Stops

As stage A (PREFLIGHT.md section 5), plus: rc 19 if `render_tail_room` does not read back, does not
go back to 0 after a job, or is not 0 at the stage's end; rc 1 if it is missing or not 0 at the
start. Any fault in r stops (it would be the 4096-wide residue showing itself: keep the logs).

## 5. Risks

- k: three faults of the class taken 14 times with health ok (r5, stage A); k3 one held fault.
- r: the largest contexts (TA data 0xbb000 and 0xd9000, inside 4 MiB); r3 overflows as E846's o7
  did, now with the tail room in place (E846 also faulted: the residue). After any stop: no reboot,
  no module unload, no register write; the lead decides.
