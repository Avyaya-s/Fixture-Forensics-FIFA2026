import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scorers.aggregate import SCORERS

for match_id in ["M006", "M031", "M051"]:
    print(f"\n=== {match_id} ===")
    for fn in SCORERS.values():
        r = fn(match_id)
        print(f"[{r['scorer']:18s}] {r['label']:>22s} | {r['reasoning']}")
