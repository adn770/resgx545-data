# Round 19 plan: the E0CC4027 module's controls, then Q088, Q192, Q045, Q038, Q191, Q107

Planner (Opus, 2026-11-14), offline and read only. Basis: resgx545 main ec50498 (kit with the
declared-knob guard), data 95df71e98, fork resgx545 456404fcffe5 (ec521047f79b + 456404fcffe5,
read through `git show`), the survey's I1 (`closing18/survey/unlock-survey.md` sections 3, 5 dpm,
zls), the question files Q038, Q045, Q088, Q107, Q191, Q192, records E310, E461, E464, E591,
E625, E627 to E631, E734, E1014, E1020, E1029, and the tool source at ec50498 (t18b) and a581c06
(t10). Records reserved: **E1077 to E1086**. Laptop wall time planned: about 45 min (section 6).

Coordinator's correction (received while planning): the laptop is its own build host on the road,
so a small sgxfive-test change is possible; no module change is planned. No row below needs a
tool change; one optional proposal is in section 7 (R19-4).

## 0. Summary

| # | session | stages (jobs) | tools | questions | records | risk |
|---|---|---|---|---|---|---|
| S1 | r19-k0 | k0 (10), f0 (12) | t10, t18b, rt | module controls | E1077, E1078 | safe (f0-down medium) |
| S2 | r19-dpm | ld (8), ldb (6), dz (15), zs (6), rd (6) | t18b, t10, rt | Q045, Q038, Q107, Q088 | E1079 to E1083 | safe (ld zero fill medium) |
| S3 | r19-own | own2 (6), own1 (6) | t18b | Q192, Q191 | E1084, E1085 | safe |
| S4 | r19-flag | fl (3) | t18b | Q045 (junk lists), f0 extreme | E1086 | **flagged, user's OK** |

Total 78 jobs (75 safe, 3 flagged). Expected outcomes: **Q088 retire** (rd: the partial renders
take the render details' ZLS word of their kick, H-RD), **Q192 retire** (own2: the zeroing is the
second context's render, measured between the close and that render, held out at two more P and
one more size), Q045 narrowed to retire-capable (load clause by ld, state-page statistic by ldb;
retires only if both hold and the lead moves clause (c) into Q191), Q038, Q107, Q191 narrowed.

Order and gating: S1 first and alone; S2 and S4 need S1's f0 controls; S3 needs only k0 (t18's
kept-copy runs on any module), so S3 runs even if f0 fails. S4 last, after every safe stage.

## 1. What the module changes, and what that means for rows

- `render_final_pb_pages` (0 default, 0x23 to 0x422, else -EINVAL), taken once by the **next**
  render context, dropped by a reset (sgxfive_debug_disarm, take_final_pb). That context's free
  list holds max(P, N) pages; its thresholds are P's (ZLS = global = P - 0x22, PDS = global -
  0x100 or 0) **except the TA's, which follows the list (list + 0x10)**. A job that closes a scene
  a geometry job opened sets the TA command's flag 0x2000 and dwords 10 to 13 = (list + 0x10,
  N - 0x22, N - 0x22, PDS(N)); the next scene's first job sets P's back (sgx_render_pb_kick).
- Consequence for controls: with the knob set, the **geometry kick itself** already runs on a
  longer free list and a TA threshold of max(P, N) + 0x10. f0 checks that this changes nothing in
  the geometry kick (f0-geo, a control that can fail).
- t18b writes the knob itself before the render context (tool line 3099); the kit guard (ec50498)
  refuses `--final-pb-pages` unless session.toml declares
  `[knobs] render_final_pb_pages = { default = "0", values = ["0"] }`; preflight then requires the
  debugfs file (E0CC4027 only) and the trap puts 0 back. Every session below that uses t18b
  declares it, and `--srcversion E0CC40275493F8AEAD8180B`.
- Tool facts the rows rely on (read in sgxfive-test.c at ec50498): `--ctx2` refuses `--geometry`
  (line 4667), so no row mixes the final PB with a second context; `--bg-layer` refuses
  `--geometry` and `-n` other than 1 (line 2598); a geometry kick that **overflows** is reported
  ENOSPC and goes through the `over` path, so `--dump-each`, `--depth-dump` (`*.1.bin`) and
  `--regs` are written after it, while a geometry kick that does not overflow skips them
  (`continue`, line 3405); `--depth` refills the buffers before every render unless
  `--depth-ctl-next` is given (line 3269), so **every geometry depth row passes
  `--depth-ctl-next`** (else the host overwrites what the partial renders stored).
