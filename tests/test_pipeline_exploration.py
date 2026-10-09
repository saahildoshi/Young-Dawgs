"""Exploration is a controlled design, not a relabelled replication ensemble."""

import json
from pathlib import Path

import numpy as np
import pytest

from metamaterial_eval.pipeline.design_space import make_plan, CONTROLS
from metamaterial_eval.pipeline.exploration import start_exploration, resume_exploration
from metamaterial_eval.pipeline.state import read_json


ANCHOR = {"phi_s": .3, "mean_strut_thickness": 3., "median_pore_diameter": 8.}
CONSTANT_GENERATOR = '''import numpy as np
def generate_microstructure(seed, solid_fraction_target, strut_scale, pore_scale):
    a = np.zeros((256, 256), dtype=np.uint8)
    a[::16, :] = 1
    a[:, ::16] = 1
    return a
'''


def prepare(tmp_path, **options):
    a = np.zeros((256, 256), dtype=np.uint8)
    a[::16, :] = a[:, ::16] = 1
    source = tmp_path / "reference.npy"
    np.save(source, a)
    return start_exploration(source, tmp_path / "run", s2_limit=.25, lineal_limit=.25, **options)


def test_lhs_stratification_replicates_and_reproducibility():
    plan = make_plan(ANCHOR, s2_limit=.2, lineal_limit=.3)
    assert plan == make_plan(ANCHOR, s2_limit=.2, lineal_limit=.3)
    assert len(plan["samples"]) == 20
    for i in range(10):
        a, b = plan["samples"][2*i:2*i+2]
        assert a["requested"] == b["requested"] and a["seed"] != b["seed"]
    for control in CONTROLS:
        lo, hi = plan["bounds"][control]
        bins = [int(10 * (r["requested"][control] - lo) / (hi-lo)) for r in plan["samples"][::2]]
        assert sorted(bins) == list(range(10))


@pytest.mark.parametrize("kwargs", [dict(designs=1), dict(replicates=0), dict(design_seed=-1),
                                     dict(seed_start=-2), dict(s2_limit=float('nan')),
                                     dict(lineal_limit=-1), dict(bounds={})])
def test_invalid_plan_rejected(kwargs):
    with pytest.raises(ValueError):
        make_plan(ANCHOR, **(dict(s2_limit=.2, lineal_limit=.3) | kwargs))


def test_undefined_anchor_metric_requires_explicit_bounds():
    with pytest.raises(ValueError, match="explicit bounds"):
        make_plan(ANCHOR | {"median_pore_diameter": None}, s2_limit=.2, lineal_limit=.2)


def test_default_workflow_detects_clones_and_ignored_controls(tmp_path):
    run = prepare(tmp_path)
    m = resume_exploration(run)
    assert m["status"] == "WAITING_FOR_LLM"
    (run / "response.txt").write_bytes(("\ufeff```python\r\n" + CONSTANT_GENERATOR.replace('\n', '\r\n') + "```\r\n").encode('utf-8'))
    with pytest.raises(ValueError, match="NOT sandboxed"):
        resume_exploration(run)
    m = resume_exploration(run, execute=True)
    assert m["status"] == "COMPLETE"
    attempt = run / m["latest_attempt"]
    report = read_json(attempt / "exploration_report.json")
    assert report["measured_count"] == report["engineering_valid_count"] == 20
    assert report["unique_geometry_count"] == 1
    assert len(report["duplicate_groups"][0]) == 20
    assert report["control_diagnostics"]["solid_fraction_target"]["measured_span"] == 0
    assert report["control_diagnostics"]["solid_fraction_target"]["spearman_requested_vs_design_mean"] is None
    assert report["samples"][0]["measured"]["phi_s"] != report["samples"][0]["requested"]["solid_fraction_target"]
    assert (attempt / "montage.png").is_file() and (attempt / "control_response.png").is_file()
    assert (attempt / "morphology_dataset.csv").read_text().count('\n') == 21
    before = (attempt / "exploration_report.json").read_bytes()
    assert resume_exploration(run, execute=True)["attempt_count"] == 1
    assert (attempt / "exploration_report.json").read_bytes() == before
    (run / "design_plan.json").write_text('{}')
    with pytest.raises(ValueError, match="input modified"):
        resume_exploration(run, execute=True)


def test_failures_and_single_replicate_uncertainty_are_explicit(tmp_path):
    run = prepare(tmp_path, designs=2, replicates=1)
    (run / "response.txt").write_text(CONSTANT_GENERATOR.replace('return a', 'raise ValueError("infeasible")'))
    m = resume_exploration(run, execute=True)
    assert m["status"] == "FAILED"
    report = read_json(run / m["latest_attempt"] / "exploration_report.json")
    assert report["measured_count"] == 0 and len(report["samples"]) == 2
    assert report["control_diagnostics"]["strut_scale"]["within_design_rms_std"] is None
    with pytest.raises(ValueError, match="retry-failed"):
        resume_exploration(run, execute=True)
    m2 = resume_exploration(run, execute=True, retry_failed=True)
    assert m2["attempt_count"] == 2
    assert (run / "attempt_001/exploration_report.json").is_file()


