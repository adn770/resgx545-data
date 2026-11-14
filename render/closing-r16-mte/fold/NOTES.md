# r16-mte fold notes (2026-11-14, after the run)

Attempt `out/20261114-093233`, rc 0, no stop, fault or hang (15 jobs). The frozen scorer re-run on
the kept files is byte-identical (`fold/reproduce.sh`). Logs: `fold/run-r16m.log`,
`fold/stage-r16m.log`.

Record: E1060 rclip (Q116).

## Verdicts (frozen scorer, as printed)

Both controls passed (g-clear-64, E348's clear clip of the whole 64 x 64 target: 4096 of 4096
0xff00ff00, equal to its no-clip twin g-twin-64). H-TILECLIP + H-BG + H-EN held on 13 of 13
held-out rows. Of the 54 combinations of form, outside and enable, one is left by every row:
TILECLIP+BG+EN (`READING rclip`); `RETIRE rclip: yes`. No pixel read the sentinel 0xdeadbeef or a
fourth value. s128-tri read 1728 object pixels, inside the frozen map's 1633 sure and 189 edge
pixels.

## Retirement (R16-6 a, the lead confirms)

Every open clause of Q116 is decided by held-out rows with passing controls: the clip drops whole
tiles for the object (no partly covered tile: H-PIXEL refuted on every partial row); its bounds
are inclusive (H-EXCL refuted); rows count from memory row 0 (H-FLIP refuted, README.md Deviation
1); bit 31 clear turns it off (H-ALWAYS and H-OFFDROP refuted on e128-off); outside the kept tiles
the background object writes the pixels (H-UNTOUCHED refuted). "Objects and clears alike": a
full-target object under E348's clear clip reads as the no-clip image, the background behaves as
everywhere else [infer]; "beyond a scissor": tile granularity only, the closed driver's mask
fills (E340) are its own way to cut inside a tile [infer].

## Sim and vectors

sgx-pipe `mte.rs`: `RegionClip`, `region_clip`, `keeps`, `clipped` (unit tests written first),
and `state()` refuses a 0xdfc3 block naming E1060 (the TA's region lists under a clip were not
dumped). `crates/sgx-pipe/tests/mte_region_clip.rs` replays the kept images, every pixel
(the default triangle's coverage by `isp::Tri::covers`, E606). The vectors table
`vectors/closing/r16-mte/pixels/rclip.table.json` names it as its replay.
