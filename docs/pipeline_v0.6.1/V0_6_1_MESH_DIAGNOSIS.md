# v0.6.1 diagnosis of the preserved v0.6 fine mesh

The saved NPZ independently reproduces all27 failures, including minimum
8.27513422° at element4970 (one-based). Angles are recomputed with atan2 of
cross/dot products, independently of the historical arccos calculation. No
source or mesh file was regenerated or overwritten.

The27 failures are about0.003313% of814939 elements.23 have only interior
corner vertices; three have boundary edges. The two triangles with two boundary
edges occupy90° immutable source corners, but sampled boundary legs are strongly
unequal (one about .005428mm, the other about .032mm). The source has only90°,
180° and270° solid-side boundary angles. Therefore there is no source wedge
below10° requiring geometry modification. The failures are mesh layout and
boundary discretization defects, not a mathematical conflict with the frozen gate.

The historical distance field samples each entire source curve at only three
locations, even for long platen/exterior edges. Point-size constraints are off.
This permits boundary mesh sizes to vary sharply near corners. It supports a
sampling/spacing explanation for boundary defects; interior-layout defects may
also respond to node relocation. This is a mechanism supported by configuration
and local measurements, not an assertion that one option caused every failure.

New element_quality.py calculates TRI6 shape-function derivative coefficients.
The determinant is a quadratic polynomial in reference(r,s). The minimum is
found over all three vertices, each edge stationary point and a feasible interior
stationary point. Positive quadratic Bernstein coefficients provide a second
sufficient lower bound. A scale-dependent floating-point guard is required.
This checks the whole reference triangle analytically; it is not Gauss-point
sampling or formal interval arithmetic. Straight-sided placement is checked
separately; curved elements remain unsupported by the geometry-transfer policy.

Actual mapping minima, midpoint deviations and invalid counts are recorded in
mesh_diagnosis/run_001/diagnosis.json. No invalid quadratic mapping was found in
the original mesh. Its angle failure remains a failure independently of that.

Each failing record includes both ID conventions, corner/midside IDs and actual
coordinates, all angles, signed area, whole-map determinant, one-ring and edge
neighbors, exact source-boundary and pore distances, recovered ring/segment
ownership, and distance to the nearest registered narrow axial chord. That last
metric is explicitly a finite feature proxy, not an exhaustive nearest-neck
measurement. Original Gmsh CAD entity IDs were not retained in the historical
NPZ; recovered source ring/segment references are reported instead.

Figures show the full failure map, worst and boundary-imbalance neighborhoods,
mesh connectivity, exact vector boundary, midsides and actual angle/corner/map
quality distributions. No figure uses a raster approximation of mesh coordinates.

The registered next step is a bounded saved-layout relocation diagnostic, then
boundary-distance sampling/spacing correction plus Relocate2D if justified by
small source-crop trials. Every attempt and all original evidence are retained.
No threshold or original geometric acceptance definition changes.
