#!/bin/bash
# fake ~/scratch/r6m/bin/sgxfive-test (t6, the d9b2969 build) for tests/run_mock.sh: tests/worlds.py answers FROM ITS ARGV
exec "${PY:?}" "${FAKE_P:-$(dirname "$0")}/worlds.py" tool "$0" "$@"
