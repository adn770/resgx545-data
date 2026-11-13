# Round 9 seeds plan: Q141, Q108, Q284, Q177, Q210, Q211, Q283, Q260, Q139

Planner: round 9 seeds (K1/Q190 excluded: another planner). Offline and read-only; nothing here
touched the laptop, cachix or a git repository. Scope: handover
`plans/resgx545-handover-2026-11-13-r8.md`
"Next" 3. State read: `doc/state_digest.md`, resgx545 main 5e58278, records to E946, module
B60AB0B4 (fork 2a650d74) on the laptop until the next reboot.

Everything this planner ran is in this directory:

| dir | script | output | what it decides |
|---|---|---|---|
| `q141/` | `aa4_inventory.py` | `aa4_inventory.out` | the region model on every kept `--aa4` tri-full image (55 jobs) |
| `q139/` | `residue_fit.py`, `residue_map.py` | `residue_fit.out` | a slot rule for E944's residue (fit) |
| `q139/` | `even_images.py`, `fx_status.py` | `even_images.out`, `fx_status.out` | that rule on 164 kept images; which words are safe |
| `q260/` | `far_e683.py`, `prec_e683.py` | `far_e683.out`, `prec_e683.out` | E943's far-vertex reading and the band on E683's 240 cases |
| `q210/` | `band6_table.py` | `band6_table.out` | the band 6 extra cells against the step error |
| `libmock/` | `dryrun.sh` (builds the bound tool's mock) | `dryrun.out` | that the proposed rows pass the library mock; E934's row does not |

Standard library only, except `q260/*.py` (numpy): the repository's `.venv` has no numpy (the brief
says it has; round 7 met the same), so they ran under `/Users/jtorra/src/nhc/.venv/bin/python -I
-B` (read only over resgx545-data). Nothing here derives from the closed firmware: all of it is
publishable if a record cites it.

## 0. Findings that change the round 8 seeds

1. **Q141: what the module refuses, and two ways to run E502's single-array context again.** The
   module's check (`sgxfive_cmd.c sgxfive_render_check`) takes a TE_AA with bit 31 or 30 when
   `ctx->aa_ms`. The fork sets that flag in `sgxfive_render.c sgxfive_render_init` as
   `ctx->aa_ms = ctx->aa4 || setting`, where `setting` is debugfs `render_rgn_arrays`. The arrays
   are `sgx_render_rgn_arrays(setting, aa4)`: the setting when it is 1, 2 or 4, else 4 with
   `--aa4` and 1 without. So `--aa4` with `dbg:render_rgn_arrays=1` gives a context that takes the
   multisampled TE_AA and has **one** array of region headers. That is E502's, E504's and E727's
   condition, except that the tail room is four times the 1x room (`sgx_render_tail_room`)
   [infer: the tail room does not reach a 128 x 96 image]. `--aa4` alone gives four arrays, which
   no record has run in modes 0 or 1. E828's j6 already ran the knob at 1 without `--aa4` and
   reproduced E827's single-array row byte for byte. The library mock refuses that form, though:
   it models `aa4` and no knob (`mock.c check_render`), so the kit would stop it.
2. **Q141 offline: no kept `--aa4` image tells the rivals apart.**
   `q141/aa4_inventory.out` scores 55 kept tri-full jobs on 4x contexts, from r3-rgn4, r4/r5/r6
   render4x, r6-misc and r7-rp, against E922's model. 51 of them are mode 2 at TE 0xe0000000.
   Both H-REGION and H-UNION predict 0 holes there, and the hardware stored 0 holes, so 51 of 51
   agree without parting anything. The other 4 are E829's empty case (bit 29 clear), which the
   model does not take. Whether four arrays change the seam holes of modes 0 and 1 is unread.
3. **Q284: E930's post hoc 32 x 32 index is E561's law.** E930 read the 32 x 32 faces post hoc:
   "fifth bits of s and t swapped", that is bit 8 = s4 and bit 9 = t4 (s is in the odd bits). E561
   (2026-11, long before E930) states the twiddle law of every 32-bit twiddled texture: tiles of 16
   x 16 interleaved, the tiles in raster order with x first, so at 32 x 32 i8 = x4 and i9 = y4. With
   s as x and t as y the two indexes are the same at every (s, t) [algebra]. A face is therefore an
   E561 texture [infer]. E930's 4831 pixels match a rule recorded before it ran, which is stronger
   than "fitted"; the rule was not frozen for r8-geo, though. At 64 x 64, E561 (i8, i9 = x4, x5;
   i10, i11 = y4, y5) and a pairwise swap (x4, y4, x5, y5) part, so a 64 x 64 face decides it.
