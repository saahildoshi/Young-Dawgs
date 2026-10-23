# Small-pore scientific qualification — separate from simplification

The saved D7/S0 source pore 1 has G1 area 1 cell², G2 area 0.96875 cell² and unchanged G2→G3 area. Its identity remains unique. The A1 regularizer adds solid in a local L1 diamond of radius 0.25 cell. One incident pore loses a right-isosceles triangle of area r²/2 = 1/32 = 0.03125 cell², giving 3.125% relative loss for a 1-cell² pore. The associated source contact, exact ring coordinates, actual footprint, perimeter and neighboring pore identities are retained in pore_policy/HISTORICAL_RECONSTRUCTION.json.

The existing A1 policy constrains global G1 occupied-area modification (0.0001), local support, validity/manifoldness, hole count, reconstruction, displacement and positive clearance. It did not register a G1-based 0.5% per-pore fidelity requirement. B2's 0.5% cap applies to each G2 pore under G2→G3. That distinction is preserved; it does not establish that a 3.125% cumulative pore change is scientifically adequate.

Both absolute and relative errors are required. The same 1/32-cell² loss gives 3.125% at area 1, 1.5625% at area 2 and 0.03125% at area 100. A single incident triangle crosses the 0.5% relative diagnostic at area 6.25 cell²; m incident contacts multiply both the construction bound and crossover by m. This is algebra, not permission to discard small pores or adopt an area tier.

Fifteen deterministic saved controls exercise these sizes, unaffected pores, shape change at equal area, merge/split/deletion/addition, exterior opening, raster-invisible change and absolute/relative diagnostic disagreement. An OR rule can accept a violation of one component; an AND rule detects both. Neither replaces topology/identity. The 0.03125-cell² absolute diagnostic is the construction scale, not an independently justified engineering allowance.

All real source pores are independently matched. Maximum G1→G2 absolute pore change is 0.0625 cell²; maximum relative change is 6.250000%. Construction-envelope violations: 0. Maximum G2→G3 per-pore area distortion remains 0.000000%. Continuous shape/perimeter changes remain separately recorded even at zero area distortion.

**Disposition: the existing policy was applied correctly within its geometric scope; cumulative small-pore scientific fidelity remains UNQUALIFIED. No amended fidelity allowance is adopted.** A physical/measurement-based criterion and fresh policy qualification remain necessary. No pore is excluded and no merge, split or deletion is forgiven because its area is small. The original C finding and HOLD remain historical evidence.

Actual cumulative G1→G3 matched-pore maxima over every setting: absolute 0.0625 cell²; relative 6.25000000%. These direct measurements are separate from the G1→G2 maxima above.

**New independent finding:** 7 source pores attain the maximum relative error. Each has area 1→0.9375 cell² and two incident contact repairs, so two 1/32-cell² triangles give 6.25% loss. All are independent-cohort pores, and identities remain unique. Their fixture/pore/contact identifiers are retained in REAL_COHORT_PORE_AUDIT.json. The construction envelope predicts this loss; it does not justify accepting it as scientific fidelity. Both fixed absolute and relative diagnostic screens reject these cases. No rule was changed after this finding.
