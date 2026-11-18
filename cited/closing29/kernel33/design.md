# N3: one emitpds form in our own firmware tasks (design note)

User decision 2026-11-16 (answer b): allow ONE `emitpds` form in our own firmware (EDM) tasks,
so that a safe session can measure where an emitted PDS program's `douta` writes land: in the
primary attributes (`pa`) or in the secondary ones (`sa`) of the task it starts.

## 0. Why

- fwsim's M2 kick (main 5745c8d, E1130, E1133) runs PDS #14 from the kick pass's `emitpds`.
  PDS #14 passes `ir0` and `tim` on with `douta` to the destination words 0 and 0x200 (E146),
  that is attributes 0 and 2 (`douta` names its attribute in bits 19-8 of its second word,
  `doc/specs/pds_isa.md` §3.4). sgx-sim puts an emitted program's `douta` in the secondary bank.
  The run then stops on a memory fault at 0x0002007c in the task PDS #14 starts (E1133). That is
  `0x00020000` (the request word E1130 names) plus 0x7c, dword 31 of TA3DCtl, which the firmware
  reads through `sa0` (E146) [infer]: the sim's `sa` landing replaced the TA3DCtl pointer.
  No hardware row says where an emitted `douta` lands (E1133, "What it does not show").
- A program PDS #13 starts from an event passes its words with `douta` to 0, 0x100 and 0x200,
  and a task of ours in the general slot sees them in `pa0`-`pa2` (E146, E532): for the event
  path the answer is `pa`. The emitted path is the open one.
- A client `emitpds` faulted or hung every job (E488 24 of 24, E520 39 of 39; Q128). The
  firmware's own three `emitpds` run on every boot and kick. So the form to allow is the
  firmware's (`.tasks.taske`, its control-word rule and its address rule, from an EDM task),
  with a program and a started task that are ours.

## 1. The allowed form (exactly one)

