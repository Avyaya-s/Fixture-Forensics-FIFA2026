"""Venue fit scorer.

Grounded in: public venue capacity data plus a team audience-size proxy
derived from FIFA world ranking. The audience proxy is a documented
simplification (see Idea_and_Solution_Report.docx Sec. 6) -- it stands in for
real ticketing/viewership data, which is not publicly available per-fixture.

Method: each team's popularity proxy is its FIFA ranking min-max normalized
across all 48 qualified teams (rank 1 -> 1.0, rank 48 -> 0.0). A match's
expected demand is the average of the two teams' proxies. Each venue's
capacity is min-max normalized across the 16 host venues. Fit is scored by
how close the match's expected-demand percentile is to the venue's
capacity percentile -- a high-demand pairing in a small venue, or a
low-demand pairing in the largest venue, both score poorly.

Scale: "goodness" (0-10, higher = better matched).
"""
from scorers.data_loader import get_match, get_team, get_venue, load_teams, load_venues


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _team_popularity(fifa_ranking: float, best: float, worst: float) -> float:
    if best == worst:
        return 0.5
    return (worst - fifa_ranking) / (worst - best)


def _venue_capacity_percentile(capacity: float, min_cap: float, max_cap: float) -> float:
    if max_cap == min_cap:
        return 0.5
    return (capacity - min_cap) / (max_cap - min_cap)


def score_venue_fit(match_id: str) -> dict:
    match = get_match(match_id)
    home, away = match["team_home"], match["team_away"]
    venue = get_venue(match["venue_id"])
    home_team, away_team = get_team(home), get_team(away)

    all_teams = load_teams()
    best_rank, worst_rank = all_teams["fifa_ranking"].min(), all_teams["fifa_ranking"].max()
    home_pop = _team_popularity(home_team["fifa_ranking"], best_rank, worst_rank)
    away_pop = _team_popularity(away_team["fifa_ranking"], best_rank, worst_rank)
    expected_demand = (home_pop + away_pop) / 2

    all_venues = load_venues()
    min_cap, max_cap = all_venues["capacity"].min(), all_venues["capacity"].max()
    capacity_pctl = _venue_capacity_percentile(venue["capacity"], min_cap, max_cap)

    gap = abs(expected_demand - capacity_pctl)
    score = round(max(0.0, 10.0 - gap * 10.0), 1)

    if gap < 0.15:
        verdict = "well matched to"
    elif expected_demand > capacity_pctl:
        verdict = "under-sized for"
    else:
        verdict = "larger than needed for"

    reasoning = (
        f"{venue['name']} (capacity {venue['capacity']:,}, "
        f"{_ordinal(round(capacity_pctl * 100))} percentile among host venues) is {verdict} the expected demand "
        f"for {home} (FIFA rank {home_team['fifa_ranking']:.0f}) vs {away} (rank {away_team['fifa_ranking']:.0f}), "
        f"a matchup estimated at the {_ordinal(round(expected_demand * 100))} demand percentile using ranking as "
        "an audience-size proxy."
    )

    return {
        "match_id": match_id,
        "scorer": "venue_fit",
        "scale": "goodness",
        "score": score,
        "label": f"{score}/10",
        "reasoning": reasoning,
        "details": {
            "venue_capacity": venue["capacity"],
            "capacity_percentile": round(capacity_pctl, 2),
            "expected_demand_percentile": round(expected_demand, 2),
            "home_fifa_ranking": home_team["fifa_ranking"],
            "away_fifa_ranking": away_team["fifa_ranking"],
        },
    }
