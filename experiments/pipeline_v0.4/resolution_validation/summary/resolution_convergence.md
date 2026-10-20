# Pipeline v0.4 Resolution Validation

## Generator

Source: `/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.3/exploration_test_01/generator.py`

v0.3 SHA-256: `61304070aad94b8eb4595c65ce61dc9cab35fe14caada60bc4526fb0175f3839`

v0.4 SHA-256: `2ed622d96eb49df566c5adf8e4d9d4414984a8dead238b4d97e5d0b5af26be89`

## Resolutions

[256, 512, 1024]

## Representative Designs

| Design | Solid fraction target | Strut scale | Pore scale | Selection |
|---|---:|---:|---:|---|
| 5 | 0.503812 | 4.167579 | 7.769583 | nearest envelope center |
| 1 | 0.432496 | 3.607490 | 6.641246 | low solid fraction |
| 2 | 0.517808 | 4.632534 | 6.020373 | high solid fraction |
| 0 | 0.479499 | 3.811718 | 8.405666 | low strut / high pore |
| 9 | 0.476923 | 4.340345 | 6.148749 | high strut / low pore |

## Topology

| Design | Seed | N | Components | Px | Py | Status |
|---|---:|---:|---:|---:|---:|---|
| 0 | 0 | 256 | 1 | 1 | 1 | COMPLETE |
| 0 | 0 | 512 | 1 | 1 | 1 | COMPLETE |
| 0 | 0 | 1024 | 1 | 1 | 1 | COMPLETE |
| 0 | 1 | 256 | 1 | 1 | 1 | COMPLETE |
| 0 | 1 | 512 | 1 | 1 | 1 | COMPLETE |
| 0 | 1 | 1024 | 1 | 1 | 1 | COMPLETE |
| 1 | 0 | 256 | 1 | 1 | 1 | COMPLETE |
| 1 | 0 | 512 | 1 | 1 | 1 | COMPLETE |
| 1 | 0 | 1024 | 1 | 1 | 1 | COMPLETE |
| 1 | 1 | 256 | 1 | 1 | 1 | COMPLETE |
| 1 | 1 | 512 | 1 | 1 | 1 | COMPLETE |
| 1 | 1 | 1024 | 1 | 1 | 1 | COMPLETE |
| 2 | 0 | 256 | 1 | 1 | 1 | COMPLETE |
| 2 | 0 | 512 | 1 | 1 | 1 | COMPLETE |
| 2 | 0 | 1024 | 1 | 1 | 1 | COMPLETE |
| 2 | 1 | 256 | 1 | 1 | 1 | COMPLETE |
| 2 | 1 | 512 | 1 | 1 | 1 | COMPLETE |
| 2 | 1 | 1024 | 1 | 1 | 1 | COMPLETE |
| 5 | 0 | 256 | 1 | 1 | 1 | COMPLETE |
| 5 | 0 | 512 | 1 | 1 | 1 | COMPLETE |
| 5 | 0 | 1024 | 1 | 1 | 1 | COMPLETE |
| 5 | 1 | 256 | 1 | 1 | 1 | COMPLETE |
| 5 | 1 | 512 | 1 | 1 | 1 | COMPLETE |
| 5 | 1 | 1024 | 1 | 1 | 1 | COMPLETE |
| 9 | 0 | 256 | 1 | 1 | 1 | COMPLETE |
| 9 | 0 | 512 | 1 | 1 | 1 | COMPLETE |
| 9 | 0 | 1024 | 1 | 1 | 1 | COMPLETE |
| 9 | 1 | 256 | 1 | 1 | 1 | COMPLETE |
| 9 | 1 | 512 | N/A | N/A | N/A | FAILED |
| 9 | 1 | 1024 | N/A | N/A | N/A | FAILED |

## Morphological Convergence

