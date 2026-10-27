# Add a trip

`Ny tur` on the group page saves a trip for the checked players and opens that trip.

## Sub-features

- `trip-empty` shows `Ingen turer ennå.` before any trip exists.
- `trip-create` saves a name, a destination, and the checked players.
- `trip-open` shows the trip name, `Runder`, and `Ingen golfrunder registrert ennå.`

## How to get to it (user POV)

- On the group page, choose `Ny tur`.

## Driving it with cursor-ide-browser

Preconditions:

- The group has a player. The player checkbox on `Ny tur` starts checked.

- Action: create a trip. Choose `Ny tur`. The heading is `Ny tur`. Fill `Navn` with `Høst 2026` and `Destinasjon` with `Lisboa`. Leave the player checked and choose `Lagre`. Result: the heading and `document.title` are `Høst 2026`, the player is listed, and `Runder` says `Ingen golfrunder registrert ennå.`

## Gotchas

- `Slett tur` and `Fjern` are on the trip page. Do not submit them.
- The group page lists trips with the newest first. The trip row shows the destination under the name.
