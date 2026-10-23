# v0.5A.1 manifold qualification results

Geometry study: **PASS_TESTED_DOMAIN**. Full acceptance awaits regression verification.

| Fixture | Contacts | Policy | Result | Added/removed area | Max displacement | Local clearance | Raster XOR |
|---|---:|---|---|---:|---:|---:|---:|
| design_000_seed_000 | 1 | preserve_exact | exact_nonmanifold | +0.000000/-0.000000 | 0.00000000 | 0.00000000 | see qualification.json |
| design_000_seed_000 | 1 | solid_separate_pores | ACCEPT_GEOMETRIC_CANDIDATE | +0.062500/-0.000000 | 0.17677670 | 0.35355339 | see qualification.json |
| design_000_seed_000 | 1 | solid_separate_contacts | ACCEPT_GEOMETRIC_CANDIDATE | +0.062500/-0.000000 | 0.17677670 | 0.35355339 | see qualification.json |
| design_000_seed_000 | 1 | void_side_probe | REJECT_CANDIDATE | +0.000000/-0.062500 | 0.17677670 | 0.35355339 | see qualification.json |
| design_009_seed_001 | 0 | preserve_exact | exact_manifold | +0.000000/-0.000000 | 0.00000000 | 0.00000000 | see qualification.json |
| design_009_seed_001 | 0 | solid_separate_pores | ACCEPT_NOOP | +0.000000/-0.000000 | 0.00000000 | 0.00000000 | see qualification.json |
| design_009_seed_001 | 0 | solid_separate_contacts | ACCEPT_NOOP | +0.000000/-0.000000 | 0.00000000 | 0.00000000 | see qualification.json |
| design_009_seed_001 | 0 | void_side_probe | ACCEPT_NOOP | +0.000000/-0.000000 | 0.00000000 | 0.00000000 | see qualification.json |
| design_001_seed_000 | 6 | preserve_exact | exact_nonmanifold | +0.000000/-0.000000 | 0.00000000 | 0.00000000 | see qualification.json |
| design_001_seed_000 | 6 | solid_separate_pores | REJECT_UNSUPPORTED_CONTACT | not produced | | | |
| design_001_seed_000 | 6 | solid_separate_contacts | ACCEPT_GEOMETRIC_CANDIDATE | +0.375000/-0.000000 | 0.17677670 | 0.35355339 | see qualification.json |
| design_001_seed_000 | 6 | void_side_probe | REJECT_CANDIDATE | +0.000000/-0.375000 | 0.17677670 | 0.35355339 | see qualification.json |
| design_002_seed_000 | 8 | preserve_exact | exact_nonmanifold | +0.000000/-0.000000 | 0.00000000 | 0.00000000 | see qualification.json |
| design_002_seed_000 | 8 | solid_separate_pores | ACCEPT_GEOMETRIC_CANDIDATE | +0.500000/-0.000000 | 0.17677670 | 0.35355339 | see qualification.json |
| design_002_seed_000 | 8 | solid_separate_contacts | ACCEPT_GEOMETRIC_CANDIDATE | +0.500000/-0.000000 | 0.17677670 | 0.35355339 | see qualification.json |
| design_002_seed_000 | 8 | void_side_probe | REJECT_CANDIDATE | +0.000000/-0.500000 | 0.17677670 | 0.35355339 | see qualification.json |
| design_005_seed_000 | 9 | preserve_exact | exact_nonmanifold | +0.000000/-0.000000 | 0.00000000 | 0.00000000 | see qualification.json |
| design_005_seed_000 | 9 | solid_separate_pores | ACCEPT_GEOMETRIC_CANDIDATE | +0.562500/-0.000000 | 0.17677670 | 0.35355339 | see qualification.json |
| design_005_seed_000 | 9 | solid_separate_contacts | ACCEPT_GEOMETRIC_CANDIDATE | +0.562500/-0.000000 | 0.17677670 | 0.35355339 | see qualification.json |
| design_005_seed_000 | 9 | void_side_probe | REJECT_CANDIDATE | +0.000000/-0.562500 | 0.17677670 | 0.35355339 | see qualification.json |

Exact source geometry is preserved in exact_geometry/. Only separately named opt-in policies produce manifold_candidate.wkb.
Subpixel ligaments remain physically unqualified. Matching frozen raster descriptors do not establish continuous equivalence.
The original v0.5A HOLD and prior v0.4.2 failure/v0.4.3 scoped amendment remain unchanged. No v0.5B work is included.
