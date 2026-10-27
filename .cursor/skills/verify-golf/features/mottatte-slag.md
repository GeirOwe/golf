# Received strokes

A course is global. Player strokes are on the group page. The public strokes page asks you to open the group and does not list players.

## Sub-features

- `course-create` saves a course and one tee, and the title becomes the course name.
- `strokes-group` shows that group's players and the WHS strokes for the chosen tee.
- `strokes-public` shows the same tee and the sentence `Åpne gruppen for å se spillerne.`

## How to get to it (user POV)

- Open `/baner`, then `Ny bane`. `/baner` is not linked from home or from the group.
- On the group page, choose `Mottatte slag`.

## Driving it with cursor-ide-browser

Preconditions:

- The group has `Verify Ada` at handicap `18.2`.
- Set the par, CR, and slope number fields with the number-input setter. Leave the other tee rows empty.

- Action: save a course. On `/baner/ny`, fill `Banenavn` with `Verify Hills` and `Anlegg` with `Verify Park`. On the first tee row set the name to `Gul`, leave `Herre`, par `72`, CR `71.2`, and slope `125`. Choose `Lagre bane`. Result: the heading and `document.title` are `Verify Hills`.
- Action: show the group's strokes. On `/g/<slug>/mottatte-slag`, choose `Bane` `Verify Hills (Verify Park)`, then the tee that starts `Gul (Herre)`, and choose `Vis mottatte slag`. Result: the table shows `Verify Ada`, `18.2`, and `19`.
- Action: open `/baner/mottatte-slag?course_id=1&tee_id=1`. Result: the page says `Åpne gruppen for å se spillerne.` and does not show `Verify Ada`.

## Gotchas

- The tee select stays disabled until a course is chosen.
- `19` is this tee and this handicap. A different CR changes the number.
- Home has no `Mottatte slag` item.
