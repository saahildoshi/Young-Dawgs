import numpy as np
from pathlib import Path
# Adjust import path if module name differs in your environment
from evaluate_and_plot import load_binary, radial_bin_map, s2_periodic, lineal_path_periodic, lineal_path_periodic_directional

# 1. Load reference array
target = load_binary(Path("data/reference/reference_binary.npy"))

# 2. Setup periodic radial binning up to max radius
max_r = 64
bins, bin_counts = radial_bin_map(target.shape, max_r)

# 3. Compute full periodic curves
s2_curve = s2_periodic(target, max_r, bins, bin_counts)
lineal_curve = lineal_path_periodic(target, max_r) # 4-direction mean
directional_lineal = lineal_path_periodic_directional(target, max_r) # includes l_x, l_y

# 4. Filter for your target sampled radii
radii = [0, 1, 2, 4, 8, 16, 32, 64]
s2_sampled = {r: s2_curve[r] for r in radii}
lineal_sampled = {r: lineal_curve[r] for r in radii}

# Format into prompt strings
s2_str = ", ".join([f"r={r}: {s2_curve[r]:.6f}" for r in radii])
lineal_str = ", ".join([f"r={r}: {lineal_curve[r]:.6f}" for r in radii])

print("Two-point correlation data:\n", s2_str)
print("Lineal-path data:\n", lineal_str)