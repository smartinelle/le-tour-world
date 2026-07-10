# route-model

Rewrite of the Python route model (`routes.py`). The JSON route schema and
the flagship map carry over; the JS path compiler (`route_path.js`) is
carried, not rewritten.

## ADDED Requirements

### Requirement: Route spec schema

A route SHALL be a validated JSON spec (`schema_version: 1`) with id,
title, description, and ordered segments; each segment has name, length m,
grade %, turn deg, road width m, kind, surface, and scenery from closed
vocabularies. Validation errors name the offending field. Bundled routes
load from packaged assets; the flagship map (Col du Rivelet) is the
reference content.

#### Scenario: Invalid spec rejected
- **WHEN** a spec omits a required field or uses an unknown surface
- **THEN** loading fails with an error naming the field, and the app's
  route list omits the bad spec

### Requirement: Distance-indexed queries

The model SHALL answer, for any distance (wrapping modulo route length):
current segment, position/progress within it, next segment, raw grade,
and 30 m-smoothed grade. It SHALL expose derived stats: total distance,
elevation gain, max grade, and a difficulty label with fixed thresholds.

#### Scenario: Lap wrap
- **WHEN** distance exceeds route length
- **THEN** queries behave as if the rider re-entered the route at the
  seam, with no discontinuity in smoothed grade

### Requirement: Compiler seam stability

The JSON spec consumed by the carried JS compiler (`buildRoutePath`) SHALL
remain the exact contract the Python model serializes, so generated or
authored routes render without translation. This is also the future
generative layer's insertion point (`route_from_spec`).

#### Scenario: Round trip
- **WHEN** a route validates in Python and is served to the browser
- **THEN** `buildRoutePath` compiles it without errors and reports its
  closure metrics
