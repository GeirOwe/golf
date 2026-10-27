# Open or create a group

Home asks for a group link and does not list groups. An organizer signs in at `/start` and creates a group, which opens at `/g/<slug>`.

## Sub-features

- `gate-open` pastes a group link and opens that group.
- `group-create` saves a group name and opens `/g/<slug>`.
- `group-empty` shows the new group with no player sentence and `Ingen turer ennå.`

## How to get to it (user POV)

- Open `/` and use `Lenken til gruppen`, then `Åpne`.
- Open `/start`. If `Kode` is shown, enter it and choose `Fortsett`.
- On `Start`, fill `Gruppenavn` and choose `Opprett gruppe`.

## Driving it with cursor-ide-browser

Preconditions:

- `verify-golf doctor` has `ok=1` and `isolated=sqlite` for this run.
- `ORGANIZER_SECRET` is `verify-secret`. A cookie from an earlier run on `127.0.0.1` with the same `FLASK_SECRET_KEY` skips `Kode` and shows the group form immediately.

- Action: create a group. On `/start`, fill `Gruppenavn` with `Lisboa` and choose `Opprett gruppe`. Result: the address is `/g/lisboa`, the heading and `document.title` are `Lisboa`, and the page says `Ingen turer ennå.`
- Action: open that group from home. On `/`, fill `Lenken til gruppen` with `/g/lisboa` and choose `Åpne`. Result: the heading is `Lisboa`.

## Gotchas

- Home is not `Fore. Out of bounds.` That sentence is the missing-page text.
- The document title is not `Hjem - Lisboa Høst`.
- Creating a group does not print the URL. The address bar is the link.
