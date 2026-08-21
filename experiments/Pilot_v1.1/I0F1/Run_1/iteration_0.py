"""
Procedural generator for binary cellular microstructures.

Algorithm
---------
The reference morphology is approximated with a stochastic warped-cell model:

1. Random nuclei are placed in a 256x256 domain.
2. A Voronoi-like cell tessellation is constructed from the nuclei.
3. The coordinate system is distorted by two smooth random displacement fields,
   making the cell boundaries irregular instead of perfectly straight Voronoi
   edges.
4. Interfaces between neighboring cells are detected.
5. Those interfaces are thickened into a connected void-channel network using
   a Euclidean distance transform.
6. A separate smooth random field modulates the local channel width.
7. The remaining cell interiors are assigned to the solid phase.

Every realization is generated entirely from random geometry/random fields.
The reference image is NOT read, embedded, traced, or accessed at runtime.

Output convention
-----------------
    solid = 1
    void  = 0

Twenty realizations are generated with random seeds 0 through 19. Each is saved
as both .npy and .png.

PNG files use palette indices 0 and 1 directly:
    index 0 = void  (displayed white)
    index 1 = solid (displayed black)

Dependencies
------------
    numpy
    scipy
    Pillow

Adjustable parameters
---------------------
BASE_NUCLEI:
    Controls characteristic feature size. More nuclei -> smaller solid regions.

COARSE_WARP_AMPLITUDE / COARSE_WARP_SIGMA:
    Control large-scale bending and irregularity of cell boundaries.

FINE_WARP_AMPLITUDE / FINE_WARP_SIGMA:
    Add smaller-scale boundary roughness.

CHANNEL_HALF_WIDTH:
    Primary control of void-channel thickness and therefore solid fraction.
    Increasing this value creates wider void channels and less solid.

CHANNEL_WIDTH_JITTER / CHANNEL_WIDTH_SIGMA:
    Control spatial variability of channel thickness.
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree


# ============================================================================
# Adjustable parameters
# ============================================================================

SIZE = 256
N_SAMPLES = 20

OUTPUT_DIR = Path("generated_microstructures")

# Typical number of random cell nuclei.
BASE_NUCLEI = 68

# Small sample-to-sample variation in the number of cells.
NUCLEI_JITTER = 3

# Large-scale smooth distortion of the cellular geometry.
COARSE_WARP_SIGMA = 14.0
COARSE_WARP_AMPLITUDE = 3.5

# Finer distortion that prevents overly idealized polygonal boundaries.
FINE_WARP_SIGMA = 4.0
FINE_WARP_AMPLITUDE = 0.8

# Approximate half-width of the connected void-channel network, in pixels.
CHANNEL_HALF_WIDTH = 2.80

# Spatial variation in channel thickness.
CHANNEL_WIDTH_JITTER = 0.50
CHANNEL_WIDTH_SIGMA = 24.0

# Safety limits on local half-width.
MIN_HALF_WIDTH = 1.6
MAX_HALF_WIDTH = 4.0


# ============================================================================
# Procedural generation functions
# ============================================================================

def normalized_smooth_noise(rng, shape, sigma):
    """
    Generate a periodic, smooth Gaussian random field with mean 0 and std 1.
    """
    field = rng.standard_normal(shape)
    field = gaussian_filter(field, sigma=sigma, mode="wrap")

    field -= field.mean()
    std = field.std()

    if std < 1e-12:
        return np.zeros(shape, dtype=np.float64)

    return field / std


def periodic_distance_to_mask(mask):
    """
    Compute Euclidean distance to a boolean mask with periodic boundaries.

    The mask is tiled 3x3 and the center tile is retained. This removes
    artificial distance-transform effects at the outer borders.
    """
    h, w = mask.shape

    tiled_mask = np.tile(mask, (3, 3))
    tiled_distance = distance_transform_edt(~tiled_mask)

    return tiled_distance[h:2 * h, w:2 * w]


def make_warp_field(rng, shape):
    """
    Produce independent x/y displacement fields with coarse and fine scales.
    """
    coarse_y = normalized_smooth_noise(
        rng, shape, COARSE_WARP_SIGMA
    )
    coarse_x = normalized_smooth_noise(
        rng, shape, COARSE_WARP_SIGMA
    )

    fine_y = normalized_smooth_noise(
        rng, shape, FINE_WARP_SIGMA
    )
    fine_x = normalized_smooth_noise(
        rng, shape, FINE_WARP_SIGMA
    )

    dy = (
        COARSE_WARP_AMPLITUDE * coarse_y
        + FINE_WARP_AMPLITUDE * fine_y
    )

    dx = (
        COARSE_WARP_AMPLITUDE * coarse_x
        + FINE_WARP_AMPLITUDE * fine_x
    )

    return dy, dx


def generate_microstructure(seed):
    """
    Generate one stochastic SIZE x SIZE binary microstructure.

    Returns
    -------
    solid : np.ndarray, dtype uint8
        Values are exactly:
            1 = solid
            0 = void
    """
    rng = np.random.default_rng(seed)

    shape = (SIZE, SIZE)

    # ----------------------------------------------------------------------
    # 1. Generate a new random population of cell nuclei.
    # ----------------------------------------------------------------------

    n_nuclei = BASE_NUCLEI + int(
        rng.integers(-NUCLEI_JITTER, NUCLEI_JITTER + 1)
    )

    nuclei = rng.uniform(
        0.0,
        float(SIZE),
        size=(n_nuclei, 2),
    )

    # ----------------------------------------------------------------------
    # 2. Construct smoothly warped coordinates.
    # ----------------------------------------------------------------------

    yy, xx = np.indices(shape, dtype=np.float64)

    dy, dx = make_warp_field(rng, shape)

    warped_y = np.mod(yy + dy, SIZE)
    warped_x = np.mod(xx + dx, SIZE)

    query_points = np.column_stack(
        (
            warped_y.ravel(),
            warped_x.ravel(),
        )
    )

    # ----------------------------------------------------------------------
    # 3. Periodic Voronoi-like nearest-nucleus assignment.
    #
    #    Because the pixel coordinates are evaluated after stochastic spatial
    #    warping, the resulting interfaces are curved/irregular rather than
    #    ideal straight Voronoi boundaries.
    # ----------------------------------------------------------------------

    tree = cKDTree(
        nuclei,
        boxsize=(SIZE, SIZE),
    )

    _, labels = tree.query(
        query_points,
        k=1,
    )

    labels = labels.reshape(shape)

    # ----------------------------------------------------------------------
    # 4. Rasterize interfaces between neighboring cells.
    # ----------------------------------------------------------------------

    interface = np.zeros(shape, dtype=bool)

    for axis in (0, 1):
        interface |= labels != np.roll(labels, 1, axis=axis)
        interface |= labels != np.roll(labels, -1, axis=axis)

    # ----------------------------------------------------------------------
    # 5. Compute distance from each pixel to the cell-interface network.
    # ----------------------------------------------------------------------

    distance = periodic_distance_to_mask(interface)

    # ----------------------------------------------------------------------
    # 6. Make the void-channel thickness spatially nonuniform.
    # ----------------------------------------------------------------------

    width_noise = normalized_smooth_noise(
        rng,
        shape,
        CHANNEL_WIDTH_SIGMA,
    )

    local_half_width = (
        CHANNEL_HALF_WIDTH
        + CHANNEL_WIDTH_JITTER * width_noise
    )

    local_half_width = np.clip(
        local_half_width,
        MIN_HALF_WIDTH,
        MAX_HALF_WIDTH,
    )

    # ----------------------------------------------------------------------
    # 7. Pixels sufficiently far inside cells become solid.
    #    Interface neighborhoods become connected void channels.
    # ----------------------------------------------------------------------

    solid = distance > local_half_width

    return solid.astype(np.uint8)


# ============================================================================
# Output functions
# ============================================================================

def save_binary_png(array01, filename):
    """
    Save a binary PNG while retaining phase indices exactly as 0 and 1.

    Palette:
        0 -> white (void)
        1 -> black (solid)

    Thus the stored palette indices remain consistent with the NPY phase
    convention while the displayed image resembles the black-solid /
    white-void appearance of the reference.
    """
    if array01.dtype != np.uint8:
        array01 = array01.astype(np.uint8)

    if not np.all((array01 == 0) | (array01 == 1)):
        raise ValueError("PNG input must contain only binary values 0 and 1.")

    image = Image.fromarray(array01, mode="P")

    # Complete 256-entry RGB palette.
    palette = [
        255, 255, 255,  # palette index 0: void  -> white
        0, 0, 0,        # palette index 1: solid -> black
    ]

    # Unused palette entries.
    palette.extend([0, 0, 0] * 254)

    image.putpalette(palette)
    image.save(filename)


# ============================================================================
# Main
# ============================================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for seed in range(N_SAMPLES):

        # Each seed initializes an independent stochastic realization.
        solid = generate_microstructure(seed)

        # Defensive checks on requested output format.
        assert solid.shape == (256, 256)
        assert solid.dtype == np.uint8
        assert np.all((solid == 0) | (solid == 1))

        stem = f"microstructure_seed_{seed:02d}"

        npy_path = OUTPUT_DIR / f"{stem}.npy"
        png_path = OUTPUT_DIR / f"{stem}.png"

        # NPY stores the phase field exactly as uint8 {0, 1}.
        np.save(npy_path, solid)

        # PNG also uses phase indices 0 and 1 via an indexed palette.
        save_binary_png(solid, png_path)

        print(
            f"seed={seed:02d} | "
            f"solid_fraction={solid.mean():.4f} | "
            f"{png_path.name} | "
            f"{npy_path.name}"
        )


if __name__ == "__main__":
    main()