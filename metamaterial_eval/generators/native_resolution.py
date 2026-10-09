"""Native-resolution continuation of the successful v0.3 cellular generator.

Coordinates, sigmas, amplitudes and distance scores use baseline-pixel units
(1 unit = 1/256 domain length); the raster samples them at spacing 256/N.
No completed binary image is resized. v0.3 is retained byte-for-byte separately.
"""
from copy import deepcopy
from functools import lru_cache
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from . import v03_baseline as baseline
from ..pipeline.resolution import BASE_RESOLUTION, resolution_scale, validate_resolution

SOURCE_V03_SHA256 = "61304070aad94b8eb4595c65ce61dc9cab35fe14caada60bc4526fb0175f3839"
GENERATOR_VERSION = "0.4.0"


def _field(rng, grid_size, blur, resolution):
    """Same latent values and normalization as v0.3, continuously sampled.

    Fixed 20/42/15/34 latent grid counts represent spatial frequencies, not
    output pixel counts. v0.3's smoothed continuous 256-grid field is the
    canonical latent representation; ONLY this floating field is interpolated.
    """
    latent = baseline._smooth_field(rng, grid_size, blur)
    coordinates = np.indices((resolution, resolution), dtype=float) / resolution_scale(resolution)
    return ndi.map_coordinates(latent, coordinates, order=3, mode="reflect")


def _valid(array):
    _, count = ndi.label(array, structure=ndi.generate_binary_structure(2, 1))
    return bool(count == 1 and array[0].any() and array[-1].any()
                and array[:, 0].any() and array[:, -1].any())


@lru_cache(maxsize=32)
def _select(seed, phi, strut, pore):
    """Fix accepted v0.3 candidate and RNG state across ALL render resolutions.

    The baseline acceptance gate is retained solely to choose the SAME latent
    realization as v0.3. High-N outputs are independently evaluated by frozen
    evaluator v1.1; no resolution-dependent rejection selects a new realization.
    """
    rng = np.random.default_rng(seed)
    for attempt in range(32):
        state = deepcopy(rng.bit_generator.state)
        solid = baseline._draw_candidate(rng, phi, strut, pore)
        if _valid(solid) and baseline._within_family(solid):
            solid.setflags(write=False)
            return state, solid, attempt
    raise RuntimeError("No valid baseline realization after 32 v0.3 attempts.")


def generate_microstructure(seed, solid_fraction_target, strut_scale, pore_scale, resolution=256):
    """Preserve baseline controls; resolution changes sampling, not design."""
    n = validate_resolution(resolution)
    phi, strut, pore = map(float, (solid_fraction_target, strut_scale, pore_scale))
    if not all(np.isfinite([phi, strut, pore])) or not (0 < phi < 1 and strut > 0 and pore > 0):
        raise ValueError("Require finite 0 < solid fraction < 1 and positive scales.")
    state, base, _ = _select(seed, phi, strut, pore)
    if n == BASE_RESOLUTION:
        return base.copy()
    rng = np.random.default_rng()
    rng.bit_generator.state = deepcopy(state)
    result = _render_native(rng, phi, strut, pore, n)
    if not _valid(result):
        raise RuntimeError("Matched native realization fails single-component spanning topology; "
                           "no new seed, island removal or bridging was substituted.")
    return result


generate_microstructure_at_resolution = generate_microstructure

