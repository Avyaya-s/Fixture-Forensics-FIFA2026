"""Travel fairness scorer.

Grounded in: established minimum rest-day norms used across professional
football scheduling (major tournaments generally target 5-6 days between a
team's matches; gaps below that are treated as an increasing burden).

We score the *asymmetry* between the two teams' rest days and travel
distance since their previous group match, not the absolute values -- a
match where both teams are equally rested/traveled is fair even if both
had a short turnaround.

Scale: "goodness" (0-10, higher = fairer / more symmetric).
"""
from scorers.data_loader import get_match, get_team_sequence_row

REST_GAP_WEIGHT = 1.5   # points of penalty per day of rest-day asymmetry
TRAVEL_GAP_KM_PER_POINT = 500  # km of travel-distance asymmetry per penalty point


def score_travel_fairness(match_id: str) -> dict:
    match = get_match(match_id)
    home, away = match["team_home"], match["team_away"]
    seq_home = get_team_sequence_row(home, match_id)
    seq_away = get_team_sequence_row(away, match_id)

    if seq_home["rest_days"] != seq_home["rest_days"] or seq_away["rest_days"] != seq_away["rest_days"]:
        # NaN check without importing numpy/math: at least one team has no
        # prior group match this tournament (this is their opener).
        return {
            "match_id": match_id,
            "scorer": "travel_fairness",
            "scale": "goodness",
            "score": None,
            "label": "N/A (tournament opener)",
            "reasoning": (
                f"{home} and/or {away} are playing their first group match of the "
                "tournament in this fixture, so there is no prior-match rest/travel "
                "baseline to compare asymmetry against."
            ),
            "details": {
                "home_rest_days": seq_home["rest_days"],
                "away_rest_days": seq_away["rest_days"],
                "home_travel_km": seq_home["travel_distance_km"],
                "away_travel_km": seq_away["travel_distance_km"],
            },
        }

    rest_gap = abs(seq_home["rest_days"] - seq_away["rest_days"])
    travel_gap = abs(seq_home["travel_distance_km"] - seq_away["travel_distance_km"])

    penalty = rest_gap * REST_GAP_WEIGHT + travel_gap / TRAVEL_GAP_KM_PER_POINT
    score = round(max(0.0, 10.0 - penalty), 1)

    # Net advantage to home = home's rest edge + home's travel edge, on the
    # same weighted scale as the penalty above, so "who's disadvantaged"
    # reflects both factors together rather than rest days alone.
    net_home_advantage = (
        (seq_home["rest_days"] - seq_away["rest_days"]) * REST_GAP_WEIGHT
        + (seq_away["travel_distance_km"] - seq_home["travel_distance_km"]) / TRAVEL_GAP_KM_PER_POINT
    )
    disadvantaged = away if net_home_advantage > 0 else home
    reasoning = (
        f"{home}: {seq_home['rest_days']:.0f} rest days, {seq_home['travel_distance_km']:.0f} km traveled "
        f"since previous match. {away}: {seq_away['rest_days']:.0f} rest days, "
        f"{seq_away['travel_distance_km']:.0f} km traveled. "
        f"Rest-day gap of {rest_gap:.0f} and travel gap of {travel_gap:.0f} km "
        f"put {disadvantaged} at the disadvantage for this fixture."
        if rest_gap > 0 or travel_gap > 0
        else f"{home} and {away} had identical rest and travel since their previous match -- fully symmetric."
    )

    return {
        "match_id": match_id,
        "scorer": "travel_fairness",
        "scale": "goodness",
        "score": score,
        "label": f"{score}/10",
        "reasoning": reasoning,
        "details": {
            "home_rest_days": seq_home["rest_days"],
            "away_rest_days": seq_away["rest_days"],
            "home_travel_km": seq_home["travel_distance_km"],
            "away_travel_km": seq_away["travel_distance_km"],
            "rest_gap_days": rest_gap,
            "travel_gap_km": round(travel_gap, 1),
        },
    }
