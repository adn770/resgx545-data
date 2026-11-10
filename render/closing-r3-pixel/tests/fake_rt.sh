#!/bin/bash
# fake regtimeline TOTAL LEAD REGS -- COMMAND...: runs COMMAND, then prints the timeline of 0x0008 0x0118 0x012c as the real one does: an
# idle row, one tick, the job's burst (length $FAKE_DIR/last.b us) with bit 6 / bit 7 of 0x0118 set at last.t6 / last.t7 us when the fake
# STATUS2 ($FAKE_DIR/s2, written by the fake tool) has them, and the closing idle row.
shift 3; [ "$1" = "--" ] && shift
rm -f "$FAKE_DIR/last.b"
"$@"; rc=$?
B=$(cat "$FAKE_DIR/last.b" 2>/dev/null || echo 500); t6=$(cat "$FAKE_DIR/last.t6" 2>/dev/null || echo 200); t7=$(cat "$FAKE_DIR/last.t7" 2>/dev/null || echo 300)
s2=$(( $(cat "$FAKE_DIR/s2" 2>/dev/null || echo 0x400) ))
echo "timeline: regs 0x0008 0x0118 0x012c samples 123456 seconds 0 start 300000000 end 900000000 rc $rc"
echo "tl 1000 00000020 00000400 20000000"
echo "tl 80000 000ccfa0 00000400 20000000"
echo "tl 90000 00000020 00000400 20000000"
t0=150000
echo "tl $t0 000a0000 00000400 20000000"
[ $((s2 & 0x40)) -ne 0 ] && printf 'tl %d 000a0000 %08x 20000000\n' $((t0 + t6 * 1000)) $((0x440))
[ $((s2 & 0x80)) -ne 0 ] && printf 'tl %d 000a0000 %08x 20000000\n' $((t0 + t7 * 1000)) $((s2))
printf 'tl %d 00000020 %08x 20000000\n' $((t0 + B * 1000)) $s2
exit $rc
