# Round 8 ranking: what is closable beyond round 7 (Opus, 2026-11-12, read-only)

Basis: resgx545 `main` 1c64f3a (records to E902; E895/E896 not used), 166 open (156 hw); data
830641e6; linux fork `resgx545` 664fd0d0 (read with `git show`/`git grep` only). Round 7 is
running and not folded: **excluded** are all it touches (Q287 Q291 Q276 Q293 Q139 Q086 Q210 Q211
Q003 Q111 Q294 Q142 Q262 Q240 Q260 Q283 Q178 Q206 Q230/Q296), 147 left. Model: round 7's ranking
(`closing7/rank/rank-round7.md`), updated.

Scratch in this directory (standard library only, public data paths, no firmware-derived content,
publishable): `index.py`/`digest.py`/`xref.py` and their `.txt` (round 7's scripts rerun on
1c64f3a), `tiers8.py`/`tiers8.out` (all 166 placed once, checked), Q284 `q284_st.py` (fit, freeze,
score), `q284_rule.json` + `q284_rule.sha256` (the freeze), `q284_fit.out`, `q284_score.out`,
`q284_rcp.py`/`q284_ties.py`/`q284_tievar.py` + `.out` (post hoc), Q141 `q141_map.py`,
`q141_ident.py`, `q141_pat.py`, `q141_src.py`, `q141_line.py`, `q141_model.py`, `q141_e504.py`,
`q141_cand.py` + `.out`.

## 0. Findings (read first)

