#!/bin/bash
# fake regtimeline TOTAL LEAD REGS -- COMMAND...: runs COMMAND, then prints a timeline of the five S3
# registers (0x0118 0x012c 0x0c00 0x0c04 0x0c08) as the real one does: the first row is the PREVIOUS
# state (here a stale fault with status2 0x480 and status bit 18, which the scorer must ignore: it is
# before the command's start), an idle row, and, if the fake GPU latched a fault, the fault row with
# FAKE_RT_EXTRA2 / FAKE_RT_EXTRA1 or-ed into status2 / status (an extra bit at the moment of the fault).
shift 3; [ "$1" = "--" ] && shift
"$@"; rc=$?
echo "timeline: regs 0x0118 0x012c 0x0c00 0x0c04 0x0c08 samples 123456 seconds 0 start 300000000 end 900000000 rc $rc"
echo "tl 0 00000c80 20040000 00000000 00090008 3e000001"
echo "tl 1000 00000400 20000000 00000000 00080000 00000000"
read -r w a s2 s < "$FAKE_DIR/state"
if [ "$w" != idle ]; then
	echo "tl 300500000 00000400 20000000 00000000 00080000 00000000"
	printf 'tl 400000000 %08x %08x 00000000 %08x %08x\n' $(( s2 | ${FAKE_RT_EXTRA2:-0} )) $(( s | ${FAKE_RT_EXTRA1:-0} )) $(( w | 0x80000 )) $((a))
	# after the hold window (snap 2 at HOLD_READ + HOLD_GAP = 3.8 s): the reset's halt and boot, the fault
	# still latched for a moment, SW_EVENT and MASTER set, status2 0x4c0; then idle
	printf 'tl 3900000000 000004c0 a0004000 00000000 %08x %08x\n' $(( w | 0x80000 )) $((a))
	echo "tl 4000000000 00000400 20000000 00000000 00080000 00000000"
fi
exit $rc
