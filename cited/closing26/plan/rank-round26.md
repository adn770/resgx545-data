# Round 26 plan: tools and sessions that could retire questions now (overnight, safe class only)

Planner (Opus, 2026-11-15, overnight; the lead takes each recommendation), offline and read only.
Basis: resgx545 main 95445c7 (139 open, 129 hw; records to E1104), data e639458f0, fork
456404fcffe5, module E0CC40275493F8AEAD8180B, laptop tools t10, t14, t18, t18b, t22 (9b62d315),
t22b (2ae2800a), t24 (fd15fce4). Read: BRIEF-COMMON (round 26), the r25 handover, rounds 22 and
24's plans, the closing log to 2026-11-15, the state digest (open list, weaknesses, sim
baseline), the last paragraph of every open hw question (all 129, extracted by script), the full
files of Q019, Q050, Q098, Q114, Q126, Q129, Q133, Q136, Q146, Q168, Q177, Q179, Q191, Q194,
Q196, Q300; records E037, E040, E484, E564, E566, E567, E722, E1061, E1103, E1104; usse_isa 7.37
(sampler state); `tools/usse-asm/vectors.py`, `crates/sgx-sim/src/{vectors,tex,usse}.rs` (the
pds-secondary `attrs` rule and the YUV refusals), `crates/SIM_UNMODELLED.toml`, the build-kit
brief. No records are made by this round's plan; E1105 and E1106 are pencilled in (section 4).

## 0. Summary (yield, honestly)

