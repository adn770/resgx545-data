#!/bin/bash
# SPDX-License-Identifier: MIT
# fake tools/bringup/health.sh for the mock session: the lines the driver checks, from the mock debugfs knobs
D=$MOCK_DIR/dbg
case ",$MOCK_SCENARIO," in *,health_bad,*) echo "job: failed"; exit 0 ;; esac
echo "job: ok"
echo "diff: 0 of 2048 pixels"
echo "tri 64x64 #1: 1062 triangle, 3034 background, 0 other"
echo "diff: 0 of 4096 pixels"
echo "hold_recovery=$(cat "$D/hold_recovery") rtds_keep=N alias_ta3d_ro=N render_pb_pages=$(cat "$D/render_pb_pages") render_ctx_flags=0x00000000 kick_no_bump=$(cat "$D/kick_no_bump") render_rgn_arrays=$(cat "$D/render_rgn_arrays") "
