"""Opt-in parametric exploration, separate from legacy replication manifests."""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path
import sys

from .config import PipelineConfig, default_evaluator_path
from .design_space import make_plan
from .execution import run_subprocess
from .exploration_report import evaluate_exploration
from .preparation import prepare_reference
from .scripts import sha256_file, write_new_script
from .state import read_json, utc_now, write_json

VERSION = "0.3.0"


def start_exploration(reference: Path, output_dir: Path, *, s2_limit: float,
                      lineal_limit: float, bounds: dict | None = None,
                      designs: int = 10, replicates: int = 2, design_seed: int = 42,
                      seed_start: int = 0, prepare_png: bool = False,
                      threshold: float | None = None, timeout: float = 1800) -> Path:
    """Prepare immutable design inputs and a manual model-response boundary."""
    import math
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be finite and positive.")
    run = output_dir.resolve()
    run.mkdir(parents=True, exist_ok=False)
    prepare_reference(reference, run / "reference",
                      config=PipelineConfig(topology_mode="single_connected_network", pipeline_version=VERSION),
                      threshold=threshold, prepare_png=prepare_png)
    target = read_json(run / "reference/target_metrics.json")
    if not target["valid"]:
        raise ValueError("Exploration anchor must be one component spanning both axes. "
                         "Inspect the saved reference; choose a suitable anchor and new output directory.")
    plan = make_plan(target, bounds=bounds, designs=designs, replicates=replicates,
                     design_seed=design_seed, seed_start=seed_start,
                     s2_limit=s2_limit, lineal_limit=lineal_limit)
    write_json(run / "design_plan.json", plan)
    prompt = f'''PARAMETRIC EXPLORATION — pipeline {VERSION}

Study the attached reference/reference_structural.png. White is solid, black void.
Infer a procedural model of its morphological family, not a pixel reconstruction.
The image is a design-space anchor, NOT a point every output must match exactly.

Write ONE complete Python module exposing this exact interface:

def generate_microstructure(seed, solid_fraction_target, strut_scale, pore_scale):
    # Return a (256, 256) numpy.ndarray with dtype uint8, values 0/1.
    ...

The pipeline—not you—selects parameter combinations and writes all output files.
There are {designs} Latin-hypercube designs with {replicates} stochastic replicates each.
Do not hard-code the plan, reference pixels or separate designs. No import-time
execution, file I/O, plotting, internet, external datasets, API calls or subprocesses.
Use only numpy, scipy, scikit-image, pillow, matplotlib and the Python standard library.
Use a local seeded random generator. Same parameters and seed must reproduce exactly;
different seeds should produce structurally distinct realizations, not just translations.

Controls and exploration bounds:
{json.dumps(plan['bounds'], indent=2)}

solid_fraction_target is dimensionless. strut_scale and pore_scale are requested
characteristic scales in pixels, associated respectively with evaluator mean strut
thickness and median enclosed-pore diameter. They are approximate controls, not
promises of exact measured values. Increasing a control should usually increase its
associated metric while preserving the recognizable morphological family.
These controls may be coupled: explain dependencies and infeasible combinations.
Do not secretly ignore or clip controls, and do not force every descriptor to an exact value.

Hard constraints: binary 256 x 256; exactly ONE 4-connected solid component; a solid
path left-to-right and top-to-bottom; no isolated dots, particles or detached islands.
Do not add islands merely to match density. Modify the connected network itself.
The pipeline does not clean or repair generated samples.

Morphology-family gates against the anchor (not objectives to minimize toward zero):
E_S2 <= {s2_limit}; E_L <= {lineal_limit}.
Each error is RMSE(sample curve, anchor curve) / RMS(anchor curve), radii 0..64.
Use the established periodic S2 and four-direction lineal conventions. Keep useful
design variation within these limits rather than returning statistical clones.
The bounds/limits are provisional operator choices, not universal scientific standards.

Measured anchor descriptors:
{json.dumps({k: target[k] for k in ('phi_s', 'mean_strut_thickness', 'p10_strut_thickness', 'median_pore_diameter', 'component_count', 'f_largest', 'Px', 'Py')}, indent=2)}
Anchor sampled curves:
{json.dumps(target['sampled_descriptors'], indent=2)}

Return one fenced Python block containing the full module. Explain the algorithm,
each control, expected tradeoffs and limitations outside that block. No FEM,
stiffness or strength claims: this stage only generates and measures morphology.
'''
    (run / "prompt.txt").write_bytes(prompt.encode("utf-8"))
    (run / "response.txt").write_bytes(b"")
    # prepare_reference also makes a replication preview. Remove ambiguity by
    # replacing this new-run-only preview with the exploration prompt.
    (run / "reference/prompt_preview.txt").write_bytes(prompt.encode("utf-8"))
    protected = ["design_plan.json", "prompt.txt", "reference/reference_binary.npy",
                 "reference/reference_structural.png", "reference/target_metrics.json"]
    manifest = {"mode": "exploration", "pipeline_version": VERSION,
                "created_at_utc": utc_now(), "status": "WAITING_FOR_LLM",
                "timeout_seconds": timeout, "attempt_count": 0,
                "planning_environment": {"python": sys.version, **{name: version(name) for name in
                                         ("numpy", "scipy", "scikit-image", "Pillow", "matplotlib")}},
                "evaluator_sha256": sha256_file(default_evaluator_path()),
                "input_hashes": {p: sha256_file(run / p) for p in protected}}
    write_json(run / "exploration_manifest.json", manifest)
    return run


