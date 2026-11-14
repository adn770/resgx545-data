# r16-zls preflight (the lead, before staging)

1. Module B60AB0B475DD1E8972419B5 loaded and installed (the kit checks both); no knob is used.
2. `~/sgxfive-test-t10` is sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb
   (built by `lead/build_tool10.sh` from a581c06; the kit's stage checks it). FROZEN.commits
   carries its `built` line (recipe data:render/closing-r10-st1/lead/build_tool10.sh).
3. `~/scratch/r16z/` absent or empty; at least 300 MiB free on `~` (zb4-20-640 dumps 316 pages,
   about 1.3 MB raw, small gzipped).
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again (verifies the freeze).
5. Runs first in the sitting (R16-1 (a): zls, usse, tex, mte, tw); log to
   `closing16/logs/run-r16z.log`. No fault is planned: a fault stops the session (4), with
   recovery and strict health by the kit.
6. OQ069 (README "Offline gate OQ069"): H-LIN passed the gate outside BEND only and H-POLYCLIP
   failed it; the lead confirms keeping zoff (else drop stage zoff from session.toml before the
   freeze: zpass2, zbits4 and zovp do not depend on it).
7. First pokes of their kind: zb4-23-bg writes render-details dword 17 (CR_ISP_BGOBJVALS) to 0x35a
   (t10's 0x300 with the STENCIL byte 0x5a; bits 8 and 9 kept), the last row of zbits4; zw2-s75
   and zw2-w0 bring a vertex depth of -0.5 after the viewport (the kept rows reached -0.375), the
   last rows of the session (zoff, `on_stop = "end"`). The library mock replays all 49 rows with
   none refused.
8. zb4-20-d12 assumes t10 maps the depth buffer at 0x3e001000 (base 0x3e000000) and the 20-page
   store at 0x3e015000 (E1042's zb2-d12 printed these; hook_check stops zovp otherwise).
