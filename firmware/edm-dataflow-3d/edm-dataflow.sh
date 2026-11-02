# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Run from the repository root with $OUT the table's directory and $RESGX545_UKERNEL the cut
# ukernel image (00_ukernel.bin of the firmware-images dataset). make_r2.sh wants the
# repository's virtual environment; a link to $RESGX545_PYTHON (default python3) stands in for
# it while the script runs.
set -eu
: "${RESGX545_UKERNEL:?set RESGX545_UKERNEL to the cut ukernel image}"
PY=$(command -v "${RESGX545_PYTHON:-python3}")
H=harness/ukernel-extract
made=
[ -x .venv/bin/python ] || { mkdir -p .venv/bin; ln -s "$PY" .venv/bin/python; made=1; }
cleanup() { [ -z "$made" ] || rm -rf .venv; rm -f "$DOC"; }
DOC=$(mktemp)
trap cleanup EXIT
echo "## make_r2.sh"
sh "$H/make_r2.sh" >/dev/null
echo "wrote sgx545_ukernel.r2 ($(wc -l < "$H/sgx545_ukernel.r2" | tr -d ' ') lines)"
echo "## edm_dataflow.py"
"$PY" "$H/edm_dataflow.py" --ukernel "$RESGX545_UKERNEL" --tsv "$OUT/edm_dataflow.tsv" \
    --doc "$DOC"
