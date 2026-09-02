"""Conservative extraction and hashing of model-generated Python scripts."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


class ScriptExtractionError(ValueError):
    """Raised when a response does not contain one unambiguous full script."""


FENCED_PYTHON = re.compile(
    r"```(?:python|py)\s*\r?\n(?P<code>.*?)```",
    flags=re.IGNORECASE | re.DOTALL,
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def script_sha256(source: str) -> str:
    return sha256_bytes(source.encode("utf-8"))


def _validate_script(source: str) -> str:
    candidate = source.strip() + "\n"
    if not candidate.strip():
        raise ScriptExtractionError("The extracted Python script is empty.")
    try:
        compile(candidate, "<llm-generator>", "exec")
    except SyntaxError as error:
        raise ScriptExtractionError(
            f"The extracted Python block is not syntactically valid: {error}"
        ) from error
    if not re.search(r"^(?:from\s+\S+\s+import|import\s+\S+|def\s+\w+)", candidate, re.MULTILINE):
        raise ScriptExtractionError("Response does not look like a complete Python script.")
    return candidate


def extract_python_script(response: str) -> str:
    """Return one full Python script or fail rather than guessing."""
    blocks = [match.group("code") for match in FENCED_PYTHON.finditer(response)]
    if len(blocks) == 1:
        return _validate_script(blocks[0])
    if len(blocks) > 1:
        raise ScriptExtractionError(
            "Response contains multiple fenced Python blocks; manual resolution is required."
        )

    # Accept an unfenced response only when the entire response compiles.
    return _validate_script(response)


def write_new_script(response: str, destination: Path) -> tuple[str, str]:
    """Extract and write a new immutable iteration script."""
    if destination.exists():
        raise FileExistsError(f"Historical script will not be overwritten: {destination}")
    source = extract_python_script(response)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source, encoding="utf-8")
    digest = script_sha256(source)
    destination.with_name(destination.stem + "_sha256.txt").write_text(
        digest + "\n", encoding="utf-8"
    )
    return source, digest

