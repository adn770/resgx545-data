#!/bin/bash
# SPDX-License-Identifier: MIT
# stage_s1.sh --src PATH [--tables-only]: copy the runner, tables and staged programs to the laptop and build the
# tool and regtimeline there from the checkout at PATH (userspace compiles only; no kernel build, no git on the
# laptop).  NOT RUN while S1b was prepared.
#   --src PATH   the resgx545 checkout whose userspace/libsgxfive is built (PATH/tools/bringup/deploy-tool.sh does the
#                build); its deploy inputs (userspace/libsgxfive without build/, include/uapi, tools/gen_tri_progs.py)
#                must hash exactly as the frozen TOOLSRC.sha256, or the staging is refused before anything is copied
# The laptop's tool is ~/sgxfive-test-s1b; its sha256 goes to TOOL.sha256 here and on the laptop, and the stage
# runner refuses any other binary.  The staging stops if the source sha256 printed on the laptop is not the sha256 of
# PATH's sgxfive-test.c, if the build printed an error, or if any step fails.  Every ssh/scp is bounded by a perl
# alarm (SSH_ALARM, 300 s for the build).  SGX_DRY_RUN=1 prints the commands.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
S1=$(dirname "$HERE")
SRC=""; TABLES_ONLY=0
[ "${1:-}" = "--src" ] && [ $# -ge 2 ] && SRC=$2
case "${3:-}" in "") ;; --tables-only) TABLES_ONLY=1 ;; *) SRC="" ;; esac
[ $# -le 3 ] || SRC=""
[ -n "$SRC" ] && [ -f "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" ] && [ -x "$SRC/tools/bringup/deploy-tool.sh" ] \
	|| { echo "usage: stage_s1.sh --src PATH (a resgx545 checkout with userspace/libsgxfive and tools/bringup)"; exit 2; }
SRC=$(cd "$SRC" && pwd)
MAIN=${RESGX545_MAIN:-$HOME/src/resgx545}
LOCAL_ENV=${SGX_LOCAL_ENV:-$MAIN/tools/bringup/local.env}
[ -f "$LOCAL_ENV" ] && . "$LOCAL_ENV"
export SGX_LOCAL_ENV="$LOCAL_ENV"
T=${SGX_TARGET_HOST:-user@sgx-target}
OPTS=${SGX_TARGET_SSH_OPTS:-}
bounded() { perl -e 'alarm shift; exec @ARGV' "$@"; }
# every step must succeed: the first failure stops the staging
run() {
	if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; return 0; fi
	bounded "${SSH_ALARM:-300}" "$@"
	st=$?
	[ $st -eq 0 ] || { echo "STAGING FAILED (status $st) at: $*"; exit 1; }
}
"$S1/run/guard_s1.sh"; g=$?
[ $g -eq 0 ] || { echo "guard failed"; exit 1; }
"$S1/run/freeze_s1.sh" verify; v=$?
[ $v -eq 0 ] || { echo "frozen files do not verify"; exit 1; }
# the tool's source must be the frozen one: every deploy input of --src hashes as TOOLSRC.sha256 (in the freeze)
. "$S1/run/lib_check.sh"
toolsrc "$SRC" > "$S1/.toolsrc.now" 2>&1
if ! cmp -s "$S1/.toolsrc.now" "$S1/TOOLSRC.sha256"; then
	echo "STAGING REFUSED: the deploy inputs differ from the freeze (TOOLSRC.sha256):"
	diff "$S1/TOOLSRC.sha256" "$S1/.toolsrc.now" | grep '^[<>]' | head -20
	exit 1
fi
echo "deploy inputs match the freeze ($(wc -l < "$S1/TOOLSRC.sha256" | tr -d ' ') files of $SRC)"
# shellcheck disable=SC2086
run ssh -o BatchMode=yes -o ConnectTimeout=10 $OPTS "$T" 'mkdir -p s1b/run s1b/tables s1b-stage'
# shellcheck disable=SC2086
run scp -q $OPTS "$S1"/run/lib_s1.sh "$S1"/run/run_stage.sh "$T:s1b/run/"
# shellcheck disable=SC2086
run scp -q $OPTS "$S1"/tables/*.txt "$T:s1b/tables/"
# the frozen hashes: the runner's preflight compares its table and programs with them
# shellcheck disable=SC2086
run scp -q $OPTS "$S1"/FROZEN.sha256 "$T:s1b/"
# shellcheck disable=SC2086
run scp -q $OPTS "$S1"/bins/*.bin "$T:s1b-stage/"
[ "$TABLES_ONLY" = 1 ] && exit 0
want=$(shasum -a 256 "$SRC/userspace/libsgxfive/tools/sgxfive-test.c" | cut -d' ' -f1)
if [ -n "${SGX_DRY_RUN:-}" ]; then
	echo "$SRC/tools/bringup/deploy-tool.sh s1b   (source sha256 $want)"
	echo "ssh $T sha256sum ~/sgxfive-test-s1b > $S1/TOOL.sha256; scp TOOL.sha256 $T:s1b/"
	exit 0
fi
bounded "${BUILD_ALARM:-600}" "$SRC/tools/bringup/deploy-tool.sh" s1b > "$S1/stage-build.log" 2>&1
st=$?
cat "$S1/stage-build.log"
[ $st -eq 0 ] || { echo "STAGING FAILED: deploy-tool.sh exited $st"; exit 1; }
[ "$(grep -c "^$want " "$S1/stage-build.log")" -ge 2 ] || { echo "STAGING FAILED: the laptop's source is not $want"; exit 1; }
grep -Eq ' error |error:' "$S1/stage-build.log" && { echo "STAGING FAILED: the build printed an error"; exit 1; }
# shellcheck disable=SC2086
bounded "${SSH_ALARM:-150}" ssh -o BatchMode=yes $OPTS "$T" 'sha256sum ~/sgxfive-test-s1b' > "$S1/TOOL.sha256"
st=$?
[ $st -eq 0 ] && [ -s "$S1/TOOL.sha256" ] || { echo "STAGING FAILED: no tool sha256 (status $st)"; exit 1; }
run scp -q $OPTS "$S1"/TOOL.sha256 "$T:s1b/"
# regtimeline: one C file, userspace; built beside the tool, from the same checkout
# shellcheck disable=SC2086
run scp -q $OPTS "$SRC/tools/sweep/regtimeline.c" "$T:s1b/regtimeline.c"
# shellcheck disable=SC2086
run ssh -o BatchMode=yes $OPTS "$T" 'cc -O2 -o ~/regtimeline ~/s1b/regtimeline.c && sha256sum ~/regtimeline'
echo "staged: tool $(cut -d' ' -f1 "$S1/TOOL.sha256") from $SRC (source $want)"
