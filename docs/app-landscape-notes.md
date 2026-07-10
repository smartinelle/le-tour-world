# Indoor Cycling App Landscape — UX Notes

Working notes (2026-07-10) on how the established apps present the ride,
gathered to calibrate le-tour's feel benchmarks
([technical-assessment.md](technical-assessment.md) §1). These are
observations from public sources, not first-hand test rides — replace with
first-hand notes as we try each app.

## How the majors present the ride

| App | World | Default view | Positioning |
|---|---|---|---|
| Zwift (~$18/mo) | Stylized CGI worlds (Watopia etc.) | Third-person chase camera behind an animated avatar | The social/gaming platform: 1M+ subscribers, races, group rides, drafting |
| MyWhoosh (free) | Stylized CGI, near-Zwift graphics | Third-person avatar chase | UCI eSports platform; cash-prize racing; funded, not subscription |
| TrainingPeaks Virtual | CGI, more realistic look | Third-person avatar | Training-first: workout execution over social |
| Rouvy (~$20/mo) | Real HD video of real roads, avatar overlaid | The video's own camera | "Ride somewhere real": Tour climbs, Iceland, Colombia |
| FulGaz / Kinomap | Real video | Video camera | Same family as Rouvy |

## What this means for ride feel

- **Nobody bobs the camera.** The CGI apps put visual "life" into the
  *avatar* — cadence-matched pedaling animation, posture changes (sitting
  up in the draft, out of the saddle on climbs) — while the camera itself
  stays heavily damped and steady. The world never oscillates. le-tour
  briefly shipped a sinusoidal camera bob; it read as riding over bumps
  and was removed (2026-07-10). Vertical camera motion now comes from
  terrain elevation only.
- **Third-person is the default everywhere CGI.** A chase camera makes
  grade changes legible (you *see* the avatar tilt onto a climb) and
  tolerates imperfect motion better — the avatar absorbs it. First-person
  exists in Zwift but is a secondary mode users must re-select each ride.
  le-tour is currently first-person-only (handlebar cockpit); an animated
  third-person avatar mode is the single biggest presentation gap.
- **Speed is app-computed everywhere** (power + rider profile + grade +
  draft), which le-tour now matches (`RiderDynamics`). Zwift additionally
  models **drafting** (~30% power saving behind a rider) — a mechanic, a
  realism cue, and the foundation of racing dynamics all at once.
- **Trainer feel**: in SIM the apps send grade to the trainer and let
  hardware provide the inertia; riders even use gearing to change pedal
  inertia feel. le-tour's smoothed-grade ramping matches this approach.

## Judgement checklist for first-hand testing

When trying each app, note: default camera and how it handles grade
transitions · what moves in the frame at steady state (avatar limbs?
scenery only?) · time from app open to pedaling · HUD density and
legibility at a glance · what happens at ride end · how ERG feels entering
and exiting intervals · draft/social presence effects.

## Sources

- Zwift camera views and first-person discussions: Zwift Forums
  (rider-view, camera-views, first-person FutureWorks threads); Zwift
  Insider on camera cycling.
- 2026 platform comparisons: T3, Cyclingnews, Cyclists Hub, Slowtwitch,
  Indoor Cycling Tips (pricing, graphics, positioning, user counts).
- Drafting mechanics: Zwift Insider ("Drafting in Zwift").
