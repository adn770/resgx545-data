# r10-zls preflight (the lead, before staging)

1. Module B60AB0B475DD1E8972419B5 loaded and installed (the kit checks both); no knob is used.
2. `~/sgxfive-test-rgn4` is sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a
   and `~/sgxfive-test-t9` is 7a28be3952fb310170e861da0622d890a2e215cb761d6f21bc9321223e1b40ce
   (both on the laptop since round 9; the kit's stage checks them). FROZEN.commits carries their
   `built` lines (t9: recipe data:render/closing-r9-k1/lead/build_tool9.sh, copied in lead/).
3. `~/scratch/r10z/` absent or empty; at least 300 MiB free on `~`.
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again (verifies the freeze).
5. Order (seeds plan R10-10 (a)): the last session of the sitting, before st1 (t10) if the lead
   builds it; log to `closing10/logs/run-r10z.log`. No fault is planned: a fault stops the
   session (4), with recovery and strict health by the kit.