**The word.** `emitpds.tasks.taske #0, r2, r3, r4, #0x0` = `0xfb20b00000008184`, one exact
64-bit word (verifier row `emitpds-own`, kind `EMITPDS`, mask all bits: no other register, bank,
flag, `#incp`, sideband or predicate). It refines listing form #149 of `doc/specs/usse_isa.md`
(`gen_verify.in_spec`). `s0` = r2, `s1` = r3, `s2` = r4 (E488's operand order). Every other
`emitpds` word stays refused as an unknown form.

**The operands are the kernel's.** A new patch kind `pds` (blob kind byte 3, slot 0-2, addend 0)
on an unpredicated `mov rN, #0xdeadbeef`, written by the kernel at the arm:

| slot | operand | value the kernel writes | rule |
|---|---|---|---|
| `pds0` | `s0`, control | `(2 << 23) \| 0x100` = `0x01000100` | `PDS_CTL`: 2 data rows, addend 0x100 (fw_format §4; PDS #14's and #12's addend; E488's base; E520: 0x100 started the program 11 of 11) |
| `pds1` | `s1`, address | `pds_addr >> 4` | `ADDR_SHR4` of the image (fw_format §4: the firmware's `emitpds` address rule) |
| `pds2` | `s2` | `0` | E488: `s2` 0, 1, 0xFFFFFFFF, 0xE17D0001 changed nothing seen; 0 is the least |

The verifier tracks these values in its base analysis (states `0xfff0 + slot`, beside a results
page offset and unknown): on every path to the `emitpds`, r2, r3 and r4 hold `pds0`, `pds1`,
`pds2`, not written since. A `pds` register used as a load or store base is refused as today
(its state is not a page offset).

**Once per task run, never from the task it starts.**

- At most one `emitpds` word in a blob (`EMIT_ONCE`).
- No path from the word after the `emitpds` reaches it again (no loop), and no path from entry 1
  (the started task's entry, below) reaches it (`EMIT_ONCE`).
- A blob with the `emitpds` has at least two entries (`EMIT_ENTRY`): entry 1 is where the image's
  `doutu` starts.
- The task source gates the emit on the tester's command and clears the command before the emit
  (section 3), so one tester command gives one emit; the verifier does not enforce that part.

**The program image (one, fixed, the kernel's).** `asm/fwtask/pds_emit.s` (ours, `pds-asm`),
written into the kernel as `sgx_own_pds.h` by `tools/fwtask/gen_verify.py` (as `gen_tri_progs.py`
writes `sgx_tri_progs.h`): 2 data rows (8 dwords), then 4 instructions, 48 bytes.

```
dword 0 ds0[0] U0      (kernel: 0x0800000f | (0x4000 + e1) << 4, e1 = entry 1's index)
dword 1 ds0[1] U1      0
dword 2 ds1[0] U2      0
dword 3 ds1[1] 0x000   douta control: attribute 0
dword 4 ds0[2] V0      (kernel: TA3DCtl dword 0 as the loader built it)
dword 5 ds0[3] V2      (kernel: TA3DCtl dword 2 as the loader built it)
dword 6 ds1[2] 0x200   douta control: attribute 2
dword 7 ds1[3] 0
        movs douta, ds0[2], ds1[1], ds0[2], ds0[2]     ; V0 to attribute 0
        movs douta, ds0[3], ds1[2], ds0[3], ds0[3]     ; V2 to attribute 2
        movs doutu, ds0[0], ds0[1], ds1[0], ds0[0]     ; start our entry 1
        halt
```

- The `douta` targets are PDS #14's (attributes 0 and 2, E146), so the answer is the one fwsim
  needs. The values are the ones `sa0` and `sa2` already hold: PDS #11's `doutd` loads TA3DCtl
  into the secondary attributes from `sa0` (E002, E003: control `0x03c0003f`, 64 dwords from
  attribute 0; `pds_isa.md`, "In the microkernel's programs"), so `sa0` = TA3DCtl dword 0 (its own
  address) and `sa2` = TA3DCtl
  dword 2 (the CCB control address). Wherever the writes land, no secondary attribute the firmware
  holds changes value: that is the safety choice, and its cost is that a landing in `sa` is not
  shown positively (section 4).
- U0 is built as the kernel builds an armed slot's word (`(trc << 24) | 0xf | index << 4`,
  `test_overlay.py`), TRC 8 (32 temporaries, what the verifier tracks), the code page's index
  0x4000 plus the instruction index of the blob's entry 1. U1 = U2 = 0: no flag. No record states
  the U1 the firmware's PDS #14 gives
  its tasks [infer: a task started with no flags runs; the session's run marker tests it].
- Placement: a page of its own, `XB_OWNPDS` = KERNEL_CODE heap + 0x22000 (beside the code page at
  + 0x20000 to + 0x21fff; the firmware's PDS programs also sit in KERNEL_CODE, at + 0x10000), 4 KiB,
  read-only for the EDM (`SGX_MMU_RO`), written by the kernel only at the arm (no debugfs write
  path), the 48-byte image at offset 0 and zeros after it.

## 2. Why it cannot reach memory we do not own (what the KUnit test checks)

1. **The emit names our image and nothing else.** The word is exact, and its three sources hold
   the kernel's values on every path (verifier, KUnit with crafted blobs). `s1` is the image's
   address, `s0` its size (2 rows) and the addend the firmware uses.
2. **The image is a constant of the kernel.** KUnit decodes `sgx_own_pds_build()`'s output and
   checks: 12 words, exactly `douta`, `douta`, `doutu`, `halt` (no `doutd`, no load or store, no
   branch, no other port); the `douta` controls 0x000 and 0x200; the values the two given; U0 =
   `0x0800000f | (0x4000 + e1) << 4` (e1: entry 1's instruction index), so the started code is our
   code page (`CBASE` 15 = the
   KERNEL_CODE heap, index inside the page's 1024 words); U1 = U2 = 0. The image page is
   read-only for the EDM and nothing but the arm writes it.
3. **The started task is verified code.** Entry 1 of the same blob, checked by the same verifier:
   its stores go to the results page only (base analysis), its code page is read-only, it cannot
   emit (rule above), its `str`/`ldr` are the allow lists'.
4. **The writes change no value the firmware holds.** `douta` to attributes 0 and 2 with the
   values `sa0` and `sa2` hold [infer: the base pointers are not rewritten after the boot; the
   kick pass reads through them, E146, E1130]. If they land in `pa`, they land in our task's
   primary attributes.
5. **One emit per run.** One word, no loop through it, not reachable from the started task.

Not covered (residual, [infer]): an `sa` landing at an offset other than the attribute number
(a per-task window) would write those two values into two other secondary attributes. The
session's health checks (tick, MISCINFO, triangles) after every job detect a broken firmware,
and a recovery reset rebuilds the stock buffers (PDS #11 reloads `sa`).

## 3. The own-task program (`asm/fwtask/emitsa.s`, generated by `gen_blobs.py`)

Results page protocol of `layout.py` (CMD dword 1, STATE 2, RUNID 3, result slots from 0x40).

- **Entry 0 (armed on slot 0, the general task; the tick runs it).** `cmd` 0: tail call to the
  closed task (`cont0`), as every source. `cmd` 1: store a marker 0x5a5a3301 and the run id in
  slot 1, store `cmd` = 0 (so the next tick does not emit again), fence (`idf`, `wdf`), set
  r2/r3/r4 from the `pds0`-`pds2` limms, `emitpds`, then the tail call (the closed task runs
  as it would have).
- **Entry 1 (the task the image starts).** Store `pa0`, `pa1`, `pa2`, `pa3` in slot 2, `sa0`,
  `sa1`, `sa2`, `sa3` in slot 3, a marker 0x5a5a3302 and the run id in slot 4, then `done`'s
  sequence (run id echo, fence, `state` = 2) and `own_end`. `pa1`, `pa3`, `sa1` and `sa3` are
  controls no `douta` writes.

Readings (the session's predictions are frozen later, not here): H-PA `pa0` = V0 and `pa2` = V2;
H-SA `pa0`, `pa2` not V0, V2 and `sa0` = V0, `sa2` = V2 (unchanged); H-NONE the entry-1 marker is
absent (the image did not start our task). Control that can fail: `sa0`/`sa2` must read V0/V2 in
every job (else the firmware's attributes changed: stop), and the slot-4 marker.

## 4. What this cannot show, and the alternative

H-SA is shown only as "not `pa`" with `sa` unchanged, since the values are `sa`'s own. A positive
`sa` landing needs distinct values in an attribute the firmware does not read, which no record
names; that would be a flagged row (a planned firmware break if wrong) and is not designed here.

## 5. The kit job kind for own-task arms

There is none: `tools/closing/kit` has no own-task row (`own_code`, `own_arm`, `own_res` are only
in `tools/fwtask/fwtask_run.py` and `run_stage.py`, the phase 11.29-11.33 runner). The runner does
what this needs today (`arm` with a blob and `slots=0x1 entry=0`, `run` with one
`cmd` per job, `reset`, `gate`), so no tool change is needed for a first session. The minimal kit
form, if the lead wants the session in the kit:

- a job kind `owntask`: `blob = "emitsa"` (sha256 from `asm/fwtask/fwtask.map`), `arm = "slots=0x1
  entry=0"`, `cmd = 1`, `params = {}`, `timeout_ms`; the stage arms once (`fwtask_run.py arm`), runs
  its jobs (`run`), and disarms with a reset at the stage end;
- the dump: `own_res` as JSON per job (the runner's `<tag>-own_res.json`), and the health gate
  after each job (`gate`);
- `kitscore` reads result slots by dword index.

The arm needs only `slots=0x1 entry=0`: entry 1 is started by the image, not by a slot.

## 6. Changes

- Linux fork (`r33-kernel` off 8bc0877e8603, red branch `r33-red`): the verifier (form row, patch
  kind, `EMIT_*` reasons, the reachability rule), `sgx_own_pds_build()`, `XB_OWNPDS`, the arm
  writing the image and the `pds` patches; KUnit first. Generated headers from the tool side.
- resgx545 (`r33-kernel-tool` off 5745c8d): `fwtask.py` (form, patch kind, reasons, rule),
  `gen_verify.py` (crafted blobs, `sgx_own_pds.h`), `asm/fwtask/pds_emit.s`, `gen_blobs.py`'s
  `emitsa`, the map, tests first; HACKING's own-task section.

## 7. As built (2026-11-16)

- Fork `/Volumes/linux/linux-sgx-r33`: `r33-kernel` = 8bc0877e8603 + b610c80be880 (the verifier's
  form, patch kind and rules; arm refused without an image) + c78059370315 (the image, its page,
  the arm); `r33-red` = ffcc222072d5 (all tests, stub implementations).
- KUnit on the Mac through `kunit-shim/run.sh` (the owntask suite in user space with
  `tools/fwtask/host/shim`): red 16/23 (`shim-red.log`), green 23/23 (`shim-green.log`).
- The runner reads the reader's slots with a job's `slots` list (`fwtask_run.py one_cmd extra`).
