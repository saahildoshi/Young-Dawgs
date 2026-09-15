#!/usr/bin/env python3
"""
Procedural generator for 256x256 binary disordered mechanical metamaterials.

White/solid is stored as 1.
Black/void is stored as 0.

The generator does NOT read a reference image. It creates an organic cellular
network from a filtered Gaussian random field, then performs topology-aware
procedural edits so that one 4-connected solid component dominates and spans
both image axes. The remaining solid budget is filled by small detached,
rounded fragments.

Dependencies:
    numpy
    scipy
    scikit-image
    Pillow

Default invocation:
    python generator.py

This generates:
    seeds 0, 1, ..., 19
    20 samples
    256x256 pixels

Held-out example:
    python generator.py \
        --seed-start 100 \
        --num-samples 20 \
        --output-dir held_out
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.draw import line


# ============================================================================
# Fixed output specification
# ============================================================================

SIZE = 256
N_PIXELS = SIZE * SIZE

# The supplied volume fraction corresponds to exactly 20374 solid pixels in
# a 256x256 image.
TARGET_SOLID_FRACTION = 0.310883
TARGET_LARGEST_COMPONENT_FRACTION = 0.876755

TARGET_SOLID_PIXELS = int(round(TARGET_SOLID_FRACTION * N_PIXELS))
TARGET_MAIN_PIXELS = int(
    round(TARGET_LARGEST_COMPONENT_FRACTION * TARGET_SOLID_PIXELS)
)
TARGET_DETACHED_PIXELS = TARGET_SOLID_PIXELS - TARGET_MAIN_PIXELS


# ============================================================================
# Adjustable morphology parameters
# ============================================================================
#
# FIELD_SIGMA controls the characteristic pore/strut length scale.
# Larger values give coarser structures and larger pores.
#
# BASE_PRECURSOR_FRACTION controls the width/density of the initial random
# network before connectivity repair.
#
# The values below are tuned for the supplied morphology/descriptors:
# thin ~2-3 pixel struts, pores of several pixels, short correlation length,
# and a dominant but not perfectly connected solid phase.
# ============================================================================

FIELD_SIGMA = 2.40
BASE_PRECURSOR_FRACTION = 0.29

# Weak second spatial scale makes cells less uniform and less Gaussian-looking.
SECOND_SCALE_WEIGHT = 0.12
SECOND_SCALE_FACTOR = 1.80

# Connectivity-repair controls.
BRIDGE_BATCH = 8
MAX_BRIDGE_LOOPS = 100

# Controls how growth is distributed around the main network.
# Higher values preferentially fill concave/thicker regions.
GROWTH_NEIGHBOR_WEIGHT = 0.30

# Statistics of small detached solid fragments.
BLOB_MEDIAN_RADIUS = 1.55
BLOB_LOG_SIGMA = 0.32
BLOB_RADIUS_MIN = 0.80
BLOB_RADIUS_MAX = 3.20

# Strict 4-neighbor connectivity.
FOUR_CONNECTED = ndi.generate_binary_structure(2, 1)


def _seed_sequence(seed: int, salt: int, attempt: int):
    """
    Deterministic seed derivation.

    Attempt zero deliberately uses only [seed, salt], so the nominal generation
    path depends directly on the requested integer seed. Later attempts are
    independent deterministic fallbacks for unusually difficult seeds.
    """
    if attempt == 0:
        return np.random.SeedSequence([int(seed), int(salt)])
    return np.random.SeedSequence([int(seed), int(salt), int(attempt)])


def _component_labels(solid: np.ndarray):
    """Return 4-connected labels, component sizes, and largest-component id."""
    labels, n_components = ndi.label(solid, structure=FOUR_CONNECTED)
    sizes = np.bincount(labels.ravel(), minlength=n_components + 1)

    if n_components == 0:
        return labels, sizes, 0

    largest_id = 1 + int(np.argmax(sizes[1:]))
    return labels, sizes, largest_id


def _make_precursor(seed: int, attempt: int = 0) -> np.ndarray:
    """
    Make an organic stochastic band network from a multiscale random field.

    Taking a band around the zero level set naturally produces a web/foam-like
    binary solid rather than isolated thresholded particles.
    """
    rng = np.random.default_rng(
        _seed_sequence(seed, 0x1234, attempt)
    )

    noise_1 = rng.standard_normal((SIZE, SIZE))
    noise_2 = rng.standard_normal((SIZE, SIZE))

    field = ndi.gaussian_filter(
        noise_1,
        sigma=FIELD_SIGMA,
        mode="wrap",
    )

    field += SECOND_SCALE_WEIGHT * ndi.gaussian_filter(
        noise_2,
        sigma=FIELD_SIGMA * SECOND_SCALE_FACTOR,
        mode="wrap",
    )

    field = (field - field.mean()) / (field.std() + 1.0e-12)

    # Since the field is continuous, a quantile of |field| gives a stable
    # precursor volume fraction while preserving completely stochastic shapes.
    threshold = np.quantile(
        np.abs(field),
        BASE_PRECURSOR_FRACTION,
    )

    solid = np.abs(field) <= threshold
    return solid


def _bridge_components(
    solid: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Procedurally join nearby 4-connected pieces.

    The largest current solid component is treated as the backbone. Euclidean
    distance transforms locate nearby components and short bridges are inserted
    until the backbone is dominant and reaches every image side.

    Diagonal raster steps are explicitly corner-filled, guaranteeing that all
    bridges are 4-connected rather than merely 8-connected.
    """
    height, width = solid.shape

    for _ in range(MAX_BRIDGE_LOOPS):
        labels, sizes, main_id = _component_labels(solid)

        main = labels == main_id
        main_size = int(sizes[main_id])
        detached_size = int(solid.sum()) - main_size

        touches_left = bool(main[:, 0].any())
        touches_right = bool(main[:, -1].any())
        touches_top = bool(main[0, :].any())
        touches_bottom = bool(main[-1, :].any())

        spans_both_axes = (
            touches_left
            and touches_right
            and touches_top
            and touches_bottom
        )

        if (
            detached_size <= TARGET_DETACHED_PIXELS
            and spans_both_axes
        ):
            return solid

        # Distance from every pixel to the current dominant component, plus
        # coordinates of the nearest dominant-component pixel.
        distance, nearest = ndi.distance_transform_edt(
            ~main,
            return_indices=True,
        )

        component_ids = np.arange(
            1,
            len(sizes),
            dtype=int,
        )
        component_ids = component_ids[
            component_ids != main_id
        ]

        if component_ids.size == 0:
            break

        # If the dominant component does not yet reach one or more boundaries,
        # first prefer components that already touch those boundaries.
        needed_ids = set()

        if not touches_left:
            needed_ids.update(
                np.unique(labels[:, 0]).tolist()
            )
        if not touches_right:
            needed_ids.update(
                np.unique(labels[:, -1]).tolist()
            )
        if not touches_top:
            needed_ids.update(
                np.unique(labels[0, :]).tolist()
            )
        if not touches_bottom:
            needed_ids.update(
                np.unique(labels[-1, :]).tolist()
            )

        needed_ids.discard(0)
        needed_ids.discard(main_id)

        if needed_ids:
            candidates = np.array(
                sorted(needed_ids),
                dtype=int,
            )
        else:
            candidates = component_ids

        min_distances = ndi.minimum(
            distance,
            labels=labels,
            index=candidates,
        )

        # Primary preference is geometric proximity. The tiny size term simply
        # prevents pathological tie behavior.
        order = np.argsort(
            min_distances
            + 0.0005 * np.sqrt(sizes[candidates])
        )

        chosen = []
        pixels_to_absorb = max(
            0,
            detached_size - TARGET_DETACHED_PIXELS,
        )
        absorbed = 0

        for j in order:
            cid = int(candidates[j])
            chosen.append(cid)
            absorbed += int(sizes[cid])

            if needed_ids:
                if len(chosen) >= min(
                    2,
                    BRIDGE_BATCH,
                ):
                    break
            else:
                if (
                    len(chosen) >= BRIDGE_BATCH
                    or absorbed
                    >= max(
                        256,
                        0.35 * pixels_to_absorb,
                    )
                ):
                    break

        for cid in chosen:
            ys, xs = np.where(labels == cid)

            nearest_idx = int(
                np.argmin(distance[ys, xs])
            )

            y = int(ys[nearest_idx])
            x = int(xs[nearest_idx])

            main_y = int(nearest[0, y, x])
            main_x = int(nearest[1, y, x])

            rr, cc = line(
                y,
                x,
                main_y,
                main_x,
            )

            solid[rr, cc] = True

            # Bresenham diagonal steps are only diagonally connected.
            # Add one of the two possible corner pixels so every bridge is
            # strictly 4-connected.
            for p in range(len(rr) - 1):
                dy = abs(
                    int(rr[p + 1]) - int(rr[p])
                )
                dx = abs(
                    int(cc[p + 1]) - int(cc[p])
                )

                if dy == 1 and dx == 1:
                    if rng.random() < 0.5:
                        solid[
                            rr[p],
                            cc[p + 1],
                        ] = True
                    else:
                        solid[
                            rr[p + 1],
                            cc[p],
                        ] = True

            # Occasional local thickening prevents repair bridges from looking
            # like conspicuous one-pixel artificial wires.
            if (
                len(rr) > 1
                and rng.random() < 0.5
            ):
                p = len(rr) // 2
                y0 = int(rr[p])
                x0 = int(cc[p])

                neighbors = [
                    (y0 - 1, x0),
                    (y0 + 1, x0),
                    (y0, x0 - 1),
                    (y0, x0 + 1),
                ]
                rng.shuffle(neighbors)

                for yy, xx in neighbors:
                    if (
                        0 <= yy < height
                        and 0 <= xx < width
                    ):
                        solid[yy, xx] = True
                        break

    return solid


