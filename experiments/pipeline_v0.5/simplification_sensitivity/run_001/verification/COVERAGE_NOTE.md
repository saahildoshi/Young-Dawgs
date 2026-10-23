# Retained first diagnostic execution

All 43 candidates and their continuous/raster measurements were retained unchanged. This execution exposed an aggregation defect: a missing registered void anchor made local clearance undefined, but the aggregate clearance-decrease event was false rather than unknown. This could falsely suggest non-monotonic recovery. The corrected implementation uses three-valued coverage flags; the unchanged primary sweep is repeated in run_002. No tolerance, metric threshold or geometry source changed. Use run_002 for final interpretation.
