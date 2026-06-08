# Atris F1 Immediate Todo

## Immediate Ships

- Stabilize the current F1 data layer end to end: current season schedule, session links, race control, weather, positions, laps, qualifying, race results, and prediction freshness.
- Add a live-session visualiser roadmap item: on-track car positions, lap delta tower, fastest lap, tyre/wear panels, fuel and damage-style telemetry panels where the upstream data supports it.
- Expand OpenF1 ingestion beyond current snapshots: car data, intervals, location, pit stops, stints, team radio metadata, and richer lap history.
- Add a race weekend telemetry table for Practice, Qualifying, and Race tabs with best lap, last lap, sector splits, speed trap, tyre/stint, position delta, and race-control flags.
- Add circuit/track view upgrades: accurate circuit map, clickable expanded view, and later car-position overlay when location data is stored.
- Add model-readiness diagnostics: what data each prediction used, latest source freshness, missing source rows, and confidence downgrade reasons.
- Add empty states that tell the truth: no sample data, no fake fallback, just the missing API layer and next refresh needed.
- Keep UI asset use strict: no poor driver/team images, no unofficial logos unless licensed/source quality is acceptable.

## Later

- Full race replay / live visualiser page for sessions with replay scrubber, driver selector, timing tower, mini-map, event timeline, and telemetry overlays.
- More historical seasons with consistent coverage checks before model training.
- Market integration after the F1 data and prediction layer is reliable.
