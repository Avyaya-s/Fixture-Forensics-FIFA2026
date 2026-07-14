"""Fetches per-match kickoff-time temperature and humidity and writes climate.csv.

Source: Open-Meteo's historical archive (ERA5 reanalysis) -- all 72 group-stage
kickoffs are already in the past by the time this runs, so the archive (not
the forecast) endpoint is the correct source. One API call per venue, spanning
that venue's full match-date range, rather than one call per match.

The kickoff instant is computed from `date` + `kickoff_local` + the venue's
IANA timezone (not the `kickoff_utc` column) because a late local kickoff can
roll over into the next UTC calendar day (e.g. a 20:00 kickoff in a UTC-6
venue is 02:00 UTC the *next* day) -- timezone-aware conversion handles that
automatically, a naive `date` + `kickoff_utc` string join would not.

Run with: python data/build_climate.py
"""
import time
from pathlib import Path

import pandas as pd
import requests

from _kickoff_time import match_utc

DATA_DIR = Path(__file__).resolve().parent
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DATA_TYPE = "ERA5 historical"


def fetch_venue_hourly(venue, start_date: str, end_date: str) -> dict:
    resp = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": venue["lat"],
            "longitude": venue["lon"],
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,relative_humidity_2m",
            "timezone": "UTC",
        },
        timeout=30,
    )
    resp.raise_for_status()
    hourly = resp.json()["hourly"]
    return {
        t: (temp, hum)
        for t, temp, hum in zip(hourly["time"], hourly["temperature_2m"], hourly["relative_humidity_2m"])
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
                raise ValueError(f"No archive data for {m['match_id']} at {key} ({venue['name']})")
            temp_c, humidity_pct = hourly[key]
            rows.append(
                {
                    "match_id": m["match_id"],
                    "temp_c": temp_c,
                    "humidity_pct": humidity_pct,
                    "data_type": DATA_TYPE,
                }
            )

    out = pd.DataFrame(rows).sort_values("match_id")
    out.to_csv(DATA_DIR / "climate.csv", index=False)
    print(f"Wrote {len(out)} rows to {DATA_DIR / 'climate.csv'}")


if __name__ == "__main__":
    main()
