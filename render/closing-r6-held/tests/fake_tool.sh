#!/bin/bash
# fake ~/sgxfive-test-rgn4 for tests/run_mock.sh: tests/worlds.py's `tool`, which answers from its argv and the fake debugfs only.
# FAKE_PY and FAKE_P are the mock's plumbing (the runner never names them).
exec "${FAKE_PY:?}" -B "${FAKE_P:?}/worlds.py" tool "$@"
