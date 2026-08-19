# Evaluator Validation

This directory contains the analytical acceptance suite used to distinguish
the frozen v1.0 evaluator from the accepted v1.1 evaluator.

| Path | Meaning |
|---|---|
| `evaluators/` | Frozen v1.0 and accepted v1.1 standalone evaluators |
| `fixtures/` | Canonical binary arrays with known analytical behavior |
| `expected/` | Hand-calculated expected values |
| `results/` | JUnit logs, integration results, console records, and figures |
| `test_evaluator.py` | 56-test scientific acceptance suite |
| `validation_notes.md` | Detailed conclusions and accepted conventions |
| `OBSIDIAN_ANALYTICAL_TEST_RESULTS.md` | Mentor-ready v1.0/v1.1 tables |

Generate the fixtures:

```bash
python validation/generate_test_images.py
```

Validate accepted v1.1:

```bash
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py \
python -m pytest validation/test_evaluator.py -v
```

Reproduce the historical v1.0 failures:

```bash
EVALUATOR_PATH=validation/evaluators/evaluator_v1_0.py \
python -m pytest validation/test_evaluator.py -v
```

Expected outcome: v1.1 passes `56/56`; v1.0 fails `20/56` acceptance tests.
