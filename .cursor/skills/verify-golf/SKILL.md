---
name: verify-golf
description: Drive the local golf Flask app against a new disposable SQLite file and prove group, player, trip, round, score, course-handicap, and finale behavior in the browser. Use when a change touches the Golf UI, routes, forms, or score calculations and needs a real user-path check before it is finished.
---

# Verify Golf

Golf is a Flask web app. Verification drives that app in a browser against a SQLite file this run creates. The live tournament database is never part of the run.

## Launch

From the repo root:

```bash
.cursor/skills/verify-golf/scripts/verify-golf launch
```

The helper creates `.cursor/skills/verify-golf/runs/<run-id>/`, starts `venv/bin/python -m flask --app app run` on `127.0.0.1` and an ephemeral port, and points `DATABASE_URL` at `runs/<run-id>/golf.db`. It sets `FLASK_SKIP_DOTENV=1` and `FLASK_ENV=production` so Flask does not load `.env`. It removes `XAI_API_KEY` and `OPENAI_API_KEY` from the child environment.

Ready means the command printed `ready=1`, `GET /health` returned `{"status":"ok"}`, `GET /` contained `Lenken til gruppen`, and `GET /start` returned 200. The sqlite file then contains `groups`, `players`, `trips`, `trip_players`, `rounds`, `golf_courses`, and `course_tees`. A health check alone is not ready: schema init runs on the first page request. The child environment sets `ORGANIZER_SECRET=verify-secret` and `FLASK_SECRET_KEY=verify-flask-secret`.

The repo venv must already exist (`venv/bin/python`, dependencies from `requirements.txt`). The SQLite branch in `app.py` `_engine_options` is what lets this empty file boot. PostgreSQL pool and libpq options stay in place for a Postgres `DATABASE_URL`.

Two instances can run at once. Each `launch` picks its own port and its own sqlite file. Drive only the `url=` printed by the launch you just started. `runs/current.json` points at the latest launch; pass `--run-id` to `doctor`, `url`, `sql`, and `cleanup` when more than one run exists.

Do not start `flask run` yourself. A shell that still has the project `.env` loaded will attach Flask to the live Neon database.

## Doctor

```bash
.cursor/skills/verify-golf/scripts/verify-golf doctor
```

Run this before driving, and again whenever the page looks like the wrong app. Exit 0 and `ok=1` means all of the following:

- The recorded pid is alive and its command is `flask --app app run` on the recorded port with `--no-reload`.
- That pid is the listener on `127.0.0.1:<port>`.
- The process has the scratch `golf.db` open, and its environment does not contain a Postgres or Neon URL.
- `GET /health` is `{"status":"ok"}`.
- `GET /` contains `Lenken til gruppen` and `GET /start` returns 200.
- The sqlite file is inside this run's directory and has the seven application tables.

Anything else is not worth driving. Do not switch to another URL to "make the check pass".

## Drive

The harness is the Cursor browser (`cursor-ide-browser`). There is no login. Open a new tab on the doctor URL only.

1. `verify-golf doctor` and `verify-golf url`.
2. `browser_tabs` with `action` `list`.
3. `browser_navigate` with `url` set to that local base URL and `newTab` true. `browser_lock` with `action` `lock` on that tab. `browser_lock` with `action` `unlock` after the last browser action.
4. `browser_snapshot`. Find the control by its role and accessible name in that snapshot. Call `browser_click`, `browser_fill`, or `browser_select_option` with the `ref` from that same snapshot. The snapshot returned inside a click result is still the old page: call `browser_snapshot` again before asserting the next heading. Refs do not survive that next snapshot.
5. Text fields (`Gruppenavn`, `Navn`, `Destinasjon`, `Banenavn`, `Anlegg`, `Henting`) accept `browser_fill`. A `type="number"` control is a spinbutton. `browser_fill` reports that ref as stale, and `browser_click` rejects it because it is an input rather than a button. Set it with `browser_cdp` method `Runtime.evaluate` and params like `{"expression":"<setter>","returnByValue":true}`. The setter for `#handicap` is:

```javascript
(() => {
  const input = document.querySelector('#handicap');
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(input, '12.4');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  return input.value;
})()
```

A score or finale field is a spinbutton named with the player. Set that `input[type=number]` the same way. Snapshot again and require the spinbutton `value` to be the new number before choosing `Lagre`. A Norwegian locale may render `12.4` as `12,4` in the screenshot; the DOM value stays `12.4`.

