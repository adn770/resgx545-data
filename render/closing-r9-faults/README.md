# r9-faults (round 9: the sitting's two fault stages, Q108's S9-k2 and Q076's bif)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 f32dfac and resgx545-data 2d666bfa. Plans:
`closing9/seeds/exp-seeds-r9.md` section 2 (S9-k2) and `closing9/rank/rank-round9.md` R9c-G (bif);
decisions `closing9/DECISIONS-R9.md`: S-6 (a) and X-4 (a), the two fault stages last in the
sitting. Built offline; nothing here touched the laptop, cachix or a git repository. Records
E964 (xf2), E965 (tri2) and E980 (bif) are reserved for its fold (the builder folds it).

## What runs, in order: 33 jobs, about 20 minutes

Laptop: the round 8 module, srcversion B60AB0B475DD1E8972419B5 (fork r8-kernel 2a650d74), debugfs
`vm_pte_flags`, `vm_pte_addr`, `alias_skip` (fork commit 42) and `render_pb_pages` at their
defaults (0, 0, 0, 0x422). Tool t4 only, `~/sgxfive-test-rgn4` (sha256 e6951558..., built from
resgx545 4623753, `userspace/libsgxfive/tools/sgxfive-test.c` sha256 703cbcea..., TOOLSRC.sha256;
recipe `userspace/libsgxfive/Makefile`; session.toml binds the source, so the kit replays every
row on the library mock). Files under `~/scratch/r9f/`.

| # | stage | jobs | what | controls |
|---|---|---|---|---|
| 1 | xf2 | 12 | E946's 9 rows token for token, then WO on a fill writing only page 2 (`--y 16`), WO on a 64 x 64 fill, EDMPROT on the copy's read-only source (PTE 0x14) | fill, copy, the address alone, isolation's READONLY fault, fill again |
| 2 | tri2 | 7 | WO\|EDMPROT (0x12) on the colour target; EDMPROT and WO on the ZLS store's buffer; EDMPROT on the depth buffer (a reading) | the triangle, the triangle with depth and store, the triangle again |
| 3 | bif | 14 | alias_skip masks on `tri -n 2 --keep-going --wait-ms 6000` (E457's form, E745's wait): the pairs and the three of 12 to 14, the 0x32 heap without TA3DCtl (0x7dc0), every buffer but 0 and 9 (0x7dfe) twice, with three renders, and with both renders overflowing at render_pb_pages 0x23 | no mask (first, last), TA3DCtl left out (E457's fault), buffer 0 left out (E745's fault), the overflowing scene without a mask (E761) |