def _grow_main_toward_target(
    solid: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Grow the dominant component toward the requested dominant-solid count.

    A one-pixel moat around every detached component prevents this operation
    from accidentally absorbing the intentionally disconnected material.
    """
    for _ in range(50):
        labels, sizes, main_id = _component_labels(
            solid
        )

        main_size = int(sizes[main_id])

        if main_size >= TARGET_MAIN_PIXELS:
            return solid

        main = labels == main_id
        other_solid = solid & ~main

        candidates = (
            ndi.binary_dilation(
                main,
                structure=FOUR_CONNECTED,
            )
            & ~solid
        )

        # Do not allow growth to merge the backbone into any detached piece.
        forbidden = ndi.binary_dilation(
            other_solid,
            structure=FOUR_CONNECTED,
        )
        candidates &= ~forbidden

        coords = np.argwhere(candidates)

        if coords.size == 0:
            break

        remaining = (
            TARGET_MAIN_PIXELS - main_size
        )

        # Local neighbor count supplies mild curvature/thickness control.
        n8 = ndi.convolve(
            main.astype(np.uint8),
            np.ones((3, 3), dtype=np.uint8),
            mode="constant",
        )

        score = (
            GROWTH_NEIGHBOR_WEIGHT
            * n8[
                coords[:, 0],
                coords[:, 1],
            ].astype(float)
            + 0.75 * rng.random(len(coords))
        )

        k = min(
            remaining,
            len(coords),
            max(
                64,
                min(1024, remaining),
            ),
        )

        if k == len(coords):
            selected = coords
        else:
            idx = np.argpartition(
                score,
                -k,
            )[-k:]
            selected = coords[idx]

        solid[
            selected[:, 0],
            selected[:, 1],
        ] = True

    return solid


def _add_detached_blobs(
    solid: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Fill the remaining solid-volume budget with rounded detached fragments.

    Every inserted fragment retains a one-pixel 4-neighbor moat, so it cannot
    join the spanning backbone or another detached component.
    """
    height, width = solid.shape
    need = TARGET_SOLID_PIXELS - int(
        solid.sum()
    )

    attempts = 0

    while need > 0 and attempts < 50000:
        attempts += 1

        cy = int(
            rng.integers(
                2,
                height - 2,
            )
        )
        cx = int(
            rng.integers(
                2,
                width - 2,
            )
        )

        if solid[cy, cx]:
            continue

        radius = float(
            np.clip(
                rng.lognormal(
                    np.log(BLOB_MEDIAN_RADIUS),
                    BLOB_LOG_SIGMA,
                ),
                BLOB_RADIUS_MIN,
                BLOB_RADIUS_MAX,
            )
        )

        ry = radius * float(
            rng.uniform(0.75, 1.30)
        )
        rx = radius * float(
            rng.uniform(0.75, 1.30)
        )

        pad = (
            int(np.ceil(max(rx, ry)))
            + 2
        )

        y0 = max(0, cy - pad)
        y1 = min(
            height,
            cy + pad + 1,
        )
        x0 = max(0, cx - pad)
        x1 = min(
            width,
            cx + pad + 1,
        )

        yy, xx = np.ogrid[
            y0:y1,
            x0:x1,
        ]

        blob = (
            ((yy - cy) / ry) ** 2
            + ((xx - cx) / rx) ** 2
            <= 1.0
        )

        if not blob.any():
            continue

        guard = ndi.binary_dilation(
            blob,
            structure=FOUR_CONNECTED,
        )

        sub = solid[
            y0:y1,
            x0:x1,
        ]

        if np.any(sub & guard):
            continue

        n_blob = int(blob.sum())

        if n_blob <= need:
            sub[blob] = True
            need -= n_blob

        elif need <= 4:
            # Handle a very small final remainder using central pixels of a
            # blob whose surrounding moat is already known to be empty.
            pixels = np.argwhere(blob)

            d2 = (
                (
                    pixels[:, 0]
                    - (cy - y0)
                )
                ** 2
                + (
                    pixels[:, 1]
                    - (cx - x0)
                )
                ** 2
            )

            pixels = pixels[
                np.argsort(d2)[:need]
            ]

            tiny = np.zeros_like(blob)
            tiny[
                pixels[:, 0],
                pixels[:, 1],
            ] = True

            tiny_guard = ndi.binary_dilation(
                tiny,
                structure=FOUR_CONNECTED,
            )

            if not np.any(
                sub & tiny_guard
            ):
                sub[tiny] = True
                need = 0

    # Conservative fallback for a rare awkward remainder.
    if need > 0:
        candidates = np.argwhere(
            ~solid
            & ~ndi.binary_dilation(
                solid,
                structure=FOUR_CONNECTED,
            )
        )

        rng.shuffle(candidates)

        for y, x in candidates:
            if need <= 0:
                break

            y = int(y)
            x = int(x)

            # Re-check against the current image because fallback pixels are
            # inserted sequentially.
            vertical_touch = solid[
                max(0, y - 1):
                min(height, y + 2),
                x,
            ].any()

            horizontal_touch = solid[
                y,
                max(0, x - 1):
                min(width, x + 2),
            ].any()

            if (
                not solid[y, x]
                and not vertical_touch
                and not horizontal_touch
            ):
                solid[y, x] = True
                need -= 1

    if need != 0:
        raise RuntimeError(
            "Could not satisfy the requested "
            "solid-pixel budget."
        )

    return solid


def _valid_structure(
    solid: np.ndarray,
) -> bool:
    """
    Check the hard requirements used by this generator.

    The dominant component must itself touch left/right and top/bottom.
    """
    if solid.shape != (
        SIZE,
        SIZE,
    ):
        return False

    if int(solid.sum()) != TARGET_SOLID_PIXELS:
        return False

    labels, sizes, main_id = _component_labels(
        solid
    )

    if main_id == 0:
        return False

    main = labels == main_id

    left_right = bool(
        main[:, 0].any()
        and main[:, -1].any()
    )
    top_bottom = bool(
        main[0, :].any()
        and main[-1, :].any()
    )

    dominant_fraction = (
        float(sizes[main_id])
        / float(solid.sum())
    )

    return (
        left_right
        and top_bottom
        and dominant_fraction >= 0.80
    )


def generate_microstructure(
    seed: int,
) -> np.ndarray:
    """
    Generate one deterministic stochastic realization for an integer seed.

    Different seeds use independent Gaussian fields and stochastic topology
    edits. A retry is only used as a robustness guard for an unusual seed.
    """
    for attempt in range(4):
        rng = np.random.default_rng(
            _seed_sequence(
                seed,
                0xA5A5,
                attempt,
            )
        )

        solid = _make_precursor(
            seed,
            attempt=attempt,
        )

        solid = _bridge_components(
            solid,
            rng,
        )

        solid = _grow_main_toward_target(
            solid,
            rng,
        )

        # With the tuned parameters this normally remains below the final
        # volume budget. If an unusually dense topology repair overshoots it,
        # regenerate from an independent stochastic realization rather than
        # risk damaging 4-connectivity by arbitrary deletion.
        if (
            int(solid.sum())
            > TARGET_SOLID_PIXELS
        ):
            continue

        solid = _add_detached_blobs(
            solid,
            rng,
        )

        if _valid_structure(solid):
            return solid.astype(
                np.uint8
            )

    raise RuntimeError(
        f"Failed to generate a valid "
        f"structure for seed {seed}."
    )


def save_sample(
    sample: np.ndarray,
    seed: int,
    output_dir: Path,
) -> None:
    """
    Save both:
        microstructure_seed_<seed>.npy
        microstructure_seed_<seed>.png

    NPY contains uint8 values 0 and 1.
    PNG contains 0 and 255 for black void and white solid.
    """
    stem = (
        f"microstructure_seed_{seed}"
    )

    np.save(
        output_dir / f"{stem}.npy",
        sample.astype(
            np.uint8,
            copy=False,
        ),
    )

    Image.fromarray(
        (
            sample.astype(np.uint8)
            * 255
        )
    ).save(
        output_dir / f"{stem}.png"
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate stochastic 256x256 "
            "binary metamaterial microstructures."
        )
    )

    parser.add_argument(
        "--seed-start",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--num-samples",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("microstructures"),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.num_samples < 1:
        raise ValueError(
            "--num-samples must be at least 1"
        )

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    seed_stop = (
        args.seed_start
        + args.num_samples
    )

    for seed in range(
        args.seed_start,
        seed_stop,
    ):
        sample = generate_microstructure(
            seed
        )

        save_sample(
            sample,
            seed,
            args.output_dir,
        )

        print(
            f"saved seed {seed}: "
            f"{int(sample.sum())} solid pixels"
        )


if __name__ == "__main__":
    main()
