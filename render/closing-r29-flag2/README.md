# r29-flag2 (round 29: r29-flag's h1 and h2, not run there)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 c0571816c4ff (kit/ is that commit's blobs, the same
kit as r29-flag) and resgx545-data 73e058d51b5e. r29-flag (attempt 20261116-055520) ran s0 and
f1 and stopped in f2 on strict health (rc 5, "the health fill or triangle failed after f2-y512
(strict): recovery, then stop"), so its h1 (Q010) and h2 (Q163) never ran. This session runs them
exactly as frozen there (the rows, the hypotheses, the predictions and the `#limit`s byte for
byte: tests/test_twin.py compares them with ../r29-flag), after a short safe s0. **FLAGGED**: 4
planned recovered hangs (h1 2, h2 2; `#limit`s 2 and 3, 5 in all), already approved by the user
(DECISIONS-R29); no fault planned, no kernel change, no boot, no clock-gate write, no held reset.
Built offline. Records: E1112 (h1 + q010-p2) and E1113 (h2), as in r29-flag. Laptop prefix
`r29g`. Module E0CC40275493F8AEAD8180B; travel cable (`host_key_alias = "cedar"`).

## Tools (none is built)

- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), source resgx545 a581c06 (sha256 23e1fa76...),
  recipe `data:render/closing-r10-st1/lead/build_tool10.sh`: the hangs, h2, the health pair.
- t22 = `~/sgxfive-test-t22` (sha256 9b62d315...), source resgx545 3c68e8d (sha256 396252bd...),
  recipe `data:render/closing-r23-pk/lead/build_tool22_laptop.sh` (`lead/`): every copy.

## What runs: 20 jobs, about 10 minutes (13 at most)

| # | stage | jobs | `#limit` | planned | tool | what | gate |
|---|---|---|---|---|---|---|---|
| 1 | s0 | 4 | 0 | 0 | t22 | c10-zc, c10-zn, c10-bc, c10-bn (r29-flag's) | none |
| 2 | h1 | 6 | 2 | 2 hangs | t22, t10 | Q010: the colour-space set across recovered hangs | the four copies |
| 3 | h2 | 10 | 3 | 2 hangs | t22, t10 | q010-p2, then Q163's three triples | its own h2-c-b |

Hypotheses (r29-flag README.md): h1 H-KEEP (a copy without the load reads 0xb6067a95fa98de2d after
a recovered hang) against H-RECOV-CLR (0xd3522437a14b6325); h2 H-PREV16 (block-2 v = 1 completes
iff the job before completed with a block at v 1 or 6: h2-a3 ok, h2-b3 hang, h2-c3 hang) against
D-PREVADD, D-C (all ok) and H-ALWAYS (all hang). Time: 13 jobs without an event at about 12 s, 4
hangs at about 50 s with the reset and strict health, staging and three preflights: about 10
minutes; with h2-a3's allowed hang and a health retry about 13.

## Q010's rule here

No fault precedes q010-af in this session, so its frozen premise (a fault in f1 or f2) does not
hold: it reads "cannot tell", and R29-3 (a) as frozen (three copies on one hypothesis) reads
"narrow only" whatever happens. `python3 score/score.py q010 out/ATT` prints that verdict and,
below it, the same rule over q010-p1 and q010-p2 alone (after the two hangs): whether that suffices
to retire Q010 is the lead's and the user's decision, not this session's. The fault clause stays
unmeasured (r29-flag's faults ran, but no copy followed them).

## Stops

As r29-flag's: any fault or hang in s0 (4), a control without its reading (25), a differing
reading closes h1's gate; an unplanned hang or fault (h2-c-b included) 4; strict health 16 / 5;
hook_fault 24 (a failed recovery, an end other than a hang, a hang without its hung line), every
flagged stage `on_stop = "end"`; a `#limit` reached with rows left 24. Never retried or rebooted.

## The mock's worlds

model, alt, always (0 everywhere), s0diff (h1 skipped, 0), s0fault (4), s0noread (s0 24, ends),
recovline (h1, h2 gates closed, 0), recovfail (24), h1fault (24), h2ctlhang (4), wedge (16). The
library-mock replay runs all 20 rows on t10's and t22's pinned sources.

## Replay vectors

`refused` for both stages, as in r29-flag (hangs; the colour-space set across a recovery and the
VDM counter are not in sgx-sim); the fold may tabulate the copies' hashes in run order.

## Layout and commands

gen/make.py (r29-flag's, its stages cut to s0, h1, h2), fit/o29_2.py and fit/o29_2.out (r29-flag's
O29-2, unchanged), score/score.py, run/hooks.sh, mock/world.py, tests/, lead/, PREFLIGHT.md,
FOLD-NOTES.md. Publishable: everything; nothing for data-private. Offline `bash tests/run_all.sh`;
freeze `python3 kit/session.py freeze .`; laptop `python3 kit/session.py stage .` then `python3
kit/session.py run .`, its log outside this directory.

## Deviations

1. s0 keeps only h1's four copy references (h2 has its own control); r29-flag's other s0 rows
   gated f1 and f2, which do not run here.
2. q010-af follows no fault here (see "Q010's rule here").
3. s0 has `on_stop = "end"`: a stop in s0 (hook_check) ends the session, so h2 never runs after
   a failed reference set (r29-flag's s0 kept the default).
