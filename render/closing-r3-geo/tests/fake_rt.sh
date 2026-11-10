#!/bin/sh
# fake regtimeline TOTAL LEAD REGS -- COMMAND...: tests/fake_rt.py (the synthetic world of FAKE_WORLD)
exec python3 "$(dirname "$0")/fake_rt.py" "$@"
