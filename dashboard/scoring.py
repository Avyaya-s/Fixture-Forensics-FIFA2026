"""Shared scoring access for the dashboard pages.

Wires the repo-root `scorers` package onto sys.path (dashboard/ is a sibling
directory, not a subpackage of it) and caches per-match score computations so
Streamlit doesn't re-run all four scorers on every widget interaction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from scorers.altitude_fairness import score_altitude_fairness
from scorers.broadcast_reach import score_broadcast_reach
from scorers.data_loader import get_match, load_matches
from scorers.travel_fairness import score_travel_fairness
from scorers.venue_fit import score_venue_fit

# climate_risk is intentionally excluded: climate.csv hasn't been built yet.
SCORERS = {
    "altitude_fairness": score_altitude_fairness,
    "travel_fairness": score_travel_fairness,
    "venue_fit": score_venue_fit,
    "broadcast_reach": score_broadcast_reach,
}

SCORER_LABELS = {
    "altitude_fairness": "Altitude",
    "travel_fairness": "Travel",
    "venue_fit": "Venue Fit",
    "broadcast_reach": "Broadcast",
}


@st.cache_data
def score_match(match_id: str) -> dict:
    """Run every scorer against one match_id -> {scorer_name: result_dict}."""
    return {name: fn(match_id) for name, fn in SCORERS.items()}


@st.cache_data
def build_overview() -> pd.DataFrame:
    """One row per match with every scorer's score plus an average column."""
    rows = []
    for match_id in load_matches()["match_id"]:
        match = get_match(match_id)
        results = score_match(match_id)
        row = {
            "match_id": match_id,
            "group": match["group"],
            "matchday": match["matchday"],
            "date": match["date"],
            "fixture": f"{match['team_home']} vs {match['team_away']}",
            "venue": match["venue_name"],
        }
        scores = []
        for name in SCORERS:
            s = results[name]["score"]
            row[SCORER_LABELS[name]] = s
            if s is not None:
                scores.append(s)
        row["Average"] = round(sum(scores) / len(scores), 1) if scores else None
        rows.append(row)
    return pd.DataFrame(rows)
