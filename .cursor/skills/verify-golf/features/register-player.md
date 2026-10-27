# Register a player

A player belongs to one group. `Ny spiller` saves a name and handicap on that group, and the row opens an edit form.

## Sub-features

- `players-empty` shows a new group with no player row and no empty-player sentence.
- `players-create` saves a name and handicap and returns to the group.
- `players-update` changes the handicap and shows one decimal on the group.

## How to get to it (user POV)

- On the group page, choose `Ny spiller`.
- On the group page, choose the player row. The accessible name is the name and the handicap, not `Endre`.

## Driving it with cursor-ide-browser

Preconditions:

- A group is open, for example `/g/lisboa`.
- Set `#handicap` with the number-input setter in `../SKILL.md`.

- Action: add a player. Choose `Ny spiller`. The heading is `Ny spiller`. Fill `Navn` with `Verify Ada`, set `#handicap` to `12.4`, and choose `Lagre`. Result: the group page shows `Verify Ada` and `12.4`. `document.title` is the group name.
- Action: change the handicap. Choose the `Verify Ada 12.4` row. The heading is `Verify Ada`. Set `#handicap` to `18.2` and choose `Lagre`. Result: the group page shows `Verify Ada` and `18.2`.
- Check: `verify-golf sql --run-id <run-id> "SELECT name, handicap FROM players"` returns `Verify Ada` and `18.2`.

## Gotchas

- There is no `HCP oversikt`, `Spillere` heading, or `Spillernavn:` field.
- The edit page has `Slett`. Do not submit it.
- A handicap above 54 stays on the form with `Handicap kan ikke være høyere enn 54.0.`
