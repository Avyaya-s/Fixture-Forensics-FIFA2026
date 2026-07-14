"""Air quality risk scorer.

Grounded in the US EPA's official Air Quality Index (AQI) categories --
Good (0-50), Moderate (51-100), Unhealthy for Sensitive Groups (101-150),
Unhealthy (151-200), Very Unhealthy (201-300), Hazardous (301+). AQI itself
comes straight from Open-Meteo's `us_aqi` field (data/air_quality.csv),
which computes the official EPA formula from pollutant concentrations --
this scorer doesn't re-derive AQI from PM2.5 itself.

Precedent: the 1986 Mexico City World Cup drew real concern over air
pollution at altitude, and Mexico City remains one of the more polluted
2026 host cities. Roof type adjusts the effective risk down, same reasoning
as climate_risk: an enclosed, climate-controlled venue filters/limits
outdoor-air exposure.

NOTE ON SCALE: like climate_risk, this reports on a *risk* scale (0-10,
higher = worse). The aggregator (scorers/aggregate.py) inverts it
(goodness = 10 - risk_score) before combining with the "goodness" scorers.
"""
from scorers.data_loader import get_match, get_venue, load_air_quality

ROOF_RISK_MULTIPLIER = {
    "open": 1.0,
    "retractable": 0.3,
    "fixed_closed": 0.15,
}

# EPA AQI category boundaries this scorer's bands are anchored to.
EPA_GOOD_MAX = 50
EPA_MODERATE_MAX = 100
EPA_UNHEALTHY_SENSITIVE_MAX = 150
EPA_UNHEALTHY_MAX = 200
EPA_VERY_UNHEALTHY_MAX = 300


def _risk_band(aqi: float) -> float:
    if aqi <= EPA_GOOD_MAX:
        return (aqi / EPA_GOOD_MAX) * 2.0  # 0-2: Good
    if aqi <= EPA_MODERATE_MAX:
        return 2.0 + (aqi - EPA_GOOD_MAX) / (EPA_MODERATE_MAX - EPA_GOOD_MAX) * 2.0  # 2-4: Moderate
    if aqi <= EPA_UNHEALTHY_SENSITIVE_MAX:
        return 4.0 + (aqi - EPA_MODERATE_MAX) / (EPA_UNHEALTHY_SENSITIVE_MAX - EPA_MODERATE_MAX) * 2.0  # 4-6
    if aqi <= EPA_UNHEALTHY_MAX:
        return 6.0 + (aqi - EPA_UNHEALTHY_SENSITIVE_MAX) / (EPA_UNHEALTHY_MAX - EPA_UNHEALTHY_SENSITIVE_MAX) * 2.0  # 6-8
    if aqi <= EPA_VERY_UNHEALTHY_MAX:
        return 8.0 + (aqi - EPA_UNHEALTHY_MAX) / (EPA_VERY_UNHEALTHY_MAX - EPA_UNHEALTHY_MAX) * 1.5  # 8-9.5
    return min(10.0, 9.5 + (aqi - EPA_VERY_UNHEALTHY_MAX) / 100 * 0.5)  # 9.5-10: Hazardous


def _epa_category(aqi: float) -> str:
    if aqi <= EPA_GOOD_MAX:
        return "Good"
    if aqi <= EPA_MODERATE_MAX:
        return "Moderate"
    if aqi <= EPA_UNHEALTHY_SENSITIVE_MAX:
        return "Unhealthy (Sensitive)"
    if aqi <= EPA_UNHEALTHY_MAX:
        return "Unhealthy"
    if aqi <= EPA_VERY_UNHEALTHY_MAX:
        return "Very Unhealthy"
    return "Hazardous"


def score_air_quality(match_id: str) -> dict:
    match = get_match(match_id)
    venue = get_venue(match["venue_id"])
    air_quality = load_air_quality()
    row = air_quality[air_quality["match_id"] == match_id]
    if row.empty:
        raise ValueError(f"No air_quality.csv row for match_id: {match_id!r}")
    row = row.iloc[0]

    raw_risk = _risk_band(row["us_aqi"])
    multiplier = ROOF_RISK_MULTIPLIER.get(venue["roof_type"], 1.0)
    risk_score = round(raw_risk * multiplier, 1)
    category = _epa_category(row["us_aqi"])

    roof_note = (
        f", reduced from an open-air risk of {raw_risk:.1f} by the venue's {venue['roof_type']} roof"
        if multiplier < 1.0 else ""
    )
    reasoning = (
        f"{category} ({risk_score}/10) -- US AQI {row['us_aqi']:.0f} ({row['pm2_5']:.1f} µg/m³ PM2.5) "
        f"at kickoff ({row['data_type']}){roof_note}."
    )

    return {
        "match_id": match_id,
        "scorer": "air_quality",
        "scale": "risk",
        "score": risk_score,
        "label": f"{category} ({risk_score}/10)",
        "reasoning": reasoning,
        "details": {
            "us_aqi": row["us_aqi"],
            "pm2_5": row["pm2_5"],
            "epa_category": category,
            "roof_type": venue["roof_type"],
            "data_type": row["data_type"],
        },
    }
