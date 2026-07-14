"""Jet lag / circadian misalignment scorer.

Grounded in published travel-fatigue research: elite athletes recover
circadian alignment at roughly one day per time zone crossed, and eastward
travel produces measurably worse, longer-lasting jet lag than westward
travel for the same number of zones. EASTWARD_MULTIPLIER (1.5x) is a
general circadian-adaptation rule of thumb from aviation/travel medicine --
no football-specific multiplier was found, so this is a documented
approximation, not a cited football figure.

Distinct from travel_fairness: two venues can be far apart in km with
almost no time-zone shift (e.g. north-south), or closer with a real shift.
This scorer isolates the time-zone dimension via each venue's UTC offset,
independent of travel_fairness's distance/rest-day measures.

Like altitude_fairness, we compute each team's own one-directional jet-lag
burden (the shift from their previous match's venue to this one, weighted
for direction), then score the *gap* between the two teams' burdens --
a match where both teams shift equally is fair even if both are affected.

All 16 venues sit within a 3-hour UTC-offset band (Pacific to Eastern), so
SEVERE_SHIFT_HOURS is calibrated to that band's max, not to a universal
"long-haul jet lag" threshold -- this tournament never produces the 5+ hour
shifts most jet-lag research actually studies.

Scale: "goodness" (0-10, higher = fairer / more symmetric).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from scorers.data_loader import get_match, get_previous_match_row, get_venue

EASTWARD_MULTIPLIER = 1.5  # general circadian-adaptation rule of thumb: eastward jet lag is worse
SEVERE_SHIFT_HOURS = 3.0  # calibrated to this tournament's max spread (Pacific to Eastern)


def _utc_offset_hours(venue, on_date: str) -> float:
    tz = ZoneInfo(venue["timezone"])
    dt = datetime.strptime(on_date, "%Y-%m-%d").replace(tzinfo=tz)
    return dt.utcoffset().total_seconds() / 3600


def _shift_hours(prev_venue, prev_date: str, this_venue, this_date: str) -> float:
    """Signed UTC-offset shift; positive = moved east, negative = moved west."""
    return _utc_offset_hours(this_venue, this_date) - _utc_offset_hours(prev_venue, prev_date)


def _burden(shift_hours: float) -> float:
    weighted = abs(shift_hours) * (EASTWARD_MULTIPLIER if shift_hours > 0 else 1.0)
    return min(1.0, weighted / SEVERE_SHIFT_HOURS)


def _direction(shift_hours: float) -> str:
    if shift_hours > 0:
        return f"{shift_hours:.0f}h eastward"
    if shift_hours < 0:
        return f"{abs(shift_hours):.0f}h westward"
    return "no time-zone shift"


def score_jet_lag(match_id: str) -> dict:
    match = get_match(match_id)
    home, away = match["team_home"], match["team_away"]
    venue = get_venue(match["venue_id"])

    home_prev = get_previous_match_row(home, match_id)
    away_prev = get_previous_match_row(away, match_id)

    if home_prev is None or away_prev is None:
        return {
            "match_id": match_id,
            "scorer": "jet_lag",
            "scale": "goodness",
            "score": None,
            "label": "N/A (tournament opener)",
            "reasoning": (
                f"{home} and/or {away} are playing their first group match of the "
                "tournament in this fixture, so there is no prior venue to measure a "
                "time-zone shift from."
            ),
            "details": {},
        }

    home_prev_venue = get_venue(home_prev["venue_id"])
    away_prev_venue = get_venue(away_prev["venue_id"])

    home_shift = _shift_hours(home_prev_venue, home_prev["date"], venue, match["date"])
    away_shift = _shift_hours(away_prev_venue, away_prev["date"], venue, match["date"])
    home_burden = _burden(home_shift)
    away_burden = _burden(away_shift)

    asymmetry = abs(home_burden - away_burden)
    score = round(max(0.0, 10.0 - asymmetry * 10.0), 1)

    if home_burden < 0.01 and away_burden < 0.01:
        reasoning = (
            f"Negligible time-zone shift for both {home} ({_direction(home_shift)}) and "
            f"{away} ({_direction(away_shift)}) since their previous match."
        )
    elif asymmetry < 0.1:
        reasoning = (
            f"Comparable time-zone shift for both {home} ({_direction(home_shift)}) and "
            f"{away} ({_direction(away_shift)}) since their previous match."
        )
    else:
        disadvantaged = home if home_burden > away_burden else away
        disadvantaged_shift = home_shift if disadvantaged == home else away_shift
        acclimated = away if disadvantaged == home else home
        acclimated_shift = away_shift if disadvantaged == home else home_shift
        reasoning = (
            f"{disadvantaged} shifted {_direction(disadvantaged_shift)} since its previous match, a bigger "
            f"circadian adjustment than {acclimated}'s {_direction(acclimated_shift)} -- an asymmetric "
            "jet-lag disadvantage."
        )

    return {
        "match_id": match_id,
        "scorer": "jet_lag",
        "scale": "goodness",
        "score": score,
        "label": f"{score}/10",
        "reasoning": reasoning,
        "details": {
            "home_shift_hours": round(home_shift, 1),
            "away_shift_hours": round(away_shift, 1),
            "home_burden": round(home_burden, 2),
            "away_burden": round(away_burden, 2),
        },
    }