1. **Q284: the cube faces' (s, t) is the public cube-map convention, held out offline on 4090 of
   4096 pixels** (`q284_*.out`). Fit on E726's eight jobs (6 axis + cu-w02/cu-w11): for each face
   the minor axis to s, the signs and the Morton bit order searched (32 combinations a face); one
   rule a face up to the s/t-swap twin (same index), 16376 of 16384 fit pixels. Read back it is
   the OpenGL cube-map table (+x: s = -w/|u|, t = -v/|u|; -x: +w, -v; +y: +u, +w; -y: +u, -w; +z:
   +u, -v; -z: -u, -v; [infer: our u, v, w as x, y, z]), texel = floor((q + 1) / 2 * 16),
   index = face * 256 + Morton(s, t) with t in bit 0 (E724's "y in the low bit"). Frozen by hash
   (`q284_rule.sha256` 52162471...) before E844's two off-axis jobs (never used for an (s, t)
   fit) were scored: **c-cube-a 2046/2048, c-cube-b 2044/2048** [HW data, held out offline; I
   had seen the first 19 values of cube-a's row 0 while checking the dump format, disclosed].
   Every miss of fit and held-out (8 + 6) is one texel low at an exact texel boundary with a
   non-power-of-two |ma| (`q284_ties.out`: at 3043 boundaries with |ma| a power of two the
   hardware takes the upper texel every time; with other |ma| 193 up, 14 down). The tie rule is
   not found: reciprocal RZ/RN x product RZ/RN fit 51-52 of 58 distinct (c, ma) pairs, and pairs
   with the same |ma| go both ways (`q284_tievar.out`) [post hoc]. Non-tie pixels: 0 off.
2. **Q141's background pixels are the landed region model's seam holes, already in the data
   but in no record.** tri-full is two triangles meeting on x/W + y/H = 1.25
   (`texture/p1141/recompute/msaa_model.py`, sha256 1c0e8205..., in the manifest frozen before
   E727). Its `predict` with the two-halves rule gives E502's 455 background pixels exactly in
   48 of 48 jobs (8 with holes, 40 without; `halves=False` fails 8 of 8) and E504's 136 at (32,
   32) in mode 0 with 0xe0000000 (15 of 15 jobs with bit 29; the 6 bit-29-clear jobs are E829's
   zero dword, not modelled) (`q141_model.out`, `q141_e504.out`). This is **in-sample**: the
   dataset's own `out/msaa_rescore.txt` reports the same 48/48 (the seam k = 1.25 was chosen on
   these data). Out of sample: E727 (the model frozen, 17/17 held out, other triangles) and E762
   (the unchanged model gave S3's 28 seam holes at 320 x 400 exactly, post hoc). Shape [data]:
   each hole is a staircase at a tile's top-left (`q141_pat.out`: slopes 1, 2, 4 pixels a row by
   mode/TE), along the seam, cut between the two stored pixels that share a source column; never
   a whole region (so "a region left without any primitive" is not it; the reading is "the half
   tile takes only its half-region's list, which lacks the seam's second triangle"). Q141's three
   readings are thus decided by records plus one held-out row (R8-1).
3. **Q271's "a xor cannot write the natural value" is overtaken by the tool:** `--vdm N=V` sets
   word N (`sgxfive-test.c:4003`, `src/poke.c` set vs `^=`), the same path as E703's `7^=`, so
   the forced = natural control exists without a tool change (a dated note, R8-4).
4. **Uncited newer records** (`xref.txt`): E893 names Q030 and Q089 (cite fix); E618 names Q141
   (refused tiles); E762 does not name Q141 but is its strongest record. The E6xx vector
   records stay as in rounds 6/7.

## 1. Candidates beyond round 7, ranked

Format: question; records; offline status; rows (count, risk, boot); what it closes; kit fit.
Boot for every row in section 1: **any test boot with the sgxfive render node** (41E2F5C7, or
37EC97AB if round 7's one-shot boot for r7-dpm s-k has happened; no row needs the r6/r7 knobs).
If the laptop is back on stock Arch, a one-shot boot of the installed module (user's OK). Tools:
t6 or t7 (`sgxfive-test`, from d9b2969/1c64f3a); probe bins built offline from main.

**R8-1. Q141 (isp, low; E618 refuses its 13 tiles in `sgx-pipe isp::msaa_source`).** Records
E502, E503, E504, E618, E727, E762; finding 2. Offline: done in-sample; the record is the
offline package's (O1). Laptop: `tri --tri-full --pixels` with E504's pokes (`cmd:1` TE,
`cmd:10`/`cmd:16` E507's sample words, `cmd:13` mode) at sizes never run, predictions frozen from
`msaa_model.predict` unchanged (`q141_cand.out`): 96 x 64 (m0/0xe 206 holes, m1/0x6 90, m1/0xe
45), 112 x 80 (m0/0x6 35, m1/0x6 134, m1/0xe 67), 128 x 96 (m0/0xe 514, m1/0x6 234, m2/0x6 20),
64 x 96 (m1/0x6 96, m2/0x6 22, m0/0xa 24), 80 x 48 (m0/0xa 103, m1/0x6 85): 14 jobs, all held
out; zero-hole twins (m2/0xa at 96 x 64 and 128 x 96: 0 predicted) 2; three single triangles of
other slopes by `--tri-v` (1/256 units; slope-a 64 x 64 (0,0)(100,0)(0,50), slope-b (0,0)(30,0)
(0,90), slope-c 128 x 64 (0,0)(150,0)(0,75)) at m1/0x6 and m2/0xe: 6 jobs (the question's own
"different slope"; the model predicts each whole stored set, 466 to 5564 pixels). Controls that
can fail: E502's A-m1-te60-64x64 as a colour job (64 holes, set known) and tri-full 64 x 64 TE
0x20000000 (0 holes); 24 jobs. Frozen: the hole set per job (sha256 of the sorted list) under
H-REGION (the model) and its null H-UNION (`halves=False`, predicts 0 holes for tri-full). Stop:
two unparsed outputs, any fault (none in E502/E504/E727's 134 jobs). ~3 minutes. Closes: Q141
retires if every held-out set is exact (answered by the record of the run); sgx-pipe's msaa
source admits the seam tiles (vectors from E502). Kit: fits (plain `tri` rows, `reads:hash`
controls, scorer reads the pixel rows of the kept text).

**R8-2. Q284 (texture, medium; no crate cite yet).** Records E726, E844, E567; finding 1.
Offline: the rule frozen and held out (O2's record). Laptop: E726/E844's probe form (`probe
--temps 32 --coords --pixels`, cubegen.py of `render/closing-r4-render4x/gen` extended): (a) four
new off-axis programs at 16 x 16, all six faces, predictions from the frozen rule with the tie
pixels listed separately (scored as "cannot tell" for ties); (b) 8 x 8 and 32 x 32 faces, three
directions each (6 jobs), frozen "same rule with N = 8, 32 and faces N*N dwords apart" [check:
the T0 size field for 8 and 32 from E725/E726's T words, else the generator refuses]; (c) a tie
sweep: |w| crossing |u| at 1/1024 steps in one image (2 jobs: does the face at |w| = |u| go to
the larger axis index, to u, or by sign) and 2 jobs whose pixels sit on exact texel boundaries
at |ma| = 1.75, 1.625, 1.875, 0.90625 (the pairs that went both ways), as a reading table
(exploratory, no rule frozen: the scorer prints direction per pair); (d) bilinear at a face edge:
2 jobs with frozen rivals H-CLAMP (filter clamped inside the face) vs H-SEAM (taps from the
neighbour face by the GL table) [infer: two rivals only]; control E726 cu-xn (2048 pixels known,
can fail). 15 jobs, ~3 minutes. Risk: lowest class (E726/E844 11 cube jobs, no fault). Closes:
Q284 retires if (a) and (b) hold and (d) decides; else narrows to ties/edges. Kit: fits (probe
rows, bins in `[files] laptop`).

**R8-3. Q101 (zls, low; 9 crate cites).** Records E411, E465, E466, E490. Offline: nothing left
(the ramps are positive in every kept dump). Laptop: E466/E490's `tri --tri-full --tri-z` with
`--depth`, `--depth-ctl` 0x0017110c with bits 26:24 = 1 and 2, with and without bit 19, a depth
ramp that is negative before the conversion (depth test always or greater [check that `--tri-z`
takes negative values and that the test passes against the fill]), `--depth-dump` kept: 8 jobs at
256 x 128 (not 1024 x 768: dumps of 128 KB), plus 2 controls rerunning E490's positive-ramp
format-1 and format-2 jobs at their size (dump sha256 known, can fail). Frozen rivals per dword:
H-ABS (bit 19 negates first, the integer of -z stored), H-CLAMP (negative z stores 0, bit 19 or
not), H-WRAP (round(z * 0xffffff) & 0xffffff, two's complement), H-NONE (bit 19 ignored by the
integer formats: E490's positive-ramp result extended). 10 jobs, ~2 minutes. Risk: lowest
(E466/E490's format jobs, no fault). Closes: Q101 retires if one rival holds on every dword
(both formats). Kit: fits (`outdir_opts` for `--depth-dump`, the dump dir made by the runner:
round 6's slip designed out by the kit).

**R8-4. Q271 (vdm, medium).** Records E546, E703; finding 3. Laptop, E703's `tri` vertex rows:
forced = natural control by `--vdm 7=<natural word>` for N = 11 (V = 3) and N = 8 (V = 4) (the
word read from a dry `--print-addrs`/`--words` run [check the tool prints the VDM words]), frozen
"image identical to the natural job's hash"; forced below natural, N = 11 with R = 3 at V = 8 and
11 (frozen rivals H-COUNT: rows are a count, vertices past R*V lost; H-LAYOUT: rows a stride, every
vertex read at the forced stride, image predicted by the decoder of E703); forced = natural + 1
at N = 2, R = 3, V = 2 (product 6: H-COUNT predicts intact, H-LAYOUT predicts a changed image).
8 jobs, ~2 minutes. Risk: "risky" class as E703's 10 (none hung); stop on one hang. Closes:
"forcing breaks a job" vs "wrong rows break a job" (the control); Q271 retires or narrows to the
layout if the control is exact. Kit: fits (plain rows; risk column).

**R8-5. Q177 (texture, low).** Records E565. Laptop: E565's tx_map probe on a 16 x 16 twiddled
texture placed at page 12 of a 24-page scratch whose every dword is named (dword i = 0xD0000000
| i over all pages: the probe's own fill, `--scratch-pages 24` and the texture base moved by
`--scratch-at` [check both options reach the T0 address in the probe form]), u swept over 128
positions at one texel a step for modes 4 to 7 (4 jobs), v swept at one texel a step (pitch 1, not
E565's 2) for modes 4 to 7 (4 jobs); control mode 0 (E565's repeat image, can fail). Frozen
rivals for u: H-MASK-V (u masked as v is: the v-axis rule of E565 on u), H-NOMASK-PAGE (the
unwrapped twiddle reaching neighbour pages: indices outside 0..255 name them), H-BORDER (a
constant); fit nothing, every job held out. 9 jobs, ~2 minutes. Risk: lowest (E565's jobs, no
fault). Closes: Q177 retires if one rival holds on u and v; else the reads are tabled per index
(the named memory makes every read decodable). Kit: fits.

Not picked, close behind: Q243 (ZLS load with integer formats and moved base: needs the load
base poke list and E831's 34 x 18; a good next row with R8-3's dumps), Q242 (16-bit format at
G != 33), Q179 (PVRTC 23-26: a decoder from the public PVRTC paper first, offline, then rows),
Q282/Q280 (offline fits on kept E723/E721 data; tried nothing this round), Q053 (weak), Q100
(after round 7's Q139 fold).

## 2. Sessions and the offline package

**Offline O8 (Mac, worktrees, `git commit -- <paths>`; ~3 h):**
- O1 Q141 record: the region model (sha256 1c0e8205, unchanged since E727's freeze) on E502's
  48 jobs and E504's 15 bit-29 jobs, in-sample, stated as such, with E727 and E762 as the
  out-of-sample evidence; Q141's text narrowed to "held-out seam row"; R8-1's prediction table
  generated from the model (frozen by hash with the session). 1 h.
- O2 Q284 record: the frozen rule (`q284_rule.json`, sha256 52162471) held out on E844's two
  jobs, 4090/4096, the misses all exact ties, the tie rule not found (post hoc table). Move the
  scripts into the data repo (`tools/records/scratch_cites.py --publish`). sgx-pipe: a cube
  sampler (face select of E844 + this (s, t)) refusing exact ties, tests from E726/E844's dumps,
  test first. 1.5 h.
- O3 Text: Q030 and Q089 cite E893; Q141 cites E762 (and E618 already names it); Q271 dated note
  (finding 3); Q103 fold into Q211 noted for after round 7's Q211 fold (E899). 30 min.

**Session `r8-geo` (any test boot, no kernel change; kit session):** R8-2 (15), R8-1 (24), R8-3
(10), R8-5 (9), R8-4 (8): **66 jobs, ~12 minutes of runs, ~35 with staging, preflight and health**.
Order: the lowest-risk stages first, the "risky" vdm rows last (R8-2, R8-1, R8-3, R8-5, R8-4).
Stop budget: one hang (R8-4 only), two unparsed outputs in a stage, free space below 300 MB. All
five fit the kit as it is (plain tool rows, knobs not needed, `reads:hash` or `reads:pixels`
controls, `outdir_opts` for depth dumps); none needs a held recovery or a stepped cell. Builder
checks before the freeze: the four [check]s above (T0 size field, negative `--tri-z`, VDM word
print, scratch placement) by mock or a dry run on the laptop's preflight; if one fails, that item
drops, not the session. Run it after round 7's sessions, on whatever test boot they leave.

**Session `r8-k` (only with the user's kernel approval; one fork series, one cachix build, one
one-shot boot; after r8-geo):** see section 3. Q190 rows first (low risk), Q108's fault rows last.
Fits the kit: knob rows (`dbg:NAME=V`, restored after every job and by trap) and plain faults the
kernel recovers; Q108's faults are not held recoveries.

## 3. Kernel-enabled questions: the exact fork change, tests, cost

Fork `resgx545` at 664fd0d0; delivery as round 6/7: test-first commits, recheck on cachix (W=1,
KUnit on and off), `tools/fork/deliver-module.sh`, `push-gma500.sh --ko`, one-shot boot,
srcversion check (HACKING "delivering and installing a checked module").

**K1 Q190, the render's one-layer background object (value medium; cost ~1 day with tooling).**
- Fork: debugfs `render_bg_layer` (bool, 0600, default 0). `sgx_render_bgobj()`
  (`sgx_render.c:413`) gains a layer path: at 1, the 23-dword form of `sgx_xfer_bgobj_copy()`
  (`sgx_xfer.c:206`) over the render rect, its source a client surface named by a second knob
  `render_bg_src` (device address, 0 = off; the render's own vm maps it). Both callers
  (`sgxfive_render.c:616` at write, `:696` at the recovery replay) take the same form, so a
  replay rebuilds it. The render bg page (`SGX_RENDER_PARAM_BG` 0x464000..0x465000) has room.
  `sgxfive_kpoke_words(SGXFIVE_KPOKE_BG)` returns 23 at knob 1, 17 at 0 (`sgxfive_kpoke.c`).
  The tag's size field is the user's `isp_bgobjtag` (uapi, unchecked beyond bits): no uapi change.
- KUnit (sgx_render_test, sgxfive_kpoke_test): knob 0 leaves the object byte-identical to today's
  17 words (and the replay path too); knob 1 equals `sgx_xfer_bgobj_copy` for the same rect and
  source; the bg poke parser refuses bg:17..22 at knob 0 and accepts them at 1; knob 1 with
  `render_bg_src` 0 refuses the render (-EINVAL), never a half-built object.
- Userspace (libsgxfive, tests first; tool t8 built on cachix): `tri --bg-layer` maps a source
  surface and sets `bgobj_words` to the copy's PDS program (libsgxfive `xfer_job.c` builds it for
  copies) [check: the copy's program iterates the layer's coordinates in a render's background
  pass; E590's object had no layer, so its program never iterated].
- Rows: E590's bg:N pokes on words 3 to 22, ten values each, coordinates first, ~40 jobs; control
  knob 0 (E590's hash). Low risk. Closes Q190's "does a render read the layer words" (and Q019's
  size-field clause in a render, [infer]).

**K2 Q108, PTE flags WRITEONLY / CACHECONSISTENT / EDMPROTECT (value medium; cost ~half a day,
no tool change).**
- Fork: `SGX_MMU_EDMPROT 0x10` in `sgx_mmu.h` (doc/specs/hw_spec.md section 4, from the GPL CE
  DDK's sgxmmu.h); debugfs `vm_pte_flags` (custom fops, 0600, default 0, accepts only bits of
  0x1a: WO 0x2, CACHED 0x8, EDMPROT 0x10; anything else -EINVAL) and `vm_pte_addr` (device
  address, 0 = off). `sgxfive_ioctl_vm_map` (`sgxfive_vm.c:343`) ORs the flags into the PTEs of
  the mapping that starts at `vm_pte_addr`, through a pure helper `sgxfive_vm_pte_flags(ro,
  addr, knob_addr, knob_flags)`; the BIF invalidate is already requested there.
- KUnit: knob 0 leaves every PTE as today (RO and RW maps); the flags reach only the mapping at
  the address; the setter refuses VALID, READONLY and bits above 0x10; RO + WO together are
  allowed (a reading row), [check: decide with the user whether RO|WO is refused instead].
- Rows (tool `--print-addrs` names the surfaces [check deterministic heap addresses on a dry
  run]): fill with WO on the destination (write: frozen "completes, hash as knob 0"), copy with
  WO on the source (read: frozen "faults like E021, CR_BIF_FAULT names the page"), CACHED on the
  source with a host write after the map (frozen "reads the new value", rival "stale"), EDMPROT on
  the destination of a fill, on a tri's colour target and on its vertex buffer (frozen rivals
  "no effect" vs "fault for client requestors"); controls knob 0 (hashes known) and E021's RO
  fill (fault known). ~16 jobs, up to 6 predicted faults + health after each, budget 6, stop on
  two -110 in a row (E848/E892's risk). Medium risk.

**K3 Q109, PDE page-size field (value low; cost ~half a day; recommend no).** A debugfs check
file like `xfer_iso` (`sgxfive_debug.c` `sgxfive_client_pd`, 0400) that builds a client PD with
one PDE of size field s over a table laid out under a frozen layout hypothesis (for 16 KiB: 256
entries of `addr >> 14 & 0xff`), runs one fill and reports. KUnit for the PD builder per s.
Rows ~12 with faults likely; the table layout is a guess with no source.

**Not with a fork change this round:** Q095 (EDM on directory list 15: boot risk, low value),
Q068/Q049/Q064/Q076 (a context-switch path and two overlapped contexts: an own phase), Q193 (a
module reload sequence on the test kernel, no fork change; low value, display risk).

| Item | Runs on | Kernel change | Jobs | Risk |
| --- | --- | --- | --- | --- |
| O1-O3 | Mac | none | 0 | none |
| r8-geo R8-1..R8-5 | any test boot | none | 66 | lowest; 8 "risky" vdm rows |
| K1 Q190 | new module, one-shot | `render_bg_layer` + `render_bg_src`, bg kpoke 23 | ~40 | low |
| K2 Q108 | same module | `vm_pte_flags` + `vm_pte_addr`, EDMPROT define | ~16 | medium (faults) |
| K3 Q109 | (no) | PDE size check file | ~12 | faults |

## 4. Ranking of all 166 (tiers; `tiers8.out`, every id once, checked complete)

- S7, touched by round 7 (excluded, 19).
- R8, picked (5): Q141 Q284 (offline + r8-geo), Q101 Q271 Q177 (r8-geo).
- K8, kernel-enabled (9): Q190 Q108 (costed, K1/K2), Q109 (K3, no), Q095 Q068 Q049 Q064 Q076
  Q193 (no).
- F8, text (5): Q030 Q089 (cite E893), Q103 (fold after r7), Q146 Q194 (round 3's "do not merge"
  stands: no new record).
- O8, offline later (19): Q100 Q053 Q288 Q200 Q280 Q282 Q078 Q163 Q075 Q012 Q008 Q261 Q125 Q107
  Q070 Q074 Q290 Q179 Q082.
- H8, safe hardware rows later (74): round 7's H less nothing taken; Q243/Q242 first.
- X (22) and P (13): unchanged.

## 5. Retire, fold and merge candidates (with records)

- **Q141 retire** after R8-1 if every held-out hole set is exact (answered by that record; E727
  and E762 already hold the model out of sample, E502/E504 in-sample). Alternative: retire now by
  decision on E727 + E762 + the in-sample 48/48 (decision 3 b).
- **Q284 narrow now, retire after R8-2**: the (s, t) and face size answered by O2 (+ R8-2 b);
  what stays is the exact-tie rule and the edge filtering. If R8-2 (c)/(d) decide both, retire.
- **Q101 retire** if one R8-3 rival holds on both integer formats.
- **Q271**: dated note (finding 3; no claim contradicted: E703 says what it ran). Retire after
  R8-4 if the control is exact and the forced rows decide H-COUNT vs H-LAYOUT.
- **Q030, Q089: cite fix**, add E893 (it names both, `xref.txt`); no text change.
- **Q103 fold into Q211** after round 7's fold of E899 (same partial-render count model).
- **Q146 / Q194**: no new record; keep apart.
- No landed claim needs a correction for any of these.

## 6. User decisions

1. **Offline package O8.** a) O1 (Q141 in-sample record + R8-1 prediction table), O2 (Q284
   record from the frozen rule, scripts published, sgx-pipe cube sampler test-first), O3 (cites,
   Q271 note, Q103 fold noted), ~3 h (recommended); b) O3 and dated notes for findings 1-2 only;
   c) none.
2. **Session r8-geo (no kernel change, any test boot, kit).** a) R8-2, R8-1, R8-3, R8-5, R8-4:
   66 jobs, ~35 min, after round 7's sessions (recommended); b) R8-1 + R8-2 only (39 jobs, ~20
   min, no [check] items); c) none this round.
3. **Q141.** a) Retire after R8-1's held-out row (recommended); b) retire now by decision on
   E727, E762 and the in-sample 48/48 (no row); c) narrow only.
4. **Q284.** a) Narrow now to ties and edges (O2), retire if R8-2 (c)/(d) decide them
   (recommended); b) retire after O2 + R8-2 (a)/(b), opening a small question for ties/edges;
   c) leave open until all rows run.
5. **Kernel work for round 8.** a) K2 (Q108, no tool change) and K1 (Q190) as one fork series,
   K1's rows only once the layer-sampling program passes its mock; one cachix build, one
   one-shot boot after r8-geo (recommended); b) K2 only; c) K1 only; d) no kernel work: note
   both as the next kernel items.
