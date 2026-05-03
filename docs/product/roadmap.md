# Product Roadmap

This roadmap is private working context for the project and the agents working
on it. It should describe the real product direction, current implementation
state, and near-term priorities without pretending unfinished ideas are already
committed product promises.

## Now: 2026-05-02

le-tour is a web-first indoor cycling app running as a local Python process
with a browser UI. The product is no longer aiming to restore or support a
terminal UI. The old Rich/TUI direction is historical context only.

The current working product shape is:

- Local Python runtime owns trainer communication, ride state, persistence, and
  domain logic.
- NiceGUI provides the active browser UI in `le_tour/web`.
- Python/Bleak is the primary hardware path for FTMS trainers and BLE heart-rate
  monitors.
- Web Bluetooth exists as an experimental browser-side path, but it is not the
  default trainer connection model.
- Free Ride, ERG, and SIM modes exist as the core training modes.
- Ride state is exposed through UI-neutral snapshots so browser surfaces can
  consume ride data without reaching into trainer internals.
- `/ride3d` is the current Three.js prototype surface for riding against the same
  runtime contracts.
- Session data is stored through the repository layer, with JSONL as the durable
  local source and SQLite as a query/cache layer.
- The History surface reads real recorded sessions from the repository.
- The Settings surface persists rider profile/default values to local config.
- Supabase auth/storage support exists, but the product is still primarily
  local-first and not yet a finished hosted multi-user product.

The current product direction is:

- Build a real app for real users, free or paid, without carrying the old
  terminal-first assumptions forward.
- Launch first toward early users: tech-comfortable indoor cyclists, makers, and
  training-focused riders who can tolerate a local app if the ride loop is
  useful and reliable.
- Keep the UI replaceable, but optimize future surfaces around richer browser/3D
  experiences, API/mobile clients, and headless workflows.
- Use Three.js worlds and routes as a differentiator.
- Explore prompt-generated routes/worlds as a future premium feature, while
  keeping generated route logic independent from NiceGUI and renderer details.
- Avoid multiplayer/social features for now.

Near-term product priorities:

- Treat the first launchable product as a polished non-3D ride cockpit for early
  users, not as a broad consumer launch or full Zwift replacement. Use
  `docs/product/mvp-spec.md` as the working MVP scope and feature audit.
- Make the existing web ride loop reliable and understandable before adding new
  product surface area.
- Make installation/running understandable enough that an early user does not
  need to understand the codebase.
- Make trainer and heart-rate connection flows clear and dependable.
- Keep trainer/device state, ride runtime, route state, and persistence behind
  domain or application contracts.
- Improve SIM route selection and route metadata so `/ride3d` can become more
  than a demo surface.
- Keep CSV export, persisted settings, and repository-backed history usable as
  part of the MVP value proposition.
- Define the generated route/world contract before building prompt UI.
- Decide the local-vs-cloud data strategy before treating Supabase as production
  persistence.
- Keep docs and ADRs aligned whenever old structure conflicts with the new
  browser-first product direction.

## Outlook

The final vision of the product is outlined in the README.md file. Obviously, we will not get there right away.
Here are my current thoughts on the roadmap and next steps:
Right now, to my knowledge, the app runs both on local files and in the browser. Would it be an app, it would have to be downloaded and then used in the browser.
I would really like to avoid that, because i have never dealt with the additional requirements of local running files. But I am also not knowledgable enough to know the pros and cons of this.
The product name is now le-tour. The Python package uses `le_tour` because Python modules cannot contain hyphens. Meanwhile we are working on improving the design as well.

For now, what I want the most is a working non-3d dockpit version, that I myself can actually use. In parallel to that we will continue to work on the 3d world and routes, and (then) on packaging the app for distribution. When we will actually have the app in distribution, we will listen to user-feedback. One thing I am sure people will want is more integrations.

In many aspects, the app should very much adhere to the same logics that ZWIFT did in the interaction and layout of pages, because a lot of functionality is similar. But obviously not all of them.

One thing I am unsure about is, with what MVP we should start launching the app. This is dependent on the question of who our users are going to be. And honestly, I am not sure yet.
If it is techies, then we should consider publishing early with a certain license and so that people can contribute (but its still our code and our copyright), and - for example - import worlds from external sources. If it is more conventional users, then the most important thing is probably that the app is easy to use and that it works well. And there must be an incentive to start using it. This of course also has consequences on whether it should be browser-only or also with a download.

Current decision: start with the more launchable early-user version. This is not
a detour from the bigger audience; it is the phase that should prove the core
ride loop, onboarding, packaging, and data model before the app tries to serve
conventional users. The broader consumer version can come later if the early
version shows that people actually want the product.
