# Feature-protection correction — v0.5C.1

The historical width-loss failure is reproduced byte-for-byte by original B2. At D4/S1 epsilon 0.50, the fixed vertical section at (57.5,556.5) changes from 9 to 8.916666666666629 cells. Original proposal p0000391 replaces [(57,561),(60,561),(60,560),(63,560)] with [(57,561),(63,560)]. The opposite boundary remains y=552. Direct coordinate interpolation gives y=560.9166666667 at x=57.5. This is a real 1/12-cell loss, not numeric tolerance.

The source probe EDT diameter is 8.94427191 cells, above the dense guard threshold 8; the nearest registered normal probe is 9.21954 cells away. The change hull lies 3.5 cells from the guard union; its opposing section is wider than the 2-cell proximity screen. The old chord passes collision, 0.25-cell clearance, raster-center, area, pore and displacement tests. **Both feature discovery and proposal-level width validation were incomplete.** None of those old gates measures this width.

The additive `guarded_dp_v2.0_impact_width` keeps all original guards and budgets. It adds local spatial queries around a proposed change, native-axis projection events, affine source/opposing boundary sections, the existing C diagnostic horizon of 16 cells and zero qualifying width loss with 1e-10-cell numeric allowance. Ambiguous affected projections restore the original subchain. No coordinate-specific exception, global tolerance decrease, guard enlargement or geometry widening is used. Original B2 source and outputs remain intact.

The corrected targeted section is 9.000000000000 cells; the offending chord is rejected for qualifying_solid_width_loss. Original untraced engine time was 0.768745 s; revised was 1.341143 s. The revised candidate has 35048 vertices. These are single same-fixture observations, not universal speed estimates.

Fifty targeted controls passed. An initial four-direction prototype produced only a no-op; that record is retained. Before all independent generation, integrated checks were restricted to the two native axes because diagonal staircase projections fold. Independent oblique sections were retained as validators. Two rotated-control lookup failures were corrected by using the same rotation operation for polygon and exact source subchain; no scientific tolerance or prior test changed.

Across the complete study, 102668 width/uncertainty rejection flags were recorded over 390787 qualifying affine-section checks. Within regression, 41016 formerly accepted original B2 leaves are now rejected specifically by width qualification. Rejection counts are repeated-setting leaf instances, not distinct physical struts or proven mechanical failures. Total local restorations 173847; unchanged chain instances 250201; assembly rollback instances 0.

Regression: 100 configurations over all 20 consumed realizations, including all prior 80 C configurations and the conservative 0.35 settings. This is development/regression evidence, not untouched validation. At epsilon 0.50, revised reduction spans 1.628392–5.157764%; at 0.75 it spans 1.164927–3.431293%. Conservative no-ops at lower settings remain explicit.

Independent width audits use unchanged C axial sections plus source-only oblique probes at 22.5/67.5/112.5/157.5 degrees. They do not select proposal event cuts. Flagged oblique widths receive separate coordinate interpolation. GEOS parsing and geometry interfaces remain shared; mathematical/kernel independence is not claimed. Global arbitrary-direction minimum-width preservation remains UNQUALIFIED.

See 01_original_failure.png, 02_corrected_behavior.png and 03_feature_coverage.png. Source, chord, guards, affine witnesses and restored chains are retained in the root_cause and per-case engine records. No B2 or C acceptance is revised.
