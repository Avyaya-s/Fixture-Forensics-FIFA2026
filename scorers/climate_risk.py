"""Climate risk scorer.

Grounded in published FIFA and FIFPro heat-safety policy, both stated in
WBGT (Wet Bulb Globe Temperature), not air temperature alone:
  - FIFA: voluntary cooling breaks from 27C WBGT; mandatory 3-minute cooling
    breaks at 32C WBGT and above.
  - FIFPro (more conservative): cooling breaks from 26C WBGT; postponement or
    suspension considered from 28C WBGT. FIFA and FIFPro have not reconciled
    these two thresholds as of 2026.
Roof type then adjusts the effective risk down, since closed/retractable
roofs are assumed to be used with climate control for hot-weather fixtures.

WBGT is approximated from temp_c + humidity_pct via the Australian Bureau of
Meteorology's simplified "WBGT (shade)" formula. This is a documented
simplification: it omits the solar-radiation/globe-temperature term (Open-
Meteo's hourly archive doesn't provide shortwave radiation), so it reads
lower than the true on-pitch WBGT a player in direct sun would experience.

NOTE ON SCALE: unlike the other scorers, this one reports on a *risk* scale
(0-10, higher = worse/riskier), because "risk" is the more intuitive framing
for climate. The aggregator (scorers/aggregate.py) inverts it
(goodness = 10 - risk_score) before combining with the other "goodness"
scorers.
"""
from scorers.data_loader import get_match, get_venue, load_climate

ROOF_RISK_MULTIPLIER = {
    "open": 1.0,
    "retractable": 0.3,
    "fixed_closed": 0.15,
}

# Published WBGT thresholds this scorer's bands are anchored to.
FIFPRO_COOLING_BREAK_C = 26.0
FIFA_VOLUNTARY_COOLING_BREAK_C = 27.0
FIFPRO_POSTPONEMENT_CONSIDERATION_C = 28.0
FIFA_MANDATORY_COOLING_BREAK_C = 32.0


def _vapor_pressure_hpa(temp_c: float, humidity_pct: float) -> float:
    """Actual water vapor pressure (hPa) via the Tetens saturation-vapor-pressure formula."""
    saturation_hpa = 6.1078 * 10 ** (7.5 * temp_c / (237.3 + temp_c))
    return saturation_hpa * (humidity_pct / 100)


def _wbgt_c(temp_c: float, humidity_pct: float) -> float:
    """Approximate WBGT in shade (Australian Bureau of Meteorology formula):
    WBGT = 0.567*Ta + 0.393*e + 3.94, where e is vapor pressure in hPa.
    """
    e = _vapor_pressure_hpa(temp_c, humidity_pct)
    return 0.567 * temp_c + 0.393 * e + 3.94


def _risk_band(wbgt: float) -> float:
    if wbgt < FIFPRO_COOLING_BREAK_C:
        return max(0.0, (wbgt / FIFPRO_COOLING_BREAK_C) * 3.0)  # 0-3: below any published threshold
    if wbgt < FIFA_VOLUNTARY_COOLING_BREAK_C:
        return 3.0 + (wbgt - FIFPRO_COOLING_BREAK_C) * 1.0  # 3-4: FIFPro cooling-break zone
    if wbgt < FIFPRO_POSTPONEMENT_CONSIDERATION_C:
        return 4.0 + (wbgt - FIFA_VOLUNTARY_COOLING_BREAK_C) * 1.0  # 4-5: FIFA voluntary cooling-break zone
    if wbgt < FIFA_MANDATORY_COOLING_BREAK_C:
        return 5.0 + (wbgt - FIFPRO_POSTPONEMENT_CONSIDERATION_C) / 4 * 3.0  # 5-8: FIFPro postponement zone
    return min(10.0, 8.0 + (wbgt - FIFA_MANDATORY_COOLING_BREAK_C) / 5 * 2.0)  # 8-10: FIFA mandatory zone


def _threshold_note(wbgt: float) -> str:
    if wbgt >= FIFA_MANDATORY_COOLING_BREAK_C:
        return f"exceeds FIFA's mandatory cooling-break threshold ({FIFA_MANDATORY_COOLING_BREAK_C:.0f}°C WBGT)"
    if wbgt >= FIFPRO_POSTPONEMENT_CONSIDERATION_C:
        return f"in FIFPro's postponement-consideration zone (>={FIFPRO_POSTPONEMENT_CONSIDERATION_C:.0f}°C WBGT)"
    if wbgt >= FIFA_VOLUNTARY_COOLING_BREAK_C:
        return f"crosses FIFA's voluntary cooling-break threshold ({FIFA_VOLUNTARY_COOLING_BREAK_C:.0f}°C WBGT)"
    if wbgt >= FIFPRO_COOLING_BREAK_C:
        return f"crosses FIFPro's cooling-break threshold ({FIFPRO_COOLING_BREAK_C:.0f}°C WBGT)"
    return "below all published cooling-break thresholds"


def score_climate_risk(match_id: str) -> dict:
    match = get_match(match_id)
    venue = get_venue(match["venue_id"])
    climate = load_climate()
    row = climate[climate["match_id"] == match_id]
    if row.empty:
        raise ValueError(f"No climate.csv row for match_id: {match_id!r}")
    row = row.iloc[0]

    wbgt = _wbgt_c(row["temp_c"], row["humidity_pct"])
    raw_risk = _risk_band(wbgt)
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
        f"{band} risk ({risk_score}/10) -- {wbgt:.1f}°C WBGT ({row['temp_c']:.0f}°C air, "
        f"{row['humidity_pct']:.0f}% humidity) at kickoff ({row['data_type']}), {_threshold_note(wbgt)}"
        f"{roof_note}."
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
            "wbgt_c": round(wbgt, 1),
            "roof_type": venue["roof_type"],
            "data_type": row["data_type"],
        },
    }
