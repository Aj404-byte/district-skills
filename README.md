# district-skills

> **Unofficial.** This project is not affiliated with, endorsed by, or supported by Zomato or District.
> It talks to the same private endpoints district.in's own website uses, so it can break at any time and
> automated use may conflict with District's terms. Personal, low-volume use only.

Agent skills + a tiny CLI for [District by Zomato](https://www.district.in): events, movies and showtimes,
restaurants, and your bookings. Runs locally, no server, **no dependencies** (Python 3.9+).

```bash
pip install district-skills
district install-skills          # copies the skills into ~/.claude/skills
```
Then ask your agent: *"comedy shows this weekend"*, *"Drishyam showtimes tonight"*, *"show my District bookings"*.
The agent will ask where you are first.

> From source: `pip install git+https://github.com/Sj0605-DataSci/district-skills`

## Skills

| Skill | Purpose | Login |
|---|---|---|
| `district` | entry point: routes to the others, setup check, location rule | — |
| `district-discover` | events, movies, showtimes, restaurants, booking links | no |
| `district-login` | phone-OTP login, status | — |
| `district-logout` | log out + delete stored session | — |
| `district-bookings` | your movie / event bookings | yes |

`district install-skills --dest DIR` installs into any SKILL.md-compatible agent's skills folder;
`--only district district-discover` installs a subset.

## CLI
```bash
district places "Koramangala"                          # confirm what a place resolves to
district events   --near "Bandra, Mumbai"
district movies   --near "Koramangala, Bengaluru"
district showtimes Drishyam --near "Andheri, Mumbai" --cinema PVR --date 2026-10-08
district search   Toit --near "Lower Parel, Mumbai"
district event    <slug>
district restaurant /mumbai/toit-lower-parel
district login start 98XXXXXXXX && district login verify 123456
district bookings
district login logout
```
There is deliberately **no remembered default location**: every lookup needs `--near` (area/city) or `--lat/--lng`,
and the skills tell the agent to ask you. The resolved place is echoed on stderr (`# location: ...`).

## Works with Claude and GPT?
The skills are plain `SKILL.md` instructions that call the `district` command. Any agent that can load that
format and run shell commands can use them. Chat UIs with no local shell (e.g. ChatGPT web) can't run the CLI,
but you can run commands yourself and paste the output.

## Security and privacy
`~/.district-skill/` (override with `DISTRICT_HOME`) stores a random device id and, after login, session cookies,
all mode 0600. `district login logout` deletes the cookies. Treat that folder like a password. The tool never
stores your OTP, and nothing is sent anywhere except district.in.

## Limits
- Read-only. It cannot book or pay: showtimes include a `seat_layout_url` to finish in your browser.
- `bookings` covers movies and events only; the non-empty response format is unverified.
- Showtimes show a subset of sessions per cinema (what the web page lists).

## Disclaimer
Unofficial and not affiliated with Zomato or District. It uses private endpoints district.in's own web app calls;
they can change without notice, and automated use may conflict with District's terms. Personal, low-volume use only.

## Contributing
Contributions are welcome: bug reports, fixes, new endpoints, more cities and docs.
- Found something broken? Open an issue with the command you ran and the (redacted) output. District changes
  its site often, so "this stopped working" reports are valuable.
- Ideas that would help: dining search/details beyond search results, per-cinema showtimes, bookings with
  real data (the non-empty `bookings` response is unverified), more `SKILL.md` polish for other agents.
- Keep it dependency-free (standard library only), read-only, and low-volume. No booking/payment automation and
  nothing that stores or sends credentials anywhere but district.in.
- Never paste cookies, OTPs, phone numbers or `~/.district-skill/` contents into issues or PRs.
- PRs: `pip install -e . pytest && pytest` must pass; add offline tests for new parsing logic.

## Development
```bash
pip install -e . pytest && pytest      # offline tests
python -m build                        # sdist + wheel (pip install build)
```
Live-API behaviour is checked manually; see `tests/` for what runs offline.

MIT licensed.
