#!/bin/bash
# fake ~/scratch/r7g/bin/sgxfive-test (t6) for tests/run_mock.sh: tests/worlds.py answers FROM ITS ARGV (and its own path), never a case name
exec "${PY:?}" "${FAKE_P:-$(dirname "$0")}/worlds.py" tool "$0" "$@"
