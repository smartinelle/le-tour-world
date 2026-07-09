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
| `flagship_05200m.png` | 5.2 km | Switchbacks — heart of the climb |
| `flagship_07600m.png` | 7.6 km | Ridge Shoulder / Crete — exposed crest |
| `flagship_09000m.png` | 9.0 km | Crete du Rivelet |
| `flagship_11500m.png` | 11.5 km | Larch Descent |
| `flagship_14200m.png` | 14.2 km | River Flats |
| `flagship_15800m.png` | 15.8 km | Home Meadows — run-in |

Regenerate after any renderer or map change (the capture script lives in
the session scratchpad for now; M6 turns it into a checked-in Playwright
harness). Note: CI containers render via SwiftShader (software GL), which
differs subtly from real GPUs — compare like with like.
