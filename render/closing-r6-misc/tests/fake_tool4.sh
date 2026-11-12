#!/bin/bash
# fake ~/sgxfive-test-rgn4 (t4) for tests/run_mock.sh: tests/worlds.py answers FROM ITS ARGV (and its own path), never a case name
exec "${PY:?}" "${FAKE_P:-$(dirname "$0")}/worlds.py" tool "$0" "$@"