| Design | Seed | N | phi_s | mean t/N | p10 t/N | median pore/N |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 256 | 0.479492 | 0.0176346 | 0.0078125 | 0.03125 |
| 0 | 0 | 512 | 0.4795 | 0.0165972 | 0.00873464 | 0.03125 |
| 0 | 0 | 1024 | 0.479499 | 0.0161202 | 0.00976562 | 0.0305712 |
| 0 | 1 | 256 | 0.479492 | 0.0176603 | 0.0078125 | 0.0322118 |
| 0 | 1 | 512 | 0.4795 | 0.0166001 | 0.00873464 | 0.0322118 |
| 0 | 1 | 1024 | 0.479499 | 0.0161161 | 0.00976562 | 0.0322709 |
| 1 | 0 | 256 | 0.432495 | 0.0136784 | 0.0078125 | 0.0281684 |
| 1 | 0 | 512 | 0.432495 | 0.0127746 | 0.0078125 | 0.0281684 |
| 1 | 0 | 1024 | 0.432496 | 0.0123056 | 0.0078125 | 0.0284379 |
| 1 | 1 | 256 | 0.432495 | 0.0137947 | 0.0078125 | 0.0297092 |
| 1 | 1 | 512 | 0.432495 | 0.0128308 | 0.0078125 | 0.0284379 |
| 1 | 1 | 1024 | 0.432496 | 0.0123874 | 0.0078125 | 0.0290353 |
| 2 | 0 | 256 | 0.517807 | 0.0157638 | 0.0078125 | 0.0247053 |
| 2 | 0 | 512 | 0.517807 | 0.0147053 | 0.00873464 | 0.0247053 |
| 2 | 0 | 1024 | 0.517808 | 0.0142659 | 0.00976562 | 0.0244726 |
| 2 | 1 | 256 | 0.517807 | 0.0157873 | 0.0078125 | 0.0247053 |
| 2 | 1 | 512 | 0.517807 | 0.0147067 | 0.00873464 | 0.0256081 |
| 2 | 1 | 1024 | 0.517808 | 0.0142098 | 0.00873464 | 0.0253906 |
| 5 | 0 | 256 | 0.503815 | 0.0178896 | 0.0078125 | 0.03125 |
| 5 | 0 | 512 | 0.503811 | 0.016767 | 0.0110485 | 0.0297491 |
| 5 | 0 | 1024 | 0.503812 | 0.0163168 | 0.00995902 | 0.0292969 |
| 5 | 1 | 256 | 0.503815 | 0.0182602 | 0.0078125 | 0.03125 |
| 5 | 1 | 512 | 0.503811 | 0.0172354 | 0.0110485 | 0.0305088 |
| 5 | 1 | 1024 | 0.503812 | 0.0167463 | 0.00995902 | 0.0305088 |
| 9 | 0 | 256 | 0.476929 | 0.014888 | 0.0078125 | 0.0281684 |
| 9 | 0 | 512 | 0.476921 | 0.0138496 | 0.0078125 | 0.0262039 |
| 9 | 0 | 1024 | 0.476922 | 0.0133677 | 0.00805294 | 0.0262039 |
| 9 | 1 | 256 | 0.476929 | 0.0149552 | 0.0078125 | 0.0281684 |
| 9 | 1 | 512 | N/A | N/A | N/A | N/A |
| 9 | 1 | 1024 | N/A | N/A | N/A | N/A |

## Cross-Resolution Error

Full native evaluator curves interpolated onto rho=0:1/256:0.25; NRMSE denominator is lower-resolution curve RMS.

| Design | Seed | 256→512 S2 | 256→1024 S2 | 256→512 L | 256→1024 L |
|---|---:|---:|---:|---:|---:|
| 0 | 0 | 0.0060067 | 0.0079476 | 0.0214927 | 0.0267117 |
| 0 | 1 | 0.00613628 | 0.00808562 | 0.0240249 | 0.0292585 |
| 1 | 0 | 0.00913033 | 0.0118397 | 0.0301627 | 0.0351712 |
| 1 | 1 | 0.00902112 | 0.0117421 | 0.0301816 | 0.0377206 |
| 2 | 0 | 0.00662687 | 0.00850588 | 0.0287928 | 0.0348609 |
| 2 | 1 | 0.00691876 | 0.00868168 | 0.0313507 | 0.0393432 |
| 5 | 0 | 0.00551845 | 0.00729884 | 0.0239869 | 0.028856 |
| 5 | 1 | 0.00521079 | 0.0070738 | 0.0194261 | 0.023454 |
| 9 | 0 | 0.00776598 | 0.00988647 | 0.0333847 | 0.0374376 |
| 9 | 1 | N/A | N/A | N/A | N/A |

### Provisional target checks: 256→1024

