# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Hand-run experiments: sgxfive-test (SGXFIVE_TEST, default ~/sgxfive-test) and regtimeline
# (SGXFIVE_REGTIMELINE, default ~/regtimeline) run each case; every output is kept and nothing
# is judged here. Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null

closed_scene_rerender() (
# Re-render a closed scene: render 1 geometry, render 2 closes it (render flags as given),
# render 3's triangle off-screen (no new geometry) appending to it (FIRST_KICK clear). If the
# closed scene was kept, render 3 stores renders 1 and 2's triangles ("other" or "outside").
# Twice over.
kp() { printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1; shift
	kp
	echo "== $name"
	sudo -n "$T" tri --keep-going -n 3 --geometry 1 --move 2:12,0 --move 3:200,200 "$@" 2>&1 |
		grep -E "^job|^tri 64x64 #[23]" | grep -v " us$"
	echo "kpoke left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
	kp
}
for r in 1 2; do
	run "3 a new scene (control)"
	run "3 appends"                       --kpoke-render 3:ta:1^=0x1
	run "2 BIT2; 3 appends"               --kpoke-render 2:ta:7^=0x4 --kpoke-render 3:ta:1^=0x1
	run "2 NO_DEALLOCATE; 3 appends"      --kpoke-render 2:ta:7^=0x8 --kpoke-render 3:ta:1^=0x1
	run "2 both; 3 appends"               --kpoke-render 2:ta:7^=0xc --kpoke-render 3:ta:1^=0x1
	run "2 both; 3 appends, no DPM load"  --kpoke-render 2:ta:7^=0xc --kpoke-render 3:ta:1^=0x9
	run "2 BIT2; 3 appends, no DPM load"  --kpoke-render 2:ta:7^=0x4 --kpoke-render 3:ta:1^=0x9
	run "3 appends, no DPM load"          --kpoke-render 3:ta:1^=0x9
done
)

geometry_kicks() (
# Scenes over several TA kicks (geometry jobs, --geometry N): the renders' triangles 12 px
# apart; a pixel of an earlier triangle in a closing render's image counts as "wrong outside"
# its reference. Twice over.
kp() { printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1; shift
	kp
	echo "== $name"
	sudo -n "$T" tri --keep-going "$@" 2>&1 | grep -E "^job|^tri|kpoke" | grep -vE "render context|us$|moved by"
	echo "kpoke left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
	kp
}
G3="-n 3 --geometry 1 --move 2:12,0 --move 3:0,12"
for r in 1 2; do
	run "control: 2 renders" -n 2 --move 2:12,12
	run "1 geometry, 2 closes" -n 2 --geometry 1 --move 2:12,12
	run "1, 2 geometry, 3 closes" -n 3 --geometry 1 --geometry 2 --move 2:12,0 --move 3:0,12
	run "1 geometry, 2 closes with BIT2; 3" $G3 --kpoke-render 2:ta:7^=0x4
	run "1 geometry, 2 closes with BIT2; 3 not first" $G3 --kpoke-render 2:ta:7^=0x4 --kpoke-render 3:ta:1^=0x1
	run "1 geometry, 2 closes with NO_DEALLOCATE; 3" $G3 --kpoke-render 2:ta:7^=0x8
	run "1 geometry, 2 closes with NO_DEALLOCATE; 3 not first" $G3 --kpoke-render 2:ta:7^=0x8 --kpoke-render 3:ta:1^=0x1
	run "1 geometry, 2 closes with both; 3 not first" $G3 --kpoke-render 2:ta:7^=0xc --kpoke-render 3:ta:1^=0x1
	run "1 geometry, 2 closes; 3 not first" $G3 --kpoke-render 3:ta:1^=0x1
	run "1 geometry, 2 closes with BIT10 clear; 3" $G3 --kpoke-render 2:ta:7^=0x400
done
)

kicks_parameter_buffers() (
# One scene over one, two and three TA kicks (geometry jobs; the later triangles moved), each
# scene's parameter buffer and TA data dumped after its closing render (--dump-render, the
# kernel's debugfs render_param and render_tadata) into $HOME/kicksN/; --keep-going because the
# closing render's image holds the earlier kicks' triangles too.
for s in "1:-n 1" "2:-n 2 --geometry 1 --move 2:12,12" \
	"3:-n 3 --geometry 1 --geometry 2 --move 2:12,12 --move 3:24,0"; do
	k=${s%%:*}; a=${s#*:}
	mkdir -p "$HOME/kicks$k"
	echo "== $k kick(s): $a"
	# shellcheck disable=SC2086
	sudo -n "$T" tri $a --keep-going --dump-render "$HOME/kicks$k" 2>&1 |
		grep -E "renders ok|FAILED|render memory|#[0-9]+: "
done
)

two_renders_one_context() (
# Two renders of one render context, the second triangle 12 px right and down: does render 2's
# scene keep render 1's triangle? Kernel pokes per render (--kpoke-render): ta:1 the TA kick
# flags (0x73: FIRST 0x1, LAST 0x2, cache invalidates), ta:7 the render flags (0x400). A pixel
# of render 1's triangle in render 2's image counts as "wrong outside". Twice over.
kp() { printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1; shift
	kp
	echo "== $name"
	sudo -n "$RT" 0 0 0x0494-0x04b4 -- "$T" tri -n 2 --move 2:12,12 "$@" 2>&1 |
		grep -E "^job|^tri|kpoke|^timeline|^tl" | grep -v "render context"
	echo "kpoke left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
	kp
}
for r in 1 2; do
	run "control"
	run "2: no FIRST" --kpoke-render 2:ta:1^=0x1
	run "1: BIT2; 2: no FIRST" --kpoke-render 1:ta:7^=0x4 --kpoke-render 2:ta:1^=0x1
	run "1: NO_DEALLOCATE; 2: no FIRST" --kpoke-render 1:ta:7^=0x8 --kpoke-render 2:ta:1^=0x1
	run "1: BIT2 NO_DEALLOCATE; 2: no FIRST" --kpoke-render 1:ta:7^=0xc --kpoke-render 2:ta:1^=0x1
	run "1: no LAST; 2: no FIRST" --kpoke-render 1:ta:1^=0x2 --kpoke-render 2:ta:1^=0x1
	run "1: BIT10 clear" --kpoke-render 1:ta:7^=0x400
done
)
echo "#### closed-scene-rerender"
closed_scene_rerender
echo "## exit $?"
echo "#### geometry-kicks"
geometry_kicks
echo "## exit $?"
echo "#### kicks-parameter-buffers"
kicks_parameter_buffers
echo "## exit $?"
echo "#### two-renders-one-context"
two_renders_one_context
echo "## exit $?"
