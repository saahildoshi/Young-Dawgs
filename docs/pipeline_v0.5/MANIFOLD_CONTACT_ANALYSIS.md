# v0.5A.1 contact root cause and classification

## Finding

**Case A: an inherent source-cell boundary singularity.** The canonical raster,
edge extraction, traced walk, decomposed rings and independent segment graph all
agree at (31,296). No extraction/polygon assembly correction can make the
strictly identical ordinary boundary a one-dimensional manifold. A different
data structure may retain the singularity; duplicating its coordinate does not
remove it from the continuous set.

The incident cells are:

| Sector | Cell (row,column) | Phase | Global 4-solid label | Global 4-void label | Global 8-void label |
|---|---|---:|---:|---:|---:|
| NW | (295,30) | void 0 | 0 | 101 | 101 |
| NE | (295,31) | solid 1 | 1 | 0 | 0 |
| SW | (296,30) | solid 1 | 1 | 0 | 0 |
| SE | (296,31) | void 0 | 0 | 102 | 101 |

The 2×2 local mask is [[0,1],[1,0]]. Local solid 4-components=2; local void
4-components=2 and void 8-components=1. Both solid sectors belong to global
solid component 1 through paths outside this tiny neighborhood. Locally they
share only the vertex, not an edge or positive-width connection. Neither void
sector connects to the exterior under the complementary-8 convention.

Exposed edges incident to the vertex are (31,296)→(31,295),
(31,296)→(31,297), (30,296)→(31,296) and (32,296)→(31,296).
Their four distinct boundary rays give a degree-four local link. Removing the
vertex from a sufficiently small boundary neighborhood leaves four branches,
where an ordinary boundary point would leave two. Ordinary polygon corners
also have degree two and are not failures merely because their tangent changes.

The source face walk 4 visits the vertex twice. Exact v0.5A decomposition gives
hole rings 4 and 5, each simple, with coincident corner coordinates. Negative
signed areas retain hole winding in x-right/y-down coordinates. Both rings are
contained by the same solid shell. OGC validity permits this point-touching
configuration with connected polygon interior; that validity criterion does
not require disjoint embedded manifold boundary components.

The enlarged native-grid figure is in
`experiments/pipeline_v0.5/manifold_qualification/run_001/design_000_seed_000/contact_diagnostics/contact_0000.png`.
It shows exact cells, integer grid, ring identity/orientation arrows and link
degree independently of the OGC validity flag. Full incidence and source-label
records are in contacts.json; there is exactly one contact in this fixture.

## General classifier

`geometry/manifold/contacts.py` constructs an STRtree over coalesced boundary
segments and uses exact intersection predicates without snapping. It examines
point intersections, distinct incident boundary rays, ring and polygon roles,
crossings, overlaps, duplicate edges, zero-length edges and ring closure/simplicity.
It separately annotates original face-walk repetition and local source sectors.
Source checkerboard enumeration is an independent completeness check, not the
sole manifold test. Contact identifiers, ring/segment incidence, local labels,
inherent-versus-representational origin and potential topology effects are saved.

Supported diagnostics include hole–hole, hole–shell/pinched exterior, diagonal
solid/void contacts, self-touching/crossing loops, multi-ring clusters, overlapping
and duplicate/zero segments. Distinct nearby rings are searched with an explicit
1e-6-cell diagnostic radius; this does not merge coordinates or redefine exact
contact. Valid patch assemblies are first evaluated as an assembled region;
shared internal seams are reported separately from its exterior boundary.

An already ordinary boundary passes without any geometric operation. Adjacent
lattice defects receive cluster records. More than two rings can meet in general
polygon fixtures (six or more incident rays); these are detected but unsupported
for candidate generation. A true checkerboard cannot occur at the very corner
of a rectangular binary domain: only one in-domain cell meets that domain
corner. General non-grid polygon contacts there are tested separately.

## Other observed contact types

The deterministic real sample includes a hole–shell contact at (850,994) in
Design 1/seed 0, in addition to its five pore–pore contacts. This is a genuine
pinched exterior boundary, not an enclosed complementary-8 digital pore.
It was identified during the source audit and included in the prospective
policy before candidate evaluation. All real contact lists remain available;
the ordinary fixture is not excluded and Design 9 is not used as sole evidence.

## Resolution consequence

Exact representation correction can remove an artificial internal patch seam
or partition a self-touching walk into rings. It cannot eliminate an actual
degree-four boundary link while preserving the same continuous set. The exact
state therefore remains `exact_nonmanifold`. Any accepted local candidate is a
different continuous solid region, even when every original-grid cell center and
all frozen raster descriptors are unchanged.
