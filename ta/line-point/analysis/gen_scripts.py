#!/usr/bin/env python3
"""Writes the run scripts (case tables from gen/table-*.txt, written by gen_p1131.py). From p1131/."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIC = "# SPDX-License-Identifier: MIT\n# SPDX-FileCopyrightText: 2026 Josep Torra\n"
KEPT = """# Raw outputs are KEPT: every tool output, whole, gzip (mtime 0) in $KEEP/NAME.txt.gz, the render's
# dumps beside it (NAME.param.bin.gz, NAME.tadata.bin.gz), the raw size and sha256 printed ("kept
# ..."), the case table in $KEEP/cases.tsv (with the exact tool arguments of every job) and the
# kernel log of the run (journalctl -k, as the short ring buffer loses it) in $KEEP/kernel.log.
# Recompute with recompute/recompute_p1131.py. After a failed job the GPU is reset (3 s), a plain
# 64x64 triangle must draw exactly (retry after 5 s waits); three failed recoveries stop the script.
# No clock-gate register is written (see lib1131.sh). Root through sudo -n.
"""

SCRIPTS = {
    "ta-object-format": ("Q070 (the object's format word and set masks over coordinate outputs)", """\
# One triangle with N coordinate outputs (N = 2 to 11 in sets of four and the rest), the coordinate
# size word (blk:16, 3 bits a set) and format word (blk:17, one bit a set) set, the TA's object read
# from the dump: the dwords a vertex takes, the format word's two bytes, the four set masks. Fit:
# five of E308's settings (N = 4). Held out: seven values of N with six size/format patterns each.
# Models (plan.md section 3): H70-F stored = 1 + sum of the sets' dwords (half precision halves a
# set, rounded up), iterated = 1 + N; H70-M mask i bit j for set j: format bit, size 1, size 3 or 5,
# size 4 or 5. Needs the pixel PDS program of E437 (stage-p1131.sh), as E308's csize probes did.
"""),
    "ta-line-point": ("Q070 (the region test for lines and points) and Q117 (what a point covers)", """\
# Lines (index list type 1, ISP word 0 + 0x8000) and points (type 2, + 0x18000) placed by the viewport
# words (blk:6-9: x offset, x scale, y offset, y scale; the vertex k of the first triangle is the
# offset + scale * its NDC position, the copies of --vertices moved c/16 pixel when the scale is
# W/2): 128x128 for the region lists (32x16 regions, 16x16 tiles), 64x64 for the pixel footprints.
# Lines: the landed geometry (fit), a near-horizontal segment round y = 16 and a near-vertical one
# round x = 16 and 32, each at ISP word 1 widths 0x10 and 0x40, then two and three lines in one
# object. Points: the landed geometry, 6-point boundary jobs, widths, and the footprints (pixel
# centres and corners, widths 0x00 to 0xf0 as ISP word 1 bits 15:8) with the vertex-output size.
"""),
    "ta-tri-boundary": ("Q070 (the region test's boundary rules on triangles it was not fitted to)", """\
# Triangles with a vertex exactly 2/16 pixel before a tile or region line, five copies moved 1/16
# pixel each (so the copies cover -2/16 to +2/16 round the line), at 64, 128 and 256 pixels (the
# viewport scale W/2); three controls on E180's geometry. H70-T1 (the rule fitted post hoc to
# E180's 26 triangles) is the declared prediction; H70-T0 (the landed record's) is scored too.
"""),
    "ta-tri-edges": ("Q070 (edges exactly on a tile or region line): NEEDS the --tri-v tool change", """\
# probe --tri ... --tri-v I=X,Y (vertex I of the first triangle in 1/16 pixel, the smallest tool
# change; tool-tests/test_cli_tri_probe_vertices.py fails against the 11.26 tool). The script runs
# only when the tool has the option (it asks the mock) and says so otherwise. Vertical and
# horizontal edges on the lines x = 16, 32 and y = 16, 32 and 1/16 either side, both orientations.
"""),
    "vdm-state-units": ("Q047 (which unit takes a state block: the marks of a two-block stream)", """\
