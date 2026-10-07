---
name: district-discover
description: Find events, movies, showtimes and restaurants on District by Zomato (district.in) in India. Use when the user asks what's on this weekend, comedy/music/nightlife events, movie listings or showtimes, restaurant info, or wants a District booking link. No login needed. Read-only; never pays.
---

# District discover (no login)

Uses the `district` CLI (`pip install district-skills`; JSON output). If `district` isn't found, ask the user to install it.

## Location first
**Ask the user where they are** (area + city, e.g. "Bandra, Mumbai") unless they already said so in this conversation.
Never assume a city or reuse an old one. Pass it as `--near "<area, city>"`; the CLI prints `# location: ...` on stderr,
so check it resolved correctly (use `district places "<text>"` to confirm with the user if unsure).

| Goal | Command |
|---|---|
| Search events / restaurants / venues | `district search "<keyword>" --near "<place>"` |
| What's on nearby | `district events --near "<place>" [--limit 25]` |
| Event details (description, venue, FAQ, offers) | `district event <slug>` (slug from `events`/`search`) |
| Movies now showing | `district movies --near "<place>"` |
| Showtimes + prices per cinema | `district showtimes <movie_id or title words> --near "<place>" [--cinema PVR] [--date YYYY-MM-DD]` |
| Restaurant details (cuisine, hours, phone, rating) | `district restaurant <seo_path>` (from `search`, e.g. `/mumbai/toit-lower-parel`) |

## How to work
- Use the narrowest command that answers the question. Summarise 3–6 best matches: name, venue/area, when, price, `url`.
- "Movie tonight near Andheri": `movies` → `showtimes "<title>" --near "Andheri, Mumbai" --cinema <brand/area>`, then
  filter start times yourself. `showtimes` returns cinemas nearest-first with `distance_km`, and a subset of sessions per cinema; say so if a requested time isn't shown.
- Times are IST with offsets; prices are INR.

## Booking and payment (hard rules)
Cannot and must not place orders or pay. Give the user the `seat_layout_url` (movies) or event `url` and let them finish
in their browser. For their own past bookings or login use `district-bookings` / `district-login`.

## Caveats
Unofficial private endpoints that can change; automated use may conflict with District's terms. Low-volume,
user-initiated lookups only. On HTTP/parse errors, say so and fall back to the district.in link.
