# N3d: the emit's word or its pass (design note, not built, not run)

Status: a design for the lead to bring to the user as a **flagged decision**. Nothing here is
built, committed, staged or run; no laptop was touched. Tags: **[HW]** measured, **[RE]** our
reading of the firmware as the records give it, **[sim]** fwsim/sgx-sim, **[infer]** reasoning,
**[post hoc]** read after a run, not frozen.

Paths: `R` = `/Users/jtorra/src/resgx545` (main dbf0657), `F` = fork `/Volumes/linux/linux-sgx`
at r38-kernel e1cf9d2b43ab, `drivers/gpu/drm/gma500/sgxfive/` (read with `git show`; the checkout
is on another branch), `C` = `/Users/jtorra/src/scratch/resgx545/closing29`. Module on the laptop:
srcversion 88ADCEB5AD9F055D077A99C, arm words `slots/entry/trc/pds=v1|crumb|halt|crumb3/
pdsat=own|fw14` (`F/sgxfive_owntask.h:196-198`).

## 0. Where N3c left it

- The stop needs the emit (E1151, `R/doc/isa/content/usse/groups/emit.md:62-65`) [HW].
- A PDS `movs tim` is the host's 0x0acc (E1152, `emit.md:54-61`) [HW], so B-1 stands: the emitted
  program never ran its first instruction (E1150) [HW + infer].
- R5 `H` (`C/r38-n3c-s4/out/20261119-112618`, kernel.log: `emit image 0x30022000 ... pds=halt
  pdsat=own`): a lone `halt` on our page, same stop (H-STOP) [HW, unfolded].
- R4 `M` (`C/r38-n3c-s3/out/20261119-112717`, kernel.log: `emit image 0x30011100 ... pds=crumb3
  pdsat=fw14`): crumb3, 3 rows, control 0x01800100, in #14's own page, same stop (M-NEVER)
  [HW, unfolded].
- So the program's instructions, its page and PTE flags, its rows field and its control word
  are not the cause. What is left is the emit itself and what surrounds it.

## 1. The remaining variables, measured against inferred

**V4. The emit word and its operands.**

- *V4a, `s2`'s value.* Ours is 0: the kernel writes `pds2` = 0 (`F/sgxfive_owntask.c:767`), and
  the verifier pins r2-r4 to the kernel's values on every path to the emit
  (`F/sgxfive_owntask.c:64, 264-273`), so no blob can change it. The firmware's #14 `s2` is
  nonzero in the sim: E1130 reports the emit "with ir0 0x00020000" (`R/evidence/edm/E1130-*.md:
  27-28`) [sim], and sgx-sim takes `ir0` from `s2` (`R/crates/sgx-sim/src/sgx.rs:760-783`), so
  that is `s2`'s value [sim, infer]. The request it names is the TA pick, 0x20000
  (`R/evidence/edm/E154-*.md:29`) [RE]. For client emits `s2` 0, 1, 0xFFFFFFFF and 0xE17D0001
  changed nothing seen and `s2` was **not** `ir0` (E488, `emit.md:38-40`) [HW]. From the EDM,
  only `s2` = 0 has been tried [HW]. Prior: low (a lone `halt` ignores `ir0`), but it is the one
  operand value we know differs.
- *V4b, the word's other fields.* Ours is exactly `emitpds.tasks.taske #0, r2, r3, r4, #0x0` =
  0xfb20b00000008184 (`C/kernel33/design.md:27-31`), "the firmware's form" by its flags. Which
  fields of the firmware's three words were compared is not in our records: E146 read the
  instruction that starts #14 for its operand **order** only (`R/evidence/edm/E146-*.md:69-73`,
  [infer]); `emit.md:72-73` says "three `emitpds`, all `.tasks.taske`". `#incp`, the 14-bit
  sideband, the source banks and register numbers, `.nosched/.end/.freep` and the predicate of
  the firmware's #14 word are **not recorded** [open]. SGX545 has two PDS pipes (the `.0/.1` of
  `mov16/mov32`, pds_isa); whether a field of the emit names one is [open].
