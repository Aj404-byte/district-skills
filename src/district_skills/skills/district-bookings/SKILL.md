---
name: district-bookings
description: Show the logged-in user's District by Zomato (district.in) movie and event bookings. Use when the user asks about their District orders, tickets, past or upcoming bookings. Requires login via the district-login skill.
---

# District bookings (needs login)

```bash
district login status
district bookings [--kind movies|events]
```

1. Check `login status`. If not logged in, use the `district-login` skill (only with the user's consent and their own number).
2. Run `bookings` (queries movies and events by default). Output is per type; `"no orders found"` means the list was empty.
3. Summarise bookings plainly: what, where, when, status. If the raw output has an unexpected shape, show the relevant
   fields rather than guessing; the non-empty response format has not been verified.

## Limits
- Read-only. This skill cannot book, cancel, refund or pay. For new tickets use `district-discover` to find the
  showtime and give the user the seat-selection link.
- Only movie and event orders are supported; dining reservation history isn't.
- Don't print or move the session files in `~/.district-skill/`.