- **Two retirements are reachable tonight, both low value and both conditional on a user
  decision about what counts as an answer.** Nothing medium or high is retire-capable with the
  tools on the laptop: every recently narrowed medium/high question (Q019, Q050, Q066, Q071,
  Q107, Q191, Q301) keeps a "why" or a multi-clause remainder no safe session can close.
  - **Q114 (low), r26-vol, t24, 45 jobs.** Its own retirement rule (R12-7 a, in the file):
    "retires on a word sweep that finds none". E567 ran the bit flips at one third coordinate
    only, so it never compared w values with a bit set. A pair per bit (w 0 against w 1.5, the
    image compared pixel for pixel) over the 19 T0/T3 bits that already ran on a twiddled
    texture without a fault decides whether any of them makes the third coordinate act.
    Retires if none does **and** R26-2 a takes the bound (the never-run bits T0 0, 2, 31, the
    T1 size bits and the faulting T3 13 stay Q300's, which already lists them).
  - **Q126 (low), r26-sa0, t24, 8 jobs.** Two clauses left (file, E1061 note): (1) the extension
    the iaddu32 test reads, which E498's measured flag rules make identical under both
    extensions for every pair (an arithmetic consequence, section 2.2), and (2) the value
    iaddu32 writes into sa0 for one instance. A fill in which one instance alone writes sa0
    decides (2). Retires if (2) holds out **and** R26-3 a retires (1) as not observable
    (precedent: Q276's predicate clause, R6-6 a).
- **The tool/sim package is offline (no laptop build) and makes records replayable, not
  retirements:** P1 = `vectors.py` attrs 64 (E1104's sa32-63 rows replay on sgx-sim, whose
  `Secondary` already takes `attrs` from the vector) and sgx-sim's YUV formats with a loaded
  colour-space set (E037's exact arithmetic) and the set carried across a batch (E1097, E1103).
  One agent, ~4 h, Rust and Python only.
- **Not reachable, checked:** Q019 (the field limits nothing a fill shows; "from another word"
  needs a word no record names), Q129/Q136 (a "why" and five clauses), Q146/Q194 (a time
  series, no rule frozen; a merge is not an answer), Q177 ("what the half is"), Q179 (needs a
  PVRTC decoder: section 3.3), Q033 (no cheap row, its own note), Q010 (a planned hang), Q063
  (other hardware), Q168/Q133 (TRC 49+ arms: not safe class).
- Summary of the sitting: r26-vol then r26-sa0 on t24, ~30 min, one sitting, no knob, no fault
  planned. Up to 2 value points, 2 questions; at worst both narrow (Q114 would then be
  *answered* in part: a bit that makes w act names a volume candidate).

## 1. Ranking

Weights as rounds 18 to 24 (high 3, medium 2, low 1); c = conditional on a decision.

| # | item | kind | retires | row | h | risk | laptop build |
|---|---|---|---|---|---|---|---|
| S1 | w pairs per T0/T3 bit | session r26-vol, t24 | Q114 (1c, R26-2) | 45 jobs | 2 | safe | no |
| S2 | one-instance sa0 write | session r26-sa0, t24 | Q126 (1c, R26-3) | 8 jobs | 2 | safe | no |
| P1a | `vectors.py` attrs 64 | tool, offline | none (E1104 replay) | - | 1 | low | no |
| P1b | sgx-sim YUV + kept set | sim, offline | none (E1103, E1097, E037) | - | 3 | low | no |
| P1c | sgx-sim T3 address bits | sim, offline | none (E722 off the list) | - | 2.5 | low | no |
| X1 | PVRTC decoder + fills | tool + session | Q179 (1c) | ~12 jobs | 5 | low, clean room | no |
| X2 | sa kept across jobs | stage in r26-sa0 | none (Q129 narrows) | 4 jobs | 0.5 | safe | no |

P1c is the one SIM_UNMODELLED entry (E722) whose kept data now let the sim model it (13 of 16
held out exact; the 3 others faulted past the scratch and stay refusals): offered, not
recommended (R26-4). X1 and X2 are listed, not proposed (R26-5, R26-6).

## 2. The two sessions that can retire something

### 2.1 r26-vol: does any bit make the third coordinate act (Q114, low)

**Open (Q114, round 12 note, decision R12-7 a):** "whether another word (T0 to T3, Q078's
unexplained bits) names a volume ... The question retires on a word sweep that finds none, or is
answered by one that finds it." No later note. Q078 was answered (E1067); its unrun bits moved to
Q300 (first bullet: "T0 bits outside the measured fields ... T3 bits 7:0, 10, 18-19 and 27-28
outside E397's and E722's fills").

**What E567 did and did not do.** Its `ind-*` jobs flipped T3 10, 14, 18, 27, 28 and T0 27, 30
under `smp3d` at **one** w (0.625) and compared with the 2D control: those bits change the image
whatever w is (E566, E722), so "differs from the control" says nothing about w (E567's own
results paragraph). No job compared two w values with a bit set. That is the missing row.

**Bits (single XOR on E567's twiddled 16 x 16 control, T0 0x07fe0000, T1 0x0c00f00f, T2
0x5caf0000, T3 0x00800800, `tx_map.s`, format 12, point):** only bits a record ran on a twiddled
texture without a fault, so the stage is safe class.

| word | bits | ran without fault on twiddled in |
|---|---|---|
| T0 | 14, 15, 16, 28, 29 | E564 (64 x 64 chain, 11 of 15 flips = control) |
| T0 | 27, 30 | E564, E567 (`ind-t0b27`, `ind-t0b30` at w 0.625) |
| T3 | 8, 9, 15, 20, 21, 22 | E564 |
| T3 | 11, 12 | E564, E1027 (level select) |
| T3 | 10, 18, 27, 28 | E567 (`ind-t3b*` at w 0.625), E722 |

Excluded (never run in a sampler table, by a scan of every `mov r20/r23` immediate in
`probes/**/*.toml`, or faulting): T0 bits 0, 2 and 31 (31 only as the copy's luma key, E275),
T3 bit 13 (faults, E566), T3 14 on twiddled (faults, E566, E567), T3 19 and 24-26 (scale and
fetch spacing; 19 is E722's scale, its large extents faulted), T1's size bits 7-11 and 19-23, T2
(the address). These stay Q300's clauses; R26-2 decides whether that bound retires Q114.

**Rows** (one fill each, 2048 pixels, `--pixels`, t24 `probe --temps 32`, E567's case text with
the one immediate changed; r26 = the third coordinate register):

- controls first (gate): `c-w0` (E567's `ty0-3d-w0` byte for byte: its pixel sha256 must equal
  E567's, can fail), `c-w15` (`ty0-3d-w15`: equal to `c-w0` pixel for pixel, E567's w3d=ignore),
  `c-cube-w5` and `c-cube-w15` (E567's `rt2-3d-w5`, `rt2-3d-w15`: their two hashes 79970597...
  and 480213ab... and **different from each other**: the control that shows a w that acts is
  seen, can fail), `c-w0b` (`c-w0` again: the reset leaves no state that moves the image).
- `vb-<word>b<k>-w0`, `vb-<word>b<k>-w15` for each of the 19 bits (38 jobs), w 0 and 1.5.
- repeats `vb-t0b27-w0r`, `vb-t0b30-w0r` (E564: values that are no name of the buffer; a repeat
  tells a w effect from a run-to-run one).

45 jobs, ~22 min (round 24's estimate for r25-sa64's 58 jobs was ~28 min with the kit's reset
and health around each job). E567's `rt2-*` rows ran in its `types-risky` group, one at a time
with a health check, and none faulted or hung; TEXTYPE 2 is the cube (E726), safe class [infer].

**Frozen.** H-NOVOL: for every bit, the w 0 and w 1.5 images are equal at all 2048 pixels.
Rival H-VOL(bit): they differ. Cannot tell: a bit whose repeat differs from its w 0 job, or a
job that did not complete. No fit set: the controls carry E567's readings, every bit row is held
out under H-NOVOL (frozen from E567's w3d=ignore, 8 of 8). Stop: any control off its reading
(gate), any fault (`#limit 0`, `on_stop = "end"`).

**Retires Q114** if H-NOVOL holds for all 19 bits with no cannot tell, under R26-2 a. If a bit
acts, Q114 is answered in part (that bit is the volume candidate; its slice layout is the next
row) and narrows. Either reading narrows Q300 (19 bits under `smp3d`).

**Kit fit.** Yes: probe fills with per-row programs rendered from E567's TOML (`tx-types.toml`)
by `tools/usse-asm/probe.py`, as r25-sa64 rendered E391's; pixel words kept; a pair scorer.
Replay: `closing_tables.py texture` (the kit kind, `pixels/`), `replay` refused with the reason
"sgx-sim reads smp3d as smp2d only at E567's T words (`tex.rs` test
`smp3d_is_smp2d_only_where_it_ran`); the flipped words are Q300's" unless the fold extends that
rule to the bits that held (a sim change the fold names, not this session).

### 2.2 r26-sa0: what one instance's iaddu32 writes into sa0 (Q126, low)

**Open (Q126, E1061 note):** "the extension the test reads, which no test tells (... [infer] not
observable, as Q276's predicate clause), and sa0 written by one instance alone."

**Clause (1) is not observable, by E498's own rules** (no run needed). E498 measured: iaddu32
`p` always true, `n` never, `z` true for (0, 0) only, the sum counted with its carry. Under zero
extension the 33-bit sum zext16(r1) + r2 is zero only for (0, 0); under sign extension the
unsigned 33-bit sum of sext16(r1) (as 32 bits) and r2 is zero only for (0, 0) too, since both
addends are non-negative below 2^32. So every test gives the same flag for every pair under
both extensions: no row can tell them. That is a consequence of measured rules, not a guess;
R26-3 decides whether it retires the clause (as R6-6 a did for Q276's predicate).

**Clause (2), rows** (t24 `probe --coords --temps 32`, E1061's generator
`resgx545-data/usse/closing-r16-usse/gen/progs.py` as the base, usse-asm of 95445c7): every
instance tests pa0 against one coordinate and branches past the body unless it is the writer
(the predicated `br` of E596's fills); the writer runs E1061's `iaddu32.testtaz.chan0 sa0, p0,
r1, SRC2`, then `mov r3, sa0` and stores r3 to its own scratch dword, eight pairs in sequence.

| row | writer | destination | pairs | label |
|---|---|---|---|---|
| c-e521 | every instance | r10 | E1061's `u-ctl-e521` byte for byte | control (8 of 8, can fail) |
| c-one-r10 | (0, 0) | r10 | E1061's u-sa0 pairs | control: the branch form, H-ZX 8 of 8 |
| s-00-a, s-00-b | (0, 0) | sa0 | E1061's u-sa0 pairs, runs a and b | held out |
| s-6331-a | (63, 31) | sa0 | the same | held out (another instance) |
| s-new-a, s-new-b | (0, 0) | sa0 | 8 new pairs, r1 low 0x8000-0xffff, seed frozen | held out |
| s-new-6331 | (63, 31) | sa0 | the new pairs | held out |

8 jobs, ~5 min. Frozen: H-ZX ((r1 & 0xffff) + source 2, 8 of 8 dwords a row) against H-SX
(sign extension; the pairs chosen so that the two differ in 7 of 8, as E1061) and H-MIX (a
dword holding another pair's value: E1061's reading with every instance writing). Stop: a
control off its reading (gate), any fault.

**Retires Q126** if H-ZX holds on all six held-out rows and R26-3 a. It also gives sa0 a
single-writer reading to set against E1061's mixture (the sharing [infer] stays Q098/Q129's).

**Kit fit.** Yes: probe rows with `--coords`, 8 scratch dwords (inside the 32 printed even on
t22), the r16-usse scorer's dword model. Replay: `vectors/closing/r16-usse/usse` form; sgx-sim
models iaddu32's value and runs the branch; whether it takes a one-writer sa0 is checked by the
builder (it refuses E1061's shared sa0 under Q126: a refusal is a valid `replay`).

## 3. P1: the offline tool and sim package (one agent, ~4 h; no laptop build)

### 3.1 P1a: `vectors.py` attrs from the run (E1104 replay)

`tools/usse-asm/vectors.py` line 41 sets `PDS_ATTRS = 16` ("what a PDS probe may write
(sgxfive-test PROBE_PDS_ATTRS)") into every pds-secondary vector; sgx-sim's `Secondary`
(`vectors.rs` 418-470) refuses a douta to `sa{n}` at n >= attrs. So E1104's 56 q019 vectors
(douta to sa32-63) stop. Change: `PDS_ATTRS = 64`, the comment naming E1104 (0-63 reach their
own sa at 0 to 8 rows; 64 the most any record read), the mock's `PROBE_PDS_ATTRS` left as it is
(a C change would need a laptop build and changes no hardware row). Tests first:
`test_vectors.py` line 172's `attrs == 16` becomes 64, plus a vector with a douta to sa40 that
replays exact, and one to sa64 that still refuses. Then convert r25-sa64's kept run into
`resgx545-data/vectors/closing/r25-sa64/` (closing_vectors.py, as r16-usse) and replay: 56 of 56
expected exact [infer: the sim's USE side stores sa32-63 to dwords 32-63 as the program does].
Earlier vector files are not regenerated (their attrs 16 were what those runs could show).

### 3.2 P1b: sgx-sim YUV with a loaded set, and the set across a batch (E037, E1097, E1103)

Today `tex.rs` lets formats 28 and 29 through only where the vector says the set is unloaded
(`job_csc_unloaded`), black; otherwise it refuses. The kept data now fix both missing parts:

- **The conversion** for set 0 holding E037's BT.601 words (0x00950095, 0x00000095, 0x010203ce,
  0x039800cc, 0): `sat_u8((cY (Y - 16) + cU (U - 128) + cV (V - 128)) >> 7)` per channel, R = (149,
  0, 204), G = (149, -50, -104), B = (149, 258, 0), alpha 0xff, format 28 as Y0 U Y1 V and 29 as U
  Y0 V Y1, two texels a dword (E037 2048 of 2048 twice; E1097 and E1103: the fills read the
  copy's hash). Zeros give opaque black (E037). Any other set's words refuse (one set's fields
  were fitted: E037 "a reading the fit confirms"), naming Q010/Q050.
- **The set as machine state across a batch, in job order:** a job whose pokes set xfer:17 bit
  0 loads xfer:18-22; a job without it reads the last loaded set; before any load since the
  batch's start the state is "not known" unless the vector says unloaded (p1132, [infer] as
  now). E1097: the set survives the debugfs reset; E1103: H-FILLLOAD 8 of 8.

Tests first: E037's three copies (BT.601, zeros, not loaded) if they are vectors in sgx-pipe's
xfer path, else a unit test on E037's formula over its source; E1103's 16 jobs converted from
`render/closing-r25-csc` (copy rows into the batch's set state, probe rows replayed): 16 of 16
exact predicted; the refusal for an unknown set and for other words. SIM_UNMODELLED does not
shrink (E1097 and E1103 are cited by the sim as refusals today), but Q050's YUV clause becomes
modelled in the sim; `HACKING.md` notes it under the sim entries.

### 3.3 Not in P1

- **P1c (R26-4 b): E722's address bits in `tex::sample`** (T3 28:27 level offset chain, 19:18
  scale, 10 base dword; held out 13 of 16, the 3 faulted rows as refusals). It takes E722 off
  `SIM_UNMODELLED.toml` (the list only shrinks). ~2.5 h more; it retires nothing.
- **X1: a PVRTC decoder for Q179 (formats 23-26).** E568's readings (one data bit moves 7 to 13
  pixels; the A pattern reads one value) fit a modulated two-colour scheme [infer]. A frozen
  decoder needs a citable layout source; the Fenney 2003 paper and the Khronos extension do not
  give the bit layout, and an open-source decoder by the vendor would need the user's clean-room
  ruling first. Not overnight (R26-5).

## 4. Sessions for tonight

| session | tool | stages (jobs) | questions | record | wall | class | kit fit |
|---|---|---|---|---|---|---|---|
| r26-vol | t24 | vc (5, gate), vb (40) | Q114 (Q300 narrows) | E1105 | ~22 min | safe | yes |
| r26-sa0 | t24 | uc (2, gate), us (6) | Q126 | E1106 | ~5 min | safe | yes |

- Scaffold each with `--srcversion E0CC40275493F8AEAD8180B`, tool t24 (fd15fce4, its binding in
  `closing24/k24/TOOL24.built`), no knob, `#limit 0`, controls first, `on_stop = "end"` after a
  failed control. Laptop prefixes `r26v`, `r26s` under `~/scratch/`.
- One sitting (~30 min, under the 45 min limit with one re-stage), r26-vol first (the longer).
  Both can be built while P1 runs; P1 touches nothing the sessions pin (`tools/usse-asm/probe.py`
  is read, `vectors.py` changed: the builders pin main 95445c7, not P1's branch).
- Fold notes (in each README): r26-vol retires Q114 only under H-NOVOL 19 of 19 and R26-2 a,
  and appends the 19 bits to Q300's note either way; r26-sa0 retires Q126 only under H-ZX 6 of 6
  and R26-3 a.

## 5. Retire summary

If both frozen forms hold and R26-2 a, R26-3 a: Q114 and Q126 retire (2 low, 2 value points) for
~4 builder hours and ~30 min of laptop. P1 retires nothing; it makes E1104 and E1103 replay.
If either form fails, it narrows (Q114 then gains a volume candidate, a real finding).

## 6. R26 decisions

1. **R26-1 The tool package.**
   - a) P1 = P1a + P1b, one agent, offline, branch `r26-tooling` off 95445c7, its own
     `CARGO_TARGET_DIR` under the lead's named worktree (recommended: the two needs the r25
     handover names, no laptop build).
   - b) P1a only (vectors), the YUV model later.
   - c) No tool work this round.
2. **R26-2 Q114's bound: retire on the 19 bits that ran without a fault.**
   - a) Yes: if no bit makes w act, Q114 retires, the never-run and faulting bits (T0 0, 2, 31,
     T3 13, 19, 24-26, T1 size bits) stay in Q300, which already holds T0's unmeasured bits
     (recommended: R12-7 a's own rule, bounded by the safe class, the bound written in the fold).
   - b) No: r26-vol only narrows Q114; the never-run bits wait for a flagged stage with the
     user's OK.
   - c) Do not run r26-vol.
3. **R26-3 Q126's extension clause.**
   - a) Retire it as not observable: under E498's measured flag rules both extensions give the
     same flag for every pair (section 2.2); with H-ZX held out on one writer, Q126 retires
     (recommended: the R6-6 a precedent, and here the argument is arithmetic, not a guess).
   - b) Keep it open: r26-sa0 only narrows Q126.
   - c) Do not run r26-sa0.
4. **R26-4 E722 in the sim (P1c).**
   - a) Not this round (recommended: no retirement, P1 stays ~4 h).
   - b) Add it to P1 (~2.5 h more; SIM_UNMODELLED loses E722).
5. **R26-5 Q179's PVRTC decoder (X1).**
   - a) Not tonight; the user rules on a citable layout source first (recommended: clean room).
   - b) Plan it for the next tools round now.
6. **R26-6 A stage on sa kept across jobs (X2, Q129 narrow).**
   - a) No (recommended: it narrows only, and E484's "kept one job" against E1104's post hoc
     "registers a job does not write keep earlier values" needs its own frozen design).
   - b) Add 4 jobs to r26-sa0: a douta to sa40, a job writing sa0-15 only, a reader of sa40
     (H-KEEP against E484's H-ONEJOB).
7. **R26-7 Q146 and Q194 (near duplicates since 2026-11-09).**
   - a) Leave both for the user's housekeeping (recommended: a merge is not an answer and the
     user deferred it twice).
   - b) Merge Q194 into Q146 at P1's fold (one fewer open, a fold, not a retirement).
