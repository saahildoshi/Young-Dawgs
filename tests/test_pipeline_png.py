"""Raw-PNG preparation and integration tests; no model calls required."""

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from metamaterial_eval.pipeline.cli import main
from metamaterial_eval.pipeline.config import PipelineConfig
from metamaterial_eval.pipeline.reference import _load_reference, canonicalize_reference


def test_preparation_thresholds_then_resizes_non_square_png(tmp_path: Path) -> None:
    source = tmp_path / "raw.png"
    pixels = np.array([[0, 100, 200], [255, 150, 30]], dtype=np.uint8)
    Image.fromarray(pixels).save(source)
    binary, metadata = canonicalize_reference(
        source, tmp_path / "reference", PipelineConfig(),
        threshold=None, evaluator_hash="test", prepare_png=True,
    )
    expected = np.asarray(
        Image.fromarray((pixels >= 128).astype(np.uint8)).resize(
            (256, 256), Image.Resampling.NEAREST
        )
    )
    np.testing.assert_array_equal(binary, expected)
    assert binary.shape == (256, 256) and binary.dtype == np.uint8
    assert set(np.unique(binary)) == {0, 1}
    np.testing.assert_array_equal(np.load(tmp_path / "reference/reference_binary.npy"), binary)
    assert (tmp_path / "reference/reference.png").is_file()
    assert metadata["source_shape"] == [2, 3]
    assert metadata["threshold"] == 0.5
    assert metadata["preprocessing"]["interpolation"] == "nearest_neighbor"


def test_custom_threshold_and_rgb_grayscale(tmp_path: Path) -> None:
    source = tmp_path / "rgb.png"
    rgb = np.array([[[0, 0, 0], [160, 160, 160], [255, 255, 255]]], dtype=np.uint8)
    Image.fromarray(rgb).save(source)
    binary = _load_reference(
        source, expected_shape=(1, 3), threshold=0.75, prepare_png=True
    )
    np.testing.assert_array_equal(binary, [[0, 0, 1]])


def test_source_png_is_preserved(tmp_path: Path) -> None:
    source = tmp_path / "original.png"
    Image.fromarray(np.array([[0, 255], [255, 0]], dtype=np.uint8)).save(source)
    original = source.read_bytes()
    canonicalize_reference(
        source, tmp_path / "reference", PipelineConfig(),
        threshold=None, evaluator_hash="test", prepare_png=True,
    )
    assert source.read_bytes() == original
    assert (tmp_path / "reference/source.png").read_bytes() == original


def test_strict_loading_still_rejects_wrong_dimensions(tmp_path: Path) -> None:
    source = tmp_path / "small.png"
    Image.fromarray(np.zeros((10, 12), dtype=np.uint8)).save(source)
    with pytest.raises(ValueError, match="Expected reference shape"):
        _load_reference(source, expected_shape=(256, 256), threshold=None)


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan")])
def test_preparation_rejects_invalid_threshold(tmp_path: Path, threshold: float) -> None:
    source = tmp_path / "image.png"
    Image.fromarray(np.zeros((2, 2), dtype=np.uint8)).save(source)
    with pytest.raises(ValueError, match="threshold"):
        _load_reference(
            source, expected_shape=(256, 256), threshold=threshold, prepare_png=True
        )


def test_preparation_does_not_resize_npy(tmp_path: Path) -> None:
    source = tmp_path / "binary.npy"
    np.save(source, np.zeros((256, 256), dtype=np.uint8))
    with pytest.raises(ValueError, match="only supported for PNG"):
        _load_reference(
            source, expected_shape=(256, 256), threshold=None, prepare_png=True
        )


def test_png_start_cli_prepares_target_and_initial_prompt(tmp_path: Path) -> None:
    reference = Path(__file__).resolve().parents[1] / "data/reference/reference_binary.npy"
    binary = np.load(reference, allow_pickle=False)
    source = tmp_path / "raw_leaf.png"
    Image.fromarray(binary * 255).convert("RGB").resize(
        (512, 512), Image.Resampling.NEAREST
    ).save(source)
    assert main([
        "start", str(source), "--prepare-png", "--run-name", "png-test",
        "--runs-root", str(tmp_path / "runs"),
    ]) == 0
    run = tmp_path / "runs/raw_leaf/png-test"
    np.testing.assert_array_equal(np.load(run / "reference/reference_binary.npy"), binary)
    assert (run / "iteration_0/prompt_0.txt").is_file()
    assert json.loads((run / "manifest.json").read_text())["status"] == "WAITING_FOR_INITIAL_LLM"
