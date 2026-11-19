# r38-n3c-s1

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 2ce7fc71a1f8 (branch r38-n3c,
not on main: emitsn's commit; kit/ is that commit's blobs) and resgx545-data 31ec9b2f210f, laptop
prefix `r38s`, HostKeyAlias `cedar`. Design: `closing29/n3c/design.md` (N3c, **session S1**: §2.1
rows R1 `n0` and R2 `th`; §3 risks; §4 items 1 and 4). **Flagged** (user present, reset ready):
stage own runs our own firmware task, stage tim stops the EDM tick by design until a reset. Built
offline, frozen, not staged, not run.

**Module.** The installed r37-kernel module, srcversion 77917296568EB311B89B0DA (fork
4f35fc20ffa9); no build, no boot. Its verifier accepts emitsn: resgx545's host-verifier test runs
the fork's verifier at the pin on every source (2ce7fc7), and the fork's KUnit suite on the Mac
shim passes 25 of 25 with emitsn added to a scratch copy of `sgxfive_owntask_blobs.h` (a
negative copy with a refused blob in the list fails test 1; logs `closing29/r38-n3c-logs/shim-*`).

## Order on the laptop (the lead)

The lead does the post-boot fill and triangle (the firmware loaded) before the run, as for r37:
the own stage's first reset needs the firmware loaded. Nothing in the session does it.

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, r37's binding): the
  health tool, stage post's rows and th's wrapped probe.
- rt = `~/regtimeline` (sha256 079f6359..., r33-tim2's binding, `wraps = true`, read only).
- The own task: `owntask/emitsn.blob`, written by `tools/fwtask/fwtask.py OUTDIR
  asm/fwtask/emitsn.s` at 2ce7fc7, sha256 31f75ec5... = `asm/fwtask/fwtask.map`'s `emitsn` there
  (the freeze pins the map). Our own code.
- bins/: the recorded probe `pds-timer-tim-host__0.bin` (sha256 3968221c...) and its USE program
  `sa_dump.bin` (a8315cce...), byte copies of resgx545-data `pds/timer/pds-timer-tim-host/bins/`
  at 31ec9b2f2 (tests/test_gen.py). Our own programs; nothing firmware-derived in this session.

## Stage own (R1 `n0`): 1 job, under a minute (alarm 600 s), flagged, on_stop "end"

The kit arms `emitsn` once (`slots=0x1 entry=0`, no `pds=` word: emitsn has no emit), runs n0 (r37
A's job word for word: one tester command 1, run id 1, the host's fill 0xdeadc0de in slots 2-5 =
dwords 72-87 first, `"ticks": true`, timeout 200 ms), keeps the page, snap0/snap9 and the record,
and after an ok end the gate, then disarms. emitsn: entry 0 stores M1 0x5a5a3301 and the run id in
slot 1, cmd = 0, fence, **X0** 0x5a5a3303 (dword 70), fence, then M4 0x5a5a3302 and the run id in
slot 4 (dwords 80-81), the echo, state 2, and the tail call into the closed task.

| outcome | X0 (dw 70) | M4 (dw 80-81), state | Δtick | gate |
|---|---|---|---|---|
| N0-OK (expected): the stop needs the emit | 0x5a5a3303 | M4 + run id, 2 | >= 25 | ok |
| N0-STOP: our path stops the tick without any emit | any | any | < 25 or no done | - |

Controls (r37's, every one can fail): PG page dword 0 = 0x4e574f53; E0 slot 1 = M1 and the run
id, cmd 0; T0 snap0's 0x0acc running (bit 24 set, 23:0 <= 400000); B BIF_FAULT 0 in snap9 (else
`FAULT`, its own outcome). Rule: `N3c-R1 RULE: <outcome>` when every control passed and exactly
one outcome holds; `FAULT`; else `CANNOT TELL`. Printed, not scored: the X0 qualifier and E1148's
signature (USE0_SERV_EVENT bit 16, count minus HostCtl dword 12).

## Stage tim (R2 `th`): 1 job, under a minute (alarm 600 s), flagged

The stock firmware (own_arm off since own's disarm) after the kit's reset: `regtimeline 0.06 0.005
0x0acc -- ~/sgxfive-test-t30 probe --temps 32 --pds 36 --use $S/bins/sa_dump.bin
$S/bins/pds-timer-tim-host__0.bin`. The program loads `tim` with 0x00abcde0 (bit 24 clear: the
counter stops, and with it the EDM tick, until a reset) and stores `tim` (after 0 to 64 nops) to
scratch +0x008 to +0x014 and +0x028 to +0x034. snap9 is read right after the job, before any
reset; the stage's last reset restarts the counter (`inputs.md:64-67`), then the kit's health.

| outcome | 0x0acc in the timeline after the change | snap9 0x0acc | scratch tim |
|---|---|---|---|
| V0-HOLDS (expected): the host sees the PDS write | 0x00abcde0, constant | 0x00abcde0 | 0x00abcde0 |
| V0-NOT: a PDS tim is not the host's 0x0acc | running throughout | running | 0x00abcde0 |

Anything else is `CANNOT TELL` (scratch not 0x00abcde0: the program did not run; another
constant; a change that moves on). The change is the first stored sample that is not a running
count; regtimeline stores a sample only when it differs, so a held constant is the last line.
Controls: `ivl` = TOTAL / samples inside E1133's bounds for one register, 2500..5000 ns; `pre`:
at least one stored sample before the change, every one running. Rule: `N3c-R2 RULE: <outcome>`
or `CANNOT TELL`. V0-NOT voids B-1's reading of E1150 (the design's §1 V0).

## Stage post: 2 jobs, under a minute (alarm 600 s), flagged

After tim's last reset: p1-tri and p2-fill on t30, the health pair's bare argv, controls
`reads:diff` frozen at 0.

## Stops

`#limit 0` in every stage. own: any fault or hang, a runner stop (no done: N0-STOP, rc 4), a
failed gate (16), arm (26) or disarm (13) ends the session; run/hooks.sh stops own (rc 24, on_stop
"end") after an ok end whose cmd, state, echo, slot 1 (M1, run id, X0), slot 4 (M4, run id) is
wrong or a dword of the fill (72-79, 82-87) changed. tim: no hook stop (a hook stop would run the
health pair before the reset, with the tick stopped); a fault, hang or failed probe is the
runner's rc 4 and ends the session. If the kit's health after tim's reset fails (rc 5 or 16), the
session ends there (design §3: flagged); a failed reset (13) means the user's ordinary reboot.
Never retried, never rebooted by the session.

## Deviations from the design (builder)

- `--pds 36`, not the design's `--pds 4`: the option is the program's data dwords, and the
  recorded harness (`tools/usse-asm/probe.py` tool_args of pds-timer-tim-host at 2ce7fc7) gives
  `--temps 32 --pds 36 --use sa_dump.bin` (9 data rows of 4 dwords, `pds_dump.s`).
- regtimeline `0.06 0.005 0x0acc`: E1133's interval bounds (2500..5000, t1d) are TOTAL / samples
  over a 5 ms idle lead and the job; t1d's 0.04 covers only 35 ms of the job (its kick came 22.75
  to 25.67 ms after the tool started, E1133), so TOTAL is r33's t1 value, 0.06, for margin. The
  in-job spacing of a probe job is not measured: `ivl` can fail on it (then CANNOT TELL, never a
  wrong outcome). A change later than 55 ms after the tool starts gives a timeline that runs
  throughout with snap9 stopped: CANNOT TELL, not V0-NOT.