def load_exploration(run: Path) -> dict:
    manifest = read_json(run / "exploration_manifest.json")
    if manifest.get("mode") != "exploration" or manifest.get("pipeline_version") != VERSION:
        raise ValueError("Not a supported exploration manifest; use replication resume for old runs.")
    return manifest


def resume_exploration(run: Path, *, execute: bool = False, retry_failed: bool = False) -> dict:
    """Run a reviewed module, save a fresh attempt, and measure all planned rows.

    Failed attempts are never overwritten. Changed responses/generators require
    a new run, making revisions explicit. Relative artifact paths permit OneDrive
    moves; hashes refer to bytes rather than platform-dependent text reads.
    """
    run = run.resolve()
    manifest = load_exploration(run)
    for relative, digest in manifest["input_hashes"].items():
        if sha256_file(run / relative) != digest:
            raise ValueError(f"Exploration input modified: {relative}. Start a new run for revised inputs.")
    if sha256_file(default_evaluator_path()) != manifest["evaluator_sha256"]:
        raise ValueError("Frozen evaluator changed since planning.")
    script = run / "generator.py"
    if manifest.get("generator_sha256") and sha256_file(script) != manifest["generator_sha256"]:
        raise ValueError("Extracted generator modified. Start a new run for a revision.")
    if manifest.get("response_sha256") and sha256_file(run / "response.txt") != manifest["response_sha256"]:
        raise ValueError("Response modified after extraction. Start a new run for a revision.")
    if manifest["status"] == "COMPLETE":
        return manifest
    if manifest["status"] in ("FAILED", "RUNNING") and not retry_failed:
        raise ValueError("Failed/interrupted attempt preserved; use --retry-failed or start a revision run.")
    response = (run / "response.txt").read_text(encoding="utf-8-sig")
    if not response.strip():
        return manifest
    if not execute:
        raise ValueError("Review response.txt first, then pass --execute. Generated Python is NOT sandboxed.")
    if not manifest.get("generator_sha256"):
        _, digest = write_new_script(response, script)
        manifest.update(generator_sha256=digest, response_sha256=sha256_file(run / "response.txt"))
        write_json(run / "exploration_manifest.json", manifest)
    manifest["attempt_count"] += 1
    attempt = run / f"attempt_{manifest['attempt_count']:03d}"
    attempt.mkdir(exist_ok=False)
    write_json(attempt / "environment.json", {"python": sys.version,
               **{name: version(name) for name in ("numpy", "scipy", "scikit-image", "Pillow", "matplotlib")}})
    manifest.update(status="RUNNING", latest_attempt=attempt.name)
    write_json(run / "exploration_manifest.json", manifest)
    plan = read_json(run / "design_plan.json")
    try:
        result = run_subprocess(
            [sys.executable, str(Path(__file__).with_name("exploration_worker.py")),
             str(script), str(run / "design_plan.json"), str(attempt / "samples")],
            cwd=attempt, log_dir=attempt / "execution", timeout_seconds=manifest["timeout_seconds"])
        report = evaluate_exploration(run, attempt, plan)
        manifest["status"] = "COMPLETE" if result.succeeded and report["measured_count"] == report["expected_count"] else "FAILED"
        manifest["counts"] = {k: v for k, v in report.items() if k.endswith("_count")}
        manifest["report"] = str((attempt / "report.md").relative_to(run))
        manifest["completion_meaning"] = "All planned geometries measured; not a claim that constraints or scientific milestones passed."
    except Exception as error:
        manifest.update(status="FAILED", failure=f"{type(error).__name__}: {error}")
        write_json(run / "exploration_manifest.json", manifest)
        raise
    write_json(run / "exploration_manifest.json", manifest)
    return manifest