- *A spec inconsistency found here.* sgx-sim's rule `ir0 = s2` cites "hw_spec 11.2"
  (`R/crates/sgx-sim/src/sgx.rs:760-761`), but `R/doc/specs/hw_spec.md:890-904` states no such
  rule, and E488 measured the opposite for client emits. E1130's "ir0 0x00020000" is therefore
  `s2`'s value [sim] and its being `ir0` is [infer]. The lead should fold this (cite E146's
  operand-order reading, tag it [infer, EDM only]).

**V5. The issuing pass and what the firmware does around its emit.**

- *V5a, the pass's event.* Ours is a timer pass: our task emits on the first pass of slot 0 that
  sees cmd 1 (`R/asm/fwtask/emitsb.s:9-14, 23-37`); with no job that is a tick, pa0 = 2,
  pa1 bits 23:0 = 0 (E746, `R/evidence/edm/E746-*.md:40`) [HW]. The firmware posts #14 from
  non-tick passes: the event task's `pa1` bits and the routines of E154's table
  (`E154-*.md:19-35`) [RE], and the render kick pass of E1130 (pa0 0, pa1 0x02000100,
  `E1130-*.md:22`) [sim]. Whether any tick pass posts #14 is not in our records [open]. A host
  GETMISCINFO kick reaches slot 0 as one non-tick pass, pa0 = 0, pa1 bits 23:0 = 0x100 (E746,
  3 of 3, with a task of ours armed in all four slots) [HW].
- *V5b, before the emit.* On the kick path the firmware reads and writes CR_BIF_CTRL (0x8, then
  0), writes CR_CACHE_CTRL 0x1000ffff, spins with no count on CR_EVENT_STATUS until bit 26,
  writes 0x04000000 to CR_EVENT_HOST_CLEAR, then emits (`E1130-*.md:22-30`) [sim, replayed
  order]. The post routine itself reads TA3DCtl dword 31, ORs the request in, writes it back and
  skips the emit when nothing changed (`E146-*.md:69-73`, `E154-*.md:12-14`) [RE]. Whether
  **every** post site has an invalidation before it (the event-task posts of E154 suggest not)
  is [open]. Our task fences (`idf drc0, bif; wdf drc0`) and emits (`emitsb.s:32-37`); it can
  write CR_EVENT_HOST_CLEAR (`R/tools/fwtask/regs.toml:13-15, 87-91`) but not CR_CACHE_CTRL or
  CR_BIF_CTRL (default deny) nor read CR_EVENT_STATUS (deny `regs.toml:109-112`).
- *V5c, after the emit.* Ours: X0, a fence, the tail call into the closed general task, which
  ends the pass (`emitsb.s:38-42`). The firmware's: tasks end through the shared routine 0x1974,
  "a cache flush and the end of the PDS task" (`E154-*.md:41-42`) [RE]; what the kick pass does
  between its #14 emit and that end is in fwsim's kept run but not in any record (E1130 stopped
  at #14's `tim`; E1133's rerun with a seeded count went past it into #14's task,
  `R/evidence/platform/E1133-*.md:39-45`, `R/crates/pysgx/tests/test_fwsim_m2.py:174-183`) [sim].
- *V5d, the code that issues.* Ours runs from our page (KERNEL_CODE + 0x20000,
  `F/sgxfive_owntask.h:24-27`). Renders ran exact with tasks of ours armed in all four slots and
  tail-calling the closed ones (E864, E918: `slots 0xf`, method fields) [HW], and every render
  needs #14's task to pick the TA (`E154-*.md:29`) [RE]; so a pass that **starts** at our page
  does not block the firmware's own emit later in that pass [infer]. Only the emit **issued by
  our code** fails. That leaves V4 and V5a-c, not the page the task started from.

