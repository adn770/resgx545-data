#!/bin/bash
# build_mock_tool.sh: build the rgn4 tool (resgx545 r3-rgn4 4623753, the source of the laptop's ~/sgxfive-test-rgn4) on the Mac into
# debug/tool4623753, for tests/mock_all.py (the tool's own --mock, no laptop).  Idempotent: does nothing if the build exists.  The source
# is `git archive` of the pinned commit; its sgxfive-test.c must hash to TOOLSRC.sha256's blob (703cbcea...).  Mac-side only: nothing
# here runs on the laptop, and the session's run/ scripts never compile.
set -eu
KP=$(cd "$(dirname "$0")/.." && pwd)
D=$KP/debug/tool4623753
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
if [ ! -x "$D/userspace/libsgxfive/build/sgxfive-test" ]; then
	mkdir -p "$D"
	git -C "$MAIN" archive 4623753 userspace/libsgxfive include | tar -x -C "$D"
	make -C "$D/userspace/libsgxfive" -j4 build/sgxfive-test > "$KP/debug/mock-build.log" 2>&1
fi
want=$(cut -d' ' -f1 "$KP/TOOLSRC.sha256")
got=$(shasum -a 256 "$D/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
[ "$want" = "$got" ] || { echo "the mock tool's source is not the pinned one ($got, pinned $want)"; exit 1; }
echo "$D/userspace/libsgxfive/build/sgxfive-test"
