# Golf verification map

This directory is the maintained source for verifying the user-facing behavior of the golf app. Read this index before driving the app, then use the matching feature file as the recipe.

## Baseline preconditions

- Launch with `.cursor/skills/verify-golf/scripts/verify-golf launch`.
- The instance serves `http://127.0.0.1:<port>` and stores data in `.cursor/skills/verify-golf/runs/<run-id>/golf.db`.
- That sqlite file is created empty by the launch. It is the only database the run may write.
- `.env` is not loaded. Do not point `DATABASE_URL` at Neon, Postgres, or any file that already exists.
- Run `verify-golf doctor` and require `ok=1`, the local URL, and `isolated=sqlite`.
- Never drive a server this run did not start. Never open the deployed Render app.

## Driving conventions

- Start every recipe from a fresh launch unless its preconditions say the named records are already absent.
- Prefer the accessible names in the feature file over CSS selectors or screen position.
- Take a snapshot, then use the `ref` from that snapshot. Refs expire on the next snapshot.
- After a click, snapshot again. The click result still shows the page you clicked on.
- Set `type="number"` fields with the number-input setter in `../SKILL.md`. `browser_fill` rejects those spinbuttons.
- List tables hide cell text in the accessibility snapshot. Read `document.body.innerText` and keep the screenshot.
- Run browser actions through `cursor-ide-browser`.
- A mutation is proved by doing it in the browser, reopening a user-facing page, and running `verify-golf sql` read-only against the scratch file.
- Do not submit `Slett`, `Slett tur`, or `Fjern`. Those controls are out of bounds even on the scratch database.
- Leave proof artifacts in place during cleanup.

## Proof and skip reporting

- Capture the user action and the resulting state, not only the final screen.
- UI proof includes an accessibility snapshot, a screenshot, and `document.title`. The title is the group name, the trip name, or the page name.
- Mutation proof includes the reopened page and the read-only SQL rows.
- Record the feature id, entry point, run id, and local URL in the artifact directory.
- Report an unreachable path with the attempted action and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with cursor-ide-browser` starts with `Preconditions:` and uses labeled bullets that pair each user action with an exact command and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

## Features

- [Open or create a group](./open-group.md) covers the home link gate and creating a group at `/start`.
- [Rename a group](./rename-group.md) covers the new name and the new short address.
- [Register a player](./register-player.md) covers adding a player to a group and changing the handicap.
- [Add a trip](./add-trip.md) covers creating a trip for the checked players.
- [Add a round](./add-round.md) covers saving a round on a trip.
- [Enter scores](./enter-scores.md) covers Stableford entry and the Order of Merit table.
- [Received strokes](./mottatte-slag.md) covers course registration and WHS strokes for one group.
- [Finale](./finale.md) covers finale score entry, the locked bonus, and the medal result.
