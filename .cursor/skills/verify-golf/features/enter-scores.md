# Enter scores

`Score` on an OOM round saves a Stableford number for each player on the trip. `Tabell OOM` shows total, snitt, and that score under a short weekday and date.

## Sub-features

- `scores-save` stores the number and returns to the trip without printing it on the round row.
- `oom-row` shows total, snitt to one decimal, and the round score.
- `oom-header` shows the round as a short weekday over `dd.mm`.

## How to get to it (user POV)

- On the trip page, under `Runder`, choose `Score` on an OOM round.
- On the trip page, choose `Tabell OOM`.

## Driving it with cursor-ide-browser

Preconditions:

- The trip has an OOM round and the player is on the trip.
- The score control is a spinbutton named with the player. Set it with the number-input setter.

- Action: save a score. Choose `Score`. The heading is `Registrer score`. Set the `Verify Ada` field to `36` and choose `Lagre`. Result: the trip returns and the round row does not show `36`.
- Action: open the table. Choose `Tabell OOM`. The heading is `Tabell OOM` and `document.title` is the trip name. The round header is `tir` over `20.10`. The row shows total `36`, snitt `36.0`, and `36`.
- Check: `verify-golf sql --run-id <run-id> "SELECT score FROM round_scores"` includes `36`.

## Gotchas

- There is no `Lagre Score` button and no `Scoreoversikt` title.
- The table scrolls sideways when the week does not fit. The player column stays pinned.
- A finale round is not an OOM column. Its `Score` link opens Finale.
