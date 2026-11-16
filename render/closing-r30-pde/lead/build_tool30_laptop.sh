#!/bin/bash
# SPDX-License-Identifier: MIT
# build_tool30_laptop.sh: build round 30's t30, sgxfive-test of resgx545 main 42c4de7 (9379de7:
# copy --src-addr, fill --dst-addr and --large-copy DIR for the linux fork's debugfs vm_pde_* and
# vm_large; 2cc9c5b: probe --tri --vertices prints its render time) ON THE LAPTOP, natively (gcc,
# no cachix: the travel runbook's section 5), and copy it to ~/sgxfive-test-t30. Run by the lead on
# the Mac over the travel cable, before r30-pde's freeze (README.md "Tool"): the freeze names the
# binary's sha256 in session.toml.
#
# Steps (t24's recipe, closing24/k24/build_tool24_laptop.sh): main is brought to the laptop's
# ~/src/resgx545 by a git bundle (base the laptop's HEAD, which must be an ancestor of COMMIT;
# scp'd to ~/scratch/travel/, verified, fetched (FETCH_HEAD), the branch r30-tool checked out or
# created at the base: a fast-forward of the laptop's clean tree to COMMIT); the source is checked
# at the pinned commit and in the working tree against its pinned sha256; then `make CC=gcc
# build/sgxfive-test` in userspace/libsgxfive from an empty build/ (timed), the binary copied to
# ~/sgxfive-test-t30 (refused if one with other bytes is there), and `make check` run there
# (pytest from ~/scratch/r30t/pylib, a copy of round 24's ~/scratch/r24t/pylib; TMPDIR
# ~/scratch/r30t/tmp, never /tmp); make check must report 0 failures (rc 2 otherwise). Prints the
# binary's sha256 and the FROZEN.commits line (TOOL30.built's format, closing24/k24's).
# Nothing is installed, no module, kernel or reboot; laptop files only under ~/scratch/ and the
# tool's own ~/sgxfive-test-t30. Do not run it while the laptop runs a GPU session or a timing
# session (make check loads the CPU for about 2 min). SGX_DRY_RUN=1 prints the commands.
# Settings: SGX_TARGET_HOST (default jtorra@10.42.0.2), SGX_TARGET_HOST_KEY_ALIAS (cedar).
set -eu
MAIN=${RESGX545_MAIN:-/Users/jtorra/src/resgx545}
T=${SGX_TARGET_HOST:-jtorra@10.42.0.2}
ALIAS=${SGX_TARGET_HOST_KEY_ALIAS:-cedar}
COMMIT=42c4de7855d6f310321cc03fa0780b698a735e4d
BRANCH=main
LBRANCH=r30-tool
SRCSHA=253fd15bcb6a0a6381d20aacbb635af1c99d764388f394f9a24dc61266b6418d
SRC=userspace/libsgxfive/tools/sgxfive-test.c
BIN=sgxfive-test-t30
KP=$(cd "$(dirname "$0")" && pwd)
OUT=$(dirname "$KP")/debug
SSH=(ssh -o "HostKeyAlias=$ALIAS" -o BatchMode=yes -o ConnectTimeout=8)
SCP=(scp -q -o "HostKeyAlias=$ALIAS" -o BatchMode=yes -o ConnectTimeout=8)
run() { if [ -n "${SGX_DRY_RUN:-}" ]; then echo "$*"; else "$@"; fi; }
bounded() { local s=$1; shift; perl -e 'alarm shift; exec @ARGV' "$s" "$@"; }
on() { run bounded "$1" "${SSH[@]}" "$T" "$2"; }

git -C "$MAIN" merge-base --is-ancestor "$COMMIT" "$BRANCH" || { echo "$COMMIT is not on $BRANCH here"; exit 1; }
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
		git fetch -q ~/scratch/travel/$(basename "$BUNDLE") $BRANCH;
		git checkout -q $LBRANCH 2>/dev/null || git checkout -q -b $LBRANCH $base;
		git merge -q --ff-only $COMMIT"
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
on 60 "set -e; mkdir -p ~/scratch/r30t/tmp; test -d ~/scratch/r30t/pylib || cp -a ~/scratch/r24t/pylib ~/scratch/r30t/pylib"
check=0
on 1800 "set -eo pipefail; cd ~/src/resgx545/userspace/libsgxfive;
	TMPDIR=~/scratch/r30t/tmp PYTHONPATH=~/scratch/r30t/pylib PYTHONDONTWRITEBYTECODE=1 \
		timeout -k 10 1700 make -s CC=gcc check PYTEST='python3 -m pytest -p no:cacheprovider' 2>&1 |
		tee ~/scratch/r30t/make_check.log | tail -n 15;
	! grep -Eq '(^| )[0-9]+ failed|^FAILED|Error [0-9]' ~/scratch/r30t/make_check.log;
	grep -Eq '^[0-9]+ passed' ~/scratch/r30t/make_check.log || grep -Eq ' [0-9]+ passed' ~/scratch/r30t/make_check.log;
	test \"\$(sha256sum build/sgxfive-test | cut -d' ' -f1)\" = \"\$(sha256sum ~/$BIN | cut -d' ' -f1)\"" || check=$?
[ "$check" = 0 ] || { echo "make check: not 0 failures (rc $check): ~/scratch/r30t/make_check.log"; exit 2; }
[ -n "${SGX_DRY_RUN:-}" ] && exit 0
s=$(bounded 30 "${SSH[@]}" "$T" "sha256sum ~/$BIN" | cut -d' ' -f1)
echo "t30 built on the laptop from resgx545 $COMMIT ($SRC $SRCSHA): ~/$BIN"
echo "sha256 $s"
echo "FROZEN.commits line: $s  built  $COMMIT  $SRC  $SRCSHA"
