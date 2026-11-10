#!/bin/sh
# fake regtimeline TOTAL LEAD REGS -- COMMAND...: runs the command, then prints a synthetic timeline of the registers
# (tests/fake_rt.py), so that the 0x072c gate of the runner has something to read.
exec python3 "$(dirname "$0")/fake_rt.py" "$@"
