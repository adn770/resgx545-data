# r30-evst2 fold notes

Attempt 20261116-132348 (fold/lead-run.log, fold/lead-stage.log): rc 0, 41 jobs, every job exact,
no fault, no hang, no stop; every control PASS (e1, e5, e2, e3 first and last, e4 first). The
scores reproduce byte for byte (fold/reproduce.out against the run's score-STAGE.txt).

**Record numbers.** The frozen README and FOLD-NOTES.md reserve E1117 and E1118; r30-pde
reserved E1117-E1119 first, so this session folds as **E1120** (the frozen E1117: e2-e4) and
**E1121** (the frozen E1118: e1, e5) (closing29/DECISIONS-R29.md, the lead).

## Frozen verdicts (all rows held out)

- **H-IDLE** held in every stage (e1 8, e5 5, e2 10, e3 8, e4 2 rows; e4's tick rate 0.998 a ms).
- **H-SE-EVENTS** held, **H-SE-TICKS** refuted: e2 10 of 10, e3 8 of 8, e4 1 of 1 (9 to 11 counts
  beyond the ticks a triangle).
- **H-CC-FLAT** refuted (19 of 19). **H-CC-KICK** has three clauses a row (the word after the
  change, held to the end, the change's lead to bit 26), so a stage prints them as rows: e3 "17
  of 24 rows decided" (8 rows x 3: 16 word and hold clauses, 1 lead read, 7 leads cannot tell: no
  render end seen or no bit 26), e4 "3 of 3". e2 prints "not supported: 24 held, 1 FAILED, 5
  cannot tell of 30" (10 rows x 3, not "of 3"): word 10 of 10, hold 10 of 10, lead 4 held, 1
  FAILED, 5 cannot tell. The FAILED clause is e2-04's lead, 106.6 us against the frozen 15 to
  60: in that job bit 13 (TA_FINISHED) came 62.4 us after the change and bit 26 only after it,
  19.5 us before the render end (bit 0 at 126.1 us); every other read lead is 19.6 to 48.3 us.
  So H-CC-KICK's word and hold clauses hold in 19 of 19 rows, and its timing clause is refuted
  as frozen (5 of 6 read leads in the window): the change does not come a fixed time before bit
  26.
- **H-NARROW4** held (e2 6 of 6 rows with bit 26, 5.0 to 7.2 us; e4 5.0). **H-NARROW27** held 2
  of 2 decided (11.9, 15.7 us; 6 rows without bit 26). **H-WIDE1** not supported in e1: 3 held
  (63.3, 80.3, 76.7 us), 1 FAILED (e1-03, 4.2 us, with no render end seen in its window).
- **H-DENSITY** held, **H-INDEP** refuted, on the edge: e1 4 of 8 against e3 2 of 8, 0.25 against
  the 0.2 bound (the scorer prints 0.2); one row either way would move it.
- **H-ALONE** refuted once: e2-03's bit 26 rose three times, and its second episode overlapped
  SW_EVENT and MASTER_INTERRUPT for one sample (0xa4004000 at 95.5 us after the change, between
  0xa0004000 samples). Every other sample with bit 26 (e1, e3, e4, e5, the rest of e2) read
  0x24000000. The word while bit 26 is set is the idle word with bit 26 and whatever other
  event bits are pending, not 0x24000000 alone.
- e1 **H-PART** held (4 of 8), H-EVERY refuted; H-BEFORE held where decided (3 rows), H-SUB 8 of
  8, H-SW where decided.
- e5: **H-ONCE** refuted (multi 4: four of five rows show bit 26 twice or more), **H-EACH**
  refuted (each 1: only e5-04 shows it three times, once a render). Post hoc (fold/posthoc.txt):
  in four rows the first render's bit 26 is 53.5 to 76.5 us wide and the later ones 4.1 to 5.9
  us, 19.5 to 107.7 us before a later render's end; e5-02 shows it only before its second render
  and 18.9 ms after its third.

## Post hoc (not frozen)

fold/posthoc.txt: CR_EVENT_STATUS's words per row from CR_CACHE_CTRL's change. The change comes
first in every row; bit 26, when seen, follows in 19.5 to 48.3 us (and 106.6 in e2-04), then
bit 13, SW_EVENT with MASTER_INTERRUPT, and the render end (bits 18, 0) at 126 to 142 us.

## What lands

- E1120 (e2, e3, e4) and E1121 (e1, e5). Q111 narrowed, not retired: which event sets each bit
  other than bit 26's place, a pulse or a level for the others and their clears stay open.
- sgx-sim hw.rs and tools/fwsim/seeds.toml: CR_CACHE_CTRL answers 0x0000ffff until a served
  event other than a tick (E1120: 24 of 24 first samples, through the lead's ticks) and is
  refused after, even over a run write, naming 0x1000ffff from the change to a reset (the change's
  time against the kick or the firmware's write is not measured). The M2 render kick now stops
  on the firmware's CR_CACHE_CTRL read after the kick, before its write: the boot's write
  answered it before, a read-back the hardware does not give after a kick. CR_USE0_SERV_EVENT
  after a kick stays refused (a range a triangle, not a rule per event); its refusal names
  E1120's 9 to 11.
