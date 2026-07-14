"""Fixture Forensics web API.

Serves the same scorer results as the Streamlit dashboard (via
scorers.aggregate) as JSON, and hosts the static frontend in web/frontend/.

Run with: uvicorn web.backend.main:app --reload
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from scorers.aggregate import PROFILE_LABELS, SCORER_LABELS, build_overview, match_summary_row, score_match
from scorers.data_loader import get_match

app = FastAPI(title="Fixture Forensics API")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.middleware("http")
async def no_store(request, call_next):
    """StaticFiles doesn't send Cache-Control on its own, so browsers fall
    back to heuristic caching -- which has served a stale app.js/charts.js
    mid-development more than once. This is a local dev tool with no CDN in
    front of it, so there's no cost to just disabling caching outright.
    """
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/scorers")
def list_scorers():
    """Scorer keys in a fixed display order, for the frontend to build legends/columns from."""
    return [{"key": key, "label": label} for key, label in SCORER_LABELS.items()]


@app.get("/api/profiles")
def list_profiles():
    """Weight-profile keys in a fixed display order, for the frontend's lens toggle."""
    return [{"key": key, "label": label} for key, label in PROFILE_LABELS.items()]


@app.get("/api/matches")
def list_matches():
    """One summary row per fixture: teams, venue, each scorer's score, the "balanced"
    Average, and a `composites` dict with every weight profile's score.
    """
    return build_overview()


@app.get("/api/matches/{match_id}")
def get_match_detail(match_id: str):
    """Full match info plus every scorer's score, label, and reasoning for one fixture."""
    try:
        match = get_match(match_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown match_id: {match_id!r}")

    return {
        "summary": match_summary_row(match_id),
        "match": {
            "match_id": match_id,
            "group": match["group"],
            "matchday": int(match["matchday"]),
            "date": match["date"],
            "kickoff_local": match["kickoff_local"],
            "kickoff_utc": match["kickoff_utc"],
            "team_home": match["team_home"],
            "team_away": match["team_away"],
            "venue_name": match["venue_name"],
            "venue_city": match["venue_city"],
            "stage": match["stage"],
        },
        "scores": score_match(match_id),
    }


# Mounted last: only paths not matched by an /api/* route above fall through here.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
