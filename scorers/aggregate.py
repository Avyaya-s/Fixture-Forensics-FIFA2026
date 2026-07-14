"""Framework-agnostic aggregation over the individual scorers.

Both the Streamlit dashboard (dashboard/scoring.py) and the web API
(web/backend/main.py) import from here, so neither reimplements which
scorers run, how a match's summary row is shaped, or JSON-safety of the
numpy scalars pandas hands back.
"""
import math
from functools import lru_cache

import numpy as np

from scorers.air_quality import score_air_quality
from scorers.altitude_fairness import score_altitude_fairness
from scorers.broadcast_reach import score_broadcast_reach
from scorers.climate_risk import score_climate_risk
from scorers.cross_border import score_cross_border
from scorers.data_loader import get_match, load_matches
from scorers.jet_lag import score_jet_lag
from scorers.travel_fairness import score_travel_fairness
from scorers.venue_fit import score_venue_fit

SCORERS = {
    "altitude_fairness": score_altitude_fairness,
    "travel_fairness": score_travel_fairness,
    "jet_lag": score_jet_lag,
    "cross_border": score_cross_border,
    "venue_fit": score_venue_fit,
    "broadcast_reach": score_broadcast_reach,
    "climate_risk": score_climate_risk,
    "air_quality": score_air_quality,
}

SCORER_LABELS = {
    "altitude_fairness": "Altitude",
    "travel_fairness": "Travel",
    "jet_lag": "Jet Lag",
    "cross_border": "Cross-Border",
    "venue_fit": "Venue Fit",
    "broadcast_reach": "Broadcast",
    "climate_risk": "Climate",
    "air_quality": "Air Quality",
}

# Discrete weight tiers (0=excluded, 1=low, 2=medium, 3=high) per stakeholder
# lens, not fabricated decimal weights -- tiers keep the judgment call honest
# about being a judgment call rather than dressed up as false precision.
# "balanced" is every scorer at equal weight, i.e. the plain unweighted mean
# -- the same number the old flat "Average" always was.
#
# Rationale per lens:
#   player_welfare  -- health/safety-backed factors (FIFA/FIFPro heat + rest
#                       standards, physiology) get High; broadcast reach gets
#                       a Low (odd kickoff times disrupt sleep/circadian
#                       rhythm, same physiology as jet lag, but indirectly);
#                       venue_fit has no credible health link, excluded.
#   fan_convenience -- broadcast reach and venue fit are direct (can you
#                       watch, can you get a ticket); climate/air quality get
#                       Medium (affects fans in an open stadium too, not just
#                       players); altitude/travel/jet lag get Low (indirect,
#                       via match quality/competitiveness); cross-border gets
#                       Medium (visa/travel burden on traveling fans too).
#   profit          -- venue_fit and broadcast reach are the only two with a
#                       direct revenue link (ticket sales, ad/sponsorship).
#                       Everything else gets Low at most, via the softer
#                       "an unfair/lopsided match is less watchable" argument
#                       -- noticeably weaker reasoning than the other two
#                       lenses' citations, not pretended otherwise.
WEIGHT_PROFILES = {
    "balanced": {
        "altitude_fairness": 1, "travel_fairness": 1, "jet_lag": 1, "cross_border": 1,
        "venue_fit": 1, "broadcast_reach": 1, "climate_risk": 1, "air_quality": 1,
    },
    "player_welfare": {
        "altitude_fairness": 3, "travel_fairness": 3, "jet_lag": 3, "cross_border": 2,
        "venue_fit": 0, "broadcast_reach": 1, "climate_risk": 3, "air_quality": 3,
    },
    "fan_convenience": {
        "altitude_fairness": 1, "travel_fairness": 1, "jet_lag": 1, "cross_border": 2,
        "venue_fit": 3, "broadcast_reach": 3, "climate_risk": 2, "air_quality": 2,
    },
    "profit": {
        "altitude_fairness": 1, "travel_fairness": 1, "jet_lag": 1, "cross_border": 0,
        "venue_fit": 3, "broadcast_reach": 3, "climate_risk": 1, "air_quality": 1,
    },
}

PROFILE_LABELS = {
    "balanced": "Balanced",
    "player_welfare": "Player Welfare",
    "fan_convenience": "Fan Convenience",
    "profit": "Profit",
}


def _to_native(obj):
    """Recursively convert numpy scalars to native Python types for JSON safety.

    NaN (e.g. rest_days/travel_distance_km for a team's tournament opener,
    where there is no prior match to compare against) becomes None -- NaN
    itself isn't valid JSON and Starlette's JSONResponse rejects it outright.
    """
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


def _goodness(result: dict):
    """A scorer's score on the shared higher-is-better 0-10 scale.

    climate_risk reports risk (higher = worse) rather than goodness, per its
    own docstring the aggregator is responsible for inverting it before
    combining with the other four -- done here via the result's own `scale`
    field so no scorer name is hardcoded.
    """
    score = result["score"]
    if score is None:
        return None
    return round(10.0 - score, 1) if result["scale"] == "risk" else score


@lru_cache
def score_match(match_id: str) -> dict:
    """Run every scorer against one match_id -> {scorer_name: result_dict}.

    Each result keeps its own native `score`/`label`/`reasoning` (e.g.
    climate_risk's risk framing) plus a `goodness` field -- the same
    higher-is-better value used in match_summary_row's Average -- so a
    risk-scale scorer's detail view can show both without the two numbers
    looking unrelated.
    """
    results = _to_native({name: fn(match_id) for name, fn in SCORERS.items()})
    for result in results.values():
        result["goodness"] = _goodness(result)
    return results


@lru_cache
def composite_score(match_id: str, profile: str = "balanced"):
    """Weighted average of every scorer's goodness value under one lens.

    Scorers with weight 0 in this profile, or a None score (e.g. a
    tournament opener), are excluded entirely rather than counted as 0 --
    same "missing, not zero" handling as the plain Average always used.
    """
    if profile not in WEIGHT_PROFILES:
        raise ValueError(f"Unknown weight profile: {profile!r}")
    weights = WEIGHT_PROFILES[profile]
    results = score_match(match_id)

    weighted_sum = 0.0
    weight_total = 0.0
    for name, weight in weights.items():
        if weight <= 0:
            continue
        goodness = results[name]["goodness"]
        if goodness is None:
            continue
        weighted_sum += goodness * weight
        weight_total += weight

    return round(weighted_sum / weight_total, 1) if weight_total else None


@lru_cache
def match_summary_row(match_id: str) -> dict:
    """One flat dict for match_id: identifying fields, each scorer's score,
    a `composites` dict of every weight profile's score, and `Average` (an
    alias for the "balanced" composite, kept for backward compatibility).
    """
    match = get_match(match_id)
    results = score_match(match_id)
    row = _to_native({
        "match_id": match_id,
        "group": match["group"],
        "matchday": match["matchday"],
        "date": match["date"],
        "team_home": match["team_home"],
        "team_away": match["team_away"],
        "venue": match["venue_name"],
        "venue_city": match["venue_city"],
    })
    for name in SCORERS:
        row[SCORER_LABELS[name]] = results[name]["goodness"]
    row["composites"] = {profile: composite_score(match_id, profile) for profile in WEIGHT_PROFILES}
    row["Average"] = row["composites"]["balanced"]
    return row


@lru_cache
def build_overview() -> list:
    """One summary row per match, in match_id order."""
    return [match_summary_row(mid) for mid in load_matches()["match_id"]]
