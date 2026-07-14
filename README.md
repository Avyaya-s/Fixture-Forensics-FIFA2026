# Fixture Forensics: FIFA 2026

Fairness and fit analysis for the FIFA World Cup 2026 group stage. Every one of
the tournament's 72 group-stage fixtures is run through a set of independent
scorers — each grounded in a documented, real-world criterion (heat-safety
guidance, altitude physiology, rest-day norms, venue capacity, broadcast
primetime) — and the results are surfaced through two interchangeable
dashboards: a Streamlit app and a standalone FastAPI + vanilla-JS web app.

The goal isn't to say a fixture is "bad," but to make *asymmetry* visible:
where one team is meaningfully more disadvantaged than its opponent by travel,
rest, altitude, or climate, and where a venue or kickoff slot is a poor fit
for the matchup it's been given.

## How it works

```
data/  →  scorers/  →  scorers/aggregate.py  →  dashboard/ (Streamlit)
                                              →  web/       (FastAPI + vanilla JS)
```

1. **`data/`** holds the reference dataset: all 72 matches, 48 qualified
   teams, and 16 host venues, plus a derived per-team match sequence (rest
   days and travel distance since each team's previous group match).
2. **`scorers/`** is a set of independent, pure functions. Each takes a
   `match_id` and returns a 0–10 score plus a human-readable explanation —
   no shared state, no ordering dependency between scorers. `scorers/aggregate.py`
   wires them together (which scorers run, how a match's summary row is shaped)
   as a framework-agnostic layer that both frontends import, so neither
   reimplements that wiring.
3. **`dashboard/`** is a Streamlit app — the original, still fully supported.
4. **`web/`** is a standalone alternative: a small FastAPI backend
   (`web/backend/main.py`) serving the same scores as JSON, plus a
   no-build-step HTML/CSS/JS frontend (`web/frontend/`) it hosts directly.

Both frontends read the same scorers and the same data; pick whichever you'd
rather run.

### Scorers

Each scorer returns its score alongside a plain-text `reasoning` string and a
`details` dict of the underlying numbers. Six report on a 0–10 **"goodness"**
scale (higher = better/fairer); `climate_risk` and `air_quality` report
**risk** (higher = *worse*) instead, since that's the more intuitive framing
on their own. `scorers/aggregate.py` inverts risk scorers (`10 - risk`) via
the result's own `scale` field wherever scores are combined or compared (the
Average column, both dashboards' comparison charts) — the scorer itself is
untouched, and its own detail view still shows the native risk framing plus
a note on what it counts as toward the average.

Every numeric threshold below is either cited to a real, published standard,
or explicitly flagged in the scorer's own docstring as a judgment call —
nothing is presented as authoritative that isn't.

| Scorer | File | What it measures |
|---|---|---|
| **Altitude fairness** | `scorers/altitude_fairness.py` | Whether the venue's elevation disadvantages one team's acclimation more than the other's, based on the gap between each team's home elevation and the venue's (informed by the Estadio Azteca precedent, 1970/1986, and vindicated by FIFA's own 2007–08 altitude-ban saga — which was abandoned specifically for measuring absolute venue elevation instead of the visiting team's relative disadvantage). Scores the *asymmetry* between the two teams' disadvantage, not raw elevation. |
| **Travel fairness** | `scorers/travel_fairness.py` | Two penalties: (1) asymmetry in rest days/travel distance between the two teams, and (2) either team resting below the **FIFA/FIFPro jointly-agreed 72-hour minimum** between matches — a real, cited standard, not a comparison. Returns `N/A` for tournament openers. |
| **Jet lag / circadian misalignment** | `scorers/jet_lag.py` | Asymmetry in each team's time-zone shift (not raw km) since its previous match, weighting eastward shifts heavier than westward per published travel-fatigue research. Distinct from travel fairness — two venues can be far apart with no time-zone shift, or close with a real one. |
| **Cross-border logistics** | `scorers/cross_border.py` | Asymmetry in each team's *cumulative* international border crossings across its group-stage matches so far — a fairness dimension only possible at a tournament hosted across three countries (USA/Mexico/Canada), which 2026 is the first to do. |
| **Venue fit** | `scorers/venue_fit.py` | How well a venue's capacity matches the expected demand for that fixture. Expected demand is estimated from each team's FIFA ranking (a documented proxy for audience size, since per-fixture ticketing data isn't public); score drops for a high-demand pairing in a small venue, or a low-demand pairing in the largest one. |
| **Broadcast reach** | `scorers/broadcast_reach.py` | How well the kickoff time lands in prime viewing windows across five weighted global markets (Europe, South America, North America, Asia, Africa), following the same logic FIFA used to set the 2026 Final's kickoff time for European primetime. |
| **Climate risk** | `scorers/climate_risk.py` | Heat-stress risk at kickoff via a real **WBGT (Wet Bulb Globe Temperature)** approximation, banded against FIFA's published thresholds (voluntary cooling breaks from 27°C, mandatory from 32°C) and FIFPro's more conservative ones (cooling breaks from 26°C, postponement consideration from 28°C) — the two bodies haven't reconciled these as of 2026. Discounted for venues with a retractable or closed roof. Sourced from `data/climate.csv`. |
| **Air quality** | `scorers/air_quality.py` | Air-pollution risk at kickoff via the official **US EPA Air Quality Index** (fetched pre-computed from Open-Meteo, not re-derived), banded against EPA's published categories (Good/Moderate/Unhealthy.../Hazardous). Same roof-type discount as climate risk. Sourced from `data/air_quality.csv`. |

**Not built**: a pitch/surface-risk factor was researched (task queued for it)
but skipped — FIFA mandates natural/hybrid grass at all 16 venues for 2026,
banning artificial turf entirely, so there's no real per-venue surface-risk
difference left to score.

All scorers read through `scorers/data_loader.py`, the single module that
knows the CSV layout and join keys — scorers never open a CSV directly.

### Weighting the average: stakeholder lenses

The plain "Average" column is an unweighted mean across all eight scorers —
fine as a neutral default, but a broadcast-timing factor and a
FIFA-mandated heat-safety factor arguably shouldn't count equally toward one
number. Both dashboards offer a **lens toggle** (`scorers/aggregate.py`'s
`WEIGHT_PROFILES`) that re-weights the same eight scorers under a different
stakeholder's priorities:

- **Balanced** — every scorer equal weight (identical to the old flat Average).
- **Player Welfare** — health/safety-backed factors (climate, altitude,
  travel/rest, jet lag, air quality) weighted highest.
- **Fan Convenience** — broadcast reach and venue fit weighted highest
  (can you watch, can you get a ticket); climate/air quality carry medium
  weight too, since heat and pollution affect fans in an open stadium, not
  just players.
- **Profit** — only venue fit and broadcast reach have a real, direct
  revenue link; everything else is weighted low at most, and the docstring
  is explicit that this lens's reasoning is the weakest-cited of the four.

Weights are discrete tiers (High/Medium/Low/Excluded), not fabricated
decimals — see the `WEIGHT_PROFILES` docstring in `scorers/aggregate.py` for
the full per-factor rationale.

### Data

| File | Contents |
|---|---|
| `data/matches.csv` | All 72 group-stage fixtures: teams, venue, group, matchday, kickoff (local + UTC) |
| `data/teams.csv` | The 48 qualified teams: confederation, home city/timezone/elevation, FIFA ranking |
| `data/venues.csv` | The 16 host venues: capacity, roof type, timezone, elevation, coordinates, country |
| `data/team_match_sequence.csv` | Derived: each team's 3 group matches in order, with rest days and travel distance (haversine, via venue coordinates) since the previous one. Built by `data/build_derived.py`. |
| `data/climate.csv` | Derived: temperature and humidity at each match's actual kickoff instant. Built by `data/build_climate.py` from Open-Meteo's historical archive (ERA5 reanalysis). |
| `data/air_quality.csv` | Derived: PM2.5 and US EPA AQI at each match's actual kickoff instant. Built by `data/build_air_quality.py` from Open-Meteo's Air Quality API. |

Both fetch scripts share `data/_kickoff_time.py`: the kickoff instant is
computed from `date` + `kickoff_local` + the venue's IANA timezone (not the
`kickoff_utc` column), since a late local kickoff can roll into the next UTC
calendar day (verified: M002's 20:00 Guadalajara kickoff is 02:00 UTC the
*next* day) — and both batch one API call per venue rather than per match.

## Getting started

Requires Python 3.10+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Run the Streamlit dashboard:**

```powershell
streamlit run dashboard/app.py
```

This opens the **Overview** page (a weight-profile lens toggle, all 72
fixtures filterable by group and matchday, a score per scorer, and a
tournament-wide distribution chart). Select a row and open **Match Detail**
in the sidebar for the full reasoning behind each score, plus a radar chart
comparing that fixture's eight scores.

**Run the web dashboard** (FastAPI backend + static frontend, served together):

```powershell
uvicorn web.backend.main:app --reload
```

Then open <http://localhost:8000>. Same two views as Streamlit — a
weight-profile lens toggle, a filterable/sortable **Overview** table with a
per-scorer average chart, and a **Match Detail** page with score cards, full
reasoning, and a comparison chart — built as plain HTML/CSS/JS with no
npm/build step, backed by JSON endpoints (`/api/matches`,
`/api/matches/{match_id}`, `/api/scorers`, `/api/profiles`).

**Run the sanity check** (prints scores + reasoning for a few sample matches
without launching the dashboard):

```powershell
python tests/sanity_check.py
```

**Rebuild the derived data** (only needed if `data/matches.csv` or
`data/venues.csv` change):

```powershell
python data/build_derived.py      # team_match_sequence.csv (rest days, travel distance)
python data/build_climate.py      # climate.csv (temperature, humidity per match kickoff)
python data/build_air_quality.py  # air_quality.csv (PM2.5, US AQI per match kickoff)
```

## Project structure

```
data/                    reference dataset + the scripts that derive team_match_sequence.csv, climate.csv, air_quality.csv
scorers/                 one file per independent scorer, plus data_loader and aggregate (shared wiring + weight profiles)
dashboard/               Streamlit app (Overview + Match Detail pages)
web/backend/             FastAPI app serving scores as JSON + the frontend static files
web/frontend/            plain HTML/CSS/JS Overview + Match Detail pages (no build step)
tests/                   lightweight sanity check over all scorers (via scorers.aggregate.SCORERS)
agent/                   reserved for a future narrative/agentic layer over the scorers
```

## Status / roadmap

- ✅ Dataset generated: 72 matches, 48 teams, 16 venues, derived rest/travel sequence, derived climate + air quality (per kickoff)
- ✅ All eight scorers built and wired into both dashboards: altitude, travel, jet lag, cross-border, venue fit, broadcast reach, climate risk, air quality
- ✅ Climate risk and travel fairness recalibrated against real FIFA/FIFPro published thresholds (WBGT heat policy, 72-hour rest standard), replacing earlier invented numbers
- ✅ Weighted composite lens toggle (Balanced / Player Welfare / Fan Convenience / Profit) in both dashboards
- ✅ Streamlit dashboard: tournament overview + per-match detail
- ✅ Web dashboard: FastAPI + vanilla-JS equivalent, same two views
- ⏳ `agent/` — placeholder for a future layer that narrates or summarizes findings across the composite score
- ❌ Pitch/surface risk factor — researched, not built: FIFA mandates uniform natural/hybrid grass at all 16 venues for 2026, so no real per-venue difference exists to score
- ❌ Host-market crowd bias — considered, not pursued: would need city-level diaspora/ancestry data (US Census, Statistics Canada, INEGI) matched to team nationality, a data-acquisition project on the scale of the climate/air-quality builds rather than a quick addition
