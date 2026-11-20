"""Read-only verification of actual v0.7.5 licensed evidence."""
from pathlib import Path

import numpy as np
import pytest

from scripts.v070_protocol import REPO, read, sha
from scripts.v075_protocol import RUN


@pytest.mark.parametrize('result', sorted((RUN/'mechanical_response').glob('*.json')), ids=lambda p: p.stem)
def test_v075_native_evidence(result):
    record = read(result)
    assert record['accepted'] and all(record['checks'].values())
    source = Path(record['source_directory'])
    readback = Path(record['independent_readback_directory'])
    assert read(source/'EXECUTION.json')['solver_release'] == '2024 R1'
    assert read(source/'EXECUTION.json')['native_process_ok']
    assert read(readback/'EXECUTION.json')['native_process_ok']
    assert all(read(readback/'READBACK.json')['identical_exports_to_solve'].values())
    provenance = read(RUN/'native_result_manifests'/source.name/'NATIVE_ARTIFACTS.json')
    for item in provenance.values():
        assert sha(Path(item['path'])) == item['sha256']
    assert sha(source/'elastic.rst') == record['native_result_sha256']
    specimen = read(RUN/'specimen_manifests'/f"{record['specimen_id']}.json")
    assert sha(REPO/specimen['source_array_path']) == specimen['source_array_sha256']
    rows = np.loadtxt(readback/'curve.csv', delimiter=',')
    x, y = -rows[:, 2], -rows[:, 5]
    assert x == pytest.approx([.001, .002, .003, .004, .005], abs=1e-9)
    assert np.polyfit(x, y, 1)[0] == pytest.approx(record['effective_modulus_MPa'], rel=1e-10)
    assert rows[:, 8] == pytest.approx(.5*x*y, rel=.001)
    assert max(abs(rows[:, 5]+rows[:, 6])/y) <= .001
    assert record['phase_results']['2']['volume_fraction'] == pytest.approx(20731/65536, abs=1e-8)
