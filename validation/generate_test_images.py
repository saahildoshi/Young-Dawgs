"""Generate the canonical analytical images used by the validation plan."""

from __future__ import annotations

from pathlib import Path

import numpy as np


OUTPUT = Path(__file__).resolve().parent / "fixtures"


def save(name: str, image: np.ndarray) -> None:
    np.save(OUTPUT / f"{name}.npy", image.astype(np.uint8), allow_pickle=False)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    save("fully_solid", np.ones((256, 256), dtype=np.uint8))
    save("fully_void", np.zeros((256, 256), dtype=np.uint8))

    half = np.zeros((256, 256), dtype=np.uint8)
    half[:, :128] = 1
    save("half_solid_vertical", half)

    quarter = np.zeros((256, 256), dtype=np.uint8)
    quarter[:128, :128] = 1
    save("quarter_solid_block", quarter)

    for width in (1, 2, 4, 8, 16):
        bar = np.zeros((128, 128), dtype=np.uint8)
        start = 64 - width // 2
        bar[start : start + width, 10:118] = 1
        save(f"horizontal_bar_w{width:02d}", bar)

    yy, xx = np.ogrid[:128, :128]
    for radius in (5, 10, 20):
        pore = np.ones((128, 128), dtype=np.uint8)
        pore[(yy - 64) ** 2 + (xx - 64) ** 2 <= radius**2] = 0
        save(f"circular_pore_r{radius:02d}", pore)

    continuous = np.zeros((64, 64), dtype=np.uint8)
    continuous[30:34, :] = 1
    save("continuous_horizontal_bar", continuous)
    broken = continuous.copy()
    broken[:, 32] = 0
    save("broken_horizontal_bar", broken)


if __name__ == "__main__":
    main()
