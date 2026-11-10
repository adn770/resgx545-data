# SPDX-License-Identifier: MIT
# lib_check.sh: small checks of s1.sh, sourced (and tested by tests/run_mock.sh).
# The kernel prints a debugfs x32 as 0x%08llx (0x00000422, 0x00000000): numbers are compared numerically.
is_num() { case "$1" in 0x[0-9a-fA-F]*|[0-9]*) return 0 ;; *) return 1 ;; esac; }
num_eq() { is_num "$1" && is_num "$2" && [ $(($1)) -eq $(($2)) ]; }