**V6. The stop's clock (not a cause; open since N3c).** Δtick 10 in E1149 and E1150
(`E1149-*.md` "TICK", `E1150-*.md` "TICK") [HW]; HostCtl dword 5 = 10 is the recovery sample
rate and the lockup path came at 2 x dword 5 (`R/doc/specs/hw_spec.md:1031-1043`) [HW]. Our stops
leave no lockup marks [HW]. The tick routine reads dword 5 (`R/doc/specs/edm_dataflow.md:304`)
[RE]; what that sample reads on the hardware is [open] (O2e).

**Residual, low prior.** An image at a **page-aligned** address in a **firmware** RW page has not
been tried (R5: aligned, our RO page; R4: +0x100 in #14's page). A client program at +0x40 ran
(E488, `emit.md:29-32`) [HW], so alignment is unlikely [infer]. Not a row here (§5).

## 2. Offline first (no laptop)

All of O1 and O2 read the stock firmware: **data-private trace work** under the fwsim terms T1-T4
(`C/fwsim/plan-fwsim.md` §0): working files only in `resgx545-data-private/firmware/fwsim/`, facts
only (register, value, order, count, field equal/different) reach a record or spec, the reader
never writes resgx545-fw, no clean-room paths. Not to be done by an agent that will write
resgx545-fw.

- **O1 (static, as E003/E146 did: our `usse-dis` at the three emit sites only).** For each of the
  firmware's three `emitpds` words (after #11's, #12's and #14's patched `mov`s, instructions
  past 430, 440 and 5986, `R/doc/specs/fw_format.md:198-206`): report, field by field against
  0xfb20b00000008184, equal or different for `#incp`, sideband, `.nosched/.end/.freep`,
  `.tasks/.taske`, predicate, the bank of each source; and for #14 which value `s2` carries
  (the dword-31 request, the OR's result or something else). Output: a fact table of
  equal/different, no words, no text. **If the user's clean-room line excludes even this static
  read, skip O1 and take the same facts from O2a** (field values are not in a trace; then O2a
  gives only the operand values, and V4b stays open into §3.2).
- **O2 (fwsim; the replayed kick of E1130/E1133, fixture `replayed` of
  `R/crates/pysgx/tests/test_fwsim_m2.py`, seeds `R/tools/fwsim/seeds.toml:88`).** One run into
  `firmware/fwsim/n3d-kick/` (run.toml, facts.txt, trace.jsonl.gz). Facts to extract:
  - O2a: the #14 emit's `s0`, `s1`, `s2` values (expect 0x01800100, #14's address >> 4,
    0x00020000).
  - O2b: everything the issuing pass does from the emit to its end: register reads and writes
    (index, value), stores (structure word), fences, spins (count of proven spins), and how it
    ends (0x1974 or not). The counts only, as E1130's "register writes in the kick pass: 4".
  - O2c: the same from the boot run (`test_sgx_boot`): after each of #11's and #12's emits, any
    spin, register write or fence before the boot task goes on.
  - O2d: the GETMISCINFO kick pass (`test_sgx_ccb` under fwsim): the number of `emitpds` in
    that pass. **K's precondition (§3.1): 0.** If 1 (the CCB reader posts #14), K would put two
    emits in one pass (client: two in a row hung, `emit.md:43-45`): K is then redesigned.
  - O2e (V6, optional): 20 ticks with HostCtl dword 5 = 10: which registers the sample pass
    reads that other passes do not, and whether it spins. Then a post-hoc read (O3) of those
    registers in the kept stop dumps.
- **O3 (public records, post hoc).** In the kept stop dumps of E1148-E1150, R4 and R5
  (`*.stop0-regs.txt.gz`, `*.snap9.regs.gz`): CLKGATESTATUS (0x20 at snap0, 0x000ccfa0 after the
  stop in E1149, `E1149-*.md` "Results") and O2e's registers, snap0 against stop. Labelled
  post hoc; it frames V6 and the K prediction's Δtick band, it scores nothing.
