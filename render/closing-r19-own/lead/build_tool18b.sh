#!/bin/bash
# SPDX-License-Identifier: MIT
# build_tool18b.sh: build round 18's t18b (sgxfive-test with tri --final-pb-pages N, which writes
# debugfs render_final_pb_pages before its render context; needs the linux fork's r18-kernel
# module, srcversion E0CC40275493F8AEAD8180B; from resgx545 commit
# ec50498e6b5cbf3ebff07233da508023dd28f4a2 on branch r18-kernel-tool, off main 959a430, so it
# also has t18's --kept-copy after the early close) for i686 on the BUILD
# HOST, the way tools/bringup/push-tools.sh does (its docker image and make line), and copy the
# binary back to <closing18>/debug/tool18b-i686/. Run by the lead on the Mac, once, before staging;
# it never touches the laptop. The source is `git archive` of the commit (not the working tree),
# checked against its pinned sha256 before anything is sent. Prints the binary's sha256: the
# input of the freeze's tool18b slot.
# Settings: SGX_BUILD_HOST (default sgx-build), SGX_TOOLS_IMAGE (default sgxhumation/arch32:igt),
# from tools/bringup/local.env. The host directory is ~/sgxt-r18b (its own). SGX_DRY_RUN=1 prints
# the commands. RECIPE_CITE names where the session publishes this recipe (the FROZEN.commits
# line's last field).
set -eu
KP=$(cd "$(dirname "$0")/.." && pwd)
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$MAIN/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
B=${SGX_BUILD_HOST:-sgx-build}
IMG=${SGX_TOOLS_IMAGE:-sgxhumation/arch32:igt}
COMMIT=ec50498e6b5cbf3ebff07233da508023dd28f4a2
SRCSHA=70aa910e14ae8040072b8c2cde5991830c4dcfe6bcd35ccf722c080ee9f38e29
CITE=${RECIPE_CITE:-data:render/closing-r18-SESSION/lead/build_tool18b.sh}
OUT=$KP/debug/tool18b-i686
SRC=$KP/debug/tool18b-src
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@"; fi; }
bounded() { local s=$1; shift; perl -e 'alarm shift; exec @ARGV' "$s" "$@"; }
mkdir -p "$OUT"
rm -rf "$SRC"; mkdir -p "$SRC"
git -C "$MAIN" archive "$COMMIT" userspace/libsgxfive include/uapi | tar -x -C "$SRC"
got=$(shasum -a 256 "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
[ "$SRCSHA" = "$got" ] || { echo "the archived sgxfive-test.c is not the pinned one ($got, pinned $SRCSHA)"; exit 1; }
run bounded 60 ssh -o BatchMode=yes "$B" "bash -c 'rm -rf ~/sgxt-r18b && mkdir -p ~/sgxt-r18b/userspace ~/sgxt-r18b/include'"
run bounded 120 scp -qr "$SRC/userspace/libsgxfive" "$B:sgxt-r18b/userspace/"
run bounded 120 scp -qr "$SRC/include/uapi" "$B:sgxt-r18b/include/"
run bounded 600 ssh -o BatchMode=yes "$B" "bash -c 'cd ~/sgxt-r18b/userspace/libsgxfive && rm -rf build && docker run --rm --user \$(id -u):\$(id -g) -e HOME=/tmp -v ~/sgxt-r18b:/s -w /s/userspace/libsgxfive $IMG make -s CC=gcc build/sgxfive-test && file build/sgxfive-test'"
run bounded 120 scp -q "$B:sgxt-r18b/userspace/libsgxfive/build/sgxfive-test" "$OUT/sgxfive-test"
[ -n "${SGX_DRY_RUN:-}" ] && exit 0
s=$(shasum -a 256 "$OUT/sgxfive-test" | cut -d' ' -f1)
echo "t18b built from resgx545 $COMMIT (sgxfive-test.c $got): $OUT/sgxfive-test"
echo "sha256 $s"
echo "FROZEN.commits line: $s  built  $COMMIT  userspace/libsgxfive/tools/sgxfive-test.c  $got  $CITE"
