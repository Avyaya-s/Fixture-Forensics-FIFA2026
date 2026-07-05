"""Builds team_match_sequence.csv from matches.csv + venues.csv.

For each team, walks their 3 group-stage matches in chronological order and
computes rest_days and travel_distance_km relative to their previous match.
A team's first match of the tournament has no prior match to compare against,
so rest_days/travel_distance_km are left blank (NaN) for it, not zero-filled --
there is no tournament travel/rest baseline before a team's opener.
"""
import math
import pandas as pd

matches = pd.read_csv("data/matches.csv")
venues = pd.read_csv("data/venues.csv").set_index("venue_id")


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# long-format: one row per (team, match) the team played in
rows = []
for _, m in matches.iterrows():
    for team in (m["team_home"], m["team_away"]):
        rows.append({
            "team": team,
            "match_id": m["match_id"],
            "date": m["date"],
            "venue_id": m["venue_id"],
        })

seq = pd.DataFrame(rows)
seq["date"] = pd.to_datetime(seq["date"])
seq = seq.sort_values(["team", "date"]).reset_index(drop=True)

out_cols = ["team", "match_id", "match_number", "date", "venue_id", "rest_days", "travel_distance_km"]
out_rows = []
for team, grp in seq.groupby("team", sort=False):
    grp = grp.sort_values("date").reset_index(drop=True)
    prev_date, prev_venue = None, None
    for i, r in grp.iterrows():
        venue = venues.loc[r["venue_id"]]
        if prev_date is None:
            rest_days, travel_km = None, None
        else:
            rest_days = (r["date"] - prev_date).days
            prev_v = venues.loc[prev_venue]
            travel_km = round(haversine_km(prev_v["lat"], prev_v["lon"], venue["lat"], venue["lon"]), 1)
        out_rows.append({
            "team": team,
            "match_id": r["match_id"],
            "match_number": i + 1,
            "date": r["date"].strftime("%Y-%m-%d"),
            "venue_id": r["venue_id"],
            "rest_days": rest_days,
            "travel_distance_km": travel_km,
        })
        prev_date, prev_venue = r["date"], r["venue_id"]

out = pd.DataFrame(out_rows, columns=out_cols)
out.to_csv("data/team_match_sequence.csv", index=False)
print(out.head(10).to_string())
print("rows:", len(out), "| teams:", out["team"].nunique())
