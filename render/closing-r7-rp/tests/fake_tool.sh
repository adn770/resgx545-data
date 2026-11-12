#!/bin/bash
# fake sgxfive-test (t4 as ~/sgxfive-test-rgn4, t6 and t7 as ~/scratch/r7r/bin/sgxfive-test-t6, -t7) for tests/run_mock.sh: the world
# of tests/worlds.py answers FROM ITS ARGV and its own path (which build), never from a case name or a kmsg marker.
exec "${PY:?}" "${FAKE_P:?}/worlds.py" tool "$0" "$@"
