# Received strokes

Received strokes lets a user pick a course and tee and see each player's WHS strokes. The course itself is registered on the baner pages, which are not linked from the home menu.

## Sub-features

- `strokes-empty` says no courses exist until one is registered.
- `course-create` saves a course, facility, and one tee.
- `strokes-show` shows the WHS stroke count for the selected tee.

## How to get to it (user POV)

- On the home page, choose `Mottatte slag`.
- Open `/baner`, then choose `Ny bane`. The home menu does not link to baner.

## Driving it with cursor-ide-browser

Preconditions:

- `verify-golf doctor` prints `ok=1` and `isolated=sqlite`.
- The scratch database has no course named `Verify Hills` and no player named `Verify Ada`.
- The browser tab URL is the `url` from that same launch.

- **See the empty strokes page.** From home, choose `Mottatte slag`. The heading is `Mottatte slag` and the page contains `Ingen baner registrert ennå.`
- **Register the player.** Follow the create steps in [Register a player](./register-player.md) through the first save, with handicap `18`. The player list shows `Verify Ada` and `18.0`.
- **Open course registration.** Navigate to `<url>/baner`. The heading is `Baner` and the page contains `Ingen baner registrert ennå.` Choose `Ny bane`. The heading is `Registrer bane`.
- **Enter one tee.** Snapshot. `browser_fill` the textbox named `Banenavn` with `Verify Hills`. `browser_fill` the textbox named `Anlegg` with `Verify Park`. The tee table has four rows and only the first may be filled. `browser_fill` the first textbox whose placeholder is `f.eks. Gul` with `Gul`. Leave Kjønn as `Herre`. Set the first `input[name=tee_par]` to `72`, the first `input[name=tee_cr]` to `71.5`, and the first `input[name=tee_slope]` to `125` with the number-input setter in `SKILL.md` (`document.querySelector` for each name). Leave the other three tee rows untouched.
- **Save the course.** Snapshot the form into `artifacts/mottatte-slag/course.aria.txt` and take `artifacts/mottatte-slag/course.png`. `browser_click` the button named `Lagre bane`. The heading is `Verify Hills` and the document title is `Verify Hills - Lisboa Høst 🥳`.
- **Show strokes.** Go home and choose `Mottatte slag`. Snapshot. `browser_select_option` on the combobox named `Bane`, with value `Verify Hills (Verify Park)`. Snapshot again. The tee combobox is enabled. `browser_select_option` on the combobox named `Tee-sted`, with the option that starts with `Gul (Herre)`. `browser_click` the button named `Vis mottatte slag`. The table contains `Verify Ada`, `18.0`, and `19`.
- **Proof.** Save the result snapshot to `artifacts/mottatte-slag/list.aria.txt` and the screenshot to `artifacts/mottatte-slag/list.png`. Run `verify-golf sql --run-id <run-id> "SELECT name, par, course_rating, slope_rating FROM course_tees"`. The row is `Gul`, `72`, `71.5`, `125`.

## Gotchas

- `/baner` is a real entry point and it is absent from the home menu. Opening only `Mottatte slag` cannot create the course.
- Empty extra tee rows are skipped. Typing into a later row without all of its numbers returns `Ugyldige tall` and does not save the course.
- The tee combobox stays disabled until a course is selected, and its options are rebuilt in the page script. Snapshot after selecting the course before choosing the tee.
- The expected `19` is `round(18 × (125 / 113) + (71.5 − 72))`. Assert the rendered integer.
- Do not drive this against a database that already has courses. The empty-state step would fail, and that failure should be reported rather than skipped.
