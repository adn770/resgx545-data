# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Run the first triangle (sgxfive-test tri, two renders each) on targets of growing size and
# print each run's result lines: the job's outcome, the target's hash and its pixel check.
set -u
T=./sgxfive-test
[ -x "$T" ] || { echo "no $T in the home directory"; exit 1; }
for size in 64x64 64x128 64x144 64x160 64x192 64x256 128x64 128x128 128x144 128x256 \
	256x64 256x128 256x256; do
	w=${size%x*}; h=${size#*x}
	echo "#### $size"
	out=$(sudo -n "$T" tri --width "$w" --height "$h" --max-width "$w" --max-height "$h" -n 2 2>&1)
	rc=$?
	echo "$out" | grep -E "^(job|target|diff|tri|failed|outside|guard)" || echo "(no result line)"
	echo "## exit $rc"
done
