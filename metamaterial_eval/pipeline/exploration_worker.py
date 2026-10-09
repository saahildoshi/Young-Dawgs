"""Execute a reviewed parameterized generator in a separate process.

This is process isolation, NOT a security sandbox. Run only trusted code.
The pipeline owns filenames, parameter selection and serialization.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import traceback

import numpy as np
from PIL import Image

from metamaterial_eval.io import validate_binary_array
from metamaterial_eval.pipeline.state import write_json


def main() -> None:
    script, plan_path, destination = map(Path, sys.argv[1:4])
    spec = importlib.util.spec_from_file_location("exploration_generator", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generate = getattr(module, "generate_microstructure")
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    destination.mkdir(parents=True, exist_ok=True)
    results = []
    for row in plan["samples"]:
        result = {"sample_id": row["sample_id"], "success": False}
        try:
            array = generate(seed=row["seed"], **row["requested"])
            if not isinstance(array, np.ndarray) or array.dtype != np.uint8:
                raise ValueError("Generator must return a numpy uint8 array, not a tuple/path/float array.")
            array = validate_binary_array(array, expected_shape=(256, 256)).copy()
            repeated = generate(seed=row["seed"], **row["requested"])
            if (not isinstance(repeated, np.ndarray) or repeated.dtype != np.uint8
                    or not np.array_equal(array, repeated)):
                raise ValueError("Same parameters and seed did not reproduce exactly.")
            path = destination / row["sample_id"]
            np.save(path.with_suffix(".npy"), array, allow_pickle=False)
            Image.fromarray(array * 255).save(path.with_suffix(".png"))
            result["success"] = True
        except Exception:
            result["error"] = traceback.format_exc()
        results.append(result)
        write_json(destination / "generation_results.json", {"samples": results})


if __name__ == "__main__":
    main()
