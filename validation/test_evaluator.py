"""Acceptance tests for the frozen/improved periodic evaluator.

Select an evaluator version with ``EVALUATOR_PATH``. The default is the frozen
v1.0 snapshot. These tests intentionally encode the validation plan's desired
scientific behavior rather than merely reproducing the current implementation.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest


VALIDATION_ROOT = Path(__file__).resolve().parent
EVALUATOR_PATH = Path(
    os.environ.get(
        "EVALUATOR_PATH",
        VALIDATION_ROOT / "evaluators" / "evaluator_v1_0.py",
    )
)
SPEC = importlib.util.spec_from_file_location("evaluator_under_test", EVALUATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
EVALUATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVALUATOR)


def disk_void(size: int, radius: int, center: tuple[int, int] | None = None) -> np.ndarray:
    image = np.ones((size, size), dtype=np.uint8)
    cy, cx = center or (size // 2, size // 2)
    yy, xx = np.ogrid[:size, :size]
    image[(yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2] = 0
    return image


def spanning_cross(size: int = 49) -> np.ndarray:
    image = np.zeros((size, size), dtype=np.uint8)
    center = size // 2
    image[center, :] = 1
    image[:, center] = 1
    return image


class TestPhaseConvention:
    def test_fully_solid(self) -> None:
        result = EVALUATOR.basic_metrics(np.ones((256, 256), dtype=np.uint8))
        assert result["phi_s"] == 1.0
        assert result["component_count"] == 1
        assert result["f_largest"] == 1.0
        assert result["Px"] == 1
        assert result["Py"] == 1

    def test_fully_void_does_not_crash(self) -> None:
        image = np.zeros((256, 256), dtype=np.uint8)
        result = EVALUATOR.basic_metrics(image)
        dimensions = EVALUATOR.local_dimensions(image)
        assert result["phi_s"] == 0.0
        assert result["component_count"] == 0
        assert result["f_largest"] == 0.0
        assert result["Px"] == 0
        assert result["Py"] == 0
        assert np.isnan(dimensions["mean_strut_thickness"])
        assert np.isnan(dimensions["median_pore_diameter"])


@pytest.mark.parametrize(
    ("image", "expected"),
    [
        (
            np.pad(
                np.ones((256, 128), dtype=np.uint8),
                ((0, 0), (0, 128)),
            ),
            0.5,
        ),
        (
            np.pad(
                np.ones((128, 128), dtype=np.uint8),
                ((0, 128), (0, 128)),
            ),
            0.25,
        ),
        (
            np.pad(
                np.ones((1, 1), dtype=np.uint8),
                ((100, 155), (100, 155)),
            ),
            1 / 65536,
        ),
    ],
)
def test_exact_volume_fractions(image: np.ndarray, expected: float) -> None:
    assert abs(EVALUATOR.basic_metrics(image)["phi_s"] - expected) < 1e-12


class TestFourConnectivity:
    def test_edge_connected_pixels(self) -> None:
        image = np.zeros((10, 10), dtype=np.uint8)
        image[4, 4:6] = 1
        result = EVALUATOR.basic_metrics(image)
        assert result["component_count"] == 1
        assert result["f_largest"] == 1.0

    def test_diagonal_pixels_are_disconnected(self) -> None:
        image = np.zeros((10, 10), dtype=np.uint8)
        image[4, 4] = image[5, 5] = 1
        result = EVALUATOR.basic_metrics(image)
        assert result["component_count"] == 2
        assert result["f_largest"] == 0.5

    def test_three_unequal_components(self) -> None:
        image = np.zeros((20, 20), dtype=np.uint8)
        image[1, 1:11] = 1
        image[5, 1:6] = 1
        image[10, 10] = 1
        result = EVALUATOR.basic_metrics(image)
        assert result["component_count"] == 3
        assert result["f_largest"] == 10 / 16


class TestPercolation:
    def test_horizontal_only(self) -> None:
        image = np.zeros((64, 64), dtype=np.uint8)
        image[30:34, :] = 1
        result = EVALUATOR.basic_metrics(image)
        assert (result["Px"], result["Py"]) == (1, 0)

    def test_vertical_only(self) -> None:
        image = np.zeros((64, 64), dtype=np.uint8)
        image[:, 30:34] = 1
        result = EVALUATOR.basic_metrics(image)
        assert (result["Px"], result["Py"]) == (0, 1)

    def test_cross_percolates_both(self) -> None:
        result = EVALUATOR.basic_metrics(spanning_cross())
        assert (result["Px"], result["Py"]) == (1, 1)

    def test_unrelated_left_right_contacts_do_not_percolate(self) -> None:
        image = np.zeros((64, 64), dtype=np.uint8)
        image[10, :10] = 1
        image[40, -10:] = 1
        assert EVALUATOR.basic_metrics(image)["Px"] == 0

    def test_unrelated_top_bottom_contacts_do_not_percolate(self) -> None:
        image = np.zeros((64, 64), dtype=np.uint8)
        image[:10, 10] = 1
        image[-10:, 40] = 1
        assert EVALUATOR.basic_metrics(image)["Py"] == 0


class TestValidityRule:
    def test_valid_with_small_islands(self) -> None:
        image = spanning_cross()
        image[1, 1] = 1
        assert EVALUATOR.structure_is_valid(EVALUATOR.basic_metrics(image))

    def test_invalid_at_about_95_percent_connected(self) -> None:
        image = spanning_cross()
        # Cross has 97 pixels; five isolated pixels give 97/102 = 0.95098.
        for coordinate in ((1, 1), (3, 3), (5, 5), (7, 7), (9, 9)):
            image[coordinate] = 1
        metrics = EVALUATOR.basic_metrics(image)
        assert metrics["f_largest"] == pytest.approx(97 / 102)
        assert not EVALUATOR.structure_is_valid(metrics)

    def test_invalid_when_one_direction_is_missing(self) -> None:
        image = np.zeros((64, 64), dtype=np.uint8)
        image[30:34, :] = 1
        metrics = EVALUATOR.basic_metrics(image)
        assert metrics["f_largest"] == 1.0
        assert not EVALUATOR.structure_is_valid(metrics)

    def test_exact_threshold_is_inclusive(self) -> None:
        image = spanning_cross()
        image[23, 23] = 1  # adjacent to the cross: main component is now 98
        image[1, 1] = 1
        image[3, 3] = 1
        metrics = EVALUATOR.basic_metrics(image)
        assert metrics["f_largest"] == 0.98
        assert EVALUATOR.structure_is_valid(metrics)

    def test_below_threshold_is_invalid(self) -> None:
        image = spanning_cross()
        image[3, 3] = 1
        image[5, 5] = 1
        metrics = EVALUATOR.basic_metrics(image)
        assert metrics["f_largest"] == pytest.approx(97 / 99)
        assert metrics["f_largest"] < 0.98
        assert not EVALUATOR.structure_is_valid(metrics)


class TestLocalDimensions:
    @pytest.mark.parametrize("width", [2, 4, 8, 16])
    def test_uniform_bar_calibrates_to_nominal_width(self, width: int) -> None:
        image = np.zeros((128, 128), dtype=np.uint8)
        start = 64 - width // 2
        image[start : start + width, 10:118] = 1
        values = EVALUATOR.local_dimensions(image)["strut_diameters"]
        assert float(np.median(values)) == pytest.approx(width, abs=1.0)
        assert float(np.percentile(values, 10)) == pytest.approx(width, abs=1.0)

    def test_bar_width_response_is_monotonic_and_linear(self) -> None:
        nominal = np.array([2.0, 4.0, 8.0, 16.0])
        measured = []
        for width in nominal.astype(int):
            image = np.zeros((128, 128), dtype=np.uint8)
            start = 64 - width // 2
            image[start : start + width, 10:118] = 1
            measured.append(
                np.median(EVALUATOR.local_dimensions(image)["strut_diameters"])
            )
        measured_array = np.asarray(measured)
        assert np.all(np.diff(measured_array) > 0)
        slope = float(np.polyfit(nominal, measured_array, 1)[0])
        assert slope == pytest.approx(1.0, abs=0.15)

    def test_mixed_width_p10_tracks_thinner_feature(self) -> None:
        image = np.zeros((128, 128), dtype=np.uint8)
        image[20:24, 10:118] = 1
        image[80:90, 10:118] = 1
        values = EVALUATOR.local_dimensions(image)["strut_diameters"]
        assert 4.0 <= float(np.mean(values)) <= 10.0
        assert float(np.percentile(values, 10)) == pytest.approx(4.0, abs=1.0)

    def test_one_pixel_line_is_finite(self) -> None:
        image = np.zeros((64, 64), dtype=np.uint8)
        image[32, 5:59] = 1
        values = EVALUATOR.local_dimensions(image)["strut_diameters"]
        assert values.size > 0
        assert np.all(np.isfinite(values))
        assert float(np.median(values)) == 2.0

    @pytest.mark.parametrize("radius", [5, 10, 20])
    def test_circular_pore_calibrates_to_diameter(self, radius: int) -> None:
        values = EVALUATOR.local_dimensions(
            disk_void(128, radius)
        )["pore_diameters"]
        assert values.size == 1
        assert float(values[0]) == pytest.approx(2 * radius, abs=1.0)

    def test_two_pores_are_weighted_per_pore(self) -> None:
        image = np.ones((160, 160), dtype=np.uint8)
        yy, xx = np.ogrid[:160, :160]
        image[(yy - 50) ** 2 + (xx - 50) ** 2 <= 5**2] = 0
        image[(yy - 105) ** 2 + (xx - 105) ** 2 <= 15**2] = 0
        values = np.sort(EVALUATOR.local_dimensions(image)["pore_diameters"])
        assert values.size == 2
        assert values[0] == pytest.approx(10.0, abs=1.0)
        assert values[1] == pytest.approx(30.0, abs=1.0)
        assert float(np.median(values)) == pytest.approx(20.0, abs=1.0)

    def test_open_edge_void_is_excluded_from_pore_population(self) -> None:
        image = np.ones((64, 64), dtype=np.uint8)
        image[20:44, :20] = 0
        values = EVALUATOR.local_dimensions(image)["pore_diameters"]
        assert values.size == 0


class TestS2:
    def test_solid_and_void_limits(self) -> None:
        bins, counts = EVALUATOR.radial_bin_map((64, 64), 20)
        solid = EVALUATOR.s2_periodic(np.ones((64, 64), np.uint8), 20, bins, counts)
        void = EVALUATOR.s2_periodic(np.zeros((64, 64), np.uint8), 20, bins, counts)
        np.testing.assert_allclose(solid, 1.0, atol=1e-12)
        np.testing.assert_allclose(void, 0.0, atol=1e-12)

    def test_target_against_itself_is_zero(self) -> None:
        rng = np.random.default_rng(10)
        target = (rng.random((64, 64)) < 0.4).astype(np.uint8)
        bins, counts = EVALUATOR.radial_bin_map(target.shape, 20)
        curve = EVALUATOR.s2_periodic(target, 20, bins, counts)
        assert EVALUATOR.normalized_rmse(curve, curve) < 1e-12

    def test_bernoulli_field_approaches_p_squared(self) -> None:
        probability = 0.4
        bins, counts = EVALUATOR.radial_bin_map((128, 128), 40)
        curves = []
        for seed in range(24):
            rng = np.random.default_rng(seed)
            image = (rng.random((128, 128)) < probability).astype(np.uint8)
            curves.append(EVALUATOR.s2_periodic(image, 40, bins, counts))
        mean_curve = np.mean(curves, axis=0)
        assert mean_curve[0] == pytest.approx(probability, abs=0.005)
        assert float(mean_curve[10:41].mean()) == pytest.approx(
            probability**2, abs=0.005
        )

    def test_translation_and_rotation_invariance(self) -> None:
        rng = np.random.default_rng(12)
        image = (rng.random((64, 64)) < 0.37).astype(np.uint8)
        bins, counts = EVALUATOR.radial_bin_map(image.shape, 20)
        original = EVALUATOR.s2_periodic(image, 20, bins, counts)
        shifted = EVALUATOR.s2_periodic(
            np.roll(image, (7, 13), axis=(0, 1)), 20, bins, counts
        )
        rotated = EVALUATOR.s2_periodic(np.rot90(image), 20, bins, counts)
        np.testing.assert_allclose(shifted, original, atol=1e-12)
        np.testing.assert_allclose(rotated, original, atol=1e-12)


class TestLinealPath:
    def test_solid_and_void_limits(self) -> None:
        solid = EVALUATOR.lineal_path_periodic(np.ones((64, 64), np.uint8), 20)
        void = EVALUATOR.lineal_path_periodic(np.zeros((64, 64), np.uint8), 20)
        np.testing.assert_allclose(solid, 1.0, atol=1e-12)
        np.testing.assert_allclose(void, 0.0, atol=1e-12)

    def test_target_against_itself_is_zero(self) -> None:
        rng = np.random.default_rng(13)
        target = (rng.random((64, 64)) < 0.4).astype(np.uint8)
        curve = EVALUATOR.lineal_path_periodic(target, 20)
        assert EVALUATOR.normalized_rmse(curve, curve) < 1e-12

    def test_directional_bar_response(self) -> None:
        horizontal = np.zeros((64, 64), dtype=np.uint8)
        horizontal[30:34, :] = 1
        vertical = horizontal.T.copy()
        horizontal_curves = EVALUATOR.lineal_path_periodic_directional(
            horizontal, 12
        )
        vertical_curves = EVALUATOR.lineal_path_periodic_directional(vertical, 12)
        assert horizontal_curves["l_x"][12] > horizontal_curves["l_y"][12]
        assert vertical_curves["l_y"][12] > vertical_curves["l_x"][12]

    def test_broken_bar_reduces_full_segment_probability(self) -> None:
        continuous = np.zeros((64, 64), dtype=np.uint8)
        continuous[30:34, :] = 1
        broken = continuous.copy()
        broken[:, 32] = 0
        full = EVALUATOR.lineal_path_periodic_directional(continuous, 20)
        cut = EVALUATOR.lineal_path_periodic_directional(broken, 20)
        assert cut["l_x"][20] < 0.75 * full["l_x"][20]


class TestNRMSE:
    def test_direct_arrays(self) -> None:
        target = np.array([0.0, 1.0])
        assert EVALUATOR.normalized_rmse(target, target) == 0.0
        generated = np.array([1.0, 0.0])
        assert EVALUATOR.normalized_rmse(generated, target) == pytest.approx(
            np.sqrt(2.0)
        )

    def test_constant_zero_target_is_safe(self) -> None:
        target = np.zeros(3)
        assert EVALUATOR.normalized_rmse(target, target) == 0.0
        assert np.isinf(EVALUATOR.normalized_rmse(np.ones(3), target))


class TestSampleDiscoveryAndCleaning:
    def test_discovery_is_npy_only_natural_and_audited(self, tmp_path: Path) -> None:
        array = np.zeros((8, 8), dtype=np.uint8)
        np.save(tmp_path / "sample_001.npy", array)
        np.save(tmp_path / "sample_000.npy", array)
        np.save(tmp_path / "sample_000_copy.npy", array)
        (tmp_path / "sample_002.png").write_bytes(b"plot")
        (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")
        (tmp_path / "subfolder").mkdir()
        discovered = EVALUATOR.find_samples(tmp_path)
        assert [path.name for path in discovered] == [
            "sample_000.npy",
            "sample_000_copy.npy",
            "sample_001.npy",
        ]
        audit = EVALUATOR.audit_sample_seeds(discovered, expected_seeds=range(3))
        assert audit["missing_seeds"] == [2]
        assert audit["duplicate_seeds"] == {"0": [
            "sample_000.npy",
            "sample_000_copy.npy",
        ]}

    @pytest.mark.parametrize(
        "array",
        [
            np.array([[True, False]], dtype=bool),
            np.array([[1.0, 0.0]], dtype=np.float64),
            np.array([[255, 0]], dtype=np.uint8),
        ],
    )
    def test_supported_binary_encodings(self, tmp_path: Path, array: np.ndarray) -> None:
        path = tmp_path / "sample.npy"
        np.save(path, array)
        loaded = EVALUATOR.load_binary(path)
        assert loaded.dtype == np.uint8
        assert set(np.unique(loaded)).issubset({0, 1})

    @pytest.mark.parametrize(
        "array",
        [
            np.array([[0, 128, 255]], dtype=np.uint8),
            np.array([[0, 1, 2]], dtype=np.int8),
            np.array([[-1, 0, 1]], dtype=np.int8),
            np.zeros((4, 4, 3), dtype=np.uint8),
            np.zeros((4,), dtype=np.uint8),
            np.empty((0, 0), dtype=np.uint8),
        ],
    )
    def test_malformed_inputs_are_rejected(
        self, tmp_path: Path, array: np.ndarray
    ) -> None:
        path = tmp_path / "invalid.npy"
        np.save(path, array)
        with pytest.raises(ValueError):
            EVALUATOR.load_binary(path)

    def test_wrong_shape_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "wrong.npy"
        np.save(path, np.zeros((128, 128), dtype=np.uint8))
        with pytest.raises(ValueError, match="expected shape"):
            EVALUATOR.load_binary(path, expected_shape=(256, 256))


class TestEnsembleStatistics:
    def test_population_standard_deviation(self) -> None:
        records = [{"phi_s": value} for value in (0.2, 0.4, 0.6)]
        summary = EVALUATOR.metric_summary(records, "phi_s")
        assert summary["mean"] == pytest.approx(0.4)
        assert summary["std"] == pytest.approx(0.16329931618554522)

    def test_diversity_ranking(self) -> None:
        rng = np.random.default_rng(20)
        base = (rng.random((64, 64)) < 0.4).astype(np.uint8)
        duplicates = np.stack([base.copy() for _ in range(20)])
        perturbed = []
        for seed in range(20):
            sample = base.copy().ravel()
            indices = np.random.default_rng(seed).choice(sample.size, 20, replace=False)
            sample[indices] = 1 - sample[indices]
            perturbed.append(sample.reshape(base.shape))
        independent = np.stack(
            [
                (np.random.default_rng(seed + 100).random(base.shape) < 0.4).astype(
                    np.uint8
                )
                for seed in range(20)
            ]
        )
        _, duplicate_score = EVALUATOR.pairwise_disagreement(duplicates)
        _, perturbation_score = EVALUATOR.pairwise_disagreement(np.stack(perturbed))
        _, independent_score = EVALUATOR.pairwise_disagreement(independent)
        assert duplicate_score == 0.0
        assert duplicate_score < perturbation_score < independent_score

    def test_base_package_all_and_valid_aggregates(self) -> None:
        from metamaterial_eval.evaluation import SCALAR_METRICS, _aggregate

        records = []
        for value, valid in ((0.2, True), (0.4, False), (0.6, True)):
            record = {metric: value for metric in SCALAR_METRICS}
            record["valid"] = valid
            records.append(record)
        all_stats = _aggregate(records, valid_only=False)
        valid_stats = _aggregate(records, valid_only=True)
        assert all_stats["solid_volume_fraction"] == {
            "mean": pytest.approx(0.4),
            "std": pytest.approx(0.16329931618554522),
            "count": 3,
        }
        assert valid_stats["solid_volume_fraction"] == {
            "mean": pytest.approx(0.4),
            "std": pytest.approx(0.2),
            "count": 2,
        }


class TestCopyDetection:
    def test_transformation_aware_ordering_and_flags(self) -> None:
        rng = np.random.default_rng(31)
        target = (rng.random((64, 64)) < 0.37).astype(np.uint8)
        noisy = target.copy().ravel()
        changed = rng.choice(noisy.size, size=int(0.01 * noisy.size), replace=False)
        noisy[changed] = 1 - noisy[changed]
        cases = {
            "exact": target,
            "shifted": np.roll(target, (5, 9), axis=(0, 1)),
            "rotated": np.rot90(target),
            "mirrored": np.fliplr(target),
            "one_percent_noise": noisy.reshape(target.shape),
            "unrelated": (rng.random(target.shape) < 0.37).astype(np.uint8),
        }
        results = {
            name: EVALUATOR.transformation_aware_similarity(sample, target)
            for name, sample in cases.items()
        }
        for name in ("exact", "shifted", "rotated", "mirrored"):
            assert results[name]["score"] > 0.999999
            assert results[name]["potential_trivial_copy"]
        assert results["one_percent_noise"]["score"] > 0.9
        assert results["one_percent_noise"]["potential_trivial_copy"]
        assert results["unrelated"]["score"] < 0.3
        assert not results["unrelated"]["potential_trivial_copy"]


def test_repeated_function_evaluation_is_identical() -> None:
    rng = np.random.default_rng(41)
    target = (rng.random((64, 64)) < 0.4).astype(np.uint8)
    bins, counts = EVALUATOR.radial_bin_map(target.shape, 20)
    first = (
        EVALUATOR.s2_periodic(target, 20, bins, counts),
        EVALUATOR.lineal_path_periodic(target, 20),
        EVALUATOR.basic_metrics(target),
    )
    second = (
        EVALUATOR.s2_periodic(target, 20, bins, counts),
        EVALUATOR.lineal_path_periodic(target, 20),
        EVALUATOR.basic_metrics(target),
    )
    np.testing.assert_array_equal(first[0], second[0])
    np.testing.assert_array_equal(first[1], second[1])
    assert first[2] == second[2]
