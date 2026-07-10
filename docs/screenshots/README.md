# Flagship map screenshot baseline

Deterministic captures of **Col du Rivelet** at fixed route distances,
taken headless (Playwright, 1440x900, UI hidden) while riding the demo
source. This set is the visual reference for the flagship map and, per
[technical-assessment.md](../technical-assessment.md) §2.1, seeds the
anchor set the future LLM judge is calibrated against.

| File | Distance | Scene |
|---|---|---|
| `flagship_00400m.png` | 0.4 km | Depart Meadows — fields warmup |
| `flagship_02400m.png` | 2.4 km | Rivelet Village |
| `flagship_03600m.png` | 3.6 km | Forest Gate — climb begins |
| `flagship_05200m.png` | 5.2 km | Cross Traverse — between the switchbacks |
| `flagship_07600m.png` | 7.6 km | Ridge Shoulder — exposed crest |
| `flagship_09000m.png` | 9.0 km | Crete du Rivelet |
| `flagship_11500m.png` | 11.5 km | Larch Descent |
| `flagship_14200m.png` | 14.2 km | Mill Return — village run-out |
| `flagship_15800m.png` | 15.8 km | River Flats |

Regenerate after any renderer or map change:

```bash
uv sync --group e2e
uv run python tests/e2e/capture_flagship_screenshots.py
```

(Rides the full loop at 450 W — takes roughly 20 minutes.) The current set
was captured 2026-07-10, after the M3 camera pass (speed-sensitive FOV and
curvature lean), so views are slightly wider than the original M2 set.
Note: CI containers render via SwiftShader (software GL), which differs
subtly from real GPUs — compare like with like.
