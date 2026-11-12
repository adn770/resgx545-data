#!/bin/bash
# SPDX-License-Identifier: MIT
# health_remote.sh TOOL: runs ON the laptop (copied to ~/scratch/r6h/p/stage/run/ by stage_p.sh; r6-held part P).  The lines of the landed
# tools/bringup/health.sh (a fill and a triangle through ~/TOOL, the driver's switches, the last kernel messages), but the debugfs directory is
# found through dri/*/sgx (the device has three names: dri/0, dri/0000:00:02.0 and dri/128) and every debugfs access goes through sudo -n.  The
# directory is the first that holds own_res.  The new module's knobs are printed too (kick_no_bump, render_rgn_arrays, timer_clock, render_tail_room), and one read
# of the r6-kernel's debugfs peek (CR_DPM_TASK_STATE; read only, bounded).  Every tool call is bounded by `timeout -k`.
set -u
TOOL=${1:?usage: health_remote.sh TOOL}
D=$(sudo -n sh -c 'for d in /sys/kernel/debug/dri/*/sgx; do if [ -e "$d/own_res" ]; then echo "$d"; break; fi; done')
[ -n "$D" ] || { echo "no sgx debugfs directory with own_res"; exit 3; }
sudo -n timeout -k 5 60 ~/"$TOOL" fill 2>&1 | grep -E "^diff|^job|ok|FAIL" | head -3
sudo -n timeout -k 5 60 ~/"$TOOL" tri 2>&1 | grep -E "^tri|^diff|FAIL" | head -3
echo "peek: $(sudo -n timeout -k 5 10 cat "$D/peek" 2>&1 | head -1)"
for s in hold_recovery rtds_keep alias_ta3d_ro render_pb_pages render_ctx_flags kick_no_bump render_rgn_arrays timer_clock render_tail_room; do
	printf "%s=%s " "$s" "$(sudo -n cat "$D/$s")"
done
echo
sudo -n dmesg | tail -3
