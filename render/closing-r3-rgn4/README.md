# R3-rgn4: the laptop check of the 4x render contexts (decision D3, 2026-11-11)

Round 3 of the resgx545 question-closing pass. A short laptop check of the linux fork's commits
11 and 12 (a 4 MiB TA-data slot; the render-context flag `DRM_SGXFIVE_CTX_RENDER_AA_4X`, which
gives a context four region-header arrays, and the debugfs `render_rgn_arrays`, 0 automatic,
1, 2 or 4 forced). Questions: Q140 (four arrays, E729's 4x fault) and the 4x layout at
4096 x 4096.

**This is not a frozen session.** There is no `FROZEN.sha256`, no `PREDICTIONS.sha256` and no
scorer. The predictions are the section "Laptop check proposal" of `rgn4-REPORT.md`, the report
of the series, copied here byte for byte (sha256
`60ed3543c0d7c9aab41559a9453e5fad57db06cd4f481a1b135a6d8950491c0a`). Its file time on the Mac is
2026-11-11 05:09:42, before the laptop was booted into the new module (07:16); that rests on a
file time and the author's word, not on a hash written before the run. The outputs were read by
hand against the proposal after the run.

## Environment

- Laptop `cedar`, kernel `7.3.0-resgx545`, booted 07:16; KUnit 14 suites with no "not ok", health
  ok before the first job.
- Module `gma500_gfx.ko` from the fork's branch `resgx545` at
  `a2788bd86537fe8de22a37c2b61b9f48408b71a5`, built on the build host (cachix,
  `~/src/linux-sgx-rgn4-deliver`, debug option on, `LOCALVERSION=` as round 3); srcversion
  `99CD90DA26E3AFF9C450517`, loaded = installed; sha256
  `68ca2d56f83b8f3702d890ccf3b91208823528d0b2bf13009528229e8486797a`.
- Tool `~/sgxfive-test-rgn4`, built from resgx545 `r3-rgn4` at `4623753` (libsgxfive: create
  render contexts for 4x targets), sha256
  `e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a`.
- Stock firmware; no firmware task of ours.

## Layout

- `rgn4-REPORT.md`: the report and its proposal (the predictions), as written before the run.
- `run/rgn4-check.sh`: the runner, as kept after the session. Each job writes debugfs `reset`,
  then `render_rgn_arrays` and `hold_recovery`, marks the kernel log, runs the tool and keeps
  the tool's output (`.out`) and the kernel-log slice between the marks (`.kmsg`).
- `out/rgn4/`: the outputs of every job run, the failed first runs included. The two dumps kept
  (`j1r`, `j6r`) are gzipped (`gzip -9n`); `out/raw.sha256` gives each raw file's path, size and
  sha256 before compression.

## Jobs

`S4X` is E824's word set: `--poke cmd:1=0xe0000000 --poke cmd:10=0xeaa26e26 --poke
cmd:13=0x80000002 --poke cmd:16=0xeaa26e26`. Order run: j5, j1, j3, j6 (case 1), j1r, j6r (case
1r), j2 (case 2), j4 (case 4).

Each job: name, the proposal's job number, `render_rgn_arrays`, the command, the outcome.

- **j5** (5; 0): 1024 x 768, `-n 1`, 1x. rc 0, hash `0xc9e301d225fe2325`, 0 of 786432 wrong,
  `207456 triangle, 578976 background, 0 other`, 1 render ok: E827's `ctl-u-1024-n1`.
- **j1r** (1; 0): 288 x 144, `--aa4`, S4X. The tool printed "render context made for 4x
  targets"; 0 of 41472 wrong, hash `0x4a61860dcb4ab325`; TA data 0x8000 bytes (sha256
  `d3741578...`).
- **j3** (3; 0): 288 x 144, no `--aa4`, S4X. `rejected (Invalid argument)` at submission; no
  fault in the kernel log.
- **j6r** (6; 1): 256 x 160, no `--aa4`, S4X. Hash `0x845a011c4fbf2325`, 0 of 40960 wrong; TA
  data 0x6000 bytes (sha256 `eaa6c96c...4372992`).
- **j2** (2; 1, `hold_recovery` Y): 288 x 144, no `--aa4`, S4X. BIF fault `0x90004` at
  `0x20006061`, recovery held; the tool: `Timer expired`, 41472 of 41472 wrong.
- **j4** (4; 0): 4096 x 4096, `--aa4`, S4X, `--keep-overflow`. Context created ("made for 4x
  targets"); the job faulted (`job faulted, context lost`), BIF fault `0x90100` at
  `0x10000011`; 15728640 of 16777216 wrong (1048576 right), the first wrong at (1024, 0).

Byte comparisons made after the run, against resgx545-data:

- j1r's target hash, diff, triangle counts and both dumps (`tri.param.bin`, `tri.tadata.bin`)
  equal E824's h1 (`render/closing-r3k-pixel`, k-f4, `h1-288x144-k4`, knob 4).
- j6r's target hash, diff, triangle counts and both dumps equal E827's row `ctl-a1-256x160-tee0`
  (`render/closing-r3k-regress`, rg-ctl), run there on the round 3 module at its default of one
  array.
- j5's lines equal E827's row `ctl-u-1024-n1`.

Against the proposal: jobs 5, 1, 3, 6 and 2 came out as written. Job 4's proposal expected the
creation to succeed and a TA data dump of 0x223000 bytes, and left the render's outcome open:
the creation succeeded, the render faulted and no dump was written, so the TA data size at
4096 x 4096 was not measured.

## Not in the files

- Health checks, from the operator's notes (no output kept): after j2's held fault (the fault read,
  `hold_recovery` back to N, `render_rgn_arrays` back to 0, a debugfs `reset`), one health
  triangle failed and the next passed; after j4, health ok 3 of 3.
- The read-backs of the knobs after each case ("knob back") went to the terminal only.
- j4's dump directory was created by the runner and stayed empty; git keeps no empty directory.

## Disclosures

- The first runs of j1 and j6 (`j1-aa4-auto`, `j6-forced1-tee0`) rendered and then failed at
  `--dump-render` (`Permission denied`; the operator: not run as root, directory missing). Their
  outputs are kept. Both jobs were rerun as `j1r` and `j6r` (case `1r`), with the same command
  lines.
- The kernel-log slices of `j1r` and `j6r` hold two start/end pairs each (about 110 s and 130 s
  after boot): case `1r` ran twice. The kept `.out` files and dumps are those of the second run;
  the first run's outputs were overwritten and are not known.
- `rgn4-check.sh` is the runner as kept at the end, case `1r` included.
