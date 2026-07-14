"""Fetches per-match kickoff-time air quality and writes air_quality.csv.

Source: Open-Meteo's Air Quality API, which serves historical data for past
dates directly (no separate archive endpoint needed, unlike the weather API).
Requests `us_aqi` directly -- Open-Meteo computes the official US EPA Air
Quality Index itself, so this doesn't need to re-derive AQI from PM2.5 via
the EPA breakpoint formula. One API call per venue, spanning that venue's
full match-date range, rather than one call per match.

Run with: python data/build_air_quality.py
"""
import time
from pathlib import Path

import pandas as pd
import requests

from _kickoff_time import match_utc

DATA_DIR = Path(__file__).resolve().parent
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
DATA_TYPE = "Open-Meteo air quality (CAMS)"


def fetch_venue_hourly(venue, start_date: str, end_date: str) -> dict:
    resp = requests.get(
        AIR_QUALITY_URL,
        params={
            "latitude": venue["lat"],
            "longitude": venue["lon"],
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "pm2_5,us_aqi",
            "timezone": "UTC",
        },
        timeout=30,
    )
    resp.raise_for_status()
    hourly = resp.json()["hourly"]
    return {
        t: (pm25, aqi)
        for t, pm25, aqi in zip(hourly["time"], hourly["pm2_5"], hourly["us_aqi"])
    }


def main():
    matches = pd.read_csv(DATA_DIR / "matches.csv")
    venues = pd.read_csv(DATA_DIR / "venues.csv").set_index("venue_id")

    matches["_utc"] = matches.apply(lambda m: match_utc(m, venues.loc[m["venue_id"]]), axis=1)

    rows = []
    for venue_id, group in matches.groupby("venue_id"):
        venue = venues.loc[venue_id]
        start_date = group["_utc"].min().strftime("%Y-%m-%d")
        end_date = group["_utc"].max().strftime("%Y-%m-%d")
        print(f"Fetching {venue['name']} ({venue_id}): {start_date}..{end_date}")
        hourly = fetch_venue_hourly(venue, start_date, end_date)
        time.sleep(0.3)

        for _, m in group.iterrows():
            key = m["_utc"].strftime("%Y-%m-%dT%H:00")
            if key not in hourly:
                raise ValueError(f"No air quality data for {m['match_id']} at {key} ({venue['name']})")
            pm2_5, us_aqi = hourly[key]
            rows.append(
                {
                    "match_id": m["match_id"],
                    "pm2_5": pm2_5,
                    "us_aqi": us_aqi,
                    "data_type": DATA_TYPE,
                }
            )

    out = pd.DataFrame(rows).sort_values("match_id")
    out.to_csv(DATA_DIR / "air_quality.csv", index=False)
    print(f"Wrote {len(out)} rows to {DATA_DIR / 'air_quality.csv'}")


if __name__ == "__main__":
    main()