- t10 (a581c06) and t18b (ec50498) build the same job without the new options: the library
  differs only by `fb_fill_set` (`--refill fb`, unused here) (`git diff a581c06 ec50498 --
  userspace/libsgxfive/src`).

## 2. S1 r19-k0: the module's own controls (E1077, E1078)

Prefix `r19k`. Tools t10, t18b, rt (regtimeline 079f6359, `wraps = true`). Knobs:
`render_pb_pages` (default 0x422, values the cells' P), `render_final_pb_pages` (default 0,
values ["0"]). Both stages `gate = true`, `#limit 0`, safe. The register set of every rt row is
r13-dpm's (0x012c, 0x0624-0x0628, 0x0658, 0x0660, 0x0700, 0x070c-0x0710, 0x0720-0x0734, 0x0748,
0x0a74) plus 0x0620 and 0x0668 (the TA and PDS thresholds).

### 2a. Stage k0: knob 0 equals B60AB0B4 (E1077; 10 jobs)

Question: does E0CC4027 with the knob at 0 run the jobs of B60AB0B4 byte for byte (ec521047's
"every PB and command as before")? Retire-vs-narrow: n/a (premise of the round).

| row | form (kept twin) | tool | jobs | frozen prediction (H-SAME) | label |
|---|---|---|---|---|---|
| k0-pr1 | r13-dpm pr2-c1 (3072x2048, 1500 v, P 0x2b6, rt) | t10 | 2 | 1 partial render, 0x0624 = 0x294 all job, as pr2-c1-1/2 | control |
| k0-pr4 | r13-dpm pr2-c4 (P 0xe2) | t10 | 1 | 4 partial renders, 0x0624 0xc0 | heldout |
| k0-a0 | r10-dpm a0-cal-2048 (2048x2048, 1500 v, P 0x162, rt, --dump-render) | t10 | 1 | param and tadata sha256 = kept (equal in r9-ldpm and r10-dpm), s2..s5 = kept | heldout [check] |
| k0-z | r13-zls zb-c-ctl (64x32 ZLS load/store) | t10, t18b | 2 | depth-store.1.bin and drawn = kept, byte for byte | control |
| k0-geo | tri 1024x768 -n 2 --geometry 1 at P 0x28, --dump-each --words --regs 0x0600-0x0750 --keep-overflow --keep-going | t10, t18b | 2 + 2 | t10 and t18b runs byte-identical (tri.1/2 param, tadata, ta3d words); render 1: 1 partial render, TA3DCtl dwords 35, 37, 38 = thr0 - 2, 1<<16 \| 6, 0x20 (E625's raised regime, 2 * 6 < 19 + k); render_words: TA command flag 0x2000 clear and dwords 10-13 zero | control |

Rival: H-DIFF (the module changes a knob-0 job: any byte of a kept file differs). Stop: any
control off stops the stage (rc 24) and the round's S2 and S4 (section 6). [check] for the
builder: k0-a0's kept twin ran on rgn4 (4623753), whose probe path differs from t10's only by the
row stride (equal at 2048) and an equal vertex expression; the builder confirms with the library
mock that both sources emit the same scene, else k0-a0 becomes a reading, not a control. The
geometry form has no kept B60AB0B4 twin (geometry rows ran on 37EC97AB and earlier modules), so
k0-geo is tool-vs-tool on the new module plus E625's readings.

### 2b. Stage f0: the threshold update (E1078; 12 jobs, t18b under rt)

Question: does the EDM apply a TA command's thresholds (flag 0x2000, dwords 10-13) before that
kick's TA? The brief's first control: the final job's 0x0624 reads N - 0x22.

Frozen hypotheses: **H-UPD** (applied at the final kick: 0x0624 during the final kick's TA and
after the job = N - 0x22, the final render follows N's threshold); **H-IGN** (flag ignored:
0x0624 = P - 0x22, or + 0x20 after a raise in the geometry kick, the final behaves as at P);
**H-LATE** (stored in the descriptor, loaded only at a later kick: 0x0624 = N - 0x22 after the job
but the final render follows P: partial renders as H-IGN). Rival for the geometry kick:
**H-LIST** (the longer free list or TA threshold max(P, N) + 0x10 changes the geometry kick)
against **H-GEO0** (it does not).

Scene: the 1024x768 default triangle, U = 19 pages (E625), second render the same triangle (the
builder may move it; the cells' U is then read from the knob-0 twin, not assumed).

| row | P | N | jobs | H-UPD | H-IGN / H-LATE | label |
|---|---|---|---|---|---|---|
| f0-same | 0x422 | 0x200 | 2 | final 0x0624 0x1de, no overflow, job ok | 0x400 | control (premise, no overflow anywhere) |
| f0-up | 0x28 | 0x100 | 2 | geometry kick 1 partial render; final 0 partial renders, 0x0624 0xde, image short of the triangle (expectdiff) | final overflows, 0x0624 0x26 | control (fit) |
| f0-up-h1 | 0x30 | 0x60 | 1 | final 0x0624 0x3e, no partial render | 0x0e, overflow | heldout |
| f0-up-h2 | 0x24 | 0x422 | 1 | 0x400, no partial render | 0x02/0x22, overflow | heldout |
| f0-back | 0x28 | 0x100 | 2 | `-n 3 --geometry 1`: render 3 (next scene) 0x0624 back to 0x06, overflows (1 partial render) | render 3 completes if N's stuck (H-STICK) | heldout |
| f0-down | 0x100 | 0x28 | 2 | geometry kick no overflow (0xde); final 0x0624 0x06, final overflows (>= 1 partial render) | final completes, 0x0624 0xde | heldout, **medium**, last |
| f0-geo | (f0-up's render 1 against k0-geo-t18b's render 1) | | 0 | | H-LIST: they differ | control (H-GEO0: partial renders, abort statuses, dwords 35-38 equal; walk differs only past P) |

Fit vs held out: the prediction values are written from the kernel's arithmetic before the run;
f0-same and f0-up are the fit-labelled premise cells, f0-up-h1/h2, f0-back, f0-down held out.
Controls that can fail: every f0 row (H-IGN and H-LATE are live: the update path, edm_dataflow.md
0x1665, has never run with our commands). Readings: 0x0624 from rt samples during each kick and
from `--regs 0x0600-0x0750` after each render (overflowed geometry kick and final); partial
renders from the 0x0658 stretches (r9-ldpm's score/read.py, pinned); the kernel's command words
from `--words` (render_words: flag 0x2000 and dwords 10-13 on the final job only; a kernel-side
premise, not a hardware control). Stop: f0-same or f0-up off stops the stage; then S2 is void
and S3 still runs (R19-1). f0-down is last in the stage with `soft`: a threshold below the pages
the open scene already holds is new (the abort at the first allocation is predicted [infer]);
risk medium, kernel recovery expected if it hangs; its premise needs nothing else.

Kit fit: yes as is (rt wraps t18b; dbg:render_pb_pages; the declared final-PB knob; expectdiff
for f0-up's final, whose image is short by design, E038: the background repaints the
partial-render macrotiles; `--keep-going --keep-overflow` on every row so both hypotheses end
in a completed class).

## 3. S2 r19-dpm: what a final render that does not overflow shows (E1079 to E1083)

Prefix `r19d`. Tools t18b (all rows with `--final-pb-pages`), t10 for the -n 1 twins, rt. Knobs:
render_pb_pages, render_final_pb_pages (["0"]), render_bg_layer and render_bg_src (dz-c only,
r9-k1's binding). `#limit 0`; stages in the order below; each stage's first rows are its
controls (gate). The common premise in every row of ld, dz, zs, rd: the geometry kick overflows
(1 partial render at 1024x768, E625) and the final render does not (0x0624 = N - 0x22, no 0x0658
stretch in the final kick), read per row (`reads:`); a row without it stops the stage (rc 25).

### 3a. Stage ld: Q045's load readback (E1079; 8 jobs) - narrow, retire-capable with ldb

Question clause: does a load task read back the lists a partial render stored in the state page
(page 6 at 1024x768, E591/E627)? Form: E631 Part B (geometry kick that overflows, then
`--tadata-fill-render 2:6:0` before the closing render) with `--final-pb-pages 0x100`, so the
closing render no longer stores over the page before any read (E631's blind spot).
**H-LOAD**: zeroed lists change the final render's frees: the free-list walk after the job (E626:
a FIFO, all pages walked after every render) is short of the pages the open scene held, or the
3D page counts after the job (0x0730, 0x0660's high half) differ from the unfilled twin.
**H-NOLOAD**: walk, counts and image byte-identical to the unfilled twin. Rows: P 0x28 base x2,
zero x2 (fit, raised regime); P 0x30 base, zero (held out, not raised: the page then holds the
abort's lists, E627); P 0x2c base, zero (held out). Control that can fail: the base pairs repeat
byte for byte (tri.2 param and tadata), and the zero rows' page 6 after render 1 holds E627's
lists before the fill (tri.1 dump). Risk: medium [infer] for the zero fill (a count-0 list read
as empty; E631 ran zero fills 4 of 4 without trouble), `soft`, last in the stage.

### 3b. Stage ldb: Q045's state-page statistic (E1080; 6 jobs, knob 0)

Round 12's frozen check failed for want of a locator (Q045, "Round 12"): run raised 4096x4096 jobs
with the page located per width (0x42000, E627). Frozen rule R-PEAK: sum of the 16 macrotile
counts = the last run's peak status (0x0724 peak in rt) - 1; rival R-THR: = thr0 - 1 (E627's
not-raised regime); rival R-NEAR: within 3. Cells: tri 4096x4096 default triangle, `--dump-each`,
P 0x40, 0x60, 0x80, 0xa0 (raised: 2 * thr0 < 287 + k, E625) all held out; controls P 0xc0 and
0x100 (not raised: R-THR, E627's 28 of 28 regime, can fail). No new module needed (t18b, knob 0).

### 3c. Stage dz: Q038's depth readback (E1081; 15 jobs) - narrow

1. dz-a (8): E628's dl form (load buffer of dword indices `--depth-fill index`, separate store
   buffer with its marker, `--depth-dump`) with the geometry kick overflowing at P 0x28 and the
   final at N 0x100; final control without load bits (0x0017110c, G 33) or with them
   (0x0017510e), via `--depth-ctl` and `--depth-ctl-next`. **H-PRPATH** (E628's inference: the
   partial-render path loads whatever the control: the final store holds indices outside tile
   rows 0-11 in both) against **H-HOSTBITS** (a final render that does not abort loads only with
   bits 1 and 14: the scene's depth without, indices with). And the zeroed load buffer:
   **H-PRZERO** (zeros in tile rows 0-11 of the load buffer already in `depth.1.bin`, after the
   geometry kick's partial render) against **H-CLRREAD** (zeros only in `depth.2.bin`, the final's
   load clears as it reads). Rows: P 0x28 no-load x2, load x2 (fit); P 0x30 no-load, load (held
   out); controls: the -n 1 0x422 cells of E628 (no-load stores the scene's depth, load stores
   indices), t10, x2, which can fail on the new module.
2. dz-c (3): the colour reload with a depth buffer, open since 11.38: `--bg-layer --depth -n 1`
   at 1024x768 P 0x28 (x2) and 0x422 (x1, control): H-WHOLE (the whole triangle, E442's remedy,
   and the store as E628's overflowing job) against H-LOSS. No geometry (the tool refuses it with
   the layer). [check] that bgl_check accepts `--depth` (it lists no depth refusal).
3. dz-ov (4): E628's ov form (two overlapping triangles, the first in the geometry kick) with the
   final at N 0x100 and no load bits, near first and near last: H-PRLOAD (nearer wins: the final
   tests against the partial render's depth) against H-OWNCLEAR (the second triangle wins
   everywhere it covers). [check] the t18b spelling of E628's ov rows (the 11.38 tool was 1135).

### 3d. Stage zs: Q107's sign, zero row and tile order (E1082; 6 jobs) - narrow

E629's ramp (`--tri-full --tri-z`, G 33 and G 1 twins) with the geometry kick overflowing at P
0x28 (raised) and 0x30 (not raised), the final at N 0x100, no load bits, `--depth-ctl-next`.
**H-PRSIGN** (the partial render's store sets the sign in the raised regime: `depth.1.bin` signed
outside tile rows 0-11, `depth.2.bin` the final's own unsigned depth over the whole window, no
zero row) against **H-FINALSIGN** (the sign and zero row are the final render's after a raise:
`.2` signed). Tile order: **H-E996** (the final store of a render that does not abort, after
partial renders, is E996's header-order overlay: q107_rule.py of closing12/plan/c3-q107 pinned,
frozen, scored on the G 1 dump against its G 33 twin) against E1020's failure. Rows: 0x28 G33 x2,
G1 x1; 0x30 G33, G1 (held out); control: E489's no-partial ramp at 0x422 G 1 (E996 holds 6 of 6;
can fail on the new module).

### 3e. Stage rd: Q088, what reads the render details' ZLS word (E1083; 6 jobs) - **retire**

d43e4bb: the kick carries rd:11 as the tool sets it per render (`--depth-ctl` render 1,
`--depth-ctl-next` render 2, `--kpoke-render N:rd:11=V` after them). The G field (bits 11:3)
marks the word in the stored layout (E465). Geometry kick at P 0x28 overflows (its partial render
stores), final at N 0x100. **H-RD**: the partial render stores with the G of render 1's word (the
render details' word of its kick); **H-FW**: another control (a constant, e.g. the library's G 1,
or the final's word). Rows: render 1 G 33 / render 2 G 1, x2 (fit); swapped, x2 (held out: only
H-RD predicts the swap); P 0x30 one of each (held out). The load half (whether the final's reload
follows the word's load bits) is dz-a's H-HOSTBITS, with 0x0011700a, E336's closed-driver word,
as the with-bits control of one dz-a row. Retire if H-RD holds 6 of 6 and dz-a decides the load
half: answer "the word is the ZLS control of every 3D render of its kick, partial renders
included" (relabel kind hw, the survey's proposal); the closed driver's motive is not a question
of ours.

## 4. S3 r19-own: Q192 and Q191 on t18's closed copy (E1084, E1085; 12 jobs)

Prefix `r19o`. Tool t18b (it has t18's `kept.closed.N.bin`), knob 0 only (no `--final-pb-pages`:
`--ctx2` refuses `--geometry`; the final-PB knob is still declared, the tool is t18b).
Knob `render_keep` (dbg:render_keep=Y; E591's commit 47, never used in a kit session: [check] the
kit's read-back of this one-shot bool before the job). Form E631: `tri --ctx2 --close-first-early
--kept-copy $W --kpoke-render 1:ta:7^=0xc` (or 0x4) `--keep-overflow --words $W`. Risk: safe;
the one known fault is the case without keep (E458/E631), and the kit refuses the row if the knob
does not read back, so it cannot run unkept.

- **own2, Q192 (6 jobs) - retire.** Owner 1024x768 at P 0x28 (one partial render). H-RSTORE: page
  6 of `kept.closed.1.bin` (after the close, before the second render) holds E464's 18 non-zero
  dwords and `kept.1.bin` holds none; H-CLOSE: the closed copy is already zero; H-CREATE: the
  second context's creation (before both) zeroed it, so both are zero and the solo pattern never
  appears. Rows: flag 0xc x2 (fit, E631's case), 0x4 x1, P 0x30 and P 0x24 x1 each (held out),
  2048x1536 at an overflowing P x1 (held out, a new size; [check] the state page's index per
  size from E627's locator). What the store writes: the pages 1 to 11 diff of closed vs after,
  reported whole. Control that can fail: E631's after-render zero (4 of 4 then) on this module.
- **own1, Q191 (6 jobs) - narrow.** (a) Kick vs close: the 64x64 owner (E631, 0xc): H-RENDER
  (owner words 0x00200047, 0x04000417 and the state words absent in the closed copy, present
  after) against H-CLOSE, x2, flag 0x4 x1 (no words in either, control). (b) The state words
  against a constant: a 1024x768 owner at P 0x422 (no partial render, 19 pages) x2: H-COUNT
  (count << 16 | head with the owner's page count) against H-CONST (0x00020001, 2), held out.
  (c) P 0x200 64x64 x1 (held out: the words do not follow P, E631). Open after: a load reading
  the words back, page 4's five words.

## 5. S4 r19-flag: flagged, after every safe stage, user's OK needed (E1086; 3 jobs)

`#limit 3`, every row `expectfault after`, `on_stop = "end"`.

- fl-junk x2 (Q045): ld's form with page 6 filled with the ramp 0xa5000000 + i (E631's junk)
  before a final render that does not overflow. H-LOAD predicts a BIF fault or a hang the kernel
  recovers (page numbers past the page table) or a corrupt walk; H-NOLOAD an exact final as the
  base twin. A planned fault possible, hence flagged. It decides ld's load clause if the zero fill
  is read as "empty lists" and leaves it ambiguous.
- fl-thr1 x1 (module): P 0x422, N 0x23 (final ZLS threshold 1) with a scene holding 19 pages:
  H-UPD predicts an abort at once and repeated partial renders (E310's P 0x23 job ended exact);
  a livelock or a recovered hang is possible. Value low: run only if time remains.

## 6. Order, time, stops

1. Boot E0CC4027 (runbook section 2, srcversion E0CC40275493F8AEAD8180B), health: ~10 min.
2. S1 (22 jobs, ~7 min + staging 3). Stop rules: k0 off: stop, decide R19-1 (B60AB0B4 back, S3
   and ldb only). f0-same or f0-up off: S2 and S4 void; S3 runs.
3. S3 (12 jobs, ~4 min + 3). 4. S2 (41 jobs, ~12 min + 3; the 4096x4096 ldb rows are the slow
   ones). 5. S4 if the user OKs it (3 jobs, ~3 min with recoveries).

Total about 45 min of laptop time (r13-zls's rate: ~13 s a job with reset and health), under the
1 h limit with ~15 min margin. Offline parts (Mac, after the run): the folds, q107_rule.py scoring,
the walk counts (E626's walker), the state-page sums (dpm_raise.py), the question edits.

Builder notes (all sessions): scaffold with `--srcversion E0CC40275493F8AEAD8180B`; t10 bound as
r13-zls binds it (`data:render/closing-r10-st1/lead/build_tool10.sh`); t18b bound by
`--tool-src t18b=ec50498:userspace/libsgxfive/tools/sgxfive-test.c@<recipe>` with
`closing18/k18/build_tool18b.sh` copied byte for byte into S1's `lead/` (its first publication;
S2 to S4 cite S1's), binary 58e79855 bound by a `built` line. Replay vectors: f0, ld, ldb tables
refused by sgx-pipe's DPM model where unmodelled (name the SIM_UNMODELLED entry); zs and rd
replay through `zls::final_store` only for the non-aborting final (it refuses overflowed stores).

## 7. R19 decisions for the user

1. **R19-1 Gating and fallback.**
   - a) S1 gates the round: k0 off stops everything; reinstall B60AB0B4 (runbook section 4, no
     build) and run S3 and ldb only. f0 off voids S2 and S4; S3 runs (recommended).
   - b) Run every safe session whatever S1 shows, and sort it out in the folds.
   - c) S1 only this stop; plan S2 to S4 after its fold.
2. **R19-2 The two medium rows in safe stages (f0-down, ld's zero fill).**
   - a) Keep them, last in their stages with `soft` and a stop rule (recommended).
   - b) Move them to S4 (flagged).
   - c) Drop them.
3. **R19-3 S4 (flagged).**
   - a) Run fl-junk only (2 jobs, planned fault possible), after every safe stage (recommended).
   - b) Run fl-junk and fl-thr1.
   - c) No flagged rows this round.
4. **R19-4 A tool change built on the road.**
   - a) None: every row runs on t10/t18b as they are (recommended).
   - b) Let `--bg-layer` take `--geometry` (drop `geometry` from bgl_check's refusal; the
     layer's reference check on the final render only; a mock test of a geometry kick plus a
     layered final), for Q038's colour reload in a final that does not overflow (2 to 3 more dz
     rows). Built natively on the laptop with its test run there; adds ~30 min before S2.
5. **R19-5 Q088 on an H-RD result.**
   - a) Relabel kind hw and retire it, answered by E1083 with E1081's load half (recommended).
   - b) Keep it open as fw (the closed driver's purpose for the word).
6. **R19-6 Q045 on ld plus ldb.**
   - a) If both hold, move clause (c) (the kept owner's slot step) into Q191 and retire Q045
     (recommended).
   - b) Narrow only; keep Q045 as the umbrella.
