# Received strokes

A course is global. Player strokes are on the group page. The public strokes page asks you to open the group and does not list players.

## Sub-features

- `course-create` saves a course and its tees, and the title becomes the course name.
- `strokes-group` shows that group's players and the WHS strokes for the chosen tee.
- `strokes-public` shows the same tee and the sentence `Åpne gruppen for å se spillerne.`

## How to get to it (user POV)

- On the group, the trip, or the round form, choose `Baner`, then `Ny bane`. Home does not link to `/baner`.
- On the group page, choose `Mottatte slag`.

## Driving it with cursor-ide-browser

Preconditions:

- The group has `Verify Ada` at handicap `18.2`.
- Set `#hole_count`, par, CR, and slope with the number-input setter. Leave tee rows after the second one empty.
- Do not choose `Hent scorekort`, `Hent CR/Slope`, or `Fjern`.

- Action: save a course. On `/baner/ny`, fill `Banenavn` with `Verify Hills` and `Anlegg` with `Verify Park`. Set `#hole_count` to `18`. On the first tee row set the name to `Gul`, leave `Herre`, par `72`, CR `71.2`, and slope `125`. On the second tee row set the name to `Rød`, `Dame`, par `72`, CR `75.1`, and slope `134`. Choose `Lagre bane`. Result: the heading and `document.title` are `Verify Hills`. The saved tees are `Rød` `Dame` and `Gul` `Herre`, with the higher course rating first. `Hjem` returns to the trip opened earlier in the session.
- Action: show the group's strokes. On `/g/<slug>/mottatte-slag`, the tee select stays disabled until a course is chosen. Choose `Bane` `Verify Hills (Verify Park)`. The tee becomes `Gul (Herre) – par 72, CR 71.2, slope 125`. Choose `Vis mottatte slag`. Result: the table shows `Verify Ada`, `18.2`, and `19`.
- Action: open `/baner/mottatte-slag` with the `course_id` and `tee_id` from that group address. Result: the tee summary is visible, the page says `Åpne gruppen for å se spillerne.`, and `Verify Ada` is absent. `Hjem` and the brand link return to the group.

## Gotchas

- Without `#hole_count`, `Lagre bane` stays on the form and says `Hent scorekortet for å sette antall hull.`
- `Fjern` is on each tee row and stays inside the tee sheet when the HCP columns make the table wider than the page column. Do not click it.
- The rating picker stays hidden until a fetch.
- `19` is this tee and this handicap. A different CR changes the number.
- Home has no `Mottatte slag` item. The course id and tee id follow insert order. Copy them from the group strokes address.
