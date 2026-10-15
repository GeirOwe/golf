# Register a player

Register a player lets a user add a name and handicap from HCP oversikt, see that player on the list, and change the handicap from the same list.

## Sub-features

- `players-empty` shows the empty list before any player exists.
- `players-create` saves a name and handicap and returns home.
- `players-persist` shows the saved name and handicap on the player list.
- `players-update` changes the handicap and shows the new value on the list.

## How to get to it (user POV)

- On the home page, choose `HCP oversikt`.
- On the player list, choose `Ny Spiller`.
- On a player row, choose `Endre`.

## Driving it with cursor-ide-browser

Preconditions:

- `verify-golf doctor` prints `ok=1` and `isolated=sqlite`.
- The scratch database has no player named `Verify Ada`.
- The browser tab URL is the `url` from that same launch.

- **Open the list.** From home, choose `HCP oversikt`. Snapshot, then `browser_click` the link named `HCP oversikt`. Snapshot again. The heading is `Spillere` and `document.body.innerText` contains `Ingen spillere registrert ennå.` The document title is `Spillerliste - Lisboa Høst 🥳`.
- **Open the form.** Choose `Ny Spiller`. Snapshot, then `browser_click` the link named `Ny Spiller`. Snapshot again. The heading is `Registrer Ny Spiller`.
- **Enter the player.** Snapshot. `browser_fill` the textbox named `Spillernavn:` with `Verify Ada`. Set `#handicap` to `12.4` with the number-input setter in `SKILL.md`. Snapshot again. The textbox value is `Verify Ada` and the spinbutton value is `12.4`.
- **Save.** Save that snapshot to `artifacts/register-player/form.aria.txt` and copy the screenshot to `artifacts/register-player/form.png`. `browser_click` the button named `Lagre`. Snapshot again. The home heading is `Lisboa Høst 🥳`.
- **Confirm persistence.** Choose `HCP oversikt` again and snapshot again. `document.body.innerText` contains `Verify Ada` and `12.4`, and it does not contain `Ingen spillere registrert ennå.` The list snapshot itself does not include the cell text.
- **Update handicap.** `browser_click` the link named `Endre`. Snapshot again. The heading is `Oppdater Spiller`, the textbox is `Verify Ada`, and the spinbutton is `12.4`. The back link is `Tilbake`. Set `#handicap` to `18.2` with the number-input setter. Snapshot again, then `browser_click` the button named `Endre`. Snapshot again. `document.body.innerText` on the player list contains `Verify Ada` and `18.2`.
- **Proof.** Save the list snapshot to `artifacts/register-player/list.aria.txt`, the inner text and document title to `artifacts/register-player/title.txt`, and the copied screenshot to `artifacts/register-player/list.png`. Run `verify-golf sql --run-id <run-id> "SELECT name, handicap FROM players"`. The only row is `Verify Ada` with handicap `18.2`.

## Gotchas

- `Lagre` on this form redirects home. The home page does not list players. Reopen `HCP oversikt` before treating the save as proved.
- Handicap above `54` redisplays the form with `Handicap cannot be greater than 54.0` and does not add a player.
- An empty name does not add a player. Assert the list, not the redirect alone.
- The list link `Endre` and the update button `Endre` are different controls. The button is on `Oppdater Spiller`. The update page's other link is `Tilbake`.
- `browser_snapshot` on the player list does not include the name or handicap cells. Assert `document.body.innerText` and the screenshot.
- `browser_fill` does not accept the Handicap spinbutton. Use the number-input setter on `#handicap`.
- A click result still shows the previous URL. Snapshot again before reading the next page.
- There is no delete control on the player list. Do not call `/player/<id>/delete`.
- Jinja prints `18.2`, not `18.20`. Assert the rendered text.
