"""Fixture Forensics -- Match Detail page.

Pick one fixture and see every scorer's score plus full reasoning.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go
import streamlit as st

from scoring import SCORER_LABELS, score_match
from scorers.data_loader import get_match, load_matches

st.set_page_config(page_title="Fixture Forensics -- Match Detail", page_icon="🔍", layout="wide")
st.title("🔍 Match Detail")

matches = load_matches().sort_values("match_id")
options = [f"{row.match_id} — {row.team_home} vs {row.team_away}" for row in matches.itertuples()]

default_index = 0
default_id = st.session_state.get("selected_match_id")
if default_id:
    for i, opt in enumerate(options):
        if opt.startswith(f"{default_id} "):
            default_index = i
            break

choice = st.selectbox("Fixture", options, index=default_index)
match_id = choice.split(" — ")[0]
match = get_match(match_id)

st.caption(
    f"{match['venue_name']}, {match['venue_city']} · {match['date']} kickoff {match['kickoff_local']} local "
    f"· Group {match['group']}, Matchday {match['matchday']}"
)

results = score_match(match_id)

cols = st.columns(len(results))
for col, (name, result) in zip(cols, results.items()):
    with col:
        score = result["score"]
        st.metric(SCORER_LABELS[name], result["label"])
        st.caption(result["reasoning"])

plot_names = [SCORER_LABELS[n] for n, r in results.items() if r["score"] is not None]
plot_scores = [r["score"] for r in results.values() if r["score"] is not None]

if plot_scores:
    st.subheader("Score comparison")
    fig = go.Figure(
        data=go.Scatterpolar(r=plot_scores + plot_scores[:1], theta=plot_names + plot_names[:1], fill="toself")
    )
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False)
    st.plotly_chart(fig, width="stretch")

with st.expander("Raw scorer output"):
    st.json(results)
