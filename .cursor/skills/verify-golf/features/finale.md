# Finale

Finale is a round on a trip. The first saved finale score locks the Order of Merit bonus. Places 1, 2, and 3 on the result are medals.

## Sub-features

- `finale-bonus` shows the live bonus before any finale score is saved.
- `finale-save` stores the score and opens Finaleresultat.
- `finale-place` shows a medal for first place and total as score plus bonus.

## How to get to it (user POV)

- On the trip page, choose `Finale`.
- `Score` on a round marked `Finale` opens the same form.

## Driving it with cursor-ide-browser

Preconditions:

- The trip has one OOM round with a saved positive score. A lone `36` gives bonus `4`.
- The trip has one round whose `Type` is `Finale`, and no finale score is saved yet.
- The score control is a spinbutton named with the player.

- Action: save the finale. Choose `Finale`. The heading is `Finale`, the field is named `Verify Ada`, and the line says `Bonus 4`. Set the field to `30` and choose `Lagre`. Result: the heading is `Finaleresultat`. The row has a medal with accessible name `1. plass`, bonus `4`, score `30`, and total `34`. `document.title` is the trip name.
- Check: `verify-golf sql --run-id <run-id> "SELECT finale_bonus FROM trip_players"` returns `4`.

## Gotchas

- There is no home `Finale` link, no `Lagre score` button, and no `Nullstill finale`.
- The form does not show a place or a total. Those are on Finaleresultat.
- The score is a `round_scores` row. The bonus is `trip_players.finale_bonus`. There is no `finale_scores` table.
- Do not submit `Slett tur`.
