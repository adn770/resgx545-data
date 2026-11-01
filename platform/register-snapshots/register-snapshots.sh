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

fourteen_job_types() (
# Register snapshots (debugfs regs) before and after each kind of job, with the difference:
# the firmware load and boot, a MISCINFO query, a POWER idle, the debugfs fill and copy, the
# triangle (64x64 and 256x256), a client fill, many render contexts, a stop, a second boot and
# two reads in a row.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
wr() { echo 1 | sudo -n tee "$D/$1" >/dev/null; echo "## write $1: exit $?"; }
rdf() { echo "## $1"; sudo -n cat "$D/$1"; }
snap() { name=$1; shift
	echo "#### $name"
	sudo -n cat "$D/regs" > "$tmp/before"
	"$@"
	sudo -n cat "$D/regs" > "$tmp/after"
	echo "## regs diff (before, after)"
	diff "$tmp/before" "$tmp/after"
}
cl() { sudo -n "$T" "$@" 2>&1; }
snap load wr load
snap boot wr boot
snap miscinfo rdf miscinfo
snap power-idle wr idle
snap xfer-fill rdf xfer_fill
snap xfer-copy rdf xfer_copy
snap tri cl tri
snap tri-twice cl tri -n 2
snap tri-256x256 cl tri --width 256 --height 256
snap client-fill cl fill
snap client-contexts cl contexts -n 8
snap stop wr stop
snap boot-again wr boot
snap reread rdf status
)
echo "#### fourteen-job-types"
fourteen_job_types
echo "## exit $?"
