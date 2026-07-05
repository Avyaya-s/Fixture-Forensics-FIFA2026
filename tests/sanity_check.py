import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scorers.altitude_fairness import score_altitude_fairness
from scorers.broadcast_reach import score_broadcast_reach
from scorers.travel_fairness import score_travel_fairness
from scorers.venue_fit import score_venue_fit

SCORERS = [score_broadcast_reach, score_travel_fairness, score_venue_fit, score_altitude_fairness]

for match_id in ["M006", "M031", "M051"]:
    print(f"\n=== {match_id} ===")
    for fn in SCORERS:
        r = fn(match_id)
        print(f"[{r['scorer']:18s}] {r['label']:>22s} | {r['reasoning']}")
