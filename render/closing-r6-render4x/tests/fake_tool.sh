#!/bin/bash
# fake sgxfive-test-rgn4 for tests/run_mock.sh: the world named by $FAKE_WORLD (tests/worlds.py) answers FROM ITS ARGV and the fake
# debugfs knobs (render_pb_pages, render_rgn_arrays, hold_recovery), never from a case name or a kmsg marker (round 4's fake answered by
# the marker's name and so could not see a row's argv).  A bare `tri` or `fill` is the health pair (FAKE_HEALTH_BAD: they fail;
# FAKE_HEALTH_SEQ: the Nth health call answers the Nth word).  FAKE_RULES ("ARGV-SUBSTRING|OUTCOME" lines) override the world:
#   fatal  logs a soft lockup;  timeout  exits 124;  hang  logs a hung job;  nodiff  rc 1, no diff line;  resetinfo  the world's job with
#   the kernel's two reset information lines logged during it (not a fault);  fault  a TA-side fault (0x90004 at 0x20006061);
#   bigdump  the job leaves less than the free-space floor on ~ (the fake df).  FAKE_SLOW_START=S: the fake answers S seconds late.
exec "${PY:?}" "${FAKE_P:-$(dirname "$0")}/worlds.py" tool "$@"
