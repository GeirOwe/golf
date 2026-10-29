# Rename a group

`Endre navn` on the group page changes the group name and the short address. The previous short address redirects to the new one.

## Sub-features

- `rename-save` saves a new name and opens `/g/<new-slug>`.
- `rename-old-slug` sends the previous `/g/<old-slug>` to the new short address.

## How to get to it (user POV)

- On the group page, choose `Endre navn`.

## Driving it with cursor-ide-browser

Preconditions:

- A group is already open, for example `/g/lisboa`.

- Action: rename. Choose `Endre navn`. The heading is `Endre navn` and `Gruppenavn` holds the current name. Replace it with `Kyst` and choose `Lagre`. Result: the address is `/g/kyst`, and the heading and `document.title` are `Kyst`. Players and trips are still listed.
- Action: open the old address `/g/lisboa`. Result: the address becomes `/g/kyst`, and the heading and `document.title` are `Kyst`.

## Gotchas

- The hidden token still opens the group and stays on the token address. The old short slug redirects to the current one.
- Do not prove the rename by only staying on the form. Reopen `/g/kyst` and the old slug.
