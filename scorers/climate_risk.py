"""Climate risk scorer.

Grounded in: FIFA's own stated venue-analysis criteria (temperature, cooling
infrastructure) plus established heat-safety practice in football (bands
informed by FIFA/FIFPro heat-policy guidance on when cooling breaks are
required). Roof type adjusts the effective risk down, since closed/retractable
roofs are assumed to be used with climate control for hot-weather fixtures.

NOTE ON SCALE: unlike the other four scorers, this one reports on a *risk*
scale (0-10, higher = worse/riskier), because "risk" is the more intuitive
framing for climate. When combining into the composite, the aggregator must
invert it (contribution = 10 - risk_score) to put it on the same
higher-is-better "goodness" scale as the other four scorers.

Depends on climate.csv (temp_c, humidity_pct per match), which is not yet
built -- this module is ready but not runnable until that data lands.
"""
from scorers.data_loader import get_match, get_venue, load_climate

ROOF_RISK_MULTIPLIER = {
    "open": 1.0,
    "retractable": 0.3,
    "fixed_closed": 0.15,
}


def _heat_index_c(temp_c: float, humidity_pct: float) -> float:
    # Simplified combined heat measure: humidity impairs evaporative cooling,
    # so it's added as a fraction of temperature rather than using a full
    # meteorological heat-index formula. Documented simplification.
    return temp_c + 0.05 * humidity_pct


def _risk_band(heat_index: float) -> float:
    if heat_index < 24:
        return 1.0 + (heat_index / 24) * 2.0       # 1-3
    if heat_index < 27:
        return 3.0 + (heat_index - 24) / 3 * 2.0    # 3-5
    if heat_index < 30:
        return 5.0 + (heat_index - 27) / 3 * 2.0    # 5-7
    if heat_index < 33:
        return 7.0 + (heat_index - 30) / 3 * 2.0    # 7-9
    return min(10.0, 9.0 + (heat_index - 33) / 5)   # 9-10


def score_climate_risk(match_id: str) -> dict:
    match = get_match(match_id)
    venue = get_venue(match["venue_id"])
    climate = load_climate()
    row = climate[climate["match_id"] == match_id]
    if row.empty:
        raise ValueError(f"No climate.csv row for match_id: {match_id!r}")
    row = row.iloc[0]

    heat_index = _heat_index_c(row["temp_c"], row["humidity_pct"])
    raw_risk = _risk_band(heat_index)
    multiplier = ROOF_RISK_MULTIPLIER.get(venue["roof_type"], 1.0)
    risk_score = round(raw_risk * multiplier, 1)

    band = (
        "Low" if risk_score < 3 else
        "Moderate" if risk_score < 6 else
        "High" if risk_score < 8 else
        "Extreme"
    )
    roof_note = (
        f", reduced from an open-air risk of {raw_risk:.1f} by the venue's {venue['roof_type']} roof"
        if multiplier < 1.0 else ""
    )
    reasoning = (
        f"{band} risk ({risk_score}/10) -- {row['temp_c']:.0f}°C, {row['humidity_pct']:.0f}% humidity "
        f"at kickoff ({row['data_type']}){roof_note}."
    )

    return {
        "match_id": match_id,
        "scorer": "climate_risk",
        "scale": "risk",
        "score": risk_score,
        "label": f"{band} ({risk_score}/10)",
        "reasoning": reasoning,
        "details": {
            "temp_c": row["temp_c"],
            "humidity_pct": row["humidity_pct"],
            "heat_index_c": round(heat_index, 1),
            "roof_type": venue["roof_type"],
            "data_type": row["data_type"],
        },
    }
