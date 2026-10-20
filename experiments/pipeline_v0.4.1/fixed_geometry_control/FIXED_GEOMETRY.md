# Frozen-geometry sampling control

Fixed 2048 raster, nearest endpoint-aligned sampling; diagnostic only, never native production output

Finite 2048 raster is not continuum truth. Attribution is approximate, not a universal bias correction.

| Design | Seed | Step | Mean thickness change % | P10 change % | Pore median change % |
|---:|---:|---|---:|---:|---:|
| 1 | 0 | 256 → 512 | -6.4933 | +0.0000 | +0.0000 |
| 1 | 0 | 512 → 1024 | -3.6997 | +0.0000 | +0.9570 |
| 1 | 0 | 1024 → 2048 | -1.9264 | -2.3719 | +0.1179 |
| 2 | 0 | 256 → 512 | -7.0739 | +11.8034 | +0.0000 |
| 2 | 0 | 512 → 1024 | -3.4226 | +11.8034 | -0.9419 |
| 2 | 0 | 1024 → 2048 | -1.8259 | -7.8046 | -0.2391 |
| 5 | 0 | 256 → 512 | -6.5442 | +0.0000 | -4.8028 |
| 5 | 0 | 512 → 1024 | -2.8903 | -9.8612 | -1.5202 |
| 5 | 0 | 1024 → 2048 | -1.6123 | +0.9570 | +0.2774 |