# Two objects (12 vertices, --obj2 6), each with its own state block. One block carries three marks:
# its viewport x offset moved 16 pixels (the MTE side), ISP word 1 = 0x20f0 against 0x10f0 (the TA
# copies it into the object), and its own pixel shader (green, the second block's; blue the first's).
# Block 2 variant: the second block marked, word 9 changed. Block 1 variant: the first block marked,
# word 1 changed. Every field value that completed in E427 and E414, twice, a control per variant
# first: a field that names units must move some marks and not others; a size or validity field
# moves them together. A control that does not show all three marks voids the job (plan.md 5).
"""),
    "vdm-state-risky": ("Q047 (bits that hang or are untried, and attribute rows against bits 11:9)", """\
# RISKY, run last: bits 11:9 = 1, 6, 7, bits 15:13 = 0, 5, 6, 7, bit 17 and bit 25 flipped, and two
# words of the closed driver's block forms (0x0800e105: pipe 7, no partitions, bit 8, MTE emit and SD
# clear; 0x08002505: the same with E185's 1 and 2), on each block, twice, a control after each
# block's; then the second block's attribute rows (bits 7:0 = 1, 2, 3, 8) against bits 11:9 = 0 to 7,
# one run each (32). Hangs are expected; the recovery path runs after each.
"""),
    "vdm-vtask": ("Q094 (vertices per vertex task against output rows)", """\
# 126 vertices (42 triangles) with N = 2, 4, 8 and 11 coordinate outputs (2, 2, 3 and 4 output
# rows of four dwords) and the vertex task's MAX_VERTICES (vdm:6 bits 31:28) at 15 (the control and
# most GLES2 draws), 13, 9, 7, 2 (the closed driver's values), 3 and 1. The vertex program writes
# the vertex's clip x and y to o4 and o5, so the TA's object holds each vertex's identity: the
# recompute counts the 126 distinct vertices that reach the objects (H94-none: all of them).
"""),
    "vdm-vtask-risky": ("Q092 (the first trailing word's top nibble against the task's attribute rows)", """\
# RISKY: five copies (15 vertices), vdm:4 at 0xf0000000, 0xd0000000, 0x70000000 against the vertex
# task's attribute rows (vdm:7 bits 14:7) at 1, 2 and 4, the object compared with the control's
# (0xf, 1). The attribute rows beyond the vertex program's may fault or hang the job.
"""),
    "ta-risky": ("Q070 and Q117 (OUTSEL bits against the format word and the point size)", """\
