# Add a round

`Ny runde` on a trip saves a round for an existing course and tee, then lists it under `Runder`.

## Sub-features

- `round-empty` shows `Ingen golfrunder registrert ennå.` before any round exists.
- `round-create` saves course, tee, date, tee time, type, and pickup, and returns to the trip.
- `round-row` shows the weekday date, tee, time, and pickup.

## How to get to it (user POV)

- On the trip page, choose `Ny runde`.

## Driving it with cursor-ide-browser

Preconditions:

- The trip exists and the course has both `Gul (Herre)` and `Rød (Dame)`. `Bane` and `Tee` are selects, not free text. `Rød (Dame)` is listed first because its course rating is higher. A new round still selects `Gul (Herre)`.
- `Type` lists `OOM`, `Trening`, and `Finale`.
- `2026-10-20` is a Tuesday. `dager til tee-off` appears only when the earliest round date is after today. On 7 Nov 2026 that Tuesday is in the past, so the line stays hidden.

- Action: add a round. Choose `Ny runde`. The heading is `Ny runde`. `Bane` is `Verify Hills` and `Tee` is `Gul (Herre)`. Fill `Dato` with `2026-10-20`, `Teetime` with `09:30`, leave `Type` as `OOM`, fill `Henting` with `Sandvika`, and choose `Lagre`. Result: the trip title stays the trip name. The row reads `Tirsdag 20.10 · Gul · 09:30 · Sandvika` and has a `Score` link. The row uses the tee name without the gender.

## Gotchas

- There is no `Tee times` page and no `Golfrunder` heading.
- `Henting` accepts at most 12 characters.
- `Baner` on this form opens `/baner`.
- A round whose `Type` is `Trening` adds `· Trening` on the row. Its `Score` link opens `Registrer score`.
- A round whose `Type` is `Finale` adds `· Finale` on the row. Its `Score` link opens Finale, not the OOM score form.
