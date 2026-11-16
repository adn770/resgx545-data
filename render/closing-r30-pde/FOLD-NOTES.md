# r30-pde fold notes

- Records reserved: E1117 (clause 1: s0's references and f1, f45's dense rows, per code), E1118
  (clause 2: the index, f2's and f45's misalign and ptoff rows), E1119 (clause 3: f67, the
  unnamed codes, the BIF's report). Checked 2026-11-16: main 42c4de7 and every branch end at
  E1114; r30-evst reserved E1115 and E1116; no other reservation past them.
- Question: Q109 only; edit only its own clauses. hw_spec.md section 4's PDE line and HACKING.md
  "Known tool weaknesses" (the vm_pde entry) change with the fold (the fork lands, the module was
  booted, the session ran).
- t30: bind its built line from lead/TOOL30.built; the recipe is lead/build_tool30_laptop.sh
  (data:render/closing-r30-pde/lead/build_tool30_laptop.sh once published).
- The fork's module: srcversion 7CE8E38EDB97FC5EA4F6C90, fork r30-kernel 8bc0877e8603; name the
  KTAP lines of the boot in the records' method (the KUnit gate, plan-kernel.md 4.2).
- sgx-sim: no MMU page-size model; add a SIM_UNMODELLED entry (or a model, test first) from the
  kept vm_large.txt and `tags:` lines.
- Kit note (shared tool, report only): a stage whose every row is voided (soft) keeps an empty
  cases.tsv, which the kept check reads as `(no row)`, not kept: the driver says 43 where the
  runner said 24 (mock world enomem45). The session ends either way.
- Delete `debug/`, `.pytest_cache` and `__pycache__` before the fold publishes.
