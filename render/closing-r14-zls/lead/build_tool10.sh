#!/bin/bash
# SPDX-License-Identifier: MIT
# build_tool10.sh: build round 10's t10 (sgxfive-test with tri --isp2, --stencil-fill bytes, --tri-unit 0 to
# 20 and int32 --tri-v, from resgx545 commit a581c06bb24d2f77e03d9b64f7ca1b2d5487b59f on main) for i686 on the BUILD HOST, the way tools/bringup/push-tools.sh
# does (its docker image and make line), and copy the binary back to <session>/debug/tool10-i686/.
# Run by the lead on the Mac, once, before staging; it never touches the laptop. The source is
# `git archive` of the commit (not the working tree), checked against its pinned sha256 before
# anything is sent. Prints the binary's sha256: the input of the freeze's tool10 slot.
# Settings: SGX_BUILD_HOST (default sgx-build), SGX_TOOLS_IMAGE (default sgxhumation/arch32:igt),
# from tools/bringup/local.env. The host directory is ~/sgxt-r10t (its own). SGX_DRY_RUN=1 prints
# the commands.
set -eu
KP=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$MAIN/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
B=${SGX_BUILD_HOST:-sgx-build}
IMG=${SGX_TOOLS_IMAGE:-sgxhumation/arch32:igt}
COMMIT=a581c06bb24d2f77e03d9b64f7ca1b2d5487b59f
SRCSHA=23e1fa76d10bb4e7cfadb0985ac110d4681e4113f2f55f17dd81bdd4b2fe183b
OUT=$KP/debug/tool10-i686
SRC=$KP/debug/tool10-src
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@"; fi; }
bounded() { local s=$1; shift; perl -e 'alarm shift; exec @ARGV' "$s" "$@"; }
mkdir -p "$OUT"
rm -rf "$SRC"; mkdir -p "$SRC"
git -C "$MAIN" archive "$COMMIT" userspace/libsgxfive include/uapi | tar -x -C "$SRC"
got=$(shasum -a 256 "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
[ "$SRCSHA" = "$got" ] || { echo "the archived sgxfive-test.c is not the pinned one ($got, pinned $SRCSHA)"; exit 1; }
run bounded 60 ssh -o BatchMode=yes "$B" "bash -c 'rm -rf ~/sgxt-r10t && mkdir -p ~/sgxt-r10t/userspace ~/sgxt-r10t/include'"
run bounded 120 scp -qr "$SRC/userspace/libsgxfive" "$B:sgxt-r10t/userspace/"
run bounded 120 scp -qr "$SRC/include/uapi" "$B:sgxt-r10t/include/"
run bounded 600 ssh -o BatchMode=yes "$B" "bash -c 'cd ~/sgxt-r10t/userspace/libsgxfive && rm -rf build && docker run --rm --user \$(id -u):\$(id -g) -e HOME=/tmp -v ~/sgxt-r10t:/s -w /s/userspace/libsgxfive $IMG make -s CC=gcc build/sgxfive-test && file build/sgxfive-test'"
run bounded 120 scp -q "$B:sgxt-r10t/userspace/libsgxfive/build/sgxfive-test" "$OUT/sgxfive-test"
[ -n "${SGX_DRY_RUN:-}" ] && exit 0
s=$(shasum -a 256 "$OUT/sgxfive-test" | cut -d' ' -f1)
echo "t10 built from resgx545 $COMMIT (sgxfive-test.c $got): $OUT/sgxfive-test"
echo "sha256 $s"
echo "FROZEN.commits line: $s  built  $COMMIT  userspace/libsgxfive/tools/sgxfive-test.c  $got  data:render/closing-r10-zls/lead/build_tool10.sh"
