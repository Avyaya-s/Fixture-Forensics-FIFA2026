"""Shared, cached access to the reference dataset for all scorers.

Every scorer reads through this module rather than opening CSVs directly, so
there is exactly one place that knows the file layout and join keys.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache
def load_matches() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "matches.csv")


@lru_cache
def load_venues() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "venues.csv").set_index("venue_id")


@lru_cache
def load_teams() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "teams.csv").set_index("team")


@lru_cache
def load_team_match_sequence() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "team_match_sequence.csv")


@lru_cache
def load_climate() -> pd.DataFrame:
    path = DATA_DIR / "climate.csv"
    if not path.exists():
        raise FileNotFoundError(
            "climate.csv has not been built yet (pending Open-Meteo fetch step); "
            "score_climate_risk is not usable until it exists."
        )
    return pd.read_csv(path)


def get_match(match_id: str) -> pd.Series:
    matches = load_matches()
    row = matches[matches["match_id"] == match_id]
    if row.empty:
        raise ValueError(f"Unknown match_id: {match_id!r}")
    return row.iloc[0]


def get_venue(venue_id: str) -> pd.Series:
    return load_venues().loc[venue_id]


def get_team(team: str) -> pd.Series:
    teams = load_teams()
    if team not in teams.index:
        raise ValueError(f"Unknown team: {team!r}")
    return teams.loc[team]


def get_team_sequence_row(team: str, match_id: str) -> pd.Series:
    seq = load_team_match_sequence()
    row = seq[(seq["team"] == team) & (seq["match_id"] == match_id)]
    if row.empty:
        raise ValueError(f"No team_match_sequence row for {team!r} / {match_id!r}")
    return row.iloc[0]
