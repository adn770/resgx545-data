cases.tsv; NAME.txt.gz is the tool output (gzip), NAME.param.txt.gz and NAME.tadata.txt.gz the kernel's
render_param and render_tadata dumps (gzip of the raw binary, despite the name). The jobs with TE
0x40000000, 0x80000000, 0xc0000000 have no dumps: the tool wrote none because the job's image check
failed (rc 1).