| Metric | Limit | Passing pairs | Worst error |
|---|---:|---:|---:|
| phi_s_absolute | 0.005 | 9/10 | 6.67572e-06 |
| mean_strut_relative | 0.05 | 0/10 | 0.102117 |
| p10_strut_relative | 0.1 | 3/10 | 0.274755 |
| pore_relative | 0.05 | 7/10 | 0.0697395 |
| S2_nrmse | 0.05 | 9/10 | 0.0118397 |
| L_nrmse | 0.05 | 9/10 | 0.0393432 |

512→1024 errors and block-reduced IoU, disagreement, SSIM and NCC are retained in the JSON.

## Parametric-Control Preservation

Spearman associations of design means; not independent causal tests.

| N | Density control | Strut control | Pore control |
|---|---:|---:|---:|
| 256 | 1 | 0.2 | 1 |
| 512 | 1 | 0.4 | 1 |
| 1024 | 1 | 0.4 | 1 |

The table above uses all complete groups available at each N. For a fair matched-cohort comparison:

Complete at every resolution: designs [0, 1, 2, 5].

| N | Matched density | Matched strut | Matched pore |
|---|---:|---:|---:|
| 256 | 1 | 0.4 | 1 |
| 512 | 1 | 0.4 | 1 |
| 1024 | 1 | 0.4 | 1 |

## Runtime

| N | Mean generation s | Mean evaluation s | Mean PNG+NPY bytes | Mean peak traced bytes |
|---|---:|---:|---:|---:|
| 256 | 0.0655014 | 0.167223 | 73975.5 | 1.1104e+07 |
| 512 | 0.231893 | 0.25836 | 282435 | 4.5865e+07 |
| 1024 | 0.6385 | 0.797811 | 1.09468e+06 | 1.79558e+08 |

## Regression Against v0.3

All selected 256 outputs equal old generator AND saved historical arrays: **True**.

Historical source inventory unchanged: **True**.

## Limitations and diagnosis

- v0.3 thickness uses discrete EDT and skeletonization; normalized estimates are quantized, especially P10.
- Native two-sided interface footprint and lattice EDT are approximate continuations of v0.3 raster rules.
- Continuous latent fields retain v0.3's 256-grid bandwidth; higher N adds boundary samples, not new random features.
- Four-direction digital lineal paths retain evaluator v1.1 conventions, including equal step indices for diagonal paths.
- LHS controls are coupled; small-sample rank trends are associations, not isolated causal effects.
- Timing includes baseline candidate selection and tracemalloc instrumentation, excludes process startup and repeatability check.
- No CAD, vectorization, STEP, STL, extrusion, FEM, ANSYS or mesh has been produced.

Mean-width drift can combine digital skeleton/EDT bias with changes in the native interface footprint. The current experiment does not isolate those contributions. P10 often quantizes to only a few pixels at 256. Do not reinterpret missed thresholds as passes or add morphology corrections to hide them.

## Conclusions

Native generation is implemented, but v0.5 readiness is NOT established. Review failed convergence gates and remaining discretization effects; no morphology was retuned to force acceptance.

## Failures

- Design 9, seed 1, N=512: Traceback (most recent call last):
  File "/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/metamaterial_eval/pipeline/resolution_worker.py", line 58, in perform_job
    array = model.generate_microstructure(job["seed"], **job["requested"], resolution=n)
  File "/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/metamaterial_eval/generators/native_resolution.py", line 68, in generate_microstructure
    raise RuntimeError("Matched native realization fails single-component spanning topology; "
RuntimeError: Matched native realization fails single-component spanning topology; no new seed, island removal or bridging was substituted.

- Design 9, seed 1, N=1024: Traceback (most recent call last):
  File "/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/metamaterial_eval/pipeline/resolution_worker.py", line 58, in perform_job
    array = model.generate_microstructure(job["seed"], **job["requested"], resolution=n)
  File "/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/metamaterial_eval/generators/native_resolution.py", line 68, in generate_microstructure
    raise RuntimeError("Matched native realization fails single-component spanning topology; "
RuntimeError: Matched native realization fails single-component spanning topology; no new seed, island removal or bridging was substituted.


Diagnostic replays of rejected rasters are saved in failure_diagnostics.json and each failed job's rejected_evidence directory. They are NOT accepted outputs.
