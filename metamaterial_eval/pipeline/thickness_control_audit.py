"""Post-hoc explanation of the worst v0.4.2 analytic control, never a new gate.

The end/interior split is diagnostic only. It does not replace frozen whole-
mask metrics or exclude the control from calibration.
"""
import argparse
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from .scripts import sha256_file
from .state import write_json
from .thickness_verification import analytic_mask, LEVELS


def bar_end_audit(n):
    width, phase = 6, .37
    a = analytic_mask(n, "bar_30", width, phase)
    sk = skeletonize(a.astype(bool))
    coords = np.argwhere(sk)
    y = (coords[:, 0] + .5) / n - .5 - phase / 256
    x = (coords[:, 1] + .5) / n - .5 + phase / 256
    along = x * np.cos(np.pi / 6) + y * np.sin(np.pi / 6)
    samples = 2 * ndi.distance_transform_edt(a)[sk] / n
    nominal = width / 256
    # Deliberately post-hoc attribution, not a change to evaluator sampling.
    near_end = .25 - np.abs(along) < nominal
    thin = samples < .9 * nominal
    return {"resolution": n, "skeleton_samples": len(samples), "nominal_width": nominal,
            "whole_p10": float(np.percentile(samples, 10)),
            "near_end_sample_fraction": float(near_end.mean()),
            "fraction_below_90_percent_nominal_width": float(thin.mean()),
            "fraction_of_thin_samples_near_ends": float(near_end[thin].mean()) if thin.any() else None,
            "interior_p10_diagnostic_only": float(np.percentile(samples[~near_end], 10)),
            "interior_mean_diagnostic_only": float(samples[~near_end].mean())}, samples, near_end


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    rows = []
    for n in LEVELS:
        row, samples, ends = bar_end_audit(n)
        rows.append(row)
        if n in (1024, 2048):
            axis = axes[0 if n == 1024 else 1]
            axis.hist([samples[ends], samples[~ends]], bins=np.linspace(0, .027, 28),
                      stacked=True, label=["Near ends", "Interior"])
            axis.axvline(row["whole_p10"], color="black", linestyle="--", label="Frozen whole-mask P10")
            axis.axvline(row["nominal_width"], color="green", linestyle=":", label="Nominal width")
            axis.set(title=f"N={n}", xlabel="Normalized skeleton thickness t/N", ylabel="Skeleton sample count")
            axis.legend(fontsize=8)
    fig.savefig(args.output_dir / "endpoint_population.png", dpi=180)
    plt.close(fig)
    write_json(args.output_dir / "audit.json", {
        "post_hoc_diagnostic_only": True, "excluded_from_acceptance": False,
        "note": "No control removed, no gate changed; whole-mask frozen metrics remain authoritative.",
        "geometry": "30 degree straight bar, width 6/256, fixed shift 0.37/256",
        "end_definition": "Within one nominal width of either analytic bar end, measured along the bar",
        "code_sha256": sha256_file(Path(__file__)), "rows": rows})
    lines = ["# Analytic P10 outlier — endpoint-population audit", "",
             "Post-hoc explanation only. The control remains in calibration and frozen whole-mask P10 remains unchanged.", "",
             "| N | Skeleton samples | Whole-mask P10 | Thin samples (<90% width) | Thin samples near ends | Interior P10 (diagnostic only) |",
             "|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['resolution']} | {r['skeleton_samples']} | {r['whole_p10']:.9f} | {100*r['fraction_below_90_percent_nominal_width']:.4f}% | {100*r['fraction_of_thin_samples_near_ends']:.1f}% | {r['interior_p10_diagnostic_only']:.9f} |")
    lines += ["", "The thin-sample population crosses 10% between 1024 and 2048. That moves whole-mask P10 into the endpoint tail despite unchanged analytic geometry.",
              "The interior statistic is not substituted for evaluator v1.1 or used to retroactively pass the control.",
              "", "![Endpoint versus interior samples](endpoint_population.png)"]
    (args.output_dir / "ENDPOINT_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
