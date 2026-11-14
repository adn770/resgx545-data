# r19-flag (round 19, S4: the flagged junk rows, `fl-junk` only)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 6809cddd24ce (kit/ is that commit's blobs) and
resgx545-data 95df71e98c95. Plan `closing19/plan/rank-round19.md` section 5 (S4); decisions
`closing19/DECISIONS-R19.md` (R19-3 a: fl-junk only, not fl-thr1; the user's OK given).
**FLAGGED (outside the safe class)**: a planned fault or a recovered hang is possible. Built
offline; nothing here touched the laptop, cachix or a git repository. Record E1086 is reserved
for its fold (the builder folds it). Laptop prefix `r19f`. Module srcversion
E0CC40275493F8AEAD8180B (fork 456404fcffe5), loaded = installed. It runs after every safe session
of the round.

## Tools

- t18b = `~/sgxfive-test-t18b` (sha256 58e79855...), bound by source to resgx545 ec50498
  `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 70aa910e...), recipe
  `data:render/closing-r19-k0/lead/build_tool18b.sh` (a byte copy of closing18/k18's, in `lead/`
  with its built line; r19-k0 publishes it first). Every row runs on it.
- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), the kit's health tool only (the strict health
  fill and triangle); bound as r18-flag binds it. No tool is built for this session.

## What runs, in order: 3 jobs, about 4 minutes (7 at most), `#limit 2`

One stage, `fl` (`on_stop = "end"`, no gate: its control is its first job).

| # | row | set | risk | what |
|---|---|---|---|---|
| 1 | fl-ctl | control | safe | ld's base form, no fill: the premise and the twin of the junk rows |
| 2 | fl-junk-a | fit | planned | the same job with page 6 filled with the ramp, before render 2 |
| 3 | fl-junk-b | heldout | planned | a replicate of fl-junk-a (the held-out label) |

The form (ld's, E631 Part B on the final-PB knob): `tri` at 1024 x 768, `-n 2 --geometry 1
--final-pb-pages 0x100`, `dbg:render_pb_pages=0x28` (P = 0x28, restored after each job). Render 1
is a geometry kick that overflows once (E625: one partial render; the scene is left open) and
leaves the lists in the state page (page 6 at 1024 x 768, E627, E631). Render 2 closes the scene
on N = 0x100 pages (the module's final free list max(P, N), the threshold update: 0x0624 = N -
0x22 = 0xde), so it does not overflow and no longer stores over page 6 before any read (the blind
spot of E631's junk rows, where the next kick's own partial render rewrote the first 34 dwords).
The junk rows add `--tadata-fill-render 2:6:0xa5000000:ramp`: the ramp 0xa5000000 + i into page
6 just before render 2's kick (the kernel's `tadata_fill`, taken once by the first kick after it
is armed; a reset disarms it). `--dump-each --dump-render "$W" --words "$W" --regs 0x0600-0x0750`
keep the page after render 1 (tri.1.tadata.bin), the final TA data, the kernel's command words
and the registers after each render.

### The question and the frozen hypotheses (Q045 clause: does a load task read the lists back?)

- **H-NOLOAD**: the final render is the control's: the job ends ok and its target hash equals
  fl-ctl's (same = 1).
- **H-LOAD-FAULT**: a load task walks the junk (page numbers past the page table): a BIF fault.
- **H-LOAD-HANG**: it hangs, the kernel recovers it (`job N hung, recovering`).
- **H-LOAD-CORRUPT**: it reads the junk as lists and draws a different image (ok, same = 0).

Predicted outcome [infer]: **H-NOLOAD**. The load task is issued only when the 9-bit field of
register 0x0740 is not zero (E158), and 0x0740 read 0 in every sample of every job run (E256,
E312, and 36 more jobs in E574, 30 of them overflowing); E631's junk rows changed no render. A
fault, a hang or a different image would show that a load task reads the lists. The control's four
readings, frozen: job ok, the kick overflowed
once, 0x0624 = 0xde, page 6 holding lists before the fill (18 non-zero dwords at P 0x28 in E464;
only "any" is read). fl-ctl can fail four ways (see Stops), and "the final follows
N's threshold" is E1078's H-UPD, unmeasured until r19-k0 runs (S1 gates this session).

## Stops (the user's conditions)

- `#limit 2` counts exactly the two planned rows (`expectfault`, not controls: E946). A planned
  row's fault or hang is a reading; each is followed by the kit's reset and strict health (a first
  health draw that fails stops the session: 16, or aborts: 5 when the retry fails too).
- An unplanned fault or hang (fl-ctl has no `expectfault`), any other failure of a job: rc 4, the
  session stops. `soft` is not used.
- hook_check (24): fl-ctl without job ok, one overflow, 0x0624 = 0xde and lists in page 6 (no
  junk row runs); a junk row that completed without job ok, the overflow or the lists.
- hook_fault (24, and `on_stop = "end"` ends the session) after a planned fault or hang: any
  `SGX recovery failed` line in its kernel slice (a failed recovery), a fault before the fill was
  armed or before the kick's overflow was read, a fault without its kernel `BIF fault S at A`
  line, a hang without `job N hung, recovering`.
- Stop budget: zero unplanned events, two planned ones. Every stop other than a clean finish ends
  the session; report it to the user, never reboot or retry.

## The mock's worlds (mock/world.py, `python3 kit/session.py mock .`)

model (H-NOLOAD: 0), corrupt (H-LOAD-CORRUPT, rc 1 with a diff line: 0), faultjunk (both junk
rows fault, the limit used on the last: 0), hangjunk (0), ctlfault (the control faults: 4), ctlthr
(0x0624 = P - 0x22, H-IGN: 24), ctlnoovf (the kick does not overflow: 24), nolists (24),
recovfail (`SGX recovery failed: -110`: 24), nobif (24), earlyfault (a fault before the fill: 24),
junkfail (a failure that is neither fault nor hang: 4), wedge (the health fails once after the
first fault: 16). The library-mock replay runs the 3 rows on t18b's pinned source (the real tool
on the mock device: none refused). The mock's rules (overflow iff P < 0x40, the page contents) are
its own [infer], not measurements.

## Replay vectors

`refused` for fl: a fault or a hang is not a table, a completed junk row repeats the control's
image, and the partial-render path (a geometry kick that overflows, the state page) is unmodelled
(`crates/SIM_UNMODELLED.toml`: E627, E630, E631 are "dpm: not modelled or refused"). If a junk row
completes with a different image (H-LOAD-CORRUPT) the fold builds no table either: the junk is not
a scene the pipe can express. Nothing is pinned for a replay.

## Layout

gen/make.py writes tables/ and predictions/ (the generator reads no repository file);
score/score.py;
run/hooks.sh; mock/world.py; tests/ (test_gen.py, test_twin.py, test_hooks.py, test_score.py);
lead/ (the recipe and built line of t18b, byte copies of closing18/k18); PREFLIGHT.md;
FOLD-NOTES.md. Publishable: everything (our own programs, tables, scorer and mock; no
firmware-derived file). **Nothing is marked for data-private.** `debug/` is scratch.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the guard, the session's tests, the library mock, the mock of
  every world, the verify once frozen); `python3 gen/make.py --check`.
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/r19-flag-run.log`).
- Score a kept attempt: `python3 score/score.py fl out/ATT/fl`.

## Deviations from the plan (the lead may object before staging)

1. **Three jobs, not two**: the plan counts the two junk rows; the stage's first job is its own
   safe control (the user's "a control that can fail"), which no junk row runs without. `#limit`
   counts only the two planned rows.
2. **The dump and words directories are `$W`**: the runner only makes the parent of an
   `outdir_opts` value, and the library mock refuses a missing directory, so `--dump-render` and
   `--words` write their fixed names (tri.N.*, words.N.txt, ta3d.N.bin) into the job's `$W`.
3. **A junk row's own threshold is a reading, not a stop**: only fl-ctl must read 0xde, so a
   legitimate "ok but different" first junk row does not cost its held-out replicate.
4. **fl-thr1 is not built** (R19-3 a).
