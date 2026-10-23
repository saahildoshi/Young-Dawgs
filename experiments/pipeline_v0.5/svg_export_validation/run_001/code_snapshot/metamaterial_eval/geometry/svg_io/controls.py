"""Analytic SVG controls; no procedural research sources are generated."""
import numpy as np
from shapely import MultiPolygon, Polygon, box
from shapely.affinity import translate

from ..conversion import convert_exact
from ..manifold.candidates import qualify_manifold_geometry


STATUSES = {"overall_scientific": "HOLD_SMALL_PORE_POLICY", "cumulative_small_pore_fidelity": "UNQUALIFIED",
            "production_simplification": "HOLD_UNQUALIFIED", "cad_kernel_interoperability": "UNQUALIFIED",
            "FEM": "UNQUALIFIED", "manufacturing": "UNQUALIFIED"}


def metadata(g, name="synthetic", n=1024):
    from hashlib import sha256
    return {"source_id": name, "source_state": "G2", "source_geometry_sha256": sha256(g.wkb).hexdigest(),
            "canonical_raster_sha256": "0" * 64, "resolution": n, "physical_scale": None,
            "source_scientific_qualification": dict(STATUSES), "source_kind": "analytic_control_no_new_generator_output"}


def repaired_control():
    mask = np.ones((256, 256), np.uint8)
    mask[100:104, 100:104] = 0; mask[104:108, 104:108] = 0
    exact = convert_exact(mask)
    result = qualify_manifold_geometry(mask, exact, "solid_separate_contacts")
    assert result["accepted"]
    return translate(result["geometry"], 700, 700)


def analytic_cases():
    cases = {
        "integer_rectangle": box(10, 20, 80, 90),
        "half_integer": box(10.5, 20.5, 80.5, 90.5),
        "quarter_cell": Polygon([(10.25, 20.75), (80.5, 20.25), (50.75, 90.5)]),
        "non_dyadic_binary64": Polygon([(10.1, 20.3), (80.7, 20.2), (50.9, 90.1)]),
        "subpixel_diamond": Polygon([(500, 499.875), (500.125, 500), (500, 500.125), (499.875, 500)]),
        "nearby_pores": box(10, 10, 90, 90).difference(MultiPolygon([box(20, 20, 40, 40), box(40 + 2**-25, 20, 60, 40)])),
        "nearly_touching_shell": box(10, 10, 90, 90).difference(box(10 + 2**-25, 20, 40, 40)),
        "concentric_nested_islands": MultiPolygon([box(10, 10, 100, 100).difference(box(20, 20, 90, 90)), box(30, 30, 80, 80).difference(box(40, 40, 70, 70)), box(50, 50, 60, 60)]),
        "near_domain_edge": box(1023.125, 1023.375, 1024 - 2**-20, 1024),
        "very_short_collinear_edge": Polygon([(10, 10), (10 + 2**-30, 10), (80, 10), (80, 80), (10, 80)]),
        "acute_corner": Polygon([(20, 20), (1000, 20.00001), (21, 21)]),
        "several_holes": box(10, 10, 100, 100).difference(MultiPolygon([box(20, 20, 30, 30), box(40, 40, 60, 70), box(80, 20, 90, 30)])),
        "single_hole": box(10, 10, 100, 100).difference(box(20, 20, 60, 60)),
        "multiple_solid_components": MultiPolygon([box(10, 10, 20, 20), box(30, 30, 60, 60)]),
        "deep_concavity": Polygon([(10, 10), (100, 10), (100, 100), (70, 100), (70, 30), (40, 30), (40, 100), (10, 100)]),
        "narrow_exterior_channel": Polygon([(10, 10), (100, 10), (100, 100), (50 + 2**-20, 100), (50 + 2**-20, 30), (50, 30), (50, 100), (10, 100)]),
        "one_cell_interior_pore": box(10, 10, 100, 100).difference(box(50, 50, 51, 51)),
    }
    angle = np.linspace(0, 2 * np.pi, 4096, endpoint=False)
    radius = 300 + 15 * np.cos(7 * angle)
    cases["thousands_of_vertices"] = Polygon(np.c_[512 + radius * np.cos(angle), 512 + radius * np.sin(angle)])
    cases["hundreds_of_holes"] = Polygon(box(10, 10, 1010, 1010).exterior.coords,
        [box(30 + 45 * x, 30 + 45 * y, 38 + 45 * x, 38 + 45 * y).exterior.coords for y in range(20) for x in range(20)])
    cases["manifold_regularized_contact"] = repaired_control()
    return cases

