"""Broadcast reach scorer.

Grounded in: FIFA's own stated logic for kickoff timing -- e.g. the 2026
Final's 3pm ET slot was chosen specifically to land in European primetime.
We generalize that same logic across matches: convert the kickoff instant
into each major football market's local time, score each against a "good
viewing window", and weight markets by their rough share of global football
viewership.

Market weights are a documented simplification (not real audience-measurement
data), loosely reflecting global football viewership distribution across
Europe, the Americas, Asia and Africa.

Scale: "goodness" (0-10, higher = better global reach).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from scorers.data_loader import get_match, get_venue

MARKETS = {
    "Europe": ("Europe/London", 0.35),
    "South America": ("America/Sao_Paulo", 0.20),
    "North America (hosts)": ("America/New_York", 0.20),
    "Asia": ("Asia/Tokyo", 0.15),
    "Africa": ("Africa/Lagos", 0.10),
}


def _viewing_window_score(local_hour: float) -> float:
    if 18 <= local_hour < 22:
        return 10.0
    if 15 <= local_hour < 18 or 22 <= local_hour < 23:
        return 7.0
    if 10 <= local_hour < 15:
        return 5.0
    if 7 <= local_hour < 10 or 23 <= local_hour < 24:
        return 3.0
    return 1.0  # 00:00-07:00 dead zone in that market


def score_broadcast_reach(match_id: str) -> dict:
    match = get_match(match_id)
    venue = get_venue(match["venue_id"])

    kickoff_utc = datetime.strptime(
        f"{match['date']} {match['kickoff_utc']}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("UTC"))

    market_scores = {}
    weighted_total = 0.0
    for market, (tz_name, weight) in MARKETS.items():
        local_dt = kickoff_utc.astimezone(ZoneInfo(tz_name))
        local_hour = local_dt.hour + local_dt.minute / 60
        window_score = _viewing_window_score(local_hour)
        market_scores[market] = {
            "local_kickoff": local_dt.strftime("%H:%M"),
            "window_score": window_score,
            "weight": weight,
        }
        weighted_total += window_score * weight

    score = round(weighted_total, 1)

    best_market = max(market_scores, key=lambda m: market_scores[m]["window_score"])
    worst_market = min(market_scores, key=lambda m: market_scores[m]["window_score"])
    reasoning = (
        f"Kickoff at {match['kickoff_local']} local ({venue['name']}) lands at "
        f"{market_scores[best_market]['local_kickoff']} in {best_market} (strong slot) and "
        f"{market_scores[worst_market]['local_kickoff']} in {worst_market} "
        f"({'strong' if market_scores[worst_market]['window_score'] >= 7 else 'weak'} slot)."
    )

    return {
        "match_id": match_id,
        "scorer": "broadcast_reach",
        "scale": "goodness",
        "score": score,
        "label": f"{score}/10",
        "reasoning": reasoning,
        "details": {"markets": market_scores},
    }
