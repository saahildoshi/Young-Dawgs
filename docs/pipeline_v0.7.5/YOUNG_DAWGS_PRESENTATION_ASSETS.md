# Young Dawgs presentation assets

- [Schematic research workflow timeline](../../experiments/pipeline_v0.7.5/run_001/figures/RESEARCH_TIMELINE.png)
- [P3 raw SEM](../../experiments/pipeline_v0.7.0/run_002_real_microscopy/references/P3/microscopy_input.png)
- [P3 evaluator annotation](../../experiments/pipeline_v0.7.0/run_002_real_microscopy/references/P3/evaluation_only_labels.npy)
- [P3 microscopy and representative generated arrays](../../experiments/pipeline_v0.7.0/run_002_real_microscopy/analysis/P3_held_REFERENCE_GENERATED.png)
- [F1 prepared C/PEEK image](../../experiments/pipeline_v0.7.0/run_002_real_microscopy/references/F1/microscopy_input.png)
- [F1 evaluator annotation](../../experiments/pipeline_v0.7.0/run_002_real_microscopy/references/F1/evaluation_only_labels.npy)
- [F1 reference and generated phase maps](../../experiments/pipeline_v0.7.4/run_001/f1/figures/F1_REFERENCE_AND_GENERATED_PHASES.png)
- [Historical porous Design 009 seed 001 array](../../experiments/pipeline_v0.4.1/resolution_validation/design_009/seed_001/1024/microstructure.npy)
- [Historical porous source and printable model](../../presentation_assets/v0.7.4/POROUS_METAMATERIAL_PREVIEW.png)
- [P3 reference and generated stress–strain](../../experiments/pipeline_v0.7.1/run_001/figures/NATIVE_CURVES.png)
- [F1 reference and generated stress–strain](../../experiments/pipeline_v0.7.4/run_001/f1/figures/F1_ACTUAL_STRESS_STRAIN_AND_FORCE.png)
- [F1 actual native curve data](../../experiments/pipeline_v0.7.4/run_001/f1/F1_NATIVE_CURVES.csv)
- [Historical stiffness increases](../../experiments/pipeline_v0.7.2/run_001/figures/HELDOUT_STIFFNESS.png)
- [Historical morphology drift](../../experiments/pipeline_v0.7.2/run_001/figures/REFERENCE_AND_GENERATED_GEOMETRY.png)
- [v0.7.4 initial and revised target errors](../../experiments/pipeline_v0.7.4/run_001/figures/P3_PAIRED_SCRIPT_TARGET_ERRORS.png)
- [P3 print-ready relief](../../presentation_assets/v0.7.4/P3_REFERENCE_PRINT_READY.stl)
- [Framed porous through-hole model](../../presentation_assets/v0.7.4/POROUS_METAMATERIAL_PRINT_READY.stl)
- [Side-by-side STL preview](../../presentation_assets/v0.7.4/P3_VS_POROUS_PRESENTATION_MODELS.png)
- [P3 STL preview](../../presentation_assets/v0.7.4/P3_REFERENCE_STL_PREVIEW.png)
- [P3 printing instructions](../../presentation_assets/v0.7.4/PRINTING_INSTRUCTIONS.md)
- [Porous printing instructions](../../presentation_assets/v0.7.4/POROUS_METAMATERIAL_PRINTING_INSTRUCTIONS.md)

The recommended P3 relief uses a solid backing and a documented 1383-pixel print-safe simplification. The framed porous model preserves the unedited crop and its 19 original interior through-holes, and encloses 16 clipped edge pockets. The historical full-resolution model contains sub-nozzle features. Both recommended STLs passed geometric checks and actual generic slicing. Physical printer results remain untested. These are enlarged educational geometries derived from 2D fields.

For a short presentation, start with how the generators reproduce different kinds of geometry. Show native curves, then the stiff but visibly lane-like revisions that motivated stronger constraints. End with the prescribed target and the question of whether measured feedback improves revisions. The v0.7.5 outcome figures depend on completion of the replicated experiment.
