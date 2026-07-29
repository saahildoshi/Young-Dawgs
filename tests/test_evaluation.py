"""Numerical and integration tests for metamaterial_eval."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from metamaterial_eval import (
    compute_basic_metrics,
    compute_lineal_path,
    compute_local_dimensions,
    compute_s2_correlation,
    evaluate_generator_output,
    make_target_dict,
    prepare_target,
)


class BasicMetricsTests(unittest.TestCase):
    def test_cross_is_one_component_and_percolates_both_axes(self) -> None:
        array = np.zeros((9, 9), dtype=np.uint8)
        array[4, :] = 1
        array[:, 4] = 1
        result = compute_basic_metrics(array)
        self.assertEqual(result["component_count"], 1)
        self.assertEqual(result["largest_component_fraction"], 1.0)
        self.assertTrue(result["percolates_x"])
        self.assertTrue(result["percolates_y"])

    def test_diagonal_pixels_are_disconnected_under_four_connectivity(self) -> None:
        array = np.eye(8, dtype=np.uint8)
        result = compute_basic_metrics(array)
        self.assertEqual(result["component_count"], 8)
        self.assertAlmostEqual(result["largest_component_fraction"], 1 / 8)
        self.assertFalse(result["percolates_x"])
        self.assertFalse(result["percolates_y"])

    def test_empty_field(self) -> None:
        result = compute_basic_metrics(np.zeros((8, 8), dtype=np.uint8))
        self.assertEqual(result["solid_volume_fraction"], 0.0)
        self.assertEqual(result["largest_component_fraction"], 0.0)
        self.assertFalse(result["percolates_x"])


class StatisticalMetricTests(unittest.TestCase):
    def test_uniform_solid_has_unit_s2_and_lineal_path(self) -> None:
        array = np.ones((32, 32), dtype=np.uint8)
        s2 = compute_s2_correlation(array, max_r=8)
        lineal = compute_lineal_path(array, max_r=8)
        np.testing.assert_allclose(s2["s2"], 1.0, atol=1e-12)
        np.testing.assert_allclose(lineal["l"], 1.0, atol=1e-12)
        np.testing.assert_allclose(lineal["l_x"], 1.0, atol=1e-12)
        np.testing.assert_allclose(lineal["l_y"], 1.0, atol=1e-12)

    def test_s2_origin_equals_volume_fraction(self) -> None:
        rng = np.random.default_rng(42)
        array = (rng.random((31, 29)) < 0.37).astype(np.uint8)
        result = compute_s2_correlation(array, max_r=10)
        self.assertEqual(result["s2"][0], array.mean())

    def test_lineal_origin_equals_volume_fraction(self) -> None:
        array = np.zeros((16, 16), dtype=np.uint8)
        array[:, ::2] = 1
        result = compute_lineal_path(array, max_r=5)
        self.assertEqual(result["l"][0], array.mean())
        self.assertEqual(result["l_x"][0], array.mean())
        self.assertEqual(result["l_y"][0], array.mean())
        self.assertEqual(result["l_x"][1], 0.0)
        self.assertEqual(result["l_y"][1], 0.5)

    def test_local_dimensions_for_single_pixel_struts(self) -> None:
        array = np.zeros((9, 9), dtype=np.uint8)
        array[4, :] = 1
        result = compute_local_dimensions(array)
        self.assertAlmostEqual(result["mean_strut_thickness"], 2.0)
        self.assertAlmostEqual(result["p10_strut_thickness"], 2.0)
        probability = result["strut_thickness_distribution"]["probability"]
        self.assertAlmostEqual(float(probability.sum()), 1.0)

    def test_skeleton_thickness_recovers_uniform_bar_width(self) -> None:
        array = np.zeros((128, 128), dtype=np.uint8)
        array[60:68, 10:118] = 1
        result = compute_local_dimensions(array)
        self.assertAlmostEqual(
            float(np.median(result["strut_thickness_samples"])), 8.0
        )
        self.assertAlmostEqual(result["p10_strut_thickness"], 8.0)

    def test_enclosed_pore_uses_one_maximal_inscribed_diameter(self) -> None:
        array = np.ones((128, 128), dtype=np.uint8)
        yy, xx = np.ogrid[:128, :128]
        array[(yy - 64) ** 2 + (xx - 64) ** 2 <= 10**2] = 0
        result = compute_local_dimensions(array)
        pore_samples = result["pore_diameter_samples"]
        self.assertEqual(pore_samples.size, 1)
        self.assertAlmostEqual(float(pore_samples[0]), 20.0, delta=1.0)

    def test_open_void_is_excluded_from_pore_population(self) -> None:
        array = np.ones((64, 64), dtype=np.uint8)
        array[20:44, :20] = 0
        result = compute_local_dimensions(array)
        self.assertEqual(result["pore_diameter_samples"].size, 0)
        self.assertEqual(result["excluded_open_pore_components"], 1)

    def test_single_phase_dimensions_are_undefined(self) -> None:
        result = compute_local_dimensions(np.ones((8, 8), dtype=np.uint8))
        self.assertTrue(np.isnan(result["mean_strut_thickness"]))
        self.assertTrue(np.isnan(result["median_pore_diameter"]))


class IoAndEvaluationTests(unittest.TestCase):
    def test_prepare_target_persists_png_and_npy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "target.png"
            pixels = np.array([[0, 255], [255, 0]], dtype=np.uint8)
            Image.fromarray(pixels, mode="L").save(source)
            result = prepare_target(source, threshold=0.5, target_shape=(8, 6))
            self.assertEqual(result.shape, (8, 6))
            self.assertEqual(result.dtype, np.uint8)
            self.assertTrue((folder / "target_binary.png").is_file())
            self.assertTrue((folder / "target_binary.npy").is_file())
            np.testing.assert_array_equal(
                result, np.load(folder / "target_binary.npy", allow_pickle=False)
            )

    def test_batch_report_and_duplicate_stem_handling(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = np.ones((24, 24), dtype=np.uint8)
            target_dict = make_target_dict(target, max_r=6)

            np.save(folder / "seed_0.npy", target, allow_pickle=False)
            Image.fromarray(target * 255, mode="L").save(folder / "seed_0.png")
            invalid = np.zeros_like(target)
            invalid[12, :] = 1
            np.save(folder / "seed_1.npy", invalid, allow_pickle=False)
            (folder / "broken.npy").write_bytes(b"not a numpy file")

            report = evaluate_generator_output(target_dict, folder)
            self.assertEqual(report["sample_count"], 3)
            self.assertEqual(report["evaluated_sample_count"], 2)
            self.assertEqual(report["valid_sample_count"], 1)
            self.assertEqual(report["failed_sample_count"], 1)
            self.assertAlmostEqual(report["samples"][0]["nrmse_s2"], 0.0)
            self.assertTrue((folder / "metrics_report.json").is_file())
            self.assertTrue((folder / "metrics_report.txt").is_file())
            with (folder / "metrics_report.json").open(encoding="utf-8") as stream:
                persisted = json.load(stream)
            self.assertEqual(persisted["schema_version"], "1.0")

    def test_batch_report_accepts_single_sample_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = np.ones((24, 24), dtype=np.uint8)
            target_dict = make_target_dict(target, max_r=6)

            sample = folder / "single_seed.npy"
            np.save(sample, target, allow_pickle=False)

            report = evaluate_generator_output(target_dict, sample)
            self.assertEqual(report["sample_count"], 1)
            self.assertEqual(report["evaluated_sample_count"], 1)
            self.assertEqual(report["valid_sample_count"], 1)
            self.assertEqual(report["failed_sample_count"], 0)


if __name__ == "__main__":
    unittest.main()
