# r37-n3b-b

A closing session built with the session kit (resgx545 HACKING.md, "Session kit", the owntask job
kind), scaffolded by `tools/closing/new_session.py` from resgx545 r37-n3b 7925c9871260 (kit/ is
that commit's blobs) and resgx545-data fb461acfffa8, laptop prefix `r37b`, HostKeyAlias `cedar`.
Design: `closing29/n3b/design.md` (N3b, **step B**: §1.3 the crumb image, §1.4 the step B table,
§1.5 controls, §2 what the tick cannot say). **Flagged** (user present, reset ready; the user
approved the step B image, which writes `tim` three times with stopped values: a planned stop of
the EDM tick until the next reset). Built offline, frozen, not staged, not run.

**Module.** The r37-kernel module (fork r37-kernel 4f35fc20ffa9), the same boot as r37-n3b-a. The
arm `slots=0x1 entry=0 pds=crumb` builds the crumb image: v1's data rows, control word and fills,
the same `douta, douta, doutu`, plus T1 `movs tim` <- 0 first, T2 <- 0x200 after both `douta`, T3
<- 0x005a3305 (data dword 7) after the `doutu`. `srcversion` in session.toml is the placeholder
`UNBUILT-r37-kernel-4f35fc20ffa9` (the preflight refuses it): **the lead writes the built module's
srcversion there after the boot and freezes again** (delete FROZEN.*, PREDICTIONS.sha256, then
`python3 kit/session.py freeze .`; the tables and predictions do not change).

## Tools (none is built)

- t30 = `~/sgxfive-test-t30` (sha256 b5ea288d..., source resgx545 42c4de7, r36-n3's binding).
- The own task: `owntask/emitsb.blob` (sha256 83c25ac3cfc0..., the map's `emitsb` at 7925c98), as
  r37-n3b-a: X0 0x5a5a3303 at page dword 70 right after the emit, S1 0x5a5a3304 at dword 84 as
  entry 1's first work, then emitsa's stores (pa, sa, M4 0x5a5a3302 at dword 80, state 2).

## Stage own: 1 job, under a minute (alarm 600 s), flagged, on_stop "end"

c1-a: one tester command 1, run id 1, the fill 0xdeadc0de in slots 2-5 (dwords 72-87) first,
`"ticks": true`, timeout 200 ms; then the page, snap0/snap9, the record, the gate after an ok end,
the disarm (its reset restarts `tim`).

## Outcomes (predictions/own.tsv, frozen; score/score.py)

T is 0x0acc in snap9 and in the stop dump (about 0.3 s apart; one read after an ok end):
`running` = bit 24 set, bits 23:0 <= 400000 and two reads differ; a constant = every read equal.

| cause | T | S1 (dw 84) | M4 (dw 80), state |
|---|---|---|---|
| B-1: (1) the program never ran | running | fill | fill, 0 |
| B-1p: (1') started, stopped at a `douta` | 0x00000000 | fill | fill, 0 |
| B-2a: (2a) stopped at the `doutu` (never issued) | 0x00000200 | fill | fill, 0 |
| B-2b: (2b) `doutu` issued, our code never stored | 0x005a3305 | fill | fill, 0 |
| B-3: (3) entry 1 started, stopped after its first store | 0x005a3305 | 0x5a5a3304 | fill, 0 |
| B-NONE: all ran | 0x005a3305 | 0x5a5a3304 | M4 + run id, 2 |

X0 (dword 70) is printed in every row as a qualifier (0x5a5a3303: the issuer went on). Cannot tell
(pre-declared): snap0's T not running (control T0), T any other value, two unequal reads while not
running (no outcome holds). S1 set with T 0 or 0x200 is printed as its own reading (`S1-EARLY`).
Residual, not separable by any store: entry 1 dying within its first three instructions reads as
B-2b. Controls as step A: PG, E0, T0, B (BIF_FAULT 0 in snap9; else FAULT, its own outcome).

T1 stops the tick by design: whenever T1 ran, the tick readings say nothing about what stopped it;
only B-1 (T running) reads as step A. The scorer prints that line, Δtick and E1148's signature
(USE0_SERV_EVENT bit 16, count minus HostCtl dword 12), and after B-NONE only the one row's landing
(exploratory, not N3's rule).

## Stage post: 2 jobs, flagged

As r37-n3b-a: after own's disarm, p1-tri and p2-fill on t30, `reads:diff` frozen at 0. Runs only
after an ok end of own (B-NONE).

## Stops

As r37-n3b-a. In B-NONE the row ends ok, so the kit runs the owntask gate with the timer stopped
(design §3, a known side effect): its outcome is not scored; a failing gate is rc 16, reset and
health, session end, data kept.

## Deviations from the design (builder)

- No "one row by design" hook stop after an ok end: with on_stop "end" it would end the session
  before own's disarm and post in the only outcome where post runs; the table has one row, which
  tests/test_twin.py holds.

## The mock's worlds and commands

As r37-n3b-a (mock/world.py, tests/, gen/ and score/ are the same files with STEP = "B"; the arm
differs). Offline: `bash tests/run_all.sh`. Laptop: `python3 kit/session.py stage .`, then
`python3 kit/session.py run .`; after the run (or a stop): `python3 score/score.py own
out/ATT/own`, `python3 score/score.py post out/ATT/post`.
