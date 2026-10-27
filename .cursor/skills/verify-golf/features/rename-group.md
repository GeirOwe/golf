# Rename a group

`Endre navn` on the group page changes the group name and the short address. The previous short address stops working.

## Sub-features

- `rename-save` saves a new name and opens `/g/<new-slug>`.
- `rename-old-slug` makes the previous `/g/<old-slug>` a missing page.

## How to get to it (user POV)

- On the group page, choose `Endre navn`.

## Driving it with cursor-ide-browser

Preconditions:

- A group is already open, for example `/g/lisboa`.

- Action: rename. Choose `Endre navn`. The heading is `Endre navn` and `Gruppenavn` holds the current name. Replace it with `Kyst` and choose `Lagre`. Result: the address is `/g/kyst`, and the heading and `document.title` are `Kyst`. Players and trips are still listed.
- Action: open the old address `/g/lisboa`. Result: heading `Fore!` and the text `Du er out of bounds - siden du leter etter finnes ikke.`

## Gotchas

- The hidden token still opens the group. The short slug does not survive a rename.
- Do not prove the rename by only staying on the form. Reopen `/g/kyst` and the old slug.
