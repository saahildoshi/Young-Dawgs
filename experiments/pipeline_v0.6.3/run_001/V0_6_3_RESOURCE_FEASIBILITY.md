# v0.6.3 resource feasibility

Fresh audit: 68403589120 bytes physical RAM,
35213840384 bytes available RAM, 1460125863936
bytes free run-drive space and 20 logical CPUs.
All solver jobs used one SMP core; no unrestricted parallel license is assumed.

The full model has 5,533,010 specimen translational DOFs before constraints.
Actual contact sparse-solver equations: 5,533,009 (one specimen UX anchor;
platen pilot DOFs constrained). Six user platen/pilot nodes and two internally
generated pilot-control nodes are distinguished from specimen nodes.

The linear no-contact WRFULL assembly diagnostic completed in
36.807 s, peak sampled tree RSS
10981822464 bytes, matrix file
1093337088 bytes. ANSYS reported 7858 MB used / 12160 MB
allocated. WRFULL skips equation solution and is not valid evidence of a
nonlinear solve, factorization capacity or physical response. It was used only
in a separately identified linear assembly diagnostic.

The actual pilot subsequently executed sparse symmetric factorizations,
reporting about 6058.8 MB sparse workspace and 294,559,232 factor nonzeros in
the first attempt. Thus the simple coordinate-array lower bound was not the
resource decision. Memory fit does not imply nonlinear convergence.

Both pilot protocols enforce 1200 s wall time, 20 GiB sampled process-tree RSS,
12 GiB available-system-RAM reserve, 20 GiB minimum disk reserve, one core and
owned-process termination. The -m 4096 MB flag is an initial allocation, not
a hard cap. Selected attempt status TIMEOUT, return code
15, runtime 1200.102 s and peak sampled
tree RSS 18193420288 bytes. Preserve distinctions among numerical plateau, timeout
and memory failure; do not declare hardware incapable from nonconvergence.

[WRFULL reference](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_WRFULL.html)
and [sparse memory options](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_BCSOPTION.html)
are v242 comparison documentation; actual commands were checked in v241.