6. **Q108's RO|WO combination.** a) Allowed as a reading row (recommended); b) refused by the
   setter.
7. **K3 (Q109) and the rest of K8.** a) No (recommended: no source for the large-page table
   layout, faults, low value); b) cost K3 in detail for a later round.

## 7. Summary (10 lines)

1. Excluding round 7's 19, 147 open remain; all 166 tiered (`tiers8.out`).
2. Q284 (cube faces) offline: the GL cube-map (s, t) rule fit on E726, frozen, held out on E844
   4090/4096; the 6 misses are exact texel ties (tie rule open).
3. Q141 offline: the landed region model already explains every background pixel (48/48 E502,
   15/15 E504, in-sample; E727/E762 out of sample); one held-out row retires it.
4. r8-geo (66 jobs, ~35 min, any test boot, fits the kit): Q284, Q141, Q101, Q177, Q271 rows.
5. Q271: the tool's `--vdm 7=V` gives the missing forced = natural control.
6. Kernel (user's choice): Q108 PTE-flag knob (~half a day, 16 jobs, faults) + Q190 bg layer
   knob (~1 day incl. tool), one series and one boot; Q109 and the rest: no.
7. Text: Q030/Q089 cite E893, Q141 cites E762, Q103 -> Q211 after round 7.
8. Seven decisions, (a) recommended throughout.
Path: `/Users/jtorra/src/scratch/resgx545/closing8/rank/rank-round8.md`
