#!/bin/bash
# SPDX-License-Identifier: MIT
# health_remote.sh TOOL: runs ON the laptop (copied to ~/r3k0/run/ or ~/r3kev/run/ by stage_r3.sh).  The lines of the landed
# tools/bringup/health.sh (a fill and a triangle through ~/TOOL, the driver's switches, the last kernel messages), but the debugfs directory is
# found through dri/*/sgx (the device has three names: dri/0, dri/0000:00:02.0 and dri/128) and every debugfs access goes through sudo -n.  The
# directory is the first that holds own_res.  The new module's knobs are printed too (kick_no_bump, render_rgn_arrays).
set -u
TOOL=${1:?usage: health_remote.sh TOOL}
D=$(sudo -n sh -c 'for d in /sys/kernel/debug/dri/*/sgx; do if [ -e "$d/own_res" ]; then echo "$d"; break; fi; done')
[ -n "$D" ] || { echo "no sgx debugfs directory with own_res"; exit 3; }
sudo -n ~/"$TOOL" fill 2>&1 | grep -E "^diff|^job|ok|FAIL" | head -3
sudo -n ~/"$TOOL" tri 2>&1 | grep -E "^tri|^diff|FAIL" | head -3
for s in hold_recovery rtds_keep alias_ta3d_ro render_pb_pages render_ctx_flags kick_no_bump render_rgn_arrays; do
	printf "%s=%s " "$s" "$(sudo -n cat "$D/$s")"
done
echo
sudo -n dmesg | tail -3
