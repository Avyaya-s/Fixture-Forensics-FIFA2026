"""Travel fairness scorer.

Grounded in the FIFA/FIFPro jointly-agreed minimum: a 72-hour (3-day) rest
interval between matches, based on research that ~72 hours is what's needed
to normalize muscle damage/inflammation, replenish glycogen stores, and
achieve full neuromuscular recovery. Falling below that floor is a welfare
concern in its own right, independent of whether the opponent is equally
short-rested -- so this scorer penalizes two distinct things:

  1. Asymmetry: the *gap* between the two teams' rest days and travel
     distance since their previous group match. A match where both teams are
     equally rested/traveled is fair even if both had a short turnaround --
     this part is about fairness between these two specific teams.
  2. Floor violation: either team resting below the 72-hour/3-day standard,
     regardless of symmetry -- this part is about player welfare on its own
     terms, since FIFA and FIFPro agreed to it as a floor, not a comparison.

Travel distance (km) has no equivalent published threshold -- it's kept as a
secondary, distance-based fatigue signal. Circadian/jet-lag effects from
crossing time zones are a related but distinct concern, tracked separately.

Scale: "goodness" (0-10, higher = fairer / more symmetric / less floor
violation).
"""
from scorers.data_loader import get_match, get_team_sequence_row

FIFA_FIFPRO_MIN_REST_DAYS = 3.0  # the jointly-agreed 72-hour minimum
BELOW_FLOOR_PENALTY_PER_DAY = 2.5  # penalty per day short of the 72h floor -- a standards violation
ASYMMETRY_PENALTY_PER_DAY = 1.0  # penalty per day of rest-day gap between two floor-compliant teams
TRAVEL_GAP_KM_PER_POINT = 500  # km of travel-distance asymmetry per penalty point


def _below_floor_penalty(rest_days: float) -> float:
    shortfall = max(0.0, FIFA_FIFPRO_MIN_REST_DAYS - rest_days)
    return shortfall * BELOW_FLOOR_PENALTY_PER_DAY


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

    asymmetry_penalty = rest_gap * ASYMMETRY_PENALTY_PER_DAY + travel_gap / TRAVEL_GAP_KM_PER_POINT
    floor_penalty = max(_below_floor_penalty(seq_home["rest_days"]), _below_floor_penalty(seq_away["rest_days"]))
    score = round(max(0.0, 10.0 - asymmetry_penalty - floor_penalty), 1)

    # Net advantage to home = home's rest edge + home's travel edge, on the
    # same weighted scale as the asymmetry penalty above, so "who's
    # disadvantaged" reflects both factors together rather than rest days alone.
    net_home_advantage = (
        (seq_home["rest_days"] - seq_away["rest_days"]) * ASYMMETRY_PENALTY_PER_DAY
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
    if floor_penalty > 0:
        below_floor_team = (
            home if seq_home["rest_days"] < seq_away["rest_days"] else away
        )
        below_floor_days = min(seq_home["rest_days"], seq_away["rest_days"])
        reasoning += (
            f" {below_floor_team} has only {below_floor_days:.0f} rest days, below the FIFA/FIFPro "
            f"agreed minimum of {FIFA_FIFPRO_MIN_REST_DAYS:.0f} (72 hours)."
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
            "below_72h_floor": floor_penalty > 0,
        },
    }