def _render_native(rng, phi, strut_scale, pore_scale, resolution):
    """Generate one stochastic cellular-wall candidate."""
    side = resolution
    scale = resolution_scale(side)

    # Both characteristic scales influence cellular spacing.
    # The density term compensates for excessive thickening
    # at higher solid fractions.
    pitch = (
        13.25
        * (pore_scale / 7.211102550927978) ** 0.82
        * (strut_scale / 4.112623910345319) ** 0.44
        * (1.0 - 1.2 * (phi - 0.4773406982421875))
    )

    if pitch <= 0.0:
        raise ValueError(
            "The scale/density combination has invalid pitch."
        )

    # Generate random nuclei beyond the image boundaries.
    # This avoids requiring an artificial perimeter frame.
    margin = 2.5 * pitch

    site_count = max(
        4,
        int(round(
            ((BASE_RESOLUTION + 2.0 * margin) / pitch) ** 2
        )),
    )

    sites = rng.uniform(
        -margin,
        BASE_RESOLUTION + margin,
        (site_count, 2),
    )

    # Mild short-range repulsion.
    # This reduces extreme clustering while retaining
    # stochastic variation in Voronoi cell sizes.
    exclusion = 0.72 * pitch

    for _ in range(7):
        pairs = np.asarray(
            sorted(
                cKDTree(sites).query_pairs(exclusion)
            ),
            dtype=np.intp,
        ).reshape(-1, 2)

        if pairs.size == 0:
            break

        i, j = pairs[:, 0], pairs[:, 1]

        delta = sites[i] - sites[j]

        separation = np.maximum(
            np.linalg.norm(delta, axis=1),
            1.0e-9,
        )

        shift = (
            0.28
            * (exclusion - separation)
            / separation
        )[:, None] * delta

        motion = np.zeros_like(sites)

        np.add.at(motion, i, shift)
        np.add.at(motion, j, -shift)

        sites += motion

    # Smooth coordinate deformation at two spatial scales.
    # Different seeds change the cellular topology and
    # pore geometry, not merely their translation.
    warp_amplitude = (
        1.7 * (pitch / 13.0) ** 0.75
    )

    warp_y = warp_amplitude * (
        _field(rng, 20, 1.0, side)
        + 0.25 * _field(rng, 42, 1.0, side)
    )

    warp_x = warp_amplitude * (
        _field(rng, 20, 1.0, side)
        + 0.25 * _field(rng, 42, 1.0, side)
    )

    yy, xx = np.indices(
        (side, side),
        dtype=np.float64,
    )

    warped_y = yy / scale + warp_y
    warped_x = xx / scale + warp_x

    positions = np.column_stack((
        warped_y.ravel(),
        warped_x.ravel(),
    ))

    # Assign each pixel to its nearest stochastic nucleus.
    _, nearest_id = cKDTree(sites).query(
        positions,
        k=1,
    )

    cells = nearest_id.reshape(side, side)

    # Construct the solid cellular interfaces.
    # Pixels on either side of a label transition
    # are retained as solid.
    wall = np.zeros(
        (side, side),
        dtype=bool,
    )

    change = (
        cells[1:, :] != cells[:-1, :]
    )

    wall[1:, :] |= change
    wall[:-1, :] |= change

    change = (
        cells[:, 1:] != cells[:, :-1]
    )

    wall[:, 1:] |= change
    wall[:, :-1] |= change

    # Coordinates relative to each pixel's assigned nucleus.
    dy = warped_y - sites[cells, 0]
    dx = warped_x - sites[cells, 1]

    theta = np.arctan2(dy, dx)
    radial_distance = np.hypot(dy, dx)

    # Independent stochastic cell-shape coefficients.
    # Second and third angular harmonics produce
    # elongated, rounded, and gently lobed pore forms.
    harmonics = rng.standard_normal(
        (site_count, 4)
    )

    angular_variation = (
        0.13 * (
            harmonics[cells, 0]
            * np.cos(2.0 * theta)
            + harmonics[cells, 1]
            * np.sin(2.0 * theta)
        )
        + 0.055 * (
            harmonics[cells, 2]
            * np.cos(3.0 * theta)
            + harmonics[cells, 3]
            * np.sin(3.0 * theta)
        )
    )

    size_variation = np.exp(
        0.18 * rng.standard_normal(site_count)
    )

    radial_score = radial_distance / (
        size_variation[cells]
        * np.exp(angular_variation)
    )

    # Distance from the cellular interface.
    distance_to_wall = ndi.distance_transform_edt(~wall) / scale
    # v0.3 paints BOTH sides of each label transition (two baseline pixels).
    # Restore this baseline physical interface footprint on the native grid.
    # This is native EDT geometry, not enlargement of a finished binary image.
    interface_buffer = 1.0 - 1.0 / scale
    wall = distance_to_wall <= interface_buffer
    distance_to_wall = np.maximum(distance_to_wall - interface_buffer, 0.0)

    # Correlated spatial variation in local wall geometry.
    width_variation = np.exp(
        0.14 * _field(rng, 15, 2.0, side)
        + 0.08 * _field(rng, 34, 1.0, side)
    )

    # Higher scores favor void.
    # The interface-distance contribution preserves
    # a cellular network; the radial contribution rounds
    # the pores and introduces variation in their shapes.
    pore_score = (
        0.80
        * distance_to_wall
        / width_variation
        - 0.20 * radial_score
    )

    # Cellular interfaces cannot become void.
    # This prevents neighboring pores from merging
    # across the constructed walls.
    eligible = ~wall

    requested_void_pixels = int(
        round((1.0 - phi) * side * side)
    )

    available_scores = pore_score[eligible]

    if not (
        0 < requested_void_pixels < available_scores.size
    ):
        raise ValueError(
            "Requested density is infeasible "
            "for this cellular partition."
        )

    # Use a density quantile to control solid fraction.
    # No matching to the reference's strut thickness,
    # pore diameter, S2, or lineal-path values occurs here.
    threshold_index = (
        available_scores.size - requested_void_pixels
    )

    threshold = np.partition(
        available_scores,
        threshold_index,
    )[threshold_index]

    void = eligible & (pore_score >= threshold)

    return (~void).astype(np.uint8)
