# v0.7.1 research handoff

Completed a native-solver-verified P3 morphology-to-mechanics study in `C:\Users\sd22446\Projects\Young-Dawgs-VSCode`, branch master, starting HEAD `913fe29351e457df1c03d70d125f27150b379d18`. All previous v0.7.0 and porous research is preserved. No nonlinear contact work, high-strain campaign, F1 mechanical solve or LLM mechanical optimization was performed.

The exact P3 reference and saved P3_A_01/r0, P3_B_02/r0, P3_C_02/r1 and paired P3_C_02/r0 seed 0 arrays were authenticated before mechanics. Native labels 1/5 map to two solid materials. H1 has 65,536 elements and 66,049 nodes; H2 has 262,144 and 263,169. Each actual native material and connectivity entry matches the source; both levels preserve phase fractions exactly and share interface nodes. Image row 0 remains at the physical top.

The illustrative computational square is 1 mm by 1 mm with 1 mm thickness in mm–N–MPa units; it is not a microscopy calibration. PLANE182 uses KEYOPT(1)=0, KEYOPT(3)=3, KEYOPT(6)=0, small-strain linear static analysis and NLGEOM OFF. E = 1000/10000 MPa, nu = 0.30 are idealized matrix-like/reinforcement-like values. Boundaries impose bottom UY=0, five actual top displacements through 0.5%, and one bottom-left UX pin, with free lateral motion. These are finite-domain apparent stiffnesses, not RVE homogenized properties.

Homogeneous, parallel-layer, series-layer and equal-material controls pass against 1000, 5500, 1818.181818 and 1000 MPa respectively. The layered analytical controls use nu=0 only as an explicit benchmark simplification. Source logs, native inventories, independent RST reopening, reaction equilibrium, stress/strain fields, strain energy, mesh topology and complete constraint inventories all qualify. The initially failed dense-grid boundary selection and its recovery are preserved.

| Specimen, saved held-out seed 0 | H1 modulus (MPa) | Signed reference error |
|---|---:|---:|
| M2_reference | 1693.289 | +0.0000% |
| M3_A01 | 1739.044 | +2.7022% |
| M4_B02 | 1691.405 | -0.1112% |
| M5_C02_r1 | 1723.643 | +1.7926% |
| M6_C02_r0 | 1676.207 | -1.0088% |


Reference H2 modulus is 1682.117418 MPa; the H1/H2 change is 0.664115%, below the prospectively registered 2% gate. All four generated H2 checks pass the same preliminary sensitivity threshold. B02 is the closest selected specimen on both levels, but its difference from the reference is smaller than observed mesh changes. Initial C02/reference agreement is also numerically unresolved under the conservative sensitivity diagnostic. Two levels do not prove asymptotic convergence or sufficient physical image resolution.

The C02 revision raises H1 modulus by47.436100MPa. Its observed absolute stiffness error changes from 1.0088% to 1.7926% on H1, and from 0.8667% to 1.8693% on H2. For this exact seed, visible morphology error worsens and hidden error improves; ten-seed means are kept distinct. The observed mechanical-agreement worsening is exploratory, and the error-change magnitude is not certified relative to the conservative mesh-change diagnostic. No causal or condition-average benefit or harm is claimed. Composition varies, and pairing does not imply identical particle identities.

Actual five-point stress–strain/force–displacement curves, shared-scale axial/equivalent stress fields, native nodal displacement components, true-scale deformed geometry, phase load sharing and mesh comparisons are in the figures and machine-readable tables. At 0.5%, reference phase-average SYY is approximately −6.783 MPa in the matrix and −12.105 MPa in reinforcement. Robust percentiles and energy shares are retained; mesh-sensitive maxima are exploratory and imply no yielding or fracture.

P3 phase 5 chemistry remains provisional; its supplied HorizontalFlip source and morphology-selection bias remain disclosed. F1 is preserved with matrix0/fiber1/void2 and transverse circle-annotation uncertainty. All physical calibration, representative-volume and experimental-validation claims remain unqualified. Actual mechanics input/output contracts and a future-only feedback schema are frozen and populated. No mechanical measurements were sent to an LLM. A future v0.7.2 can prospectively expand controlled realizations and test a target normalized modulus at fixed reinforcement fraction with new held-out seeds and an equal-attempt control.

Validation: 896 active tests, 475 archived replay checks across nine groups, 23 historical licensed-artifact checks and 26 new licensed-artifact checks passed. All 16,294 pre-existing tracked files are unchanged. There were 32 native processes (15 solves, 17 readbacks), 14 accepted source models and one preserved rejected source model. Supervised native time was11.349min; peak RSS2.779GiB; raw artifacts9.229GiB outside Git. No push was performed.

Raw artifact root: `C:\Users\sd22446\AppData\Local\YoungDawgs\artifacts\solver\v071\run_001`. Compact source/field hashes, material/mesh identities, actual checkpoint data and acceptance records are in `experiments/pipeline_v0.7.1/run_001`. Reproduction must use a new registered native run/budget; existing destinations deliberately reject overwrites. Read-only verification is `python -m pytest validation/ansys_v071_integration.py -q`; active tests require `EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py`. Protocol, analytical controls, detailed results, morphology analysis, future contracts and validation have separate reports in this directory.

Scientific status: **QUALIFIED_EXPLORATORY_P3_TWO_SOLID_ELASTIC_BENCHMARK__ILLUSTRATIVE_MATERIALS__PRELIMINARY_MESH_SENSITIVITY__NO_CALIBRATION_RVE_OR_OPTIMIZATION**. Stop this milestone here.
