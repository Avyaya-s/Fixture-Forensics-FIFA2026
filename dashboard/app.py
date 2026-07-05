"""Fixture Forensics -- Overview page.

Run with: streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import plotly.express as px
import streamlit as st

from scoring import SCORER_LABELS, build_overview

st.set_page_config(page_title="Fixture Forensics -- Overview", page_icon="⚽", layout="wide")
st.title("⚽ Fixture Forensics: FIFA 2026")
st.caption(
    "Fairness and fit scoring across all 72 group-stage fixtures. "
    "Every column is a 0-10 \"goodness\" score -- higher is better."
)

df = build_overview()

with st.sidebar:
    st.header("Filters")
    groups = st.multiselect("Group", sorted(df["group"].unique()), default=sorted(df["group"].unique()))
    matchdays = st.multiselect(
        "Matchday", sorted(df["matchday"].unique()), default=sorted(df["matchday"].unique())
    )

filtered = df[df["group"].isin(groups) & df["matchday"].isin(matchdays)].sort_values("match_id")

col1, col2, col3 = st.columns(3)
col1.metric("Matches shown", len(filtered))
col2.metric("Avg score", f"{filtered['Average'].mean():.1f}" if len(filtered) else "–")
if len(filtered) and filtered["Average"].notna().any():
    worst = filtered.loc[filtered["Average"].idxmin()]
    col3.metric("Lowest scoring fixture", worst["fixture"], f"{worst['Average']:.1f}")
else:
    col3.metric("Lowest scoring fixture", "–")

st.subheader("All fixtures")
st.caption("Click a row, then open **Match Detail** in the sidebar to see full reasoning.")

score_cols = list(SCORER_LABELS.values())
event = st.dataframe(
    filtered,
    width="stretch",
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_order=["match_id", "group", "matchday", "fixture", "venue", *score_cols, "Average"],
    column_config={
        "match_id": "ID",
        "group": "Grp",
        "matchday": "MD",
        **{
            c: st.column_config.ProgressColumn(c, min_value=0, max_value=10, format="%.1f")
            for c in [*score_cols, "Average"]
        },
    },
)

selected_rows = event.selection.rows if event and event.selection else []
if selected_rows:
    st.session_state["selected_match_id"] = filtered.iloc[selected_rows[0]]["match_id"]
    st.success(f"Selected {st.session_state['selected_match_id']} -- open **Match Detail** to see it.")

st.subheader("Score distribution by scorer")
melted = filtered.melt(
    id_vars=["match_id", "fixture"], value_vars=score_cols, var_name="Scorer", value_name="Score"
)
fig = px.box(melted, x="Scorer", y="Score", points="all", hover_data=["fixture"])
fig.update_yaxes(range=[0, 10])
st.plotly_chart(fig, width="stretch")
