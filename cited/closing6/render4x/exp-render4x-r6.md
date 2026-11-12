# Proposal round 6, RENDER / 4x: Q292's tail-room form, the kernel change, Q293

Planner output, 2026-11-12. Offline and read-only; nothing here touched the laptop, cachix or a
repository. Scripts and outputs beside this file (`closing6/render4x/`): `d_map.py`, `d_cmp.py`,
`d_cmp2.py`, `morton.py`, `cells.py`, `residue.py`, `sep.py` and their `.out` files. All read only
the published session `resgx545-data/render/closing-r5-render4x` (standard library, no firmware-
derived input), so they are publishable with `tools/records/scratch_cites.py --publish`.

## 0. Summary for the decision

- **Offline, the kept data decides the form [post hoc, needs a held-out run].** The tail pointers
  of a 4x job are one dword a tile of the doubled grid (16 x 8 pixel tiles) at TA-data offset
  4 x Z(x, y), Z the bit interleave with y on the even bits and x on the odd bits (Z-order).
  I call it **H-TPM**. Fitted on E869's one held dump: the 1023 stream offsets that dump lost are
  exactly the 1023 header dwords that are an in-target tile's entry (set equality, 0 extra, 0
  missing). Checked on data not used for the fit: "fault iff the entries pass the context's
  `td.rgn`" gives 26 of 26 outcomes on record, including the eight rows E868 could not fit and
  three cells exactly at the limit. The other interleave misses 3; the limits tail, OTPM and state
  miss 3 to 8.
- **The room a 4x context needs** is 4 x (Z(2tx-1, 2ty-1) + 1) bytes for its maximum, at most
  4 x (2 side)^2: Q292's planned change (side doubled, four times the bytes) is a sufficient
  bound at every size. At 4096 x 4096 the exact need is 0x80000, the bound 0x100000.
- **Rows that need no kernel change (stage A, 16 jobs, about 15 min, 6 predicted faults)**: H-TPM
  predicts outcomes no monotone rule gives, on the rgn4 kernel as booted: 1024 x 1280 on its own
  maximum completes while 1024 x 800 and 1024 x 1024 fault; 1024 x 1024 completes on a 1024 x
  1280 context; two held faults with the exact set of lost offsets frozen.
