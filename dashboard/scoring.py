"""Streamlit-facing wrapper around scorers.aggregate.

Wires the repo-root `scorers` package onto sys.path (dashboard/ is a sibling
directory, not a subpackage of it), then wraps the shared aggregate module's
functions with st.cache_data so Streamlit doesn't re-run all four scorers on
every widget interaction, and shapes the overview as a DataFrame for
st.dataframe.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from scorers.aggregate import PROFILE_LABELS, SCORER_LABELS, build_overview as _build_overview
from scorers.aggregate import composite_score as _composite_score
from scorers.aggregate import score_match as _score_match

__all__ = ["PROFILE_LABELS", "SCORER_LABELS", "score_match", "composite_score", "build_overview"]

score_match = st.cache_data(_score_match)
composite_score = st.cache_data(_composite_score)


@st.cache_data
def build_overview(profile: str = "balanced") -> pd.DataFrame:
    df = pd.DataFrame(_build_overview())
    df.insert(4, "fixture", df["team_home"] + " vs " + df["team_away"])
    df["Average"] = df["composites"].apply(lambda c: c[profile])
    return df.drop(columns=["composites"])
