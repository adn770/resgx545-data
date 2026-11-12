#!/bin/bash
# SPDX-License-Identifier: MIT
# lead/build_tool6.sh: build r6-misc's t6 (sgxfive-test from resgx545 d9b2969, whose userspace/libsgxfive is a6d78db's: odd target
# heights allowed) for i686 on the BUILD HOST, the way tools/bringup/push-tools.sh does (its docker image and make line), and copy the
# binary back to this session's debug/tool6-i686/sgxfive-test.  Run by the lead on the Mac, once, before staging; it never touches
# the laptop (run/stage_m.sh copies the binary there).  The source is `git archive d9b2969` (not the working tree), checked against
# TOOL6SRC.sha256 before anything is sent.  Prints the binary's sha256: the input of `run/freeze_m.sh tool6 SHA`.
# Settings: SGX_BUILD_HOST (default sgx-build), SGX_TOOLS_IMAGE (default sgxhumation/arch32:igt, push-tools.sh's), from
# tools/bringup/local.env.  The build host directory is ~/sgxt-r6m (its own: push-tools.sh's ~/sgxt is left alone).
# SGX_DRY_RUN=1 prints the commands.
set -eu
KP=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$MAIN/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
B=${SGX_BUILD_HOST:-sgx-build}
IMG=${SGX_TOOLS_IMAGE:-sgxhumation/arch32:igt}
COMMIT=d9b2969
OUT=$KP/debug/tool6-i686
SRC=$KP/debug/tool6-src
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@"; fi; }
bounded() { local s=$1; shift; perl -e 'alarm shift; exec @ARGV' "$s" "$@"; }
mkdir -p "$OUT"
rm -rf "$SRC"; mkdir -p "$SRC"
git -C "$MAIN" archive "$COMMIT" userspace/libsgxfive include/uapi | tar -x -C "$SRC"
want=$(sed -n 1p "$KP/TOOL6SRC.sha256" | cut -d' ' -f1)
got=$(shasum -a 256 "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
[ "$want" = "$got" ] || { echo "the archived sgxfive-test.c is not TOOL6SRC.sha256's ($got, pinned $want)"; exit 1; }
run bounded 60 ssh -o BatchMode=yes "$B" "bash -c 'rm -rf ~/sgxt-r6m && mkdir -p ~/sgxt-r6m/userspace ~/sgxt-r6m/include'"
run bounded 120 scp -qr "$SRC/userspace/libsgxfive" "$B:sgxt-r6m/userspace/"
run bounded 120 scp -qr "$SRC/include/uapi" "$B:sgxt-r6m/include/"
run bounded 600 ssh -o BatchMode=yes "$B" "bash -c 'cd ~/sgxt-r6m/userspace/libsgxfive && rm -rf build && docker run --rm --user \$(id -u):\$(id -g) -e HOME=/tmp -v ~/sgxt-r6m:/s -w /s/userspace/libsgxfive $IMG make -s CC=gcc build/sgxfive-test && file build/sgxfive-test'"
run bounded 120 scp -q "$B:sgxt-r6m/userspace/libsgxfive/build/sgxfive-test" "$OUT/sgxfive-test"
[ -n "${SGX_DRY_RUN:-}" ] && exit 0
s=$(shasum -a 256 "$OUT/sgxfive-test" | cut -d' ' -f1)
echo "t6 built from resgx545 $COMMIT (sgxfive-test.c $got): $OUT/sgxfive-test"
echo "sha256 $s"
echo "next: run/freeze_m.sh tool6 $s && run/freeze_m.sh verify $s && run/stage_m.sh $s"
