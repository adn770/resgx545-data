# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# One scene over one, two and three TA kicks (geometry jobs; the later triangles moved), each
# scene's parameter buffer and TA data dumped after its closing render (--dump-render, the
# kernel's debugfs render_param and render_tadata) and printed here as gzip in base64 between
# "#### param NAME" or "#### tadata NAME" and "#### end" (isp_words.py unpack writes them back
# to NAME.param.bin and NAME.tadata.bin); --keep-going because the closing render's image holds
# the earlier kicks' triangles too. Twice over. Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
W=$(mktemp -d)
for r in 1 2; do
	for s in "1:-n 1" "2:-n 2 --geometry 1 --move 2:12,12" \
		"3:-n 3 --geometry 1 --geometry 2 --move 2:12,12 --move 3:24,0"; do
		k=${s%%:*}; a=${s#*:}
		mkdir -p "$W/k$k"
		echo "== run $r, $k kick(s): $a"
		# shellcheck disable=SC2086
		sudo -n "$T" tri $a --keep-going --dump-render "$W/k$k" 2>&1 |
			grep -E "renders ok|FAILED|render memory|#[0-9]+: "
		for f in param tadata; do
			echo "#### $f kicks$k-r$r"
			sudo -n gzip -c "$W/k$k/tri.$f.bin" | base64 -w 76
			echo "#### end"
		done
		sudo -n rm -rf "$W/k$k"
	done
done
rm -rf "$W"