# RISKY, run after the safe scripts: the OUTSEL word (blk:13) with one bit flipped at a time (bits 11
# and 12 are the known controls: the colour and 1/w bits that set format bits 19 and 18), the object's
# format word read; then, for the unknown bits, a point job whose vertex program writes the size to
# the one coordinate output (1.0 and 8.0) with that bit flipped: a bit that makes the footprint
# follow the size shows where a size comes from. Faults and hangs are expected for some bits.
"""),
}

EVENTS_TIMELINES = r'''
SCRIPT_NAME=event-timelines
. "$(dirname "$0")/lib1131.sh"
[ -x "$RT" ] || { echo "no $RT: build tools/sweep/regtimeline.c on the laptop first"; exit 1; }
PB_RESTORE=$(sudo -n cat "$D/render_pb_pages")
begin
# The two event registers alone (CR_EVENT_STATUS2 0x0118, CR_EVENT_STATUS 0x012c) at the finest
# sampling regtimeline gives, and the same with five registers of the units (0x0218 the TA's dip,
# 0x0700, 0x0710, 0x0724, 0x0748 the DPM's), through each kind of job after a reset, in turn; the
# idle control is `sleep`. Read-only (/dev/mem), nothing is written but the reset, render_pb_pages
# (0x30 for the partial render, put back at exit) and kpoke clears.
R2="0x0118,0x012c"
R7="0x0118,0x012c,0x0218,0x0700,0x0710,0x0724,0x0748"
TLPY=$(cat <<'PYEOF'
import re, sys
regs, rows, hdr = [], [], ""
for line in sys.stdin:
    if line.startswith("timeline:"):
        hdr = line.split()
        regs = [t for t in hdr if t.startswith("0x")]
    elif line.startswith("tl "):
        rows.append(line.split()[1:])
if not rows:
    print("  no timeline"); sys.exit(0)
smp = int(hdr[hdr.index("samples") + 1]) if "samples" in hdr else 0
try:
    span = (int(hdr[hdr.index("end") + 1]) - int(hdr[hdr.index("start") + 1])) / 1000.0
    print("  %d changes, %s samples in %.0f us (%.2f us a sample)" % (len(rows), smp, span, span / max(smp, 1)))
except ValueError:
    print("  %d changes" % len(rows))
for i, r in enumerate(regs):
    vals = sorted({row[1 + i] for row in rows if len(row) > 1 + i})
    orv = 0
    for v in vals:
        orv |= int(v, 16)
    print("  %s: %d values %s ... or %#x" % (r, len(vals), " ".join(vals[:6]), orv))
PYEOF
)
rt_job() { # NAME KIND REGS: reset, then regtimeline 0 0.05 REGS -- the job
	name=$1 kind=$2 regs=$3
	case $kind in
	fill) cmd="fill" ;; copy) cmd="copy" ;;
	tri64) cmd="tri --width 64 --height 64" ;;
	tri256n3) cmd="tri --width 256 --height 256 -n 3" ;;
	zstore) cmd="tri --width 64 --height 64 --depth --depth-store" ;;
	partial) cmd="tri --width 1024 --height 768 -n 2 --keep-overflow --wait-ms 20000" ;;
	idle) cmd="sleep 0.3" ;;
	esac
	reset_gpu
	if [ "$kind" = partial ]; then set_knob render_pb_pages 0x30; else set_knob render_pb_pages "$PB_RESTORE"; fi
	[ "$kind" = idle ] && prog="" || prog="$T"
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$kind" "0" "0" "regtimeline 0 0.05 $regs -- $prog $cmd" >> "$KEEP/cases.tsv"
	echo "== $name kind=$kind regs=$regs"
	mark "$name"
	sudo -n timeout 120 "$RT" 0 0.05 "$regs" -- $prog $cmd > "$W/$name.out" 2>&1 </dev/null
	echo "  rc $?"
	python3 -c "$TLPY" < "$W/$name.out"
	keep "$name" "$W/$name.out"
	if grep -qE "failed|faulted|hung" "$W/$name.out"; then reset_gpu; health </dev/null || true; fi
	rm -f "${W:?}/${name:?}.out"
}
for i in 1 2 3; do rt_job "tl-idle-r2-$i" idle "$R2"; rt_job "tl-idle-r7-$i" idle "$R7"; done
for run in 1 2 3 4 5 6 7 8 9 10; do
	for kind in tri64 fill tri256n3 copy zstore partial; do rt_job "tl-$kind-r2-$run" "$kind" "$R2"; done
done
for run in 1 2 3 4 5; do
	for kind in tri64 fill tri256n3 copy zstore partial; do rt_job "tl-$kind-r7-$run" "$kind" "$R7"; done
done
health </dev/null || true
echo "## end"
'''

EVENTS_IRQ = r'''
SCRIPT_NAME=event-irq-matrix
. "$(dirname "$0")/lib1131.sh"
PB_RESTORE=$(sudo -n cat "$D/render_pb_pages")
begin
# E444's method over ordinary jobs: after a reset one host event enable bit is written through
# debugfs kregnow (CR_EVENT_HOST_ENABLE 0x0130 = 0x4000 | bit for CR_EVENT_STATUS, CR_EVENT_HOST_ENABLE2
# 0x0110 = bit for CR_EVENT_STATUS2; kregnow_enable refuses every other offset, CR_CLKGATECTL2 among
# them), a job runs, one second later kregnow's counters ("host_irqs N extra M last S1 S2 ...": an
# interrupt with no SW_EVENT counts as extra, and puts the enables back, so one detection a run) and
# the two status registers are read. KINDS and the BITS variables restrict the matrix.
# Limits (plan.md 6): an event that coincides with the EDM's SW_EVENT (bit 14) in one interrupt is
# not counted as extra, the status word `last` shows it; bits 29 and 31 of status and bit 10 of
# status2 are set with no job (E444) and are not armed; CR_EVENT_HOST_CLEAR cannot be written.
KINDS=${KINDS:-"tri64 tri256n3 zstore partial fill copy"}
STAT_BITS=${STAT_BITS:-"0 1 2 3 4 5 6 7 8 9 10 11 12 13 15 16 18 19 20 21 22 23 24 25 26 28"}
STAT2_BITS=${STAT2_BITS:-"0 1 2 3 4 5 6 7 8 9 11 12 13 14 15"}
irq_job() { # NAME KIND REG VALUE ("" "" for the unarmed control)
	name=$1 kind=$2 reg=$3 val=$4
	case $kind in
	fill) cmd="fill" ;; copy) cmd="copy" ;;
	tri64) cmd="tri --width 64 --height 64" ;;
	tri256n3) cmd="tri --width 256 --height 256 -n 3" ;;
	zstore) cmd="tri --width 64 --height 64 --depth --depth-store" ;;
	partial) cmd="tri --width 1024 --height 768 -n 2 --keep-overflow --wait-ms 20000" ;;
	esac
	reset_gpu
	if [ "$kind" = partial ]; then set_knob render_pb_pages 0x30; else set_knob render_pb_pages "$PB_RESTORE"; fi
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$kind" "0" "0" "enable ${reg:-none}=${val:-none}; $T $cmd" >> "$KEEP/cases.tsv"
	mark "$name"
	{
		echo "case $name kind $kind enable ${reg:-none}=${val:-none}"
		echo "before: status $(rd 0x012c) $(rd 0x0118) enable $(rd 0x0130) $(rd 0x0110)"
		echo "kregnow before: $(kregnow_counts)"
		[ -n "$reg" ] && kregnow_enable "$reg" "$val"
		sudo -n timeout 120 "$T" $cmd 2>&1 </dev/null | grep -E "^(job|diff|tri|fill|copy)|failed|overflow" | head -n 4 | sed 's/^/job: /'
		sleep 1
		echo "after: status $(rd 0x012c) $(rd 0x0118) enable $(rd 0x0130) $(rd 0x0110)"
		echo "kregnow after: $(kregnow_counts)"
		echo "kernel: $(sudo -n dmesg | tail -n 12 | grep -E 'kregnow|host interrupt' | sed 's/^\[[ 0-9.]*\] //' | tr '\n' ';')"
	} > "$W/$name.out" 2>&1
	sed 's/^/  /' "$W/$name.out"
	keep "$name" "$W/$name.out"
	rm -f "${W:?}/${name:?}.out"
}
for kind in $KINDS; do
	for i in 1 2 3; do irq_job "irq-$kind-none-$i" "$kind" "" ""; done
	for b in $STAT_BITS; do irq_job "irq-$kind-st$b" "$kind" 0x0130 "$(printf '0x%x' $(( 0x4000 | (1 << b) )))"; done
	case $kind in tri64|fill|copy)
		for b in $STAT2_BITS; do irq_job "irq-$kind-st2b$b" "$kind" 0x0110 "$(printf '0x%x' $(( 1 << b )))"; done ;;
	esac
	health </dev/null || true
done
echo "## end"
'''


def table_script(name, title, desc):
    table = (ROOT / "gen" / ("table-%s.txt" % name)).read_text()
    extra = ""
    if name == "ta-tri-edges":
        extra = '''if ! "$T" --mock probe --tri pixel --tri-v 0=0,0 --tri-v 1=1024,0 --tri-v 2=0,1024 --width 64 --height 64 "$S/p1131-green__0.bin" >/dev/null 2>&1; then
	echo "## skipped: $T has no probe --tri --tri-v (the tool change of tool-tests/test_cli_tri_probe_vertices.py)"
	exit 0
fi
'''
    return f'''#!/bin/bash
{LIC}# 11.31 {name} (draft phase): {title}.
{desc}{KEPT}SCRIPT_NAME={name}
. "$(dirname "$0")/lib1131.sh"
for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do
	[ -f "$f" ] || {{ echo "no $f: run stage-p1131.sh and copy"; exit 1; }}
done
{extra}begin
TABLE=$(cat <<'TABLE'
{table.rstrip()}
TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
'''


def main():
    for name, (title, desc) in SCRIPTS.items():
        (ROOT / (name + ".sh")).write_text(table_script(name, title, desc))
    (ROOT / "event-timelines.sh").write_text(
        "#!/bin/bash\n" + LIC + "# 11.31 event-timelines (draft phase): Q111, which job sets which bit of CR_EVENT_STATUS and\n"
        "# CR_EVENT_STATUS2, as a timeline.\n" + KEPT + EVENTS_TIMELINES)
    (ROOT / "event-irq-matrix.sh").write_text(
        "#!/bin/bash\n" + LIC + "# 11.31 event-irq-matrix (draft phase): Q111, which bit of the event registers each kind of job\n"
        "# sets, seen as a host interrupt.\n" + KEPT + EVENTS_IRQ)
    for f in ROOT.glob("*.sh"):
        f.chmod(0o755)


main()
print("scripts written")
