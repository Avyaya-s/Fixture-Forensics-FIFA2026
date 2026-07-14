"""Fixture Forensics -- Match Detail page.

Pick one fixture and see every scorer's score plus full reasoning.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go
import streamlit as st

from scoring import PROFILE_LABELS, SCORER_LABELS, composite_score, score_match
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

top_left, top_right = st.columns([3, 2])
with top_left:
    choice = st.selectbox("Fixture", options, index=default_index)
with top_right:
    profile_label = st.radio("Weight the composite by", list(PROFILE_LABELS.values()), index=0, horizontal=True)
    profile_key = next(k for k, v in PROFILE_LABELS.items() if v == profile_label)

match_id = choice.split(" — ")[0]
match = get_match(match_id)

st.caption(
    f"{match['venue_name']}, {match['venue_city']} · {match['date']} kickoff {match['kickoff_local']} local "
    f"· Group {match['group']}, Matchday {match['matchday']}"
)

composite = composite_score(match_id, profile_key)
st.metric(f"Composite score ({profile_label})", f"{composite}/10" if composite is not None else "N/A")

results = score_match(match_id)

cols = st.columns(len(results))
for col, (name, result) in zip(cols, results.items()):
    with col:
        st.metric(SCORER_LABELS[name], result["label"])
        st.caption(result["reasoning"])
        if result["scale"] == "risk" and result["goodness"] is not None:
            st.caption(f"Counts as {result['goodness']}/10 goodness toward the average (risk, inverted).")

# Every axis plotted on the shared higher-is-better "goodness" scale -- climate_risk's
# native score is risk (higher = worse), so plotting it unconverted would make a larger
# radar area look "better" on that axis while meaning the opposite.
plot_names = [SCORER_LABELS[n] for n, r in results.items() if r["goodness"] is not None]
plot_scores = [r["goodness"] for r in results.values() if r["goodness"] is not None]

if plot_scores:
    st.subheader("Score comparison")
    fig = go.Figure(
        data=go.Scatterpolar(r=plot_scores + plot_scores[:1], theta=plot_names + plot_names[:1], fill="toself")
    )
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False)
    st.plotly_chart(fig, width="stretch")

with st.expander("Raw scorer output"):
    st.json(results)