**Order.** The plans' own: Q108 first (decision S-6's stage, the more informative one: it decides
WO's fault page, EDMPROTECT on reads and on the ZLS, and the two flags together, and reruns E946's
held transfer row), then bif, whose masks leave out the EDM's own buffers (buffer 0's fault is in
the EDM's code heap): the riskier rows last. Inside bif the controls that must fault come first
(c9) and last (c1, E745's order).

**Health.** Every row that is not a knob-free control has `after` (the kit's strict health fill
and triangle after it; a fault or hang takes the reset and strict health anyway); the controls
that fault (xf-c-ro, bif-c9, bif-c1) take it as faults. Time: about 6 s a job with its reset and
health, the stage health, staging and copy back: about 20 minutes.

### Addresses (Q108)

The tool allocates per VM from each heap's base (tests/test_twin.py reads them back from the
tool's source on the library mock): a fill's destination at 0x3e001000 (64 x 32 and 64 x 16 at y
16: 3 pages with the guard; 64 x 64: 5), a copy's read-only source at 0x3e001000 (3 pages), the 64
x 64 colour target at 0x3e001000 (5 pages); `tri --depth --depth-store`: the depth buffer at
0x3e001000 and the store's buffer at 0x3e015000 (20 pages each), the colour target at 0x3e029000.
The ZLS pokes are rd:11 = 0x0017100c (bit 1, the load, clear: doc/specs/3d.md section 11.5, E467),
rd:12 = 0x1000 (the load base, the depth buffer), rd:13 = 0x15000 (the store). So EDMPROT on the
depth buffer (tri-edm-dld) is a reading: no requestor is known to touch it [infer], the plan's
[check]. The page of the last pixel written: 0x3e002000 (64 x 32 and 64 x 16 at y 16), 0x3e004000
(64 x 64); the mapping's last page 0x3e003000 or 0x3e005000.

### The buffers (Q076)

E573's debugfs layout (pinned): ids 0 to 14 at 0x30000000 (0, 13 pages), 0x3000d000 to 0x30011000
(1 to 5), 0x32000000 (6, 2 pages), 0x32002000 to 0x32006000 (7 to 11; 9 is TA3DCtl at 0x32004000),
0x32007000 (12, 7 pages), 0x3200e000 (13), 0x3200f000 (14); bit 15 names none. That B60AB0B4
lays them out the same is [infer]: the fold reads the layout again if a fault lands elsewhere.

## Hypotheses, controls, verdicts (frozen in predictions/, scored by score/score.py)

Q108 outcomes: `exact` (job ok, diff 0, the row's reference hash), `diff`, `fault` and
`fault@PAGE` (a kernel `BIF fault S at A` line with A's page inside the flagged mapping, the first
such); readings matching no hypothesis: `fault-elsewhere`, `hang`; not a reading: `rejected`, a
job with no job line, a row without its PTE line with the frozen flags. The reference hash of an
exact row is its stage's knob-free control's (fill, copy, triangle), the library mock's fill hash
for the two new fill sizes (equal to the laptop's for the default fill), and tri-c-depth's own
read hash for the depth rows.

- **WO's fault page** (xf-wo-fill-low, xf-wo-fill-64 held out; xf-wo-fill the fit, E946 post hoc):
  frozen H-LASTROW (the page of the last pixel written) against H-MAPEND (the mapping's last page)
  and H-FIRST (its first page).
- **EDMPROTECT on a transfer read** (xf-edm-copy; xf-edm-fill a repeat): frozen H-EDM-WRITE
  (client writes fault, reads do not: the copy is exact) against H-EDM-REQ (the copy faults).
- **EDMPROTECT on the ZLS** (tri-edm-dst held out, tri-edm-dld a reading): frozen H-EDM-WRITE (the
  store faults, the untouched depth buffer is exact) against H-EDM-3D (only the colour write
  faults: both exact).
- **Flags together** (tri-woedm-fb, 0x12): frozen H-OR (fault) against H-CANCEL (exact); which
  flag's fault: H-EDM-FIRST (the target's first page, E945's EDMPROT) against H-WO-FIRST (the last
  pixel's page, E945's WO), neither favoured.
- **WO on the ZLS write** (tri-wo-dst) and E946's rows: r8-k2's frozen groups unchanged (H-WO,
  H-WO-NONE, H-WO-ALL; H-CC-NEW, H-CC-STALE; H-EDM-NONE, H-EDM-CLIENT). S9-k2 favours H-WO-ALL
  (E945, E946).
- **Q076**: frozen H-ONLY09 (E457, E573, E745, E761's HI: only buffers 0 and 9 are needed, every
  held-out mask draws exactly as the mask-free control, hashes and all) against H-SET (HJ: the
  mask faults in a buffer it leaves out, `needed`). bif-most and bif-most-r2 are replicates
  (scorekit.combine: mixed is never held).
- **Controls**: r8-k2's (r7-rp's health fill and triangle, copy-addresses, render/client-jobs's
  isolation); tri-c-depth (job ok, fb 0x3e029000, 4096 stored dwords changed: E465's window, 8
  tiles of 512 at G = 1); bif-c0 and bif-c0-end (E745's two-render hashes 0x99385a04ee01c585 and
  0xab267bd98022a81d), bif-c9 (E457: 0x90400 at page 0x32004000), bif-c1 (E745: 0x91000 at page
  0x3000b000), bif-c-ovf (E761: `0 of 2 renders ok, 2 overflowed`, 0xc9e301d225fe2325 and
  0xed1bce7108aded25). xf2's controls gate every xf2 row; tri-c and tri-c-end gate tri2, and
  tri-c-depth the depth rows; bif's gate every bif row, bif-c-ovf only the overflowing one. A
  summary of a hypothesis new in S9-k2 counts held-out rows only (E946's rows are post hoc).

**Predicted outcomes and planned faults.** Under the frozen hypotheses: xf2 5 faults (xf-wo-fill,
xf-edm-fill, xf-wo-copy, xf-wo-fill-low, xf-wo-fill-64) plus the isolation control's; tri2 3
(tri-woedm-fb, tri-edm-dst, tri-wo-dst); bif 0 held-out faults plus the two control faults (c9,
c1). Planned faults: 10 (8 Q108 rows + 2 bif controls) and the isolation control's own three;
up to 7 more if the rivals hold (xf-cc-copy, xf-edm-copy, tri-edm-dld) or H-SET holds (9).

**Stops.**
- `#limit` = the stage's expectfault rows that are not controls, plus one (S-6 (a)): xf2 8, tri2
  5, bif 10. A control's own expected fault is not counted (the kit since f32dfac, its test
  `test_a_control_that_expects_its_fault_does_not_count_against_the_limit`; E946's slip). So the
  count never stops a stage inside the plan's rows: every end control runs.
- An undeclared fault or hang (a row without `expectfault`: every knob-free control and the
  mask-free bif controls) stops the session (4).
- Strict health after every fault and every knob row: a health fill or triangle that does not
  draw at its first try stops the session (16), or aborts it (5) when the retry fails too.
- Two `SGX recovery failed: -110` lines in the kernel log since the stage began stop the stage at
  the next row that reads ok (hook_check, 24); a -110 whose health fails stops it before (16).
  This is the plan's "two -110 in a row" as far as the kit can read it: no hook runs after a
  fault row (kit gap, fold/FOLD-NOTES.md).
- hook_check stops the stage (24) when a fill, copy or triangle reads ok without `job: ok` (or an
  overflowed-kept job line for bif's --keep-overflow rows), or when a knob row with flags has no
  kernel PTE line for its address. A control without its reading stops at its stage (25).

## The mock's worlds (mock/world.py, kit/session.py mock)

The fake tool runs every argv through the real tool's source on libsgxfive's in-process mock
(`debug/libmock`, built by tests/run_all.sh; tri --depth writes its pokes to a scratch file);
the knobs are read from the fake debugfs. Worlds: model (S9-k2's frozen hypotheses and H-ONLY09:
0), rival (every rival: 0), allfault (every PTE flag faults: no count stop, every end control
runs: 0), nopte (xf2 and tri2 stop at their first knob row: 24), rejected (the kit's runner takes a
`job: rejected` under expectdiff as a failure: 4), undeclared (bif-c0
faults: 4), hangctl (tri-c-depth hangs: 4), hang (bif-most hangs: a reading, 0), noalias
(alias_skip without effect: bif-c9 has no fault reading, 25), two110 (two faults with -110 in a
row, health drawing: bif stops at the next row, 24), wedge (a -110, the first health fails: 16),
wedge2 (the retry fails too: 5).

## Replay vectors

- xf2, tri2: `vectors/closing/r9-faults/pte-flags.table.json` (`sgx545-tables`, kind `pte` of
  `tools/usse-asm/closing_tables.py`, pinned with `closing_vectors.py`); replay:
  `crates/sgx-pipe/src/bif.rs` `pte_access` (pinned). It models WO and EDMPROT on a pixel write
  and a stream read today; the fold adds the readings that hold (WO's page, EDMPROT on a transfer
  read and on the ZLS store, 0x12) test first, and the rows of a flag that stays open are
  `refused`.
- bif: `refused`: closing_tables.py has no alias kind and bif.rs keeps Q076 in OPEN (no model of
  the client directory's alias); the fold reports the table as not built.

## Layout

- gen/make.py writes `tables/` and `predictions/` from one spec (rows, mappings, buffers,
  hypotheses, the control values and their sources); tests/test_twin.py checks it is current.
- score/score.py, run/hooks.sh (readings job, hash, hash2, src, fb, renders, dstore, ro, rostat,
  fstat, fpage; the job-ok, PTE and -110 checks), mock/world.py, `tests/` (test_twin.py,
  test_score.py, kept.py), PREFLIGHT.md, fold/FOLD-NOTES.md, TOOLSRC.sha256.

Publishable: everything (our own tables, scorer and mock; no firmware-derived file). **Nothing is
marked for data-private.** `debug/` is scratch (the library mock's build, the mock's runs).

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the library mock, the guard, the session's tests, the mock of
  every world, the verify once frozen).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/run-r9f.log`): a new file here fails the
  verify (stop codes: kit/session.py).
- Score again on a kept attempt: `python3 score/score.py STAGE out/ATT/STAGE`.

## Deviations from the plans (the lead may object before staging)

1. **bif's rows are not the ranking's list.** R9c-G names buffers 0 to 5 and 12 to 15 one at a
   time, 6/7/8/10/11 together and that set overflowing; E573 ran every one of those singles (2
   of 2 each), E573 and E745 the five together, E761 the five overflowing, so the rows would only
   repeat landed results and close no clause. Kept: the form, ~14 jobs, the controls (no mask,
   TA3DCtl), the overflow scene, up to 12 declared faults; the held-out rows are the masks no
   record ran (Q076's open "pairs among 12 to 15", the 0x32 heap without TA3DCtl, every buffer but
   0 and 9 over two and three renders and overflowing). Buffer 0 is a control (E745's), last.
2. **xf2's `#limit` is 8, not the plan's 6**: the rule "expectfault held-out rows + 1" counts 7
   such rows (the plan's 5 left out xf-cc-copy and xf-edm-copy), and a 6th fault with rows left
   would repeat E946's slip.
3. **tri-c-depth runs second, not sixth**: a control before the rows it gates, a new form (64 x
   64 depth and store) checked knob-free before any knob row uses it.
4. **The -110 rule** is the kit's strict health (stricter) plus a stop at two -110 lines since
   the stage began, read at the next row that reads ok (above).
