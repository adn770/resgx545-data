#!/bin/bash
# SPDX-License-Identifier: MIT
# build_tool14.sh: build round 14's t14 (sgxfive-test with tri --refill K:BUF=V and probe
# --scratch-pages up to 256, from resgx545 commit c58f9f9c87aa3f8370d2b66917898550d86f6879 on
# branch r14-tooling) for i686 on the BUILD HOST, the way tools/bringup/push-tools.sh
# does (its docker image and make line), and copy the binary back to <session>/debug/tool14-i686/.
# Run by the lead on the Mac, once, before staging; it never touches the laptop. The source is
# `git archive` of the commit (not the working tree), checked against its pinned sha256 before
# anything is sent. Prints the binary's sha256: the input of the freeze's tool14 slot.
# Settings: SGX_BUILD_HOST (default sgx-build), SGX_TOOLS_IMAGE (default sgxhumation/arch32:igt),
# from tools/bringup/local.env. The host directory is ~/sgxt-r14t (its own). SGX_DRY_RUN=1 prints
# the commands.
set -eu
KP=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$MAIN/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
B=${SGX_BUILD_HOST:-sgx-build}
IMG=${SGX_TOOLS_IMAGE:-sgxhumation/arch32:igt}
COMMIT=c58f9f9c87aa3f8370d2b66917898550d86f6879
SRCSHA=9cef7a202fc8267fa04ab6986145b69fd4ab18beafbe6fdb5e65dd009a00b612
OUT=$KP/debug/tool14-i686
SRC=$KP/debug/tool14-src
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@"; fi; }
bounded() { local s=$1; shift; perl -e 'alarm shift; exec @ARGV' "$s" "$@"; }
mkdir -p "$OUT"
rm -rf "$SRC"; mkdir -p "$SRC"
git -C "$MAIN" archive "$COMMIT" userspace/libsgxfive include/uapi | tar -x -C "$SRC"
got=$(shasum -a 256 "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
[ "$SRCSHA" = "$got" ] || { echo "the archived sgxfive-test.c is not the pinned one ($got, pinned $SRCSHA)"; exit 1; }
run bounded 60 ssh -o BatchMode=yes "$B" "bash -c 'rm -rf ~/sgxt-r14t && mkdir -p ~/sgxt-r14t/userspace ~/sgxt-r14t/include'"
run bounded 120 scp -qr "$SRC/userspace/libsgxfive" "$B:sgxt-r14t/userspace/"
run bounded 120 scp -qr "$SRC/include/uapi" "$B:sgxt-r14t/include/"
run bounded 600 ssh -o BatchMode=yes "$B" "bash -c 'cd ~/sgxt-r14t/userspace/libsgxfive && rm -rf build && docker run --rm --user \$(id -u):\$(id -g) -e HOME=/tmp -v ~/sgxt-r14t:/s -w /s/userspace/libsgxfive $IMG make -s CC=gcc build/sgxfive-test && file build/sgxfive-test'"
run bounded 120 scp -q "$B:sgxt-r14t/userspace/libsgxfive/build/sgxfive-test" "$OUT/sgxfive-test"
[ -n "${SGX_DRY_RUN:-}" ] && exit 0
s=$(shasum -a 256 "$OUT/sgxfive-test" | cut -d' ' -f1)
echo "t14 built from resgx545 $COMMIT (sgxfive-test.c $got): $OUT/sgxfive-test"
echo "sha256 $s"
echo "FROZEN.commits line: $s  built  $COMMIT  userspace/libsgxfive/tools/sgxfive-test.c  $got  data:render/closing-r14-flag/lead/build_tool14.sh"
