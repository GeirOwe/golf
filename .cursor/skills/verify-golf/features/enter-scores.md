# Enter scores

Enter scores lets a user type a Stableford score for a player on a round, then see that player's total and average on Tabell OOM.

## Sub-features

- `scores-open` opens the score form from the round's `Score` link.
- `scores-save` stores a Stableford value and returns to the rounds list.
- `scores-oom` shows the total, average, and score list, excluding zeros.

## How to get to it (user POV)

- On the home page, choose `Tee times`, then choose `Score` on a round.
- On the home page, choose `Tabell OOM` to read the result.

## Driving it with cursor-ide-browser

Preconditions:

- `verify-golf doctor` prints `ok=1` and `isolated=sqlite`.
- The scratch database has no player named `Verify Ada` and no round for `Verify Hills`.
- The browser tab URL is the `url` from that same launch.

- **Create the player.** Follow the create steps in [Register a player](./register-player.md) through the first save, using handicap `12.4`. Stop before the handicap update. The player list shows `Verify Ada`.
- **Create the round.** Follow [Add a tee time](./add-round.md) through save. The rounds list shows `Verify Hills` and a `Score` link.
- **Open score entry.** Snapshot, then `browser_click` the link named `Score` on the `Verify Hills` row. The heading is `Registrer Score` and the page contains `Verify Hills` and `Verify Ada`.
- **Enter the score.** The Stableford input has no accessible name and `browser_fill` will not take its spinbutton ref. Set the number input in the table row whose text contains `Verify Ada` with the number-input setter in `SKILL.md`, using value `36`. Snapshot again. That spinbutton's value is `36`.
- **Save.** Snapshot the filled row into `artifacts/enter-scores/form.aria.txt` and take `artifacts/enter-scores/form.png`. `browser_click` the button named `Lagre Score`. The heading is `Golfrunder`.
- **Read Order of Merit.** Go home and choose `Tabell OOM`. The table contains `Verify Ada`, total `36`, snitt `36.0`, and score `36`. The document title is `Scoreoversikt - Lisboa Høst 🥳`.
- **Proof.** Save the OOM snapshot to `artifacts/enter-scores/list.aria.txt` and the screenshot to `artifacts/enter-scores/list.png`. Run `verify-golf sql --run-id <run-id> "SELECT score FROM round_scores"`. The row is `36`.

## Gotchas

- A score of `0` is stored but omitted from Tabell OOM because only truthy scores are averaged. Use `36` for this proof.
- The score field is not labelled. Matching the first spinbutton on the page is wrong once more than one player exists. Match the `Verify Ada` row.
- `Lagre Score` returns to the rounds list, which does not show the Stableford value. Tabell OOM is the persistence view.
- Do not open `/scores/reset`. That route deletes every score.
