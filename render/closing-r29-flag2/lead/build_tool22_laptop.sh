#!/bin/bash
# SPDX-License-Identifier: MIT
# build_tool22_laptop.sh: build round 22's t22 (sgxfive-test whose probe --poke keeps its poke set
# alive through the job and echoes `probe NAME: poked SPACE:N 0xOLD -> 0xNEW`, whose probe --place
# maps a program of up to 8192 words across pages and code steps, and whose tri --depth-pages
# floor is the store's tile extent; from resgx545 commit COMMIT on branch r22-p1, off main
# 0a7849e) ON THE LAPTOP, natively (gcc, no cachix: the travel runbook's section 5), and copy it
# to ~/sgxfive-test-t22. Run by the lead (or the tooling agent) on the Mac over the travel cable.
#
# Steps (t20's recipe, closing21/k21/build_tool20_laptop.sh): the branch is brought to the
# laptop's ~/src/resgx545 by a git bundle (made here from the Mac's repository, base the laptop's
# HEAD, scp'd to ~/scratch/travel/, verified, fetched into the branch r22-p1, checked out: a
# fast-forward of the laptop's clean tree); the source is checked at the pinned commit and in the
# working tree against its pinned sha256; then `make CC=gcc build/sgxfive-test` in
# userspace/libsgxfive from an empty build/ (timed), the binary copied to ~/sgxfive-test-t22
# (refused if one with other bytes is there), and `make check` run there (pytest from
# ~/scratch/r22t/pylib, a copy of round 21's ~/scratch/r21t/pylib, the Mac venv's pure-Python
# pytest: the laptop has none; TMPDIR ~/scratch/r22t/tmp, never /tmp). Unlike t20's recipe, make
# check must report 0 failures: the script stops with rc 2 otherwise (t20's two test_cli_poke.py
# SIGSEGVs were the probe's dangling poke set, fixed in 72a28dc). Prints the binary's sha256 and
# the FROZEN.commits line (TOOL22.built's format, closing21/k21/TOOL20.built's).
# Nothing is installed, no module, kernel or reboot; laptop files only under ~/scratch/ and the
# tool's own ~/sgxfive-test-t22. SGX_DRY_RUN=1 prints the commands.
# Run 2026-11-15 (closing22/k22/debug/build_tool22_laptop.log): build 47.7 s, sha256
# 9b62d31539564b0ca9e949aa1b44e325455b485a985fdfa65976684888d219ee; make check: every C test passed,
# pytest 497 passed, 2 skipped, 0 failed (t20's two test_cli_poke.py SIGSEGVs gone); rc 0.
# Settings: SGX_TARGET_HOST (default jtorra@10.42.0.2), SGX_TARGET_HOST_KEY_ALIAS (cedar).
set -eu
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
T=${SGX_TARGET_HOST:-jtorra@10.42.0.2}
ALIAS=${SGX_TARGET_HOST_KEY_ALIAS:-cedar}
COMMIT=3c68e8de6bdfeecd37b97e2d6095fef932e0e6d9
BRANCH=r22-p1
SRCSHA=396252bdb513282a17ed9c17446754c6478984fc423fba55236b6865bfb023c0
SRC=userspace/libsgxfive/tools/sgxfive-test.c
BIN=sgxfive-test-t22
KP=$(cd "$(dirname "$0")" && pwd)
OUT=$KP/debug
SSH=(ssh -o "HostKeyAlias=$ALIAS" -o BatchMode=yes -o ConnectTimeout=8)
SCP=(scp -q -o "HostKeyAlias=$ALIAS" -o BatchMode=yes -o ConnectTimeout=8)
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@"; fi; }
bounded() { local s=$1; shift; perl -e 'alarm shift; exec @ARGV' "$s" "$@"; }
on() { run bounded "$1" "${SSH[@]}" "$T" "$2"; }