- **Kernel change (stage B, 20 jobs, about 20 min, one reboot with the user's OK)**: the room of a
  4x context from the doubled grid, plus a debugfs knob for the room so one kernel places the
  limit a page under and over the need. Exact files and KUnit tests in section 3.
- **Q293**: nothing in the kept data closes it. Four cheap rows are offered (section 5); its
  first open item is an unbounded search and I recommend rewording it.

## 1. What the kept data decides offline

### 1.1 The header pattern of E869's held dump is the Z-order image of the target

`d_cmp.py`, `d_cmp2.py`: row d's held TA data (1280 x 1024 on its own maximum, `td.rgn` 0x7000)
against m1's completed twin (same target on 1280 x 1040, `td.rgn` 0x13000; m1 and m2 have 0
headers differing, so a completed job's headers are reproducible).

| class | headers | what |
|---|---|---|
| same | 10160 | all three words equal m1's |
| A | 1023 | word 1 (stream offset) zero, word 0 x/y/macrotile intact (3 of them also lost flag 0x04 or 0x10) |
| C | 189 | word 0 zero, word 1 intact |
| B | 914 (+2) | word 0 has bit 27 set where m1 has not (2 more: flags 0x04, 0x10 off), word 1 equal |

E869 counted A + C as 1212 off the rule. B is new: the frozen rule does not read bit 27.

The A dwords fill aligned blocks of the TA data and nothing else: [0x7000, 0x8800),
[0x9000, 0x9800), [0xc000, 0xc800), [0xd000, 0xd800) (E869's "runs within 4 bytes of a 2 KiB
boundary"). Read as dword index / 4 in Z-order with y on the even bits, 0x7000 to 0x8000 is tiles
x 32-63, y 96-127 and each later 0x1000 is a 32 x 32 block with x 64-95; the target's doubled
grid is 80 x 128 tiles, so x 64-79 is the first half of each block (0x800 bytes in, 0x800 out),
and the blocks with x 96-127 (0xa000, 0xb000, 0xe000, 0xf000) are out. That is the pattern.

`morton.py` part 1, the exact statement:

- Every header of the target whose word-1 dword address equals 4 x Z(x, y) of some in-target
  tile of the doubled grid lost its stream offset, and no other did: predicted 1023, lost 1023,
  both 1023 (y even). With x on the even bits: predicted 1708, both 426.
- The 189 C dwords (word 0) all lie at entries of the header grid outside the target (x 80-95,
  the macrotile span past the target's edge): 189 of the 682 word-0 dwords at such entries.
  Word-0 dwords at in-target entries: 1025, of which 1 lost (header 0, whose x, y and macrotile
  are 0: only its flag is gone).
- The 914 headers with bit 27 are all headers whose own tile's entry lies inside the region
  headers (3072 in-target tiles have their entry there; 3072 in control/OTPM/state; 4096 in the
  room). None of the six completed dumps of the session has bit 27 anywhere (`cells.py` part 1).

[infer] The TA keeps its tail pointers Z-ordered from `CR_TE_TPC_ADDR`; at 4x the index is the
doubled grid's. The entries are zero after the TA ends (every dump, completed or held, is zero
below `td.rgn`), and the zeroing of in-target entries comes after the stream offsets are written;
word 0's x/y survives at the same addresses, so either word 0 is written again later or the
entry write keeps it [not decided by one dump]. Bit 27 marks tiles whose entry the TA read back
from header memory [infer, weak]. A zero stream offset sends the 3D to the request base (E869).

Rests on: E869 (d), E867 (m1, m2). One dump: a fit. Refuted by: a second held fault whose lost
offsets are not the frozen set (stage A rows h1, h2).

### 1.2 The onset: 26 of 26 cells, with the limit at `td.rgn`

`morton.py` part 2. Rule: a four-array 4x job faults iff 4 x (Z(2tx-1, 2ty-1) + 1), the end of
the target's entries, is greater than the `td.rgn` of the context's maximum. No number was fitted
on these outcomes (the interleave came from d's dump; the limit is the one where 1.1's losses
start).

| interleave | limit | misses of 26 |
|---|---|---|
| y even | `td.rgn` | **0** |
| y even | state / OTPM / control page | 3 / 4 / 8 |
| x even | `td.rgn` / state / OTPM / control | 3 / 5 / 8 / 8 |

The cells that killed E868's eleven rules and the 192 post hoc extents, under H-TPM:

| cell | entries end | `td.rgn` | H-TPM | measured |
|---|---|---|---|---|
| 1024 x 768 own | 0x7000 | 0x7000 | complete (at the limit) | complete (E824) |
| 1024 x 512 own | 0x4000 | 0x4000 | complete (at the limit) | complete (E868 x1) |
| 1024 x 800 own | 0x7ac0 | 0x7000 | fault | fault (x3) |
| 1184 x 768 own | 0xc760 | 0x7000 | fault | fault (x2) |
| 2048 x 240 own | 0xaff0 | 0x7000 | fault | fault (l1) |
| 256 x 1536 own | 0x11800 | 0x13000 | complete | complete (l2) |
| 768 x 2048 own | 0x17800 | 0x13000 | fault | fault (l3) |
| 1280 x 1024 on 2048 x 1024 | 0xd800 | 0x7000 | fault | fault (m3) |
| 2048 x 1536 on 4096 x 4096 | 0x1c000 | 0x43000 | complete | complete (m4) |

A wide target faults early because x 64 sets bit 13 of the index (0x8000 bytes); a tall one late
because y sits on the lower bit of each pair. Entries over the control, OTPM and state pages do
not fault a job that completes (1024 x 768 reaches 0x7000 with the room at 0x4000; 640 x 480
reaches 0x35c0 with the room at 0x1000): the limit is the headers, not the room. Whether those
overlaps disturb a job whose DPM pages are live (an overflow) is not known; E866's overflows at
640 x 480 and 512 x 384 ended cleanly with such an overlap [data, not examined further].

Tiles of the target or of the header grid give the same 26 outcomes, and `sep.py` finds no size
up to 2048 each way where the two differ on an own maximum: the outcome cannot separate them.
The dump does (1.1: only in-target entries lose word 1), so the form is the target's.

Rests on: E824, E828, E845, E846, E867, E868 (outcomes), E869 (form). Status: post hoc over 26
known outcomes with 2 x 4 variants tried, 1 fitting. Needs the held-out check (stage A).
Refuted by: stage A's a1, a8 or a9 faulting, or a4/a12/a13 faulting, or a2/a5/a14 completing.

### 1.3 What it means for the tail-room form

- Need of a 4x context for a maximum of tx x ty single-sampled tiles: N4 = 4 x (Z(2tx-1, 2ty-1)
  + 1) bytes (Z is monotone in each coordinate, so the far corner is the largest index).
- N4 <= 4 x (2 side)^2 always (both doubled spans are at most 2 side). So Q292's planned "side
  doubled, four times the bytes" is a bound, never short, and stays right if the orientation
  were wrong somewhere unmeasured. It cannot test the form: every own-maximum row completes
  under any reading that needs at most that.
- The 1x room (4 side^2) already bounds the 1x Z-order need; no 1x change. Whether 1x is
  Z-ordered the same way is [infer]: no 1x dump can show it (the entries are zero afterwards).

### 1.4 The 4096-wide residue is not explained

`residue.py`: for E828's 4096 x 4096 and E846's 4096 x 1152 H-TPM gives lost offsets from
macrotile 0 on (header 0 at 4096 x 4096), so it does not give the 1024-wide right block. Both
scenes also overflow, so the TA did not end as in 1.1. Left as it was; stage B's 4096 x 960
(961 pages, fits) is the first 4096-wide row with one effect only.

One thing the model adds: a fault does not need header 0. 1040 x 1280 and 1280 x 768 on their
own maximum lose offsets only from a later header on (header 1707, in macrotile 1, and header
341, in macrotile 0), so the 3D should draw some tiles right before it faults [infer]. I did
not check E868's l4 (1280 x 768) for right pixels. Stage A reads it (explore).

## 2. Stage A: rows that need no kernel change (rgn4 boot as it is)

Session `r6-render4x`, built from r5-render4x's generator, runner and scorer (twin and argv
mock tests, dump-name census, gate files; `closing5/r5-render4x/`). Changes: every laptop path
under `~/scratch/r6x/` (run, stage, out, work, `mktemp -d ~/scratch/tmp/r6x.XXXXXX`), a 300 MB
free-space check per job, no `/tmp`. `gen/rules.py` gains H-TPM (`morton.py`'s `z`, `lay`), kept
beside the eleven dead rules, which still print their predictions as the comparison.

Every row: `tri --tri-full --keep-going --keep-overflow --wait-ms 20000 --aa4` with E824's four
pokes, `--dump-render`, `--regs 0x0700-0x072c`, `render_rgn_arrays 0`, `render_pb_pages 0x422`
read back, a debugfs reset before each job, the fill and strict health after each fault.

| row | target | maximum | entries end / `td.rgn` | H-TPM (frozen) | K-OR, every size rule |
|---|---|---|---|---|---|
| s0 | r5's three controls | | | pass | |
| a1 | 1024 x 1280 | own | 0x13000 / 0x13000 | **complete**, 0 wrong | fault |
| a2 | 1024 x 1296 | own | 0x13ab0 / 0x13000 | fault | fault |
| a3 | 1040 x 1280 | own | 0x18560 / 0x13000 | fault | fault |
| a4 | 1024 x 768 | 2048 x 1024 | 0x7000 / 0x7000 | complete | complete |
| a5 | 1024 x 800 | 2048 x 1024 | 0x7ac0 / 0x7000 | fault | fault |
| a8 | 1024 x 1024 | 1024 x 1280 | 0x8000 / 0x13000 | **complete** | fault |
| a9 | 1024 x 800 | 1024 x 1280 | 0x7ac0 / 0x13000 | **complete** | fault |
| a12 | 992 x 1280 | own | 0x12fe0 / 0x13000 | **complete** | fault |
| a13 | 512 x 1536 | own | 0x12000 / 0x13000 | **complete** | fault (H > 768) |
| a14 | 1024 x 1536 | own | 0x14000 / 0x13000 | fault | fault |
| h1 | 1024 x 800 held | own | 0x7ac0 / 0x7000 | fault; lost offsets = the frozen 43 headers, 0x7000 to 0x7ab0, header 0 among them | |
| h2 | 1280 x 768 held | own | 0xc800 / 0x7000 | fault; lost offsets = the frozen 511 headers, 0x7ffc to 0xc7f0, header 0 intact | |

16 jobs (s0 3, a 10, h 2, plus one replicate of a1 if it completes). Scene pages 190 to 385,
all far below the 1000 the buffer gives.

- **Fit vs held out.** Fit: d's dump (form) and nothing else. Held out: all twelve rows. a1,
  a8, a9, a12, a13 are the rows where H-TPM and every dead rule disagree; a2, a5, a14 are their
  one-step neighbours (16 rows more, or the same context one size up).
- **Controls that can fail.** s0; a4 (the context of m3's fault completes a size at the limit:
  a fault there says the limit is below `td.rgn` on that context); a2/a14 (if they complete,
  the faults moved and the boot differs from r5's).
- **Held rows** (r5's stage d path: `hold_recovery` Y, `render_param` and `render_tadata` read in
  the hold, reset, N). Frozen in `predictions/h.tsv`: the list of header offsets that lose word
  1 (`cells.py` `lost()`), compared as sets with the headers the held dump shows without one.
  Verdict words: `set equal`, or the three counts both / lost only / predicted only.
  Explore, reported and not predicted: word-0 losses at grid-only entries, bit 27, flags 0x04
  and 0x10, and h2's and a3's right-pixel counts (1.4).
- **No twin needed.** A lost offset is read with r5's frozen header rule (word 0 on the rule,
  the tile inside the target, word 1 zero), as E869's scorer did; a9 is h1's completed twin on
  a larger maximum and is compared as well.
- **Stops.** A fault whose word is not 0x90100 at 0x10000011: stop the session, strict health.
  s0 or a4 failing: stop (premise). Predicted faults 6 (a2, a3, a5, a14, h1, h2); limit 8 for
  a + h, the ninth fault-class event stops the stage. a1 faulting does not stop anything: it
  is the refutation, and the remaining rows say how the rule fails.
- **Verdict.** H-TPM held if all ten a rows match and both sets are equal. Any a row off:
  refuted as stated; the verdict prints which (interleave, limit) variants still fit every cell.

Risk: 6 faults on the laptop, each of the kind r5 took 8 of with health ok after every one.
No reboot. Wall time about 15 minutes, plan 30. Build about 20 minutes (reuse).

## 3. The kernel change (linux fork, branch `resgx545`, tip a2788bd8; through the lead)

Read from `drivers/gpu/drm/gma500/sgxfive/` at a2788bd8. Today
`sgx_render_tadata_layout_in()` packs tail pointers (`l.tail_size` = 4 side^2 of the maximum),
control, OTPM, state, then `arrays` x region headers, then the ZLS headers; `sgxfive_render.c:226`
calls it with `sgx_render_rgn_arrays(setting, ctx->aa4)`. The layout does not know the context
is 4x except through the array count, and the debugfs knob can force four arrays on a 1x context.

### 3.1 What changes (two commits, tests first)

1. `sgx_render.c`, `sgx_render.h`: new
   `u32 sgx_render_tail_room(u32 max_w, u32 max_h, bool aa4, u32 setting)`:
   - `setting` a whole number of pages, non-zero: that many bytes (the debugfs override);
   - else 1x: `l.tail_size` of the maximum (as today, byte for byte);
   - else 4x: 4 x (2 side)^2, i.e. `4 * l.tail_size` (decision 2; the alternative is the exact
     N4 rounded up to a page, with `max(l.tail_size, N4)`).
   `sgx_render_tadata_layout_in()` and `sgx_render_tadata_layout()` take the room as a new
   argument and set `n.control = round_up(room, SZ_4K)`; nothing else in the packing moves.
   `SGX_RENDER_TD_MAX4_SIZE` becomes the 4x maximum's size, 0x2e3000 (0x223000 + 0xc0000),
   still under `SGX_RENDER_TD_LIMIT` 4 MiB; the comment in `sgxfive_ctx.h:69` follows.
   The RT data word `SGX_RENDER_RT_TAILSIZE` stays the target's single-sampled `l.tail_size`:
   it is what m1, m2 and m4 ran with on a larger room (E867), so the change alters one thing.
2. `sgxfive_render.c:218-227`: pass
   `sgx_render_tail_room(ctx->max_width, ctx->max_height, ctx->aa4, sgxfive_render_tail_room(sgx))`.
   `sgxfive_priv.h`, `sgxfive_debug.c`: `u32 render_tail_room`, debugfs `render_tail_room`
   (x32, 0600, default 0 = automatic), its reader beside `sgxfive_render_rgn_arrays()` with the
   same stub for the no-debugfs build. Read when a context is created, like `render_rgn_arrays`.

No uAPI change (the flag exists), no IGT change (the runner writes the knob), no firmware change.

### 3.2 Tests (KUnit in `sgx_render_test.c`, written before the code)

- `sgx_render_test_tail_room`: 1x equals `l.tail_size` for the ten sizes of
  `sgx_render_test_tadata`; 4x table: 1024 x 768 0x10000, 1280 x 1024 0x10000, 2048 x 240
  0x10000, 768 x 2048 0x40000, 2048 x 1536 0x40000, 4096 x 4096 0x100000; setting 0xb000 gives
  0xb000 for either kind; a setting that is not whole pages is ignored.
- `sgx_render_test_tail_covers` (the form as a test): a local `zorder(x, y)` with y on the even
  bits; for every maximum of a 32 x 16 lattice up to 4096 x 4096 (and the 26 recorded cells by
  name), `4 * (zorder(2tx - 1, 2ty - 1) + 1) <= room` at 4x and `4 * (zorder(tx - 1, ty - 1) +
  1) <= room` at 1x.
- `sgx_render_test_tail_records`: the 26 cells with the OLD room (setting = the maximum's
  `l.tail_size`): `entries end > t.rgn` equals the measured fault, cell by cell. This pins the
  evidence in the fork and fails if the layout drifts.
- `sgx_render_test_tadata_arrays` updated: with the 4x room 4096 x 4096 at four arrays is
  0x2e3000, fits, and is -E2BIG at 0x2e2fff; with the 1x room the old 0x223000 numbers stay
  (arrays and room are independent); `t.control == room`, the other offsets follow.
- `sgx_render_test_tadata` unchanged and passing (1x layouts byte-identical: the regression).
- The fork's own check (`tools/fork/`, checkpatch, the KUnit suite under UML or on cachix as
  the earlier commits did) and `forkpin.py` repinned in resgx545 after the commit lands.
- resgx545 side, same fold: `doc/specs` `render_uapi.md` (the 4x paragraph, line 174) and the
  layout transcriptions (`gen/rules.py`, `pbmodel.py` copies in the new session) take the room.

### 3.3 Build and boot

Lead only: commit on `resgx545` in the Mac fork, build on cachix, install to the laptop's test
slot, `boot-test-kernel.sh` (one-shot, no GRUB change), `test-session.sh`, then check the loaded
gma500 srcversion against the installed module (initramfs). **The reboot ends the rgn4 boot**,
so it needs the user's OK and stage A should run first (decision 1). If stage A cannot run
first, the knob reproduces the old layout exactly (`render_tail_room` = the maximum's 4 side^2),
so stage A's rows can run on the new kernel with one more write per row; the frozen predictions
are the same.

## 4. Stage B: rows the kernel change enables

On the new kernel. Same command form, runner and scorer as stage A.

| row | target (own maximum) | room | entries end / `td.rgn` | frozen |
|---|---|---|---|---|
| s0 | r5's three controls; a 1x full 1024 x 768 | auto | | pass; TA-data size as before at 1x |
| b1-b8 | 1280 x 1024, 1184 x 768, 1024 x 800, 2048 x 240, 768 x 2048, 2048 x 1536, 1280 x 768, 1024 x 1024 | auto | all below | complete, 0 wrong, 0 headers off, nothing non-zero below `td.rgn`, scene pages U4 |
| b9 | 1024 x 768 | auto | | complete (the completed stay so) |
| k1 | 1280 x 1024 | 0x4000 | 0xd800 / 0x7000 | fault (the knob reproduces E869: control) |
| k2 | 1280 x 1024 | 0xb000 | 0xd800 / 0xe000 | **complete** (entries over control, OTPM, state only) |
| k3 | 1280 x 1024 held | 0xa000 | 0xd800 / 0xd000 | fault; lost offsets = the frozen 171 headers 0xd000 to 0xd7f8 |
| k4 | 1024 x 768 | 0x3000 | 0x7000 / 0x6000 | fault, 341 offsets lost from 0x6000 (a size that never faulted, one page short) |
| k5 | 1024 x 768 | 0x4000 | 0x7000 / 0x7000 | complete |
| r1 | 4096 x 960 | auto | 0x2ff00 / 0x43000 | complete, 0 wrong (961 pages; explore: the 4096-wide residue) |
| r2 | 2048 x 2032 | auto | 0x1fff0 / 0x43000 | complete (1017 pages, the largest that fits) |
| r3 | 4096 x 1152 | auto | | -ENOSPC, no fault (H-ENOSPC4 at 4096 wide; explore) |

20 jobs. Predicted faults 3 (k1, k3, k4). About 20 minutes on the laptop, plan 40; r1 to r3 are
the large ones (r2's TA data dump is about 2.2 MB as m4's; no dump above 2048 x 2048: r1 and r3
run without `--dump-render`, r5-dpm's lesson).

- **Held out**: b1-b8 are Q292's own test of the planned change (E845's and E868's faulting
  cells). k2 to k5 separate the exact form from the bound: under "the room must be four times"
  k2 faults; under H-TPM it completes and k3, one page less, faults with a frozen set.
- **Controls that can fail**: s0, b9, k1 (if k1 completes the knob does not do what it says and
  k2-k5 are void), k5.
- **Stops**: s0 or b9 failing, a fault in b1-b8 after the first (one is the refutation of the
  change; a second adds nothing), any fault word other than 0x90100 at 0x10000011, any fault in
  r1-r3 (stop, strict health, keep the logs: it is the residue showing itself).
- **If it holds**: Q292 closes for sizes that do not overflow (the room's rule and what clears
  the offsets), with the 4096-wide residue either closed by r1 or split off as its own
  question; E824 and E828 get appended corrections (their four-array layout lacks the tail
  room past 1024 x 768); E868's "none of the eleven" stands and a new record carries H-TPM.
  sgx-sim and sgx-pipe: the layout model takes the Z-order need and refuses a 4x job whose
  entries pass the headers (refuse the unmeasured), with the 26 + new cells as vectors.

## 5. Q293: nothing closes it

The kept data holds no row for any of its four open items (E865's list): a setting that makes
the 3D read the displaced layout, 0xc0000000 on a line or a point, a non-zero value in the
inserted dword, render 2's own object. H-TPM does not touch it (the dword is in the parameter
buffer's object, not in the TA data).

Offered, riding on stage A with r5's stage t machinery (4 jobs, no fault predicted, 3 minutes):
t5, t6 = `CR_TE_AA` 0xc0000000 on the 11.31 line and point (frozen: one zero dword before the
format word at 9 and 11, empty image, as 0x40 and 0x80); t7 = the 0x40 triangle with a non-zero
value poked at dword 11 (frozen: image empty, the 3D reads it as the format word as in E829);
t8 = r5's t6 control. They would settle items 2 and 3. Item 1 ("is there a setting") has no
finite test; I recommend rewording Q293 to the three bounded items and noting the first as not
pursued (decision 5).

## 6. Order, counts, time

1. Build `r6-render4x` stage A (+ t rows if decided), freeze, dry run with the mock: 20 min.
2. Stage A on the laptop as booted: 16 jobs (20 with t), 15 min, 6 faults predicted.
3. Fold A. If H-TPM is refuted, stop: the kernel change falls back to the plain bound with no
   knob rows, and Q292 keeps its text.
4. Kernel commits with KUnit (section 3), cachix build, user's OK, one-shot boot.
5. Stage B: 20 jobs, 20 min, 3 faults predicted. Fold; corrections to E824, E828; Q292.

Steps 1 and 4's preparation overlap (the kernel commits can be written and built while stage A
runs; only the boot waits).

## 7. User decisions

1. **Order of the two stages.**
   a. (recommended) Stage A now on the rgn4 boot, then the kernel build and the one-shot boot
      for stage B. The form gets its held-out test before any kernel work depends on it.
   b. Kernel first; stage A's rows run on the new kernel with the knob set to the old room.
      One session instead of two, but the control "the old kernel still faults" is then the
      knob's own claim.
   c. Stage A only this round; kernel change later.
2. **Default room of a 4x context in the kernel.**
   a. (recommended) The bound: side doubled, 4 x the bytes (Q292's planned text; 4096 x 4096
      takes 0x2e3000 of the 4 MiB slot). Right under any reading that needs at most that.
   b. The exact Z-order need rounded to a page (4096 x 4096: 0x263000). Smaller, but the
      default then rests on H-TPM at sizes never run.
3. **The debugfs knob `render_tail_room`.**
   a. (recommended) Add it: rows k1-k5 turn "more room completes" into "this many bytes, one
      page apart", and it reproduces the old layout for regressions.
   b. No knob; stage B is b1-b9 and r1-r3 only (the bound is tested, the form rests on stage A).
4. **The reboot for stage B** (ends the rgn4 boot; the next reboot after it returns to stock).
   a. (recommended) OK after stage A is folded and the new kernel passes KUnit on cachix.
   b. Not this round.
5. **Q293.**
   a. (recommended) Add t5-t8 to stage A (4 jobs) and reword the question to its bounded items.
   b. Leave Q293 as it is, no rows.
6. **The 4096-wide rows r1-r3 in stage B** (large targets, about 6 of the 20 minutes).
   a. (recommended) Run them: r1 is the first clean test of the residue.
   b. Skip; the residue stays open in Q292.
7. **Held rows in stage A** (h1, h2: two held faults with debugfs dumps in the hold).
   a. (recommended) Both: two contexts, one with header 0 lost and one without.
   b. h1 only.
