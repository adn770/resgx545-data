# r37-n3b-a

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 r37-n3b 7925c9871260 (kit/ is
that commit's blobs) and resgx545-data fb461acfffa8, laptop prefix `r37a`, HostKeyAlias `cedar`.
Design: `closing29/n3b/design.md` (N3b, **step A**: §1.1 blob `emitsb`, §1.2 `ticks`, §1.4 the
step A table, §1.5 controls). **Flagged** (user present, reset ready): stage own runs our own
firmware task, a planned firmware break if wrong. Built offline, frozen, not staged, not run.

**Module.** Both N3b sessions run on the r37-kernel module (fork r37-kernel 4f35fc20ffa9: own_arm
takes `pds=v1|crumb`), one boot. This session's arm has no `pds=` word, so that module arms the
**v1 image** (`douta, douta, doutu, halt`), the one E1148 ran on C01FB320: step A is E1148's
program with `emitsb`'s two breadcrumbs. `srcversion` in session.toml is the placeholder
`UNBUILT-r37-kernel-4f35fc20ffa9` (the preflight refuses it): **the lead writes the built module's
srcversion there after the boot and freezes again** (delete FROZEN.*, PREDICTIONS.sha256, then
`python3 kit/session.py freeze .`; the tables and predictions do not change).

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, r36-n3's binding): the
  health tool (the kit's health pair and the own-task gate) and stage post's two rows.
- The own task: `owntask/emitsb.blob`, written by `tools/fwtask/fwtask.py OUTDIR
  asm/fwtask/emitsb.s` at 7925c98, sha256 83c25ac3cfc0... = `asm/fwtask/fwtask.map`'s `emitsb` at
  7925c98 (the freeze pins the map). Our own code. The kernel verifier accepts it: the fork's KUnit
  on the Mac shim at c78059370315 with emitsb in its blobs list (25 of 25 at r37-kernel, 23 of 23
  at c78059: `closing29/n3b/logs/shim-*.log`).

## Stage own: 1 job, under a minute (alarm 600 s), flagged, on_stop "end"

The kit arms `emitsb` once (`slots=0x1 entry=0`), runs c1-a (one tester command 1, run id 1, the
host's fill 0xdeadc0de in slots 2-5 = dwords 72-87 first, `"ticks": true`, timeout 200 ms), keeps
the results page, snap0/snap9 and the record, and (after an ok end) the gate, then disarms.

emitsb: entry 0 stores M1 0x5a5a3301 and the run id in slot 1, cmd = 0, fence, the one `emitpds`,
then **X0** 0x5a5a3303 in slot 1 dword 2 (page dword 70), fence, the closed task. Entry 1 first
stores **S1** 0x5a5a3304 in slot 5 dword 0 (page dword 84), fence, then pa0-pa3 (slot 2), sa0-sa3
(slot 3), M4 0x5a5a3302 and the run id (slot 4), echo, state 2.

## Outcomes (predictions/own.tsv, frozen; score/score.py)

| outcome | X0 (dw 70) | S1 (dw 84) | M4 (dw 80), state | Δtick |
|---|---|---|---|---|
| A-ISSUER: the emit stops or ends the issuing task | fill | fill | fill, 0 | 0-2 |
| A-PAST: issuer on; no entry-1 store: (1), (2), early (3) | 0x5a5a3303 | fill | fill, 0 | any |
| A-E1: (3) entry 1 stopped after its first store | 0x5a5a3303 | 0x5a5a3304 | fill, 0 | any |
| A-DONE: E1148 not reproduced | 0x5a5a3303 | 0x5a5a3304 | M4 + run id, 2 | >= 25 |

Expected from the design's §0 [infer]: A-PAST with Δtick 0-2. Δtick is the record's `ticks`:
HostCtl dword 12 from right before the command write to 30 ms after the window, which ends at done
or at 200 ms. The page is `c1-a.own_res.json` (else the stop dump). Controls (every row; all can
fail): PG page dword 0 = 0x4e574f53; E0 slot 1 = M1 and the run id, cmd 0; T0 snap0's 0x0acc
running (bit 24 set, 23:0 <= 400000); B BIF_FAULT 0 in snap9 (else the FAULT outcome, its own).

Rule: every control passed and exactly one outcome holds: `N3b-A RULE: <outcome>`; B failed:
`FAULT`; else `CANNOT TELL`. Printed, not scored: the X0 qualifier, Δtick against the window,
USE0_SERV_EVENT bit 16 and count minus HostCtl dword 12 in snap0, snap9 and the stop dump (E1148's
signature, design §0, §2), and after A-DONE only the landing of the one row (pa0/pa2 against
snap0's TA3DCtl dwords 0 and 2: exploratory, not N3's rule).

## Stage post: 2 jobs, under 1 minute (alarm 600 s), flagged

After own's disarm (fwtask_run.py's reset): p1-tri and p2-fill on t30, the health pair's bare argv,
controls `reads:diff` frozen at 0. Runs only after an ok end of own (A-DONE): every other outcome is
a runner stop (rc 4), which ends the session.

## Stops

`#limit 0` in both stages: any fault or hang (rc 4), a runner stop (no done: rc 4, every outcome
but A-DONE; the stop dump is kept), a failed gate (16), arm (26) or disarm (13) ends the session.
run/hooks.sh (r36-n3's page checks plus X0 and S1) stops own (rc 24; on_stop "end") after an ok
end whose cmd, state, echo, slot 1 (M1, run id, X0), S1, slot 4 (M4, run id) or sa0-sa3 (TA3DCtl
dwords 0-3) is wrong. Never retried, never rebooted.

## Deviations from the design (builder)

- A-DONE's Δtick is frozen `>= 25`, not the design's `>= 150`: fwtask_run.py's window ends at done,
  so a job that ends ok reads about 30 ticks (the 30 ms after the window) plus its run time.
- No "one row by design" hook stop after an ok end: with on_stop "end" it would end the session
  before own's disarm and post in the only outcome where post runs; the table has one row, which
  tests/test_twin.py holds.

## The mock's worlds

model (A-DONE: every store): 0; nox0, nos1, nomark4, sabad (a store missing or wrong after a done
job: own 24, ends); ownstop and ownhang (no done: own 4); owngatebad (16); ownarmbad (26); postbad
(post 24, driver 0). The fake runner stores nothing for a job that is not done, so the stop
outcomes are tests/test_score.py's, on attempts built by tests/attempt.py from E1148's kept
register snapshots (pinned).

## Layout and commands

gen/make.py (+ gen/pins.py, gen/constants.txt; STEP = "A"), owntask/emitsb.blob, score/score.py
(STEP = "A"), run/hooks.sh, mock/world.py, tests/, PREFLIGHT.md. r37-n3b-b is the same tree with
STEP = "B" and `pds=crumb`.

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python`, which the offline tests use unless
  `PY` names another.
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Freeze: `python3 kit/session.py freeze .` (done by the builder; again after srcversion is set).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`. After the run (or
  a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post out/ATT/post`.
  The driver keeps its own logs; tee nothing into this directory's top.
