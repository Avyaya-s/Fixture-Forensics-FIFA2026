"""Cross-border logistics burden scorer.

2026 is the first World Cup hosted across three countries (USA/Mexico/
Canada), so a team's group-stage schedule can require actual international
border crossings between matches -- customs, currency, connectivity, and
travel-document logistics that a single-host tournament never produces.
This is a fixture-specific consequence of the 2026 format, not a general
football-scheduling concern, so it's tracked separately from travel_fairness
(distance/rest) and jet_lag (time-zone shift).

We count each team's *cumulative* border crossings across its group-stage
matches up to and including this one (not just the one step into this
match), then score the asymmetry -- same normalized-asymmetry pattern as
altitude_fairness and jet_lag. A team that has stayed in one country all
group stage is unaffected even if its opponent has bounced between all
three; what matters is the gap between the two teams' accumulated burden.

No official threshold exists for "how many border crossings is too many,"
so unlike climate_risk/travel_fairness this scorer has no absolute-floor
component -- purely relative, and we're not claiming otherwise.

Scale: "goodness" (0-10, higher = fairer / more symmetric).
"""
from scorers.data_loader import get_match, get_team_sequence_row, get_venue, load_team_match_sequence

MAX_CROSSINGS_THIS_TOURNAMENT = 2  # 3 group matches -> at most 2 border transitions


def _team_country_sequence(team: str, match_id: str) -> list:
    row = get_team_sequence_row(team, match_id)
    seq = load_team_match_sequence()
    team_rows = seq[(seq["team"] == team) & (seq["match_number"] <= row["match_number"])].sort_values(
        "match_number"
    )
    return [get_venue(vid)["country"] for vid in team_rows["venue_id"]]


def _crossings(countries: list) -> int:
    return sum(1 for a, b in zip(countries, countries[1:]) if a != b)


def _burden(crossings: int) -> float:
    return min(1.0, crossings / MAX_CROSSINGS_THIS_TOURNAMENT)


def _describe(countries: list) -> str:
    return " -> ".join(countries)


def _border_word(crossings: int) -> str:
    return "border" if crossings == 1 else "borders"


def score_cross_border(match_id: str) -> dict:
    match = get_match(match_id)
    home, away = match["team_home"], match["team_away"]

    home_countries = _team_country_sequence(home, match_id)
    away_countries = _team_country_sequence(away, match_id)
    home_crossings = _crossings(home_countries)
    away_crossings = _crossings(away_countries)

    home_burden = _burden(home_crossings)
    away_burden = _burden(away_crossings)
    asymmetry = abs(home_burden - away_burden)
    score = round(max(0.0, 10.0 - asymmetry * 10.0), 1)

    if home_crossings == away_crossings:
        if home_crossings == 0:
            reasoning = (
                f"{home} and {away} have both stayed within a single host country through this point "
                "in the group stage -- no cross-border logistics burden for either."
            )
        else:
            reasoning = (
                f"{home} ({_describe(home_countries)}) and {away} ({_describe(away_countries)}) have each "
                f"crossed {home_crossings} international {_border_word(home_crossings)} so far -- an equal "
                "logistics burden."
            )
    else:
        disadvantaged = home if home_crossings > away_crossings else away
        disadvantaged_seq = home_countries if disadvantaged == home else away_countries
        disadvantaged_crossings = home_crossings if disadvantaged == home else away_crossings
        acclimated = away if disadvantaged == home else home
        acclimated_seq = away_countries if disadvantaged == home else home_countries
        reasoning = (
            f"{disadvantaged} has crossed {disadvantaged_crossings} international "
            f"{_border_word(disadvantaged_crossings)} so far this group stage ({_describe(disadvantaged_seq)}), "
            f"a heavier cross-border logistics burden than {acclimated} ({_describe(acclimated_seq)}) -- a "
            "fairness gap only possible at a tournament hosted across three countries."
        )

    return {
        "match_id": match_id,
        "scorer": "cross_border",
        "scale": "goodness",
        "score": score,
        "label": f"{score}/10",
        "reasoning": reasoning,
        "details": {
            "home_country_sequence": home_countries,
            "away_country_sequence": away_countries,
            "home_crossings": home_crossings,
            "away_crossings": away_crossings,
        },
    }
