#!/bin/bash
# fake sgxfive-test-rgn4 for tests/run_mock.sh: the world named by $FAKE_WORLD (tests/worlds.py) answers; the case is the one named by the
# last "resgx545 case NAME RUN" marker of $KMSG (the runner writes it right before the job), a plain `tri` or `fill` after a health
# marker is a health check (FAKE_HEALTH_BAD: they fail).  FAKE_RULES ("CASEPART|OUTCOME" lines) override the world:
#   fatal  logs a soft lockup;  timeout  exits 124;  hang  logs a hung job;  nodiff  rc 1, no diff line;  resetinfo  the world's job with
#   the kernel's two reset information lines logged during it (not a fault)
exec "${PY:?}" "${FAKE_P:-$(dirname "$0")}/worlds.py" tool "$@"
