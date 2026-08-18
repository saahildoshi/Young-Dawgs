# Evaluator Validation

This directory freezes and validates the periodic evaluator before research
use.

```text
evaluator_validation/
├── evaluator/          immutable and candidate evaluator versions
├── test_images/        canonical analytical NPY fixtures
├── expected_results/   hand-calculated expectations
├── actual_results/     pytest logs, XML, and integration checks
├── test_evaluator.py   automated acceptance suite
└── validation_notes.md version conclusions and conventions
```

Generate fixtures:

```bash
python evaluator_validation/generate_test_images.py
```

Validate frozen v1.0:

```bash
EVALUATOR_PATH=evaluator_validation/evaluator/evaluator_v1_0.py \
python -m pytest evaluator_validation/test_evaluator.py -v
```

Validate candidate v1.1:

```bash
EVALUATOR_PATH=evaluator_validation/evaluator/evaluator_v1_1.py \
python -m pytest evaluator_validation/test_evaluator.py -v
```
