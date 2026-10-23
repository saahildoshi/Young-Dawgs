"""Parametric exploration — stochastic connected cellular microstructures.

Public interface:
    generate_microstructure(
        seed, solid_fraction_target, strut_scale, pore_scale
    )

Returns:
    numpy.ndarray, shape (256, 256), dtype uint8
    1 = solid, 0 = void

No file I/O, plotting, external data, or import-time generation.
"""

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree


def _smooth_field(rng, grid_size, blur):
    """Generate a normalized spatially correlated random field."""
    coarse = rng.standard_normal((grid_size, grid_size))

    field = ndi.zoom(
        coarse,
        (256.0 / grid_size, 256.0 / grid_size),
        order=3,
        mode="reflect",
    )

    if blur > 0.0:
        field = ndi.gaussian_filter(
            field, blur, mode="reflect"
        )

    field -= field.mean()
    field /= field.std() + 1.0e-12

    return field


def _draw_candidate(rng, phi, strut_scale, pore_scale):
    """Generate one stochastic cellular-wall candidate."""
    side = 256

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
            ((side + 2.0 * margin) / pitch) ** 2
        )),
    )

    sites = rng.uniform(
        -margin,
        side + margin,
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
        _smooth_field(rng, 20, 1.0)
        + 0.25 * _smooth_field(rng, 42, 1.0)
    )

    warp_x = warp_amplitude * (
        _smooth_field(rng, 20, 1.0)
        + 0.25 * _smooth_field(rng, 42, 1.0)
    )

    yy, xx = np.indices(
        (side, side),
        dtype=np.float64,
    )

    warped_y = yy + warp_y
    warped_x = xx + warp_x

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
    distance_to_wall = ndi.distance_transform_edt(
        ~wall
    )

    # Correlated spatial variation in local wall geometry.
    width_variation = np.exp(
        0.14 * _smooth_field(rng, 15, 2.0)
        + 0.08 * _smooth_field(rng, 34, 1.0)
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


def _within_family(solid):
    """Evaluate the provisional morphology-family gates.

    S2: periodic autocorrelation, radially averaged using
        integer-offset shells of radius +/- 0.5 pixels.

    Lineal path: periodic intersections over four directions:
        horizontal, vertical, and both diagonals.

    Samples are accepted based on gate membership only.
    Their errors are not minimized toward zero.
    """
    radii = (0, 1, 2, 4, 8, 16, 32, 64)

    target_s2 = np.array([
        0.4773406982421875,
        0.3947792053222656,
        0.33225250244140625,
        0.2364339828491211,
        0.21403948465983072,
        0.22579738071986608,
        0.22819389180934174,
        0.22817278775301847,
    ])

    target_lineal = np.array([
        0.4773406982421875,
        0.3947792053222656,
        0.3141937255859375,
        0.19487762451171875,
        0.08710479736328125,
        0.01860809326171875,
        0.001361846923828125,
        0.0,
    ])

    # Periodic two-point correlation via FFT.
    as_float = solid.astype(np.float64)

    F = np.fft.fft2(as_float)

    autocorrelation = (
        np.fft.ifft2(np.abs(F) ** 2).real
        / solid.size
    )

    offsets = np.fft.fftfreq(256) * 256

    yy, xx = np.meshgrid(
        offsets,
        offsets,
        indexing="ij",
    )

    distances = np.hypot(yy, xx)

    s2 = np.array([
        autocorrelation[
            np.abs(distances - radius) <= 0.5
        ].mean()
        for radius in radii
    ])

    # Four-direction periodic lineal-path probability.
    as_bool = solid.astype(bool)

    lineal = np.empty(
        len(radii),
        dtype=np.float64,
    )

    lineal[0] = as_bool.mean()

    samples = {
        radius: []
        for radius in radii[1:]
    }

    directions = (
        (0, 1),
        (1, 0),
        (1, 1),
        (1, -1),
    )

    for dy, dx in directions:
        segment = as_bool.copy()

        for length in range(1, 65):
            segment &= np.roll(
                as_bool,
                (length * dy, length * dx),
                axis=(0, 1),
            )

            if length in samples:
                samples[length].append(
                    segment.mean()
                )

    for j, radius in enumerate(
        radii[1:],
        start=1,
    ):
        lineal[j] = np.mean(
            samples[radius]
        )

    # Normalized RMSE, equivalent to the ratio
    # of the corresponding Euclidean norms.
    s2_error = (
        np.linalg.norm(s2 - target_s2)
        / np.linalg.norm(target_s2)
    )

    lineal_error = (
        np.linalg.norm(lineal - target_lineal)
        / np.linalg.norm(target_lineal)
    )

    return (
        s2_error <= 0.25
        and lineal_error <= 0.25
    )


def generate_microstructure(
    seed,
    solid_fraction_target,
    strut_scale,
    pore_scale,
):
    """Return a binary, connected, spanning 256x256 microstructure.

    All solid pixels must belong to one 4-connected component.
    That component must span both image axes.

    The local RNG ensures reproducibility.
    Invalid candidates are discarded, not repaired.
    """
    phi = float(solid_fraction_target)
    strut = float(strut_scale)
    pore = float(pore_scale)

    if not (
        np.isfinite(phi)
        and np.isfinite(strut)
        and np.isfinite(pore)
    ):
        raise ValueError(
            "All three controls must be finite."
        )

    if not (
        0.0 < phi < 1.0
        and strut > 0.0
        and pore > 0.0
    ):
        raise ValueError(
            "Require 0 < solid fraction < 1 "
            "and positive characteristic scales."
        )

    rng = np.random.default_rng(seed)

    four_neighbors = np.array([
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
    ], dtype=np.uint8)

    # Deterministic rejection sampling.
    # Never attach islands or insert artificial bridges
    # to repair a disconnected realization.
    for _ in range(32):
        solid = _draw_candidate(
            rng,
            phi,
            strut,
            pore,
        )

        _, component_count = ndi.label(
            solid,
            structure=four_neighbors,
        )

        if component_count != 1:
            continue

        # With one connected component touching both
        # opposing boundaries, the corresponding spanning
        # path must exist.
        if not (
            solid[:, 0].any()
            and solid[:, -1].any()
            and solid[0, :].any()
            and solid[-1, :].any()
        ):
            continue

        if not _within_family(solid):
            continue

        return solid

    raise RuntimeError(
        "Could not generate a spanning, 4-connected "
        "sample inside the morphology-family gates "
        "after 32 deterministic attempts."
    )