[ "$(git -C "$MAIN" rev-parse "$BRANCH")" = "$COMMIT" ] || { echo "$BRANCH is not $COMMIT here"; exit 1; }
got=$(git -C "$MAIN" show "$COMMIT:$SRC" | shasum -a 256 | cut -d' ' -f1)
[ "$got" = "$SRCSHA" ] || { echo "$SRC at $COMMIT is $got, pinned $SRCSHA"; exit 1; }
mkdir -p "$OUT"
base=$(bounded 30 "${SSH[@]}" "$T" 'git -C ~/src/resgx545 rev-parse HEAD')
git -C "$MAIN" merge-base --is-ancestor "$base" "$COMMIT" || { echo "the laptop's HEAD $base is not an ancestor of $COMMIT"; exit 1; }
BUNDLE=$OUT/resgx545-$BRANCH-${COMMIT:0:12}.bundle
if [ "$base" != "$COMMIT" ]; then
	run git -C "$MAIN" bundle create "$BUNDLE" "$BRANCH" "^$base"
	run bounded 120 "${SCP[@]}" "$BUNDLE" "$T:scratch/travel/"
	on 120 "set -e; cd ~/src/resgx545; test -z \"\$(git status --porcelain)\";
		git bundle verify ~/scratch/travel/$(basename "$BUNDLE") >/dev/null;
		git fetch -q ~/scratch/travel/$(basename "$BUNDLE") $BRANCH:$BRANCH;
		git checkout -q $BRANCH; git merge -q --ff-only $COMMIT"
fi
on 60 "set -e; cd ~/src/resgx545; test \"\$(git rev-parse HEAD)\" = $COMMIT;
	test -z \"\$(git status --porcelain)\";
	test \"\$(git show $COMMIT:$SRC | sha256sum | cut -d' ' -f1)\" = $SRCSHA;
	test \"\$(sha256sum $SRC | cut -d' ' -f1)\" = $SRCSHA; echo source $SRCSHA at $COMMIT"
on 900 "set -e; cd ~/src/resgx545/userspace/libsgxfive; rm -rf build;
	s=\$(date +%s.%N); timeout -k 10 840 make -s CC=gcc build/sgxfive-test; e=\$(date +%s.%N);
	awk -v s=\$s -v e=\$e 'BEGIN { printf \"build_seconds %.1f\\n\", e - s }'; file build/sgxfive-test"
on 60 "set -e; cd ~/src/resgx545/userspace/libsgxfive; n=\$(sha256sum build/sgxfive-test | cut -d' ' -f1);
	if [ -e ~/$BIN ] && [ \"\$(sha256sum ~/$BIN | cut -d' ' -f1)\" != \"\$n\" ]; then
		echo ~/$BIN exists with other bytes; exit 1; fi
	cp build/sgxfive-test ~/$BIN; chmod 755 ~/$BIN; sha256sum ~/$BIN"
on 60 "set -e; mkdir -p ~/scratch/r22t/tmp; test -d ~/scratch/r22t/pylib || cp -a ~/scratch/r21t/pylib ~/scratch/r22t/pylib"
check=0
on 1800 "set -eo pipefail; cd ~/src/resgx545/userspace/libsgxfive;
	TMPDIR=~/scratch/r22t/tmp PYTHONPATH=~/scratch/r22t/pylib PYTHONDONTWRITEBYTECODE=1 \
		timeout -k 10 1700 make -s CC=gcc check PYTEST='python3 -m pytest -p no:cacheprovider' 2>&1 |
		tee ~/scratch/r22t/make_check.log | tail -n 15;
	! grep -Eq '(^| )[0-9]+ failed|^FAILED|Error [0-9]' ~/scratch/r22t/make_check.log;
	grep -Eq '^[0-9]+ passed' ~/scratch/r22t/make_check.log || grep -Eq ' [0-9]+ passed' ~/scratch/r22t/make_check.log;
	test \"\$(sha256sum build/sgxfive-test | cut -d' ' -f1)\" = \"\$(sha256sum ~/$BIN | cut -d' ' -f1)\"" || check=$?
[ "$check" = 0 ] || { echo "make check: not 0 failures (rc $check): ~/scratch/r22t/make_check.log"; exit 2; }
[ -n "${SGX_DRY_RUN:-}" ] && exit 0
s=$(bounded 30 "${SSH[@]}" "$T" "sha256sum ~/$BIN" | cut -d' ' -f1)
echo "t22 built on the laptop from resgx545 $COMMIT ($SRC $SRCSHA): ~/$BIN"
echo "sha256 $s"
echo "FROZEN.commits line: $s  built  $COMMIT  $SRC  $SRCSHA"
