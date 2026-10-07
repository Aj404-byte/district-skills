---
name: district-login
description: Log the user into their District by Zomato (district.in) account with a phone-number OTP, or check whether they are logged in. Use when the user asks to log in / sign in to District, check login status, or when district-bookings reports login is required.
---

# District login

Uses the `district` CLI (`pip install district-skills`; if the command is missing, ask the user to install it). Run it as:

```bash
district login <action> [value]
```

## Flow
1. Ask the user for **their own** phone number (digits only; add `--country-code` if not 91). Never pick a number yourself and never reuse one from elsewhere.
2. `login start <phone>` — District texts a 6-digit OTP to that phone. Tell the user to expect it.
3. Ask the user to read the OTP to you. Don't guess or retry codes.
4. `login verify <otp>` — on success the session is stored locally in `~/.district-skill/` (mode 0600).
5. `login status` — `{"logged_in": true|false}`; use any time to check, e.g. before `district-bookings`.

## Rules
- Only start a login when the user explicitly asks for it and supplies the number. An OTP SMS is a real message to a real person.
- Never print, read back, copy or transmit anything in `~/.district-skill/` (session cookies). The OTP is single-use; don't store it.
- A failed verify returns the site's message; relay it. After 2 failed codes, stop and ask the user whether to send a new OTP.
- To end a session use the `district-logout` skill.
