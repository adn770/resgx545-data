# r38-n3c-s4

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 94a7de5eaeb0 (branch
r38-rebuild, not on main; kit/ is that commit's blobs) and resgx545-data 5fa307500702, laptop
prefix `r38d`, HostKeyAlias `cedar`. Design: `closing29/n3c/design.md` (N3c, **session S4**:
§2.2 row R5 `H`; §3 risks; §4 items 2, 3, 5-7). **Flagged** (user present, reset ready). Built
offline, frozen, not staged, not run.

**Module.** The r38-kernel module (fork r38-kernel e1cf9d2b43ab, red r38-red 82b6c2082130), not built
yet. `srcversion` in session.toml is the placeholder `UNBUILT-r38-kernel-e1cf9d2b43ab` (the preflight
refuses it): **the lead writes the built module's srcversion there after the boot and freezes
again** (delete FROZEN.*, PREDICTIONS.sha256, then `python3 kit/session.py freeze .`; the tables
and predictions do not change). Delivery scripts: `closing29/kernel38/`.

**When.** After the r38-kernel build and one-shot boot; S3 and S4 on the same boot, in either order (the design runs S4 first only after V0-NOT; R2 read V0-HOLDS).

**The arm.** `slots=0x1 entry=0 pds=halt`. Image: halt (`asm/fwtask/pds/halt.s`): v1's 8 data dwords, then `halt` alone; control word 0x01000100 (2 rows); the kernel's own read-only page at KERNEL_CODE + 0x22000, as r37.

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, r37-n3b-b's binding).
- The own task: `owntask/emitsb.blob` (sha256 83c25ac3cfc0..., the map's `emitsb` at 94a7de5,
  r37-n3b-b's blob): X0 0x5a5a3303 at page dword 70 right after the emit, S1 0x5a5a3304 at
  dword 84 as entry 1's first work, then pa, sa, M4 0x5a5a3302 at dword 80, state 2.

## Stage own: 1 job, under a minute (alarm 600 s), flagged, on_stop "end"

c1-a: one tester command 1, run id 1, the fill 0xdeadc0de in slots 2-5 (dwords 72-87) first,
`"ticks": true`, timeout 200 ms; then the page, snap0/snap9, the record, the gate after an ok end,
the disarm (its reset restarts `tim` and zeroes #14's slack).

## Outcomes (predictions/own.tsv, frozen; score/score.py)

| outcome | `alive` (alive_at_stop.advancing) | Δtick |
|---|---|---|
| H-STOP (expected after V0-HOLDS): any program, no instruction needed | false | 9-11 |
| H-ALIVE: the stop needs an instruction of v1/crumb | true | >= 150 |

halt has no `doutu`: the job never reports done, so the runner always stops it (rc 4) and the
reading is the tick. H-ALIVE with V0-HOLDS (r38-n3c-s1's R2) contradicts B-1: record both and
re-open the instrument.

Controls (r37's, every row): PG page dword 0 = 0x4e574f53; E0 slot 1 = M1 and the run id,
cmd 0; T0 snap0's 0x0acc running; B BIF_FAULT 0 in snap9 (else FAULT, its own outcome). The
scorer also prints the arm's kernel log line (the address the emit names, pds=, pdsat=), Δtick,
alive, and E1148's signature; never scored.

## Stage post: 2 jobs, flagged

As r37-n3b-b: after own's disarm, p1-tri and p2-fill on t30, `reads:diff` frozen at 0. Runs only
after an ok end of own (never for halt: its job cannot report done).

## Stops

As r37-n3b-b: a runner stop ends the session after reset and health (rc 4); a failed reset (rc
13 or 5) means the user's ordinary reboot to the default entry. In H every run ends in a runner stop by design.

## Deviations from the design (builder)

- Controls are r37's (PG, E0, T0, B); the arm's log line is printed, not a control (an arm that
  cannot place the image fails the load: the kit's arm is not ok, rc 26).
- The mock's model world ends ok (the fake runner cannot model halt); it tests the kit's
  plumbing only. Every H outcome is a runner stop, tested by the scorer's attempts.

## The mock's worlds and commands

As r37-n3b-b (mock/world.py, tests/, gen/ and score/ are the same files in r38-n3c-s3 to -s6,
STEP = "M", "H", "P" or "W"; the arm differs). Offline: `bash tests/run_all.sh`. Laptop:
`python3 kit/session.py stage .`, then `python3 kit/session.py run .`; after the run (or a stop):
`python3 score/score.py own out/ATT/own`, `python3 score/score.py post out/ATT/post`.
