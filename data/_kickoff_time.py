"""Shared helper for data/build_*.py fetch scripts.

Computes a match's true UTC kickoff instant from `date` + `kickoff_local` +
the venue's IANA timezone -- not the `kickoff_utc` column, because a late
local kickoff can roll into the next UTC calendar day (e.g. a 20:00 kickoff
in a UTC-6 venue is 02:00 UTC the *next* day). Timezone-aware conversion
handles that automatically; a naive `date` + `kickoff_utc` string join would
not. See build_climate.py's docstring for the original discovery of this.
"""
from datetime import datetime
from zoneinfo import ZoneInfo


def match_utc(match, venue) -> datetime:
    local_dt = datetime.strptime(
        f"{match['date']} {match['kickoff_local']}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo(venue["timezone"]))
    return local_dt.astimezone(ZoneInfo("UTC"))
