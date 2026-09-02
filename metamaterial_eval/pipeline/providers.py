"""Narrow model-provider boundary for the deterministic pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LLMResponse:
    """Raw provider response and optional provenance metadata."""

    text: str
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Interface separating nondeterministic model calls from orchestration."""

    name: str

    @abstractmethod
    def generate(
        self,
        initial_prompt: str,
        reference_image: Path,
        context: dict[str, Any],
    ) -> LLMResponse | None:
        raise NotImplementedError

    @abstractmethod
    def revise(
        self,
        feedback_prompt: str,
        previous_context: dict[str, Any],
    ) -> LLMResponse | None:
        raise NotImplementedError


class ManualFileProvider(LLMProvider):
    """Read a researcher-supplied response file or pause when it is absent."""

    name = "manual-file"

    @staticmethod
    def _read(context: dict[str, Any]) -> LLMResponse | None:
        path = Path(context["response_path"])
        if not path.is_file():
            return None
        return LLMResponse(
            text=path.read_text(encoding="utf-8"),
            model=context.get("model"),
            metadata={"response_path": str(path)},
        )

    def generate(
        self,
        initial_prompt: str,
        reference_image: Path,
        context: dict[str, Any],
    ) -> LLMResponse | None:
        del initial_prompt, reference_image
        return self._read(context)

    def revise(
        self,
        feedback_prompt: str,
        previous_context: dict[str, Any],
    ) -> LLMResponse | None:
        del feedback_prompt
        return self._read(previous_context)


def make_provider(name: str) -> LLMProvider:
    if name == ManualFileProvider.name:
        return ManualFileProvider()
    raise ValueError(
        f"Unknown provider {name!r}. Pipeline v0.1 ships with 'manual-file'."
    )
