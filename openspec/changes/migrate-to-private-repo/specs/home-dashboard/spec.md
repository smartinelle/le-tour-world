# home-dashboard

New launch surface replacing the upstream NiceGUI app (app.py/theme.py
were 97% upstream). Designed fresh — this is where "we won't keep the
interface exactly as is" lands hardest. The 2D ride view, live-snake, and
browser-BLE pages are NOT ported.

## ADDED Requirements

### Requirement: Launch surface

The home page SHALL present route cards (title, difficulty, elevation
sparkline, distance/gain/max-grade) that open the 3D surface with the
route preselected; a mode picker + Start Ride that launches the 3D surface
directly; recent rides; and entry points to history and settings. The 3D
surface is the only ride cockpit.

#### Scenario: Card to riding
- **WHEN** the user clicks a route card and then a mode
- **THEN** they are riding that route on the 3D surface with no
  intermediate 2D screens

### Requirement: Settings

Settings SHALL cover rider profile (mass, FTP, units), defaults (ERG
target, SIM route), and device pairing (scan/connect/disconnect for
trainer and HR), persisted locally.

#### Scenario: FTP flows to the HUD
- **WHEN** the user changes FTP in settings
- **THEN** the next ride's power-zone coloring uses the new value

### Requirement: Own visual identity

The dashboard's layout, styles, and components SHALL be authored fresh in
the new repo (new theme, new component set) — both for ownership and
because the product brand will differ from the upstream project.

#### Scenario: No inherited chrome
- **WHEN** the new dashboard ships
- **THEN** no template, stylesheet, or component file originates from the
  fork's `web/components` or `theme.py`
