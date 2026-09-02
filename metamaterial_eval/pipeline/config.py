"""Central configuration for Pipeline v0.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PIPELINE_VERSION = "0.1.0"
PROMPT_VERSION = "1.0"
EVALUATOR_VERSION = "1.1"
IMAGE_SHAPE = (256, 256)
DEVELOPMENT_SEEDS = tuple(range(20))
HELDOUT_SEEDS = tuple(range(100, 120))
MAX_FEEDBACK_ROUNDS = 3
GENERATOR_TIMEOUT_SECONDS = 1800.0
EVALUATOR_TIMEOUT_SECONDS = 600.0
S2_SAMPLE_RADII = (0, 1, 2, 4, 8, 16, 32, 64)


def repository_root() -> Path:
    """Return the repository containing the installed editable package."""
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class PipelineConfig:
    """Explicit, serializable settings for a reproducible pipeline run."""

    image_shape: tuple[int, int] = IMAGE_SHAPE
    development_seeds: tuple[int, ...] = DEVELOPMENT_SEEDS
    heldout_seeds: tuple[int, ...] = HELDOUT_SEEDS
    max_feedback_rounds: int = MAX_FEEDBACK_ROUNDS
    generator_timeout_seconds: float = GENERATOR_TIMEOUT_SECONDS
    evaluator_timeout_seconds: float = EVALUATOR_TIMEOUT_SECONDS
    sample_radii: tuple[int, ...] = S2_SAMPLE_RADII
    max_r: int = 64
    pipeline_version: str = PIPELINE_VERSION
    prompt_version: str = PROMPT_VERSION
    evaluator_version: str = EVALUATOR_VERSION

    def __post_init__(self) -> None:
        if len(self.image_shape) != 2 or any(value <= 0 for value in self.image_shape):
            raise ValueError("image_shape must contain two positive integers.")
        if not self.development_seeds or not self.heldout_seeds:
            raise ValueError("Development and held-out seed sets must be non-empty.")
        if set(self.development_seeds) & set(self.heldout_seeds):
            raise ValueError("Development and held-out seeds must be disjoint.")
        if self.max_feedback_rounds < 0:
            raise ValueError("max_feedback_rounds must be non-negative.")
        if self.generator_timeout_seconds <= 0 or self.evaluator_timeout_seconds <= 0:
            raise ValueError("Timeouts must be positive.")
        if self.max_r < max(self.sample_radii):
            raise ValueError("max_r must cover every sampled descriptor radius.")
        if self.max_r >= min(self.image_shape) // 2:
            raise ValueError("max_r is too large for unambiguous periodic radial bins.")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in (
            "image_shape",
            "development_seeds",
            "heldout_seeds",
            "sample_radii",
        ):
            result[key] = list(result[key])
        return result

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "PipelineConfig":
        converted = dict(values)
        for key in (
            "image_shape",
            "development_seeds",
            "heldout_seeds",
            "sample_radii",
        ):
            if key in converted:
                converted[key] = tuple(int(item) for item in converted[key])
        return cls(**converted)


def default_evaluator_path() -> Path:
    return repository_root() / "validation" / "evaluators" / "evaluator_v1_1.py"


def default_runs_root() -> Path:
    return repository_root() / "experiments" / "pipeline_v0.1"

