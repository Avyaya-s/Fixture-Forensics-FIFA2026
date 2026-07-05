"""Altitude fairness scorer.

Grounded in: well-documented physiological effects of playing at elevation
(reduced oxygen availability, faster fatigue) and ball-flight effects (thinner
air carries a struck ball farther and faster), with direct World Cup precedent
at Estadio Azteca / Mexico City (~2,240m) in 1970 and 1986. The effect is
asymmetric: a team ascending from sea level to altitude is disadvantaged;
a team descending from altitude to sea level is not correspondingly harmed.

We therefore compute each team's one-directional "altitude disadvantage" for
this venue, then score the *gap* between the two teams' disadvantage -- not
the absolute elevation.

Scale: "goodness" (0-10, higher = fairer / more symmetric).
"""
from scorers.data_loader import get_match, get_team, get_venue

# A team is only meaningfully disadvantaged once the gap they must climb
# passes a physiologically relevant threshold; below this, treat as noise.
NEGLIGIBLE_GAP_M = 500
# Gap (in m) at which the disadvantage is treated as maximal for scoring
# purposes -- calibrated to the Mexico City scenario (~2,240m venue vs. a
# sea-level home team is close to a "worst case" real fixture).
SEVERE_GAP_M = 2200


def _disadvantage(venue_elevation_m: float, home_elevation_m: float) -> float:
    gap = max(0.0, venue_elevation_m - home_elevation_m - NEGLIGIBLE_GAP_M)
    return min(1.0, gap / (SEVERE_GAP_M - NEGLIGIBLE_GAP_M))


def score_altitude_fairness(match_id: str) -> dict:
    match = get_match(match_id)
    home, away = match["team_home"], match["team_away"]
    venue = get_venue(match["venue_id"])
    home_team, away_team = get_team(home), get_team(away)

    venue_elev = venue["elevation_m"]
    home_disadv = _disadvantage(venue_elev, home_team["home_elevation_m"])
    away_disadv = _disadvantage(venue_elev, away_team["home_elevation_m"])

    asymmetry = abs(home_disadv - away_disadv)
    score = round(10.0 - asymmetry * 10.0, 1)

    if home_disadv < 0.01 and away_disadv < 0.01:
        reasoning = (
            f"{venue['name']} sits at {venue_elev:.0f}m -- negligible altitude effect "
            f"for both {home} ({home_team['home_elevation_m']:.0f}m home elevation) and "
            f"{away} ({away_team['home_elevation_m']:.0f}m)."
        )
    elif asymmetry < 0.1:
        reasoning = (
            f"{venue['name']} ({venue_elev:.0f}m) poses a similar altitude adjustment for "
            f"both {home} ({home_team['home_elevation_m']:.0f}m) and {away} "
            f"({away_team['home_elevation_m']:.0f}m) -- comparable acclimation gap."
        )
    else:
        disadvantaged = home if home_disadv > away_disadv else away
        acclimated = away if disadvantaged == home else home
        reasoning = (
            f"{venue['name']} sits at {venue_elev:.0f}m. {disadvantaged} comes from "
            f"{(home_team if disadvantaged == home else away_team)['home_elevation_m']:.0f}m and "
            f"faces a meaningful acclimation gap, while {acclimated} "
            f"({(home_team if acclimated == home else away_team)['home_elevation_m']:.0f}m home elevation) "
            "is comparatively unaffected -- an asymmetric altitude disadvantage."
        )

    return {
        "match_id": match_id,
        "scorer": "altitude_fairness",
        "scale": "goodness",
        "score": score,
        "label": f"{score}/10",
        "reasoning": reasoning,
        "details": {
            "venue_elevation_m": venue_elev,
            "home_elevation_m": home_team["home_elevation_m"],
            "away_elevation_m": away_team["home_elevation_m"],
            "home_disadvantage": round(home_disadv, 2),
            "away_disadvantage": round(away_disadv, 2),
        },
    }
