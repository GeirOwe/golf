# Add a tee time

Add a tee time lets a user save a course, date, tee time, and pickup place, then see that round on the Tee times list.

## Sub-features

- `rounds-empty` shows the empty rounds list.
- `rounds-create` saves a round and returns to the list.
- `rounds-persist` shows the Norwegian date, course, tee time, and pickup on the list.

## How to get to it (user POV)

- On the home page, choose `Tee times`.
- On the rounds list, choose `Ny Runde`.

## Driving it with cursor-ide-browser

Preconditions:

- `verify-golf doctor` prints `ok=1` and `isolated=sqlite`.
- The scratch database has no round for course `Verify Hills`.
- The browser tab URL is the `url` from that same launch.

- **Open the list.** From home, choose `Tee times`. Snapshot, then `browser_click` the link named `Tee times`. The heading is `Golfrunder` and the page contains `Ingen golfrunder registrert ennå.`
- **Open the form.** Choose `Ny Runde`. Snapshot, then `browser_click` the link named `Ny Runde`. The heading is `Ny Golfrunde`.
- **Enter the round.** Snapshot. `browser_fill` the textbox named `Bane` with `Verify Hills`. `browser_fill` the textbox named `Dato` with `2026-10-20`. `browser_fill` the textbox named `Teetime` with `09:30`. `browser_fill` the textbox named `Henting` with `Sandvika`. The four values are visible.
- **Save.** Snapshot the filled form into `artifacts/add-round/form.aria.txt` and take `artifacts/add-round/form.png`. `browser_click` the button named `Lagre`. The heading is `Golfrunder`.
- **Confirm persistence.** The list contains `Tirsdag 20.10`, `Verify Hills`, `09:30`, and `Sandvika`, plus a `Score` link. It does not contain `Ingen golfrunder registrert ennå.`
- **Proof.** Save the list snapshot to `artifacts/add-round/list.aria.txt`, the screenshot to `artifacts/add-round/list.png`, and the document title `Golfrunder - Lisboa Høst 🥳` to `artifacts/add-round/title.txt`. Run `verify-golf sql --run-id <run-id> "SELECT course_name, tee_time, pick_up FROM rounds"`. The row is `Verify Hills`, `09:30`, `Sandvika`.

## Gotchas

- `Dato` is a date input. Fill `2026-10-20`, not `20.10.2026`. The list then shows `Tirsdag 20.10` from the fixed Norwegian weekday names. If `browser_fill` rejects `Dato` or `Teetime`, set `#play_date` and `#tee_time` with the same value setter the skill uses for number inputs.
- `Teetime` is a time input. Fill `09:30`.
- `Henting` accepts at most 12 characters. `Sandvika` fits.
- The home countdown text depends on today's date. Assert the rounds list, not the number of days until tee-off.
- The delete control on a round is commented out of the page. Do not post to `/round/<id>/delete` or `/rounds/reset`.
