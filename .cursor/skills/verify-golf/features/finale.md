# Finale

Finale lets a user enter one finale score per player, see the Order of Merit bonus added to it, and open a read-only result table.

## Sub-features

- `finale-open` shows every player with a live bonus before any finale score exists.
- `finale-save` stores a finale score and ranks the player.
- `finale-result` shows the same place, total, score, and bonus on the read-only result page.

## How to get to it (user POV)

- On the home page, choose `Finale`.
- On the finale page, choose `Finaleresultat`.

## Driving it with cursor-ide-browser

Preconditions:

- `verify-golf doctor` prints `ok=1` and `isolated=sqlite`.
- The scratch database has no player named `Verify Ada` and no finale score.
- The browser tab URL is the `url` from that same launch.

- **Create a scored player.** Follow [Enter scores](./enter-scores.md) through the Order of Merit check so `Verify Ada` has Stableford `36`. Tabell OOM shows total `36`.
- **Open finale.** Go home and choose `Finale`. The heading is `Finale`. The `Verify Ada` row shows OOM place `1`, bonus `4`, and no place badge yet.
- **Enter the finale score.** The finale input has no accessible name and `browser_fill` will not take its spinbutton ref. Set the number input in the table row whose text contains `Verify Ada` with the number-input setter in `SKILL.md`, using value `30`. Snapshot the row into `artifacts/finale/form.aria.txt` and copy the screenshot to `artifacts/finale/form.png`. The spinbutton value is `30`.
- **Save.** `browser_click` the button named `Lagre score`. The page returns to `Finale`. The `Verify Ada` row shows place `1`, finale `30`, bonus `4`, and total `34`.
- **Open the result.** Choose `Finaleresultat`. The heading is `Finaleresultat`. The table contains place `1`, `Verify Ada`, total `34`, score `30`, and bonus `4`. The document title is `Finaleresultat - Lisboa Høst 🥳`.
- **Proof.** Save the result snapshot to `artifacts/finale/list.aria.txt` and the screenshot to `artifacts/finale/list.png`. Run `verify-golf sql --run-id <run-id> "SELECT score, bonus FROM finale_scores"`. The row is `30` and `4`.

## Gotchas

- Bonus stays live until the first finale score is saved, then it is locked. With one player whose Order of Merit total is `36`, the bonus is `4` both before and after that first save. Total is `30 + 4 = 34`.
- A player with no Order of Merit scores has bonus `0`. Do not assert bonus `4` unless the score entry above was actually saved.
- The finale input is not labelled. Match the `Verify Ada` row.
- `Nullstill finale` opens a confirmation page whose button is `Ja, slett finalen`. Do not choose either control, and do not open `/finale/reset`. Cleanup deletes the scratch database file instead.
- Players with no finale score are omitted from `Finaleresultat`. The result page is empty until the save above succeeds.