def test_islands_are_measured_not_removed(tmp_path):
    run = prepare(tmp_path, designs=2, replicates=1)
    (run / "response.txt").write_text(CONSTANT_GENERATOR.replace('return a', 'a[7, 7] = 1\n    return a'))
    m = resume_exploration(run, execute=True)
    report = read_json(run / m["latest_attempt"] / "exploration_report.json")
    assert m["status"] == "COMPLETE" and report["engineering_valid_count"] == 0
    assert report["samples"][0]["measured"]["component_count"] == 2
    assert np.load(run / report["samples"][0]["npy_path"])[7, 7] == 1


def test_extracted_generator_cannot_change_silently(tmp_path):
    run = prepare(tmp_path, designs=2, replicates=1)
    (run / "response.txt").write_text(CONSTANT_GENERATOR)
    resume_exploration(run, execute=True)
    (run / "generator.py").write_text(CONSTANT_GENERATOR + '# change\n')
    with pytest.raises(ValueError, match="generator modified"):
        resume_exploration(run, execute=True)


def test_parameterized_generator_moves_measured_geometry(tmp_path):
    bounds = {"solid_fraction_target": [.2, .5], "strut_scale": [1, 6], "pore_scale": [8, 24]}
    run = prepare(tmp_path, designs=4, replicates=2, bounds=bounds)
    source = '''import numpy as np
def generate_microstructure(seed, solid_fraction_target, strut_scale, pore_scale):
    rng = np.random.default_rng(seed)
    width = max(1, int(round(strut_scale + 3 * solid_fraction_target)))
    pitch = max(width + 2, int(round(pore_scale + width)))
    y, x = np.indices((256, 256))
    dx, dy = rng.integers(0, pitch, size=2)
    return (((x + dx) % pitch < width) | ((y + dy) % pitch < width)).astype(np.uint8)
'''
    (run / "response.txt").write_text(source)
    m = resume_exploration(run, execute=True)
    assert m["status"] == "COMPLETE"
    report = read_json(run / m["latest_attempt"] / "exploration_report.json")
    assert report["engineering_valid_count"] == 8
    assert report["unique_geometry_count"] >= 4
    assert report["control_diagnostics"]["strut_scale"]["measured_span"] > 0
    assert report["control_diagnostics"]["pore_scale"]["measured_span"] > 0
    assert any(not r["family_pass"] for r in report["samples"])


@pytest.mark.parametrize("replacement", ["return a.astype(float)",
    "a[7, 7] = np.random.randint(0, 2)\n    return a"])
def test_bad_dtype_and_nondeterminism_are_not_silently_accepted(tmp_path, replacement):
    # Use a deterministic counter to guarantee the second return differs.
    if "randint" in replacement:
        source = CONSTANT_GENERATOR.replace('import numpy as np', 'import numpy as np\ncounter = 0')
        source = source.replace('    a =', '    global counter\n    counter += 1\n    a =')
        source = source.replace('return a', 'a[7, 7] = counter % 2\n    return a')
    else:
        source = CONSTANT_GENERATOR.replace('return a', replacement)
    run = prepare(tmp_path, designs=2, replicates=1)
    (run / "response.txt").write_text(source)
    m = resume_exploration(run, execute=True)
    assert m["status"] == "FAILED"
    report = read_json(run / m["latest_attempt"] / "exploration_report.json")
    assert report["measured_count"] == 0
    assert all(r["error"] for r in report["samples"])


def test_timeout_leaves_all_missing_rows_and_logs(tmp_path):
    run = prepare(tmp_path, designs=2, replicates=1, timeout=.01)
    (run / "response.txt").write_text(CONSTANT_GENERATOR)
    m = resume_exploration(run, execute=True)
    assert m["status"] == "FAILED"
    attempt = run / m["latest_attempt"]
    assert read_json(attempt / "execution/metadata.json")["timed_out"]
    report = read_json(attempt / "exploration_report.json")
    assert report["measured_count"] == 0 and len(report["samples"]) == 2


def test_cli_routes_exploration_without_replication_manifest(tmp_path, capsys):
    from metamaterial_eval.pipeline.cli import main
    run = prepare(tmp_path, designs=2, replicates=1)
    assert main(["explore-status", str(run)]) == 0
    assert '"mode": "exploration"' in capsys.readouterr().out
    assert main(["explore-resume", str(run)]) == 0
    assert not (run / "manifest.json").exists()
