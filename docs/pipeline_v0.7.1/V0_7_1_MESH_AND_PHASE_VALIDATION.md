# Mesh and phase validation

H1:66049 nodes and65536 counterclockwise PLANE182 quads. H2:263169 nodes and262144 quads. Every native element connectivity and material ID matches the authenticated categorical source, and every native coordinate matches the structured grid. No holes, duplicate interface nodes, removed matrix pixels or separate contact bodies occur. Native1→material1 and native5→material2 are both solids. Shared nodes enforce ideal bonded displacement compatibility. Exact native boundary inventories contain only top/bottom UY and one bottom-left UX pin.

Image row0 stays at the physical top. Refinement subdivides each pixel without averaging labels. All exact phase fractions survive H1/H2. The reference H1/H2 difference is0.664115%, below the prospectively fixed2% gate. H1 is the common initial production mesh.

| Specimen | H1 E (MPa) | H2 E (MPa) | Difference relative to H2 |
|---|---:|---:|---:|
| M2_reference | 1693.288605 | 1682.117418 | 0.66411% |
| M3_A01 | 1739.043969 | 1728.407955 | 0.61536% |
| M4_B02 | 1691.405496 | 1681.045842 | 0.61626% |
| M5_C02_r1 | 1723.642834 | 1713.561814 | 0.58831% |
| M6_C02_r0 | 1676.206734 | 1667.538868 | 0.51980% |

Native tables compare phase-average stress, stress percentiles, energy, reactions, runtime and memory at both levels. This is preliminary two-level FE sensitivity; asymptotic convergence, pixel-resolution adequacy and physical interface geometry remain unqualified.