- N0-OK's gate: the kit's gate file (`n0.gate.json` ok); N0-STOP is `<25|nodone` (a done job with
  fewer than 25 ticks reads N0-STOP too).
- The fork's KUnit list (`sgxfive_owntask_blobs.h`) is not changed (no fork commit); resgx545's
  `OK_BLOBS` leaves emitsn out until a kernel series carries it (the full check compares the two).
- Post runs after tim (the lead's brief), not in the design's S1.

## The mock's worlds

model (N0-OK, V0-HOLDS: 0); v0not (th's timeline running throughout: 0); nox0, nomark4, fillbad
(own 24, ends); ownstop and ownhang (own 4); owngatebad (16); ownarmbad (26); probefail (tim 4);
postbad (post 24, driver 0). The scorers are tested on attempts (tests/attempt.py: r37 A's kept
registers, E1149; E1133's kept t1d timelines for V0-NOT, a fabricated constant for V0-HOLDS).

## Replay vectors

No vectors table: own is an owntask row (no table kind) and th a timeline (closing_tables.py has
no timeline kind): both refused as tables. The fold changes sgx-sim (the EDM tick under our task,
`tim` written by a PDS program as the host's 0x0acc) only from what the frozen rows decide.

## Layout and commands

gen/make.py (+ gen/pins.py, gen/constants.txt), owntask/emitsn.blob, bins/, score/score.py,
run/hooks.sh, mock/world.py, tests/, PREFLIGHT.md.

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python`, which the offline tests use unless
  `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` (done by the builder).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`. After the run (or
  a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py tim out/ATT/tim`,
  `python3 score/score.py post out/ATT/post`. The driver keeps its own logs; tee nothing into this
  directory's top.
