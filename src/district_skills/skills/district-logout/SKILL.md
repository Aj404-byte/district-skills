---
name: district-logout
description: Log out of District by Zomato (district.in) and delete the locally stored session. Use when the user asks to log out, sign out, remove their District login, or wipe saved District credentials from this machine.
---

# District logout

```bash
district login logout
district login status   # confirm: {"logged_in": false}
```
`logout` asks District to end the session and deletes the stored cookie file in `~/.district-skill/`.
Run `login status` afterwards and tell the user the result. Public lookups (events, movies, showtimes,
restaurants) keep working without login.

If the user wants *everything* removed (including the saved device id and last location), tell them they can
delete the folder `~/.district-skill/`; do that only if they ask.