4. **Q139 offline: the residue has a rule that fits.** `q139/residue_map.py` shows that in the
   three readable residue dumps a block row of the first macrotile takes **8 floor(fx / 2)** slots,
   where R7-BLK has 16 floor(fx / 4): 40 slots at fx = 10 and at fx = 11, 88 at fx = 23. Call this
   H-EVEN. It is the same rule as R7-BLK whenever fx is 0 or 1 mod 4. With block order unchanged it
   gives the wrong-tile set and every header slot of all three (`residue_fit.out`; fitted on
   B2-10 and B2-11, the 640 x 480 row checked after the form was chosen). On the 164 other kept
   whole images of ta/mtile-fields{,-risky} it agrees with R7-BLK, 163 of 164
   (`even_images.out`; the one miss is 1280 x 720 m2-B3p1, which no model gives).
   H-4FX (4 fx slots) is refuted offline (0 of 5 images where it parts). **No kept image outside the
   fit parts H-EVEN from R7-BLK, and every kept job at another fx of 2 or 3 mod 4 faulted or was
   cut** (`fx_status.out`, 30 jobs). So a hardware held-out row for H-EVEN is not safe class.
5. **Q260 offline: E943's far-vertex reading does not hold as a rule on E683.**
   `q260/far_e683.out`: of E683's 240 S3 cases, 167 have a vertex past the far edge and 61 of
   those are off HA (pixels up to 2.3e-3 px from an edge, edges under 195 px included); of the 73
   without one, 6 are off. A far vertex raises the miss rate (37% against 8%), but "a sweep misses
   iff a far vertex" fails both ways, and E943's band (6.4e-4 px, edges of 195 px or more) does not
   bound E683's misses. `prec_e683.out`: no threshold on distance / length, distance / |coordinate|
   or distance / (length x |coordinate|) separates the 101 wrong pixels from the 1931 right pixels
   within 3e-3 px of an edge (1546 to 1739 right pixels lie below the largest wrong ratio). More
   sweeps of E943's kind would add misses, not a rule. What is missing is an arithmetic candidate
   (section 8).
6. **Q210 offline: band 6's extra cells do not follow the step error.** `q210/band6_table.out`
   (from r8-ldpm `postrun/misses.out`, post hoc) lists, per target, the extra cells and the
   calibration's S_6 against E874's replay: 3072x2048 is +1 page with 0 extra cells, and 2560x2560
   is 0 pages with +2 extra cells. The two do not track each other. Two cells read "left 0x6"
   (3072x3072 at 0x3cf, 1024x1024 at 0x82), which looks like a reader artefact: OD-2 must check
   it before it fits anything.
7. **The kit's `#limit` (E946's slip, now fixed).** A control's expected fault is no longer
   counted, but the runner still stops when the count reaches `#limit` **with rows left**
   (`run_stage.sh` lines 183-189). A stage with N expectfault held-out rows that all fault needs
   `#limit N + 1`, or its end control never runs again.
8. **Tool binding for the library mock.** None of the round 8 sessions declared `source` for t4,
   so their rows were never replayed on the library mock. Every round 9 session must declare
   `source = "4623753:userspace/libsgxfive/tools/sgxfive-test.c"` and `source_sha256 =
   "703cbceaae8cdff3eda280b7ef89f3c5ef14ba7d378dd269bc66ef714aaead69"`. Verified here: the archive
   of 4623753 has the mock's aa4 check (`mock.c` line 756), and `libmock/dryrun.out` shows E934's
   row `job: rejected` while the same row with `--aa4` gives `job: ok`. The handover's "not yet"
   (`new_session.py` has no option for it) means the builder adds the two lines to session.toml
   by hand.

## 1. Q141: the seam row, rerun with the flag its premise needs

**Offline first.** Done (finding 2): no kept image decides it, so the rows are needed. The
frozen R8-1 table (`closing8/offline/r8-1/q141_r8pred.tsv`, sha256 file beside it, E922) is
reused byte for byte. The model is unchanged, the jobs are the same, and only the context flags
differ.

**Arms** (stages of S9-geo, section 10):

- **seam1, the held-out row (decides Q141).** The 24 R8-1 rows, each with `--aa4` and
  `dbg:render_rgn_arrays=1`, which gives E502's single array (finding 1).
  - Frozen: the R8-1 table, holes or stored set per job, H-REGION (msaa_model 1c0e8205...)
    against H-UNION (halves off).
  - Controls that can fail: `ctl-a-m1-6-64x64` (64 holes, the set's sha256 equal to E502's
    A-m1-te60-64x64) and `ctl-tf-64x64-m2-2` (0 holes). Both must pass, or the stage's rows
    cannot tell. The first is also the premise check: it fails if the 4x tail room or anything
    else in the `--aa4` context changes E502's image.
  - Held out: 14 tri-full sets, 6 single triangles; twins: 2.
  - Verdict: if H-REGION is exact on every held-out row, **Q141 retires (R8-3 a)**. If it misses
    any held-out row while the controls pass, Q141 narrows: the model fails out of sample.