6. Score tables omit their cell text from `browser_snapshot`. Read `document.body.innerText` with `Runtime.evaluate` and keep the screenshot. `browser_take_screenshot` returns a `Saved to:` path outside the repo; copy that file into the artifact directory. `document.title` is the group name, the trip name, or the page name.

Stable handles are the visible labels and link text, not coordinates:

| Page | Path | Heading | Title |
| --- | --- | --- | --- |
| Home | `/` | `Lenken til gruppen` | `Lenken til gruppen` |
| Organizer | `/start` | `Start` | `Start` |
| Group | `/g/<slug>` | the group name | the group name |
| New player | `/g/<slug>/players` | `Ny spiller` | the group name |
| Edit player | `/g/<slug>/players/<id>` | the player name | the group name |
| Rename group | `/g/<slug>/navn` | `Endre navn` | the group name |
| New trip | `/g/<slug>/trips` | `Ny tur` | the group name |
| Trip | `/g/<slug>/trips/<id>` | the trip name | the trip name |
| New round | `.../rounds` | `Ny runde` | the trip name |
| Scores | `.../rounds/<id>/scores` | `Registrer score` | the trip name |
| Order of Merit | `.../oom` | `Tabell OOM` | the trip name |
| Finale | `.../finale` | `Finale` | the trip name |
| Finale result | `.../finale/resultat` | `Finaleresultat` | the trip name |
| Courses | `/baner` | `Baner` | `Baner` |
| New course | `/baner/ny` | `Registrer bane` | `Registrer bane` |
| Course | `/baner/<id>` | the course name | the course name |
| Public strokes | `/baner/mottatte-slag` | `Mottatte slag` | `Mottatte slag` |
| Group strokes | `/g/<slug>/mottatte-slag` | `Mottatte slag` | `Mottatte slag` |

`/` asks for the group link and does not list groups. Organizer work starts at `/start` with `Kode` `verify-secret`, unless an earlier cookie on `127.0.0.1` already signed that session in. Course registration is not linked from `/` or from the group. Open `/baner`.

Do not submit `Slett`, `Slett tur`, or `Fjern`. Cleanup removes the scratch directory; it does not delete rows through the app.

The weather image on a trip is loaded from yr.no when the trip has a Yr-id. A missing image is not an application failure.

## Evidence

Write proof under `.cursor/skills/verify-golf/artifacts/<feature-id>/`. Cleanup must not delete that directory.

For each driven feature, keep:

- An accessibility snapshot taken while the user action is on screen, and another of the resulting page.
- A screenshot of the resulting page.
- `document.title`, which is the group name, the trip name, or the page name.
- For a mutation, a second user-facing view (reopen the list or result page) and a read-only check:

```bash
.cursor/skills/verify-golf/scripts/verify-golf sql --run-id <run-id> "SELECT name, handicap FROM players"
```

`verify-golf sql` opens the scratch file with `mode=ro` and accepts one `SELECT` or `PRAGMA` only.

A filled form that was never submitted is not proof. A status message with no reopened record is not proof. Do not use a test-only route or a direct database insert as the user action. The SQL command is only the side-effect check after the browser path.

Copy a screenshot into the artifact path if the browser tool stores it elsewhere. Record the feature id, the entry point, and the local URL in `run.txt`.

## Cleanup

```bash
.cursor/skills/verify-golf/scripts/verify-golf cleanup --run-id <run-id>
```

This sends `SIGTERM` (then `SIGKILL` if needed) only to the pid recorded for that run, and only after `ps` still shows the verification flask command. It then deletes `.cursor/skills/verify-golf/runs/<run-id>/` and, if `current.json` points at that id, deletes `current.json`. It does not delete `artifacts/`. It does not kill by process name and does not remove any other directory.

Run cleanup after a failed launch too, so a half-started pid and port are not left behind.

After cleanup, confirm the artifact files are still on disk and the run directory is gone.

## Helpers

The helper is `.cursor/skills/verify-golf/scripts/verify-golf`.

```bash
.cursor/skills/verify-golf/scripts/verify-golf launch
.cursor/skills/verify-golf/scripts/verify-golf doctor
.cursor/skills/verify-golf/scripts/verify-golf doctor --run-id <run-id>
.cursor/skills/verify-golf/scripts/verify-golf url
.cursor/skills/verify-golf/scripts/verify-golf sql --run-id <run-id> "SELECT name, handicap FROM players"
.cursor/skills/verify-golf/scripts/verify-golf cleanup --run-id <run-id>
```

`launch` prints `run_id`, `url`, `pid`, `data_dir`, and `database_path`. Use those values for the rest of the run. Feature recipes live in `features/`.
