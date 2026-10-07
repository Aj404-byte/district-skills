---
name: district
description: Entry point for District by Zomato (district.in) tasks in India: what's on (events, comedy, music, nightlife), movies and showtimes, restaurants and dining, or the user's District bookings and login. Use first for any District / Zomato going-out request; it routes to the right district-* skill and covers setup and the location rule.
---

# District: start here

District by Zomato is a going-out app (events, movies, dining). This skill set reads it through a local CLI named `district`.

## Setup check (once per session)
Run `district --help`. If the command isn't found, tell the user to run `pip install district-skills`
(Python 3.9+, no other dependencies), then retry. Don't install packages without their OK.

## Location rule (applies to every lookup)
Lookups need a place. **Ask the user where they are** (area + city is best, e.g. "Koramangala, Bengaluru") unless
they already said so in this conversation. Never assume a city and never reuse one from an earlier session.
- Pass it as `--near "<area, city>"`. The CLI prints `# location: ...` on stderr showing the place it resolved.
  Check that line; if it's the wrong place, run `district places "<text>"` and confirm with the user.
- Coordinates also work: `--lat 12.93 --lng 77.62`.

## Which skill to use
| User wants | Skill |
|---|---|
| Events, movies, showtimes, restaurants, booking links | `district-discover` (no login) |
| To log in / check login | `district-login` |
| To log out / wipe the saved session | `district-logout` |
| Their own past movie/event bookings | `district-bookings` (login first) |

Typical flows:
- *"Something to do Saturday night"* → ask location → `district-discover` (`events`, then `event <slug>` for details).
- *"Movie tonight"* → ask location → `movies` → `showtimes` → give the `seat_layout_url`.
- *"Show my bookings"* → `district login status` → if not logged in, `district-login` → `district-bookings`.

## Hard rules
- Read-only: never place orders or pay; hand the user the district.in link to finish booking.
- Login only when the user asks and gives their own phone number. Never read, print or send `~/.district-skill/`.
- Unofficial private endpoints; keep it to low-volume, user-initiated lookups. On errors, say so and link district.in.
