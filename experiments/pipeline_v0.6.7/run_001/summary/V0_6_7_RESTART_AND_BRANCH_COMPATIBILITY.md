# v0.6.7 restart and branch compatibility

The exact full parent remains LS 3SS6, time 0.009270608836206897 on FINE_FULL_SELF_CONTACT_NODAL_V066_021. Initial and final authentication covers RDB, LDHI, R001, RST. Fresh independent POST1 returns UY−0.09493103448275862 mm, upperRF−10.90307046622248 N and lowerRF+10.90287635833509 N. Sampled native U/S/EPEL agrees with retained qualified fields; original files are unchanged.

One genuine local native restart copied and authenticated the FKN 1 RDB/LDHI/R001–R003/RST, resumed LS 18SS8 with CONTINUE and increased NEQIT 24→64. Actual native inventory identifies the selected frame. It converged LS 18SS9, then failed the next substep. This proves that the control change executes on this local restart; it does not prove that an FKN change from the full FKN 100 parent is qualified.

ANSYS ignored RESCONTROL, DEFINE during CONTINUE and warned explicitly. Existing frame retention remained available; this warning did not cause the subsequent64-iteration nonconvergence. The warning and error are preserved. Any future controller should set retention after native ENDSTEP or use the supported restart modification route.

No full-parent clone was solved or modified. A pure numerical stiffness/control correction would require actual FKN-change qualification plus the already validated native ENDSTEP route before a full retry. Projection changes the integration/detection layout and requires a fresh same-fine-mesh branch with independent precontact response reproduction. Projection failed local geometry, so no such branch is launched. No result curves are spliced.
