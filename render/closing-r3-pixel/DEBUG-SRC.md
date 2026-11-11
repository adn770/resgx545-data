# debug-src/: the scratch harness the offline tests build

`debug-src/simcheck/` is the source of the scratch cargo crate `simcheck` that the session's own
offline test `tests/test_loops.py` builds from `debug/simcheck/` (see the `debug/` line of
`README.md`). It runs a USSE `.bin` as a vertex task (with `--pixel`, a pixel task) in
`crates/sgx-sim` at a chosen code index and prints the registers written
and the emits; it only reads the simulator.

It was added on 2026-11-11, after the run and after the freeze, so that the session's tests can
be re-run from the published data (`tools/closing/session_tests.sh`, which copies
`debug-src/` to `debug/` in a scratch copy). It is source only: `Cargo.toml`, `Cargo.lock` and
`src/main.rs`, copied byte for byte from the session's `debug/simcheck/` (no `target/`, no build
output). It is not in `FROZEN.sha256`, it was not used on the laptop and no job of the session
depends on it. `Cargo.toml` names `crates/sgx-sim` and `crates/usse-isa` by the absolute path of
the author's resgx545 checkout; the runner points them at the pinned tree in its copy.

`README.md` is a pre-run document and is left as it was.