- **Decision gate.** If O1 or O2a shows a field of #14's word that differs from ours, or `s2`
  carrying something other than the request, the rebuild of §3.2 carries `form=fw14` as well as
  `pds2=req`. If O2b shows a spin or register write right after the emit, it joins the
  pre-emit sequence as the post-Z user decision (§3.3). If O2d gives 1, K is not run as written.

## 3. Rows, cheapest first, frozen predictions

Readings as N3c §2 and R4: page dwords X0 = 70, S1 = 84, M4 = 80-81, state; T = 0x0acc in
snap9 and the stop dump; `alive`; controls PG, E0, T0, B as R4. Image in every emitting row:
`crumb3` at `pdsat=fw14` (R4's), so each row changes **one** thing against M-NEVER. One owntask
row per stage, `#limit 0`, `on_stop = "end"`, class flagged; one stop ends a session.

The common outcome table (R4's `M` table, `C/n3c/design.md:180-187`), read the same in every
emitting row:

| outcome | T | S1 | M4, state | Δtick from the emit's trigger |
|---|---|---|---|---|
| NEVER: as R4, the change is not the cause | running | fill | fill, 0 | 8-11 |
| T1: started, stopped at the first `douta` | 0x00000000 | fill | fill, 0 | any |
| T2: stopped at the `doutu` | 0x00000200 | fill | fill, 0 | any |
| T3: `doutu` issued, entry 1 never stored | 0x005a3305 | fill | fill, 0 | any |
| E1: entry 1 started, stopped after S1 | 0x005a3305 | 0x5a5a3304 | fill, 0 | any |
| DONE: all ran | 0x005a3305 | 0x5a5a3304 | M4 + run id, 2 | any |

Any T1..DONE = **RUN** (the changed variable lets the program start). Anything else, or a failed
control: CANNOT TELL.

### 3.1 No rebuild, no boot (module 88ADCEB5, arm words as today)

**Session S1: row K, the kick-pass emit (V5a).** New blob `emitsk` = emitsb with one change in
entry 0: the emit path is taken only when cmd = 1 **and** pa1 bit 8 is set (the CCB reader's bit,
E746: a GETMISCINFO kick); every other pass tail-calls with cmd untouched. Arm `slots=0x1
entry=0 pds=crumb3 pdsat=fw14` (R4's word, already approved and run). Job: command 1, run id 1,
then (new, runner) one debugfs `miscinfo` read (a GETMISCINFO kick, `R/tools/fwtask/
fwtask_run.py:201-205`), HostCtl dword 12 read at the kick; `ticks` on; timeout 200 ms.
Extra controls: **K0** before the kick: cmd still 1 and slot 1 still fill (the ticks did not
emit); **K1** after: slot 1 = M1 + run id, cmd 0 (the gate fired on the kick pass). The
`miscinfo` answer (or "no MISCINFO_READY") is printed, not scored. Δtick from the kick.

| outcome | meaning |
|---|---|
| K-NEVER (lean [infer]: nothing ties the PDS to the event) | not the timer pass: V4 or V5b/c |
| K-RUN (any of T1..DONE) | the pass's event decides: an emit works from a kick pass |
| CANNOT TELL: K0 or K1 fails (no kick pass seen, or a tick emitted) | |

What it needs: blob (gen_blobs), runner `kick` step (kit), scorer. No kernel change: the module's
verifier sees the same emit with r2-r4 pinned; a pa read and a predicated branch are already in
accepted blobs (emitsb's entry 1, E600/E601).

**Session S2 (optional, V6): row D, the clock.** emitsb, `pds=halt` (no `tim` in the image),
debugfs `timer_clock` = 800000 (`F/sgxfive_debug.c:2327`), as N3c R3 (`C/n3c/design.md:156-165`)
with halt instead of v1. D-COUNT: Δtick 9-11 at 485-499 Hz; D-TIME: Δtick 4-6. Kit knob only.
Run after K, only if the lead wants V6's answer for the record.

### 3.2 One module build and one one-shot boot (only after K-NEVER)

Fork change (one build): own_arm word `pds2=0|req` (req = 0x00020000, E1130's value; closed
list, the kernel writes it into the `pds2` slot at `F/sgxfive_owntask.c:767`), and, only if O1
found a differing field, `form=own|fw14` (a second allowed `emitpds` word: #14's fields with our
r2-r4; generated by `R/tools/fwtask/gen_verify.py` into the verifier table). Blobs unchanged
except that `form=fw14` needs `emitsb`/`emitsk` built with that word (gen_blobs variant).

**Session S3: row Z, the full mirror** (`emitsk` + kick, `pds=crumb3 pdsat=fw14 pds2=req`
[+ `form=fw14`]). Everything we can mirror of the firmware's #14 emit at once.

| outcome | meaning |
|---|---|
| Z-NEVER | the word, `s2`, the pass, page, rows and control are not it: V5b/c (§3.3) |
| Z-RUN | `s2` (or the form) decides, alone or with the kick pass: run S |

**Session S4 (after Z-RUN): row S, the operand alone** (`emitsb`, tick pass, `pds=crumb3
pdsat=fw14 pds2=req` [+ `form=fw14`]). S-RUN: the operand/form alone; S-NEVER: it takes the
operand **and** the kick pass. If O1 found a field difference and Z ran, a fifth session splits
`pds2` from `form` (same table).

### 3.3 Not designed here (a user decision after Z-NEVER)

The firmware's pre-emit sequence (CR_CACHE_CTRL bit 28, a spin on CR_EVENT_STATUS bit 26, the
bit-26 clear) and whatever O2b finds after the emit. Mirroring it means verifier deny rows
opened (`regs.toml:109-116`, "PDS cache events") and a countless spin in our task: a new risk
class. O2b and O1's per-site answer (does every post site invalidate first?) decide whether it
is worth asking.

### 3.4 What needs what

| row | session | new blob | kit change | rebuild + boot |
|---|---|---|---|---|
| K | S1 | `emitsk` | runner `kick` step, scorer K0/K1 | no |
| D | S2 (opt.) | no | owntask stage knob `timer_clock` (N3c W3) | no |
| Z | S3 | none, or `form` variants | arm words `pds2`, `form` | **yes, one** |
| S | S4 (cond.) | as Z | as Z | same build |

## 4. Risk, recovery, work list, time

**Recovery.** Every owntask emit stop so far (E1148-E1150, R4, R5: 5 of 5) and 13 of 13 earlier
EDM stops were recovered by the kit's debugfs reset; a failed reset (rc 13 or 5) means the
user's ordinary reboot to the default entry.

- **K.** Our words in #14's page as R4 (approved, run; the disarm reset zeroes the slack, KUnit
  `fw14_disarm`). New: our emit sits in the GETMISCINFO pass before the closed handler; if that
  pass is spoiled the reply may not come (the kernel's `miscinfo` read gives up at 500 ms,
  `F/sgxfive_debug.c:172-186`) and an unanswered command stays in the kernel CCB until the reset
  rebuilds it [infer]. A GETMISCINFO with a task of ours armed is E746's own method [HW]. Two
  emits in one pass are excluded by O2d. If the program runs, T1 stops the tick by design (as
  R4's approved image).
- **D.** As A; the knob is restored before the kit's last reset (the firmware copies it at boot).
- **Build.** No clock-gate path is touched; the one-shot boot as `C/kernel33/deliver-laptop.sh:
  17-20`, only with the user's OK; a bad boot falls back to the default entry.
- **Z, S.** As R4 and B. `s2` = 0x00020000 is E1130's request word; our image ignores `ir0`. If
  `s2` were consumed as a request by something other than the program, a stock task could run on
  an empty TA queue [infer: low; #14 would have to be the program run, and it is not ours].
- **Within the rules.** No clock-gate write, no `trc_hazard`, no `trc=`, no GRUB edit beyond the
  one-shot boot, every owntask stage flagged, one stop ends a session.
- **Main risk**: K's emit inside a host-command pass (a stuck GETMISCINFO at the stop); Z adds a
  second allowed emit word to the verifier if O1 asks for it.

**Work list (tests first, red then green).**

resgx545 (branch off main dbf0657), no rebuild:

1. `tools/fwtask/gen_blobs.py` `gen_emitsk()` and the map entry. Tests beside
   `tools/fwtask/test_emitpds.py`: one `emitpds`, reached only on the path where cmd = 1 and the
   pa1 & 0x100 test is set; on every other path cmd is not stored and the tail call follows;
   M1/X0/S1/M4 offsets as emitsb; `fwtask.refusal(...) is None`; lint clean; the
   `and`/`testtanz` with #0x100 assembles and disassembles round trip.
2. The fork's verifier on the Mac (`C/kernel33/kunit-shim/run.sh` against e1cf9d2b43ab, no
   build): `emitsk` accepted (as a23cfdd listed `emitsn`).
3. `fwtask_run.py one_cmd`: a job key `kick: "miscinfo"`, done once right after the command
   write, recording dword 12, cmd and slot 1 just before it and the reply line. Tests in
   `tools/closing/test_kit.py`: argv order on the fake laptop (arm, fill, cmd, K0 read, kick,
   poll), `kick` refused outside an owntask flagged stage and for any other value.
4. Scorer: R4's table plus K0/K1 and Δtick from the kick; tests on R4's kept attempt (as a
   K-NEVER shape with K0/K1 fabricated) and a fabricated DONE.
5. Session `r39-n3d-k` (`tools/closing/new_session.py`), predictions frozen.

Fork + resgx545, only after K-NEVER (one build):

6. KUnit: `pds2=0|req` parsed (others refused; refused without an emitting blob); the apply
   writes 0x00020000 in the `pds2` slot; `own_arm` shows it; the log names it. If O1 asks:
   `form=own|fw14`, the second word accepted only with `form=fw14`, every other `emitpds` still
   refused.
7. `gen_verify.py` (table) and the kit's arm-word list; sessions `r39-n3d-z`, `-s`.

Offline: O1, O2a-d before K is frozen (O2d gates K); O2e and O3 any time.

**Laptop time.** K: about 15 min, no build. D: about 10 min. The build: about 45 min unattended
plus 15 min install, one-shot boot and srcversion checks. Z and S: 10 min each. All rows: about
1 h 35, about 45 min attended; K alone: 15 min.

## 5. Rejected alternatives

- **Emitting the firmware's own #14 (address, control) from our task.** H-STOP and M-NEVER already
  say the program does not matter; it would also start a stock task out of its protocol.
- **Tail-calling into the closed post routine (0x1756) to make the closed code emit for us.**
  A new continue target (rebuild) and a real request on an empty queue; and the closed emit is
  already known to work (V5d).
- **Mirroring the cache invalidation now.** Deny rows and a countless spin; only after Z-NEVER and
  O1/O2b (§3.3).
- **CR_EVENT_HOST_CLEAR bit 26 alone before the emit** (allowed today): without the invalidation
  the bit is not set, so a no-op on any reading [infer]; a row that cannot separate anything.
- **`s2` from a blob.** The verifier pins r4 (`F/sgxfive_owntask.c:264-273`); loosening it lets a
  task emit any operand.
- **K with v1 on our page** (B's job moved to a kick pass). Cleaner if it runs (no planned stop),
  but it changes two things against R4 and cannot tell "never started" from "stuck at a `douta`".
- **An aligned image in a firmware RW page** (the residual of §1): needs a placement word and a
  free firmware page; low prior after E488's +0x40 client run.
- **fwsim for the stop itself.** sgx-sim starts an emitted program at once and has no PDS stall
  (`C/n3c/design.md:323-324`); it would read DONE.
- **Several rows in one session.** Every emit row so far stopped, and a stop ends the session.
