# Regression Baseline v1

- Generated: 2026-03-11T00:56:36
- Commit: b7e1091
- Manifest: `tests/regression_samples_manifest.json`
- Samples: 4
- Total elapsed: 105.577 ms

## Sample Metrics

| Sample | Input Shape | Output Shape | Non-finite In | Elapsed (ms) | Out mean | Out std | Out p01 | Out p99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| layered_small | 256x80 | 256x80 | 0 | 0.322 | -0.000000 | 0.249931 | -0.628843 | 0.624132 |
| hyperbola_target | 320x96 | 320x96 | 0 | 0.387 | 0.000000 | 0.106869 | -0.164456 | 0.575107 |
| clutter_spiky | 200x72 | 200x72 | 0 | 0.196 | -0.000000 | 0.026925 | -0.036567 | 0.036691 |
| nan_inf_robustness | 180x60 | 180x60 | 7 | 0.132 | 0.000000 | 0.198906 | -0.487373 | 0.484302 |