- **seam4, a reading (opens or answers a new clause).** The same 24 rows with `--aa4` and no knob
  (four arrays), plus one more control: E828's j1r (288 x 144, mode 2, TE 0xe0000000, `--aa4`, 0
  background, hash 0x4a61860dcb4ab325). Rivals, frozen per job:
  - H-SAME4: four arrays store the H-REGION set, as one array does.
  - H-FULL4 [infer]: no holes, because each half reads a complete list.
  - H-UNION.
  The control can fail. The verdict goes to a follow-up line of Q141's record, or to a new
  question if H-SAME4 fails.

**Every row carries its premise (E934's trap).** The generator test asserts two things: every row
whose cmd:1 sets bit 31 or 30 has `--aa4`, and every seam1 row has `dbg:render_rgn_arrays=1`
(session.toml `[knobs] render_rgn_arrays = { default = "0", values = ["0", "1"] }`). The kit's
mock replays every row (finding 8): `libmock/dryrun.out` shows tri-full, mode 0 at 0xa0 and
single-triangle rows with `--aa4` all `job: ok`. The mock ignores the knob, which is harmless
here: the knob only widens what the kernel accepts.

**Stops.** Any fault or hang stops the stage (none in E502's, E504's, E727's 134 jobs on one
array, or in the 55 four-array jobs). A control without its pixel rows stops it (rc 25). The
second row without pixel rows stops it (hook, rc 24). Rows are `expectdiff` with `job: ok`.

**Risk.** Safe class: one array at 128 x 96 or below is E502's ground. Four arrays at modes 0 and
1 have never run [infer: no fault expected at these sizes]. 49 jobs, about 5 minutes.

Records: E953 (seam1), E954 (seam4).

## 2. Q108: the transfer stage again, and EDMPROTECT's split

**Offline first.** Nothing offline decides it, because these flags have no kept data beyond
E945/E946. Read from the dry run (`libmock/dryrun.out`): `tri --depth --depth-store` maps the
depth buffer at 0x3e001000 (20 pages) and the depth store at 0x3e015000. These are the
addresses the new knob rows aim at, and the builder confirms them on the laptop's preflight
dry run.

**Rows** (session S9-k2, module B60AB0B4, reusing r8-k2's generator `gen/make.py`):

- **xf2, 12 jobs.** First E946's 9 rows token for token: xf-c-fill, xf-c-copy, xf-c-addr, xf-c-ro
  (isolation, an expectfault control: not counted), xf-wo-fill, xf-cc-copy, xf-edm-fill,
  xf-wo-copy, then xf-c-end. Then 3 new rows:
  - `xf-wo-fill-low`: `fill --width 64 --height 16 --y 16`, WO, so the fill writes only the
    image's second page.
  - `xf-wo-fill-64`: `fill --width 64 --height 64`, WO, four pages [check: whether the
    destination grows with the fill's size; the dry run prints none].
  - `xf-edm-copy`: EDMPROTECT on the copy's read-only source (PTE 0x14), a transfer read.

  `#limit 6` (5 expectfault held-out rows + 1, finding 7). Frozen:
  - WO's fault page: H-LASTROW (the page of the last pixel written) against H-MAPEND (the
    flagged mapping's last page) and H-FIRST (its first page), on the three WO fills.
  - EDMPROTECT on a read: H-EDM-WRITE (it faults client writes only: the copy is exact) against
    H-EDM-REQ (it faults the transfer's requestors: the copy faults).
  - E946's own frozen predictions, unchanged: H-WO-ALL, H-CC-NEW, H-EDM-CLIENT.
- **tri2, 7 jobs.**
  - `tri-c`
  - `tri-woedm-fb`: flags 0x12, both flags together.
  - `tri-edm-dst`: `tri --depth --depth-store`, EDMPROTECT at 0x3e015000 (the ZLS write).
  - `tri-edm-dld`: EDMPROTECT at 0x3e001000, the depth load [check: whether control 0x0017100c
    loads depth, otherwise the row is a reading].
  - `tri-wo-dst`: WO at 0x3e015000.
  - `tri-c-depth`: the knob-free depth control.
  - `tri-c-end`

  `#limit 5`. Frozen: H-EDM-WRITE (every client write faults, no read does: dst faults, dld exact)
  against H-EDM-3D (only the pixel back end's colour write faults: dst and dld exact), and
  H-WO-ALL on the ZLS write.
- **Knob values to add.** `vm_pte_flags` takes 0x12, inside the knob mask: the fork's
  `sgxfive_vm_pte_flags_set` refuses anything outside `SGXFIVE_VM_PTE_KNOB`, and
  `sgxfive_vm_pte_flags` ORs READONLY in from the mapping. So `xf-edm-copy` writes the knob as
  0x10 and the PTE reads 0x14. `vm_pte_addr` takes 0x3e015000.

**Not planned.** CACHECONSISTENT on data cached before the host's write needs a tool that reads,
writes from the host and reads again in one context. sgxfive-test cannot, so this is a tool
change, left for later. WRITEONLY alone on a texture read needs a probe scratch's address
in the knob before the job [check: probe's scratch is allocated after the program; if the dry run
shows a fixed address, add `tex-wo-scr` and `tex-edm-scr`, 2 more expectfault rows].

**Risk.** Not safe class: about 9 planned faults, each in an expectfault row followed by a reset
and strict health, as r8-k2 ran without incident (E945, E946). This is decision R9-6. About 19
jobs, 12 minutes (the faults' resets and health checks dominate).

Narrows or answers: Q108's "which access faults at the last page", "EDMPROTECT on reads other than
the stream page's", "flags together", and "a held transfer row" (xf2's gate decides). It retires
only if CACHECONSISTENT's stale-data clause is dropped or split. Records: E964 (xf2), E965 (tri2).

## 3. Q284: 32 x 32 held out, 64 x 64 and 4 x 4 faces, ties and edges

**Offline first.** Finding 3: an offline record (E951) states that E930's 32 x 32 index is E561's
law [HW, E930 post hoc, matching a rule recorded earlier; in effect held out, though not frozen
for r8-geo]. Q284's 32 x 32 clause then narrows to the hardware row below.

**Stage cube2** (S9-geo; r8-geo's `gen/cube.py` copied and extended with N = 4 and 64), 17 jobs:

| part | jobs | frozen | rivals |
|---|---|---|---|
| control | 1 | E726's cu-xn (2048 px as kept) | can fail |
| 32 x 32, three new off-axis directions | 3 | H-E561: E923's face and (s, t), the face-local index E561's | H-MORTON (E923's 5-bit), H-PAIRSWAP (pairs above bit 7 swapped) |
| 64 x 64 faces (T1 0x4c03f03f, faces 4096 dwords apart) | 3 | H-E561 (i8, i9 = s4, s5; i10, i11 = t4, t5) | H-PAIRSWAP, H-MORTON |
| 4 x 4 faces (T1 0x4c003003) | 2 | H-NN (faces 16 dwords apart, 2-bit Morton: E561's "whole texture when smaller") | H-PAD64 (faces 64 dwords apart) [infer, from E940's padding]; no pick: decided by the read |
| face ties of the other pairs | 4 | H-HIGHAXIS (a tie goes to the higher axis, z > y > x, E931's w over u) | H-LOWAXIS, H-SIGN (by the sign of the minor coordinate); x = y and y = z, both signs |
| texel ties | 2 | readings: \|ma\| 1.5 and 1.25 (not powers of two), the boundary table per E931 | none frozen [infer: E931's pattern a function of the boundary] |
| bilinear at a face edge | 2 | H-SEAM-ADJ (the out-of-face taps read the neighbour face's texels adjacent across the edge, per the cube-map table) | H-SEAM-WRAP (the same local (s, t) in the neighbour face); edges +z/+x and -y/+z, the blend premise gating each as in E931 |

**Premise flag (E934's kind of trap).** 64 x 64 faces take 6 x 4096 dwords (24 pages): every
64 x 64 row must carry `probe --scratch-pages 32` (16 is not enough, and reading past the
mapping would fault), and the generator test checks it. The 32 x 32 rows keep E930's form.

Held out: everything but the control. Fit: none. Stops: any fault or hang (none in E726's,
E844's, E930's or E931's jobs), and the second row without pixel rows.

Retires when the 64 x 64 and 32 x 32 rows hold H-E561, the face-tie rows hold one rival on all 4,
and the edge rows decide one rival. The texel-tie clause stays as a reading unless a rule is
frozen offline from E931 + cube2 (round 10). Otherwise it narrows to what fails.
Records: E955 (sizes), E956 (ties, edges).

## 4. Q177: what sets 180 on the u axis

**Offline first.** No kept data varies size, format or T3 under modes 4 to 7 on u. E566 shows T3
bit 11 changes every pixel on a twiddled chain texture, and every addr job ran T3 = 0x00800800
(bits 11 and 23 set), so T3 is a live suspect [infer]. Nothing here is decisive offline.

**Stage addr2** (S9-geo; r8-geo's `gen/addr.py` copied and extended), 11 jobs, every texture at
page 12 of a named 32-page scratch (`--scratch-pages 32` and T2 0x5CAFC000 on every row, checked by
the generator):

- Control: `addr-ctl-u0` (mode 0 on u, repeat). Replicate: `addr-u4` at 16 x 16 (E932's +180 on
  2048 of 2048).
- u mode 4 and mode 6 at 8 x 8 (T1 0x0c007007) and at 32 x 32 (0x0c01f01f) twiddled (4 jobs).
  Frozen rivals per pixel:
  - H-OFF180: H-MASK-V's index + 180 dwords at every size.
  - H-OFFSCALE: + 180 N^2 / 256 dwords, so 45 at 8 x 8 and 720 at 32 x 32.
  - H-OFFNONE: no offset at sizes other than 16.
- u mode 4 at 16 x 16 with T3 0x00000000, 0x00000800 and 0x00800000 (3 jobs). Readings with a
  frozen null, H-T3-INERT (+180 whatever T3).
- u mode 4 with v mode 4 too (1 job): H-OFF180 on u only, H-MASK-V on v.
- u mode 5 at 16 x 16, base page 12 (1 job): a reading of what mode 5 reads past the texture.
  The named buffer below the texture makes every read decodable.

Stops: as r8-geo's addr. Narrows to "what sets 180" or answers it (if H-OFF180 holds at both
sizes and H-T3-INERT fails, 180 is a T3 function to decode). Retires only if size, T3 and mode 5
are all decided. Record: E957.

## 5. Q283: the remaining texture types

**Offline first.** Nothing kept varies type 1 off powers of two or type 4 off multiples of 32
(E910, E940, E941).

**Stage tx6** (S9-lgeo; r8-lgeo's `gen/texbuild.py`, `texcatalog.py`, `texmodel.py` copied),
14 jobs:

- Controls: E910's type 4 64 x 32 image and E725's type 3 32 x 16 map image (both can fail).
- Type 1 at 24 x 8 and 40 x 8 through the linear axis, with its bridge (type 1 32 x 16 through the
  same axis) gating them as E940's soft rows: RASTERW against RASTERP2 (3 jobs).
- Type 4 at 48 x 64, 96 x 32 and 80 x 64, through 64 x 32 windows moved by the map axis's offset
  (7 windows). Rivals:
  - H-CEIL: E941's blocks row by row with ceil(w / 32) blocks a block row.
  - H-P2: the blocks of the width rounded up to a power of two.
  - H-PACK: a partial block (w mod 32) columns wide.
- Type 3's padding: 4 x 8 at a 16-bit format, two texels a dword (2 jobs). Rivals: H-DW8 (rows
  max(8 dwords, w / 2)) against H-TX8 (max(8 texels, w)). [check: the 16-bit format's dword
  decoding in texmodel; if it is not modelled, label these explore.]

The scorer reads the `scratch at ... (N KiB)` premise line as tx4 did. Narrows: type 1's
non-power-of-two widths and type 4's partial blocks answered if one rival holds; the padding's
cause narrowed to dwords or texels. Record: E958.

## 6. Q139: the residue, offline first

**Offline (record E950 now, decision R9-2).** H-EVEN (finding 4): a block row of the first
macrotile takes 8 floor(fx / 2) slots. It is fitted on E944's three readable residue dumps
(3 of 3, wrong set and every slot) and agrees with R7-BLK on all 163 other kept whole images.
It cannot be held out on kept data: no image outside the fit parts it from R7-BLK. Refuters: a
dump at a new fx of 2 or 3 mod 4 whose slots differ. Q139's line narrows: "why" a partial block
takes an even number of columns stays open, along with the y-side residue, the stride's relation
and E509's faults.

**Stage q139b** (S9-lgeo; r8-lgeo's `gen/q139model.py`, `q139_fit.py` and the scorer's
`lib_dump.py` copied), 4 jobs, safe: every word drew in its dataset.

- `q139-ctl-1280x720` (control): unpoked, `--dump-render "$W"`. Exact image, one header a tile.
  It gives the header base E944 lacked.
- `q139-ctl-768x640` (control), likewise.
- `q139-res-1280x720-m2-B3p1`, dumped (it replicates its 52 wrong tiles: E944, ta/mtile-fields).
- `q139-res-768x640-m2-B3p1`, dumped (24 wrong tiles in its dataset; every model gives that
  set). Frozen: H-EVEN's slots (= R7-BLK's here; fx = 12).

The 1280 x 720 residue is a reading. Its slots are read after the run against the new baseline,
to fit the last-bound rule (B3 = 37, not a multiple of 4), which is a y-side analogue of H-EVEN
[infer] and stays in sample. Stops: needhash (the second row without a hash), any fault. The
kept rows show no fault (`fx_status.out`, E944). Record: E959.

**Not in safe class (decision R9-7).** Holding H-EVEN out needs fx = 6, 7, 14 or 15 at 256 x 256
(or B1 = 18, 19, 22 at 640 x 480). Every such kept job faulted or was cut (E506's risky
script).

## 7. Q210 and Q211: band 6, counts at many objects and several kicks

**Offline first: three steps, each run by the S9-ldpm builder before anything is frozen** (they
need r8-ldpm's dumps and OL7's replay code, which this planner did not rebuild):

- **OD-1 (Q211 U of wide scenes).** `dpm.rs scene_page_need` (HU1, E939) predicts the need of the
  1500-vertex scene and of `vtx_coord8`-written scenes at four wide targets with a need below
  0x3f0 (for example 4096x1024, 4096x1536, 3584x1024, 2048x512 [check each U < 0x3f0]). The
  predictions are frozen by hash. Refuter: one calibration's need off.
- **OD-2 (Q210 band 6).** On r8-ldpm's m6 mapped dumps (3072x3072 0x3ce..0x3d8, 2560x2560
  0x2b0..0x2b5), check the "left 0x6" cells first (finding 6). Then fit where the second page is
  kept past A_6, from the object block straddling pages 5 and 6 (its size, its last region, the
  macrotile it opens). Candidates are scored on the 10 targets' cells
  (`q210/band6_table.out`): fit on the two mapped targets, held out offline on the other eight
  (their cells are kept; only the dumps are new to the fit). Freeze by hash only if the candidate
  holds offline on at least 7 of the 8. Otherwise m6b runs as replicates and readings only.
- **OD-3 (Q211 several kicks).** Fit a count rule on OL7's 31 kept cells (fit) and score it on
  E938's 20 k cells. Those are semi-held-out: E938 printed H-KICKS' aggregate, and a candidate
  formed now has seen that 4096x4096 held and 2048x2048 did not. First candidate:
  H-KICKS-NORAISE, H-KICKS with R-5's non-raise when a partial render leaves 2 global pages
  (E918, E938's band 4 cells) [infer]. Rows run only if it gets at least 18 of 20.

**Design for the 8-pair scenes (E937).** Never the plain 8-pair program: only `vtx_coord8.bin`
(every output written, the same 53 blocks in three runs). Every cell is paired with a calibration
run in the same stage and dumped. Predictions are frozen as functions of that calibration
(two-step freeze, as E916's calibrations), never as values copied from round 8.

**Stages** (S9-ldpm, reusing r8-ldpm's `gen/plan.py`, `asm/`, bins and regtimeline wrapper; every
probe row `expect:rc3-overflow`, `#limit 0`, safe class):

| stage | jobs | what | frozen | stop |
|---|---|---|---|---|
| a0 | 6 | r8-ldpm's a0 rows, the premise on B60AB0B4 | E935's readings | a control off: no later stage opens (gate) |
| m6b | 34 | 4 new targets near band 6 (for example 2304x2304, 1792x1792, 2816x2048, 2048x2560 [check need < 0x3f0]): calibration + A_6 - 1 .. A_6 + 3 + 1 mapped cell each (28); replicates of 1536x1536 and 4096x2048 at A_6 .. A_6 + 2 (6), controls that can fail (do the extra cells repeat on this module?) | OD-2's candidate if frozen, against H-SPAN and E936's three class rivals | a replicate off: the rest are readings |
| w | 8 | OD-1's 4 scenes x (calibration at 0x400 + 1 cell) | HU1 (OD-1 hash) against H-BBOX | a calibration's need off: rc 24 |
| f9b | 9 | F9's replay at 3 new targets x 3 cells, cells chosen off band 4's 2-left cells, + 1 band 4 cell each where R-5's non-raise is frozen as H-NORAISE | F9 (E938), d = 7/4, d = 1 | a calibration off |
| k2 | 20 (only if OD-3 passes) | 5 new multi-kick scenes (2048x2048 K 3, 4; 3072x3072 K 2; 4096x2048 K 2, 3) x (calibration + 3 cells) | OD-3's candidate, H-KICKS, H-UNION | (gate only) |

77 jobs (57 without k2). About 28 minutes: k2 is about 30 s a job under regtimeline (r8-ldpm's
k stage), the rest 7 s. Narrows Q210 (band 6 by OD-2's candidate, or by "replicated, no rule")
and Q211 (U of wide scenes; the count at many objects; several kicks if k2 runs). Neither question
retires this round: both lines have clauses no stage touches (E802's one page, the lag).
Records: E960 to E963.

## 8. Q260: no laptop rows until an arithmetic candidate survives E683

**Offline first (OZ, before any row; decision R9-8).** Finding 5 refutes the far-vertex "iff" and
the band as rules on E683. OZ fits fixed-point edge-function variants on E914's and E943's kept
images (the in-sample fit). Each is frozen by hash and held out offline on E683's 240 S3 cases,
which are kept and which no variant has seen. The variants:

- the edge coefficients at b fractional bits, b from 4 to 12;
- the origin at the target, the tile (32 x 16) or the region;
- evaluation at the pixel centre or the sample point;
- HA vertex rounding throughout.

E683 is the held-out set: a candidate is kept only if it is exact on at least 235 of 240 (HA:
173). With `coverage-envelope/recompute/model1140.py` this is a scratch numpy task of a few
hours.

**Rows (zs3, about 60 sweep steps, S9-lgeo, only if OZ passes).** E943's suggestion: sweeps with
and without a vertex past the far edge at matched edge lengths (300 and 600 px), on both axes and
both targets, with OZ's candidate frozen against HA and against H-FAR (E943's reading).
Otherwise Q260 narrows by the offline record E952 alone, and its line drops the far-vertex
clause.

## 9. What each verdict does

| question | retires if | narrows if | record |
|---|---|---|---|
| Q141 | seam1: H-REGION exact on every held-out row, controls pass | seam1 misses held out; seam4's clause becomes a new line if H-SAME4 fails | E953, E954 |
| Q108 | not this round (the CACHECONSISTENT stale clause needs a tool) | xf2, tri2 decide WO's page, EDM on reads and writes, flags together | E964, E965 |
| Q284 | cube2: H-E561 at 32 and 64, face ties one rival 4 of 4, edges decided | the texel tie stays (reading) | E951, E955, E956 |
| Q177 | size, T3 and mode 5 all decided | 180's dependence named | E957 |
| Q283 | type 1 off powers of two, type 4 partial blocks, and padding decided | any of the three | E958 |
| Q139 | no | E950 offline (H-EVEN fit), q139b's y residue read | E950, E959 |
| Q210 | no | OD-2 / m6b | E960, E961 |
| Q211 | no | w, f9b, k2 | E962, E963 |
| Q260 | no | E952 offline; zs3 only if OZ passes | E952 (E966, E967 if zs3) |

E-numbers proposed: **E950 to E967** (E950-E952 offline, E953-E959 S9-geo and S9-lgeo, E960-E963
S9-ldpm, E964-E965 S9-k2, E966-E967 reserved for zs3). The lead assigns the final ones. E951
appends nothing to E930: it cites it. No landed claim is contradicted, so no correction is
needed.

## 10. Kit sessions (one sitting on B60AB0B4, in this order)

New session directories under `closing9/`, scaffolded from main (or the round 9 tooling merge)
with `new_session.py`. The generators are copied byte for byte from the round 8 dirs and
extended; the frozen r8 dirs are not edited, since a freeze is never rewritten. Tool t4
`~/sgxfive-test-rgn4` (e6951558...) with `source`/`source_sha256` added (finding 8), so every row
goes through the kit's library-mock replay. `srcversion = "B60AB0B475DD1E8972419B5"`.

| session | stages (jobs) | jobs | wall | class | reuses | records |
|---|---|---|---|---|---|---|
| S9-geo | seam1 (24), seam4 (25), cube2 (17), addr2 (11) | 77 | ~20 min | safe | r8-geo gen/seam.py + gen/o8, cube.py, addr.py, texprog.py | E953-E957 |
| S9-lgeo | tx6 (14), q139b (4), [zs3 (~60) only if OZ] | 18 [78] | ~12 [~20] min | safe | r8-lgeo texbuild/texcatalog/texmodel, q139model, q139_fit, lib_dump, zsmodel | E958-E959 [E966-E967] |
| S9-ldpm | a0 (6), m6b (34), w (8), f9b (9), [k2 (20) only if OD-3] | 57 [77] | ~18 [~28] min | safe | r8-ldpm gen/plan.py, gen/ol7, asm, bins, rt wrapper | E960-E963 |
| S9-k2 | xf2 (12), tri2 (7) | 19 | ~12 min | **medium: planned faults** (R9-6) | r8-k2 gen/make.py | E964-E965 |

Total: 171 jobs (251 with zs3 and k2), about 62 minutes of jobs and preflight (about 80 with
both). S9-k2 goes last, so that its faults and resets come after every safe session.

**Per-row premise checks** (each session's tests, besides the kit's library-mock replay):

| session | check |
|---|---|
| S9-geo | seam rows: cmd:1 bit 31 or 30 implies `--aa4`; seam1 rows `dbg:render_rgn_arrays=1`; cube 64 x 64 rows `--scratch-pages 32`; addr rows `--scratch-pages 32` and the T2 base |
| S9-lgeo | tx rows: the frozen scratch size; q139b rows: `--dump-render "$W"`, `--keep-going`, `expectdiff` with `job: ok` |
| S9-ldpm | every probe row `expect:rc3-overflow`; every cell has its calibration earlier in the same stage; 8-pair rows only `vtx_coord8.bin` |
| S9-k2 | knob values declared; `#limit` = expectfault held-out rows + 1; every expectfault row has `after` |

**Library mock.** `libmock/dryrun.out` shows E934's row (no `--aa4`) refused and the seam1/seam4
forms, the q139b forms and the S9-k2 forms not refused. rc 1 lines come from the mock's absent
debugfs (`kpoke`) or an output directory the kit makes and the dry run did not. `kit/session.py`
`libmock()` counts neither as a finding. The probe rows (cube2, addr2, tx6) need their program
binaries: the builder's own `tests/run_all.sh` replays them.

**Kit gaps.** The library mock does not model debugfs `render_rgn_arrays` (so the exact
E502 form, the knob without `--aa4`, would be refused; R9-1 (c) is the tooling route), and
`new_session.py` has no option for the source binding (added by hand). Nothing else is missing.

## User decisions

**R9-1 Q141's rerun.**
- (a) **Recommended.** seam1 (`--aa4` + `render_rgn_arrays=1`: one array, retires Q141 on H-REGION)
  and seam4 (`--aa4` alone: four arrays, a reading). 49 jobs, about 5 minutes, safe.
- (b) seam4 only, 25 jobs. It cannot retire Q141, since its premise is not E502's.
- (c) The round 9 tooling agent teaches the library mock `render_rgn_arrays` first. seam1 then runs
  without `--aa4`, E828 j6's exact form (4x tail room gone). One tooling change with a test, the
  same jobs.

**R9-2 Offline package O9 (records now, no laptop).**
- (a) **Recommended.** E950 (Q139 H-EVEN fitted on E944's residue, 163 of 164 kept images
  consistent), E951 (Q284: E930's 32 x 32 index is E561's law), E952 (Q260: E943's far-vertex
  reading and band fail as rules on E683's 240 cases). Scripts here are publishable as
  `cited-scratch:closing9/seeds/`.
- (b) E950 and E951 only, and E952 after OZ.
- (c) None: the findings only steer the sessions.

**R9-3 S9-geo** (Q141, Q284, Q177).
- (a) **Recommended.** All four stages, 77 jobs, about 20 minutes, safe.
- (b) Without seam4, 52 jobs.
- (c) seam1 alone, 24 jobs.

**R9-4 S9-lgeo** (Q283, Q139).
- (a) **Recommended.** tx6 and q139b, 18 jobs, about 12 minutes; zs3 joins only if OZ passes
  (R9-8).
- (b) q139b only, 4 jobs.

**R9-5 S9-ldpm** (Q210, Q211).
- (a) **Recommended.** OD-1 to OD-3 offline by the builder first. Then a0, m6b, w and f9b (57
  jobs, about 18 minutes), plus k2 (20 jobs, about 10 minutes) only if OD-3's candidate gets at
  least 18 of 20.
- (b) The same without k2 whatever OD-3 gives.
- (c) Defer the DPM to round 10 and run the offline steps only.

**R9-6 Q108's S9-k2, which plans faults (not safe class).**
- (a) **Recommended.** Allow it as r8-k2 was allowed: expectfault rows, `#limit` = fault rows + 1,
  strict health after each, the session last. 19 jobs, about 12 minutes, about 9 planned faults.
- (b) Only E946's 9 rows again (5 planned faults): the held transfer row and nothing new.
- (c) No Q108 rows this round.

**R9-7 Q139's held-out row for H-EVEN, whose words faulted in E506.**
- (a) **Recommended.** Not this round: Q139 narrows by E950 and q139b.
- (b) A risky stage of 4 dumps at fx = 6, 7, 14, 15 (256 x 256), `expectfault` with
  `#limit 5`, after S9-k2.

**R9-8 Q260.**
- (a) **Recommended.** OZ offline first (fixed-point edge variants fitted on E914 + E943, held out
  on E683's 240 cases); zs3 (about 60 jobs, about 6 minutes) only if a candidate gets at least 235
  of 240.
- (b) Run E943's matched-length far-vertex sweeps now as readings. They would add misses, not a
  rule (finding 5).
- (c) Park Q260 after E952.

**R9-9 Order and sitting.**
- (a) **Recommended.** One sitting on B60AB0B4: S9-geo, S9-lgeo, S9-ldpm, S9-k2, about 62
  minutes (about 80 with zs3 and k2), before the reboot to stock Arch. K1's Q190 rows (the other
  planner) go between S9-lgeo and S9-ldpm if they are ready.
- (b) Two sittings: the safe sessions first, S9-k2 after review.

**R9-10 Record numbers.**
- (a) **Recommended.** The lead assigns from this planner's range E950 to E967 (O9 E950-E952,
  S9-geo E953-E957, S9-lgeo E958-E959, S9-ldpm E960-E963, S9-k2 E964-E965, zs3 E966-E967).
- (b) Renumber after K1's range.
