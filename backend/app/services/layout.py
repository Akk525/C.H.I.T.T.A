"""
Simplified wind turbine layout planner for CHITTA.

Generates a wind-aligned candidate turbine grid and estimates wake losses
using a simplified Jensen/Park model. All outputs are preliminary screening
only — not suitable for engineering design, permitting, or investment decisions.

Wake model: Jensen 1983 (top-hat, single-wake), with RSS superposition for
multiple upstream wakes (Katic et al. 1986 approach).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.services.methodology import generate_analysis_id, utc_now_iso

LAYOUT_MODEL_VERSION = "1.0"
WAKE_MODEL_LABEL = "Jensen/Park top-hat (simplified)"
MIN_SAFE_SPACING_ROTOR_DIAMETERS = 3.0
WAKE_HALF_ANGLE_DEG = 7.0


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class TurbinePosition:
    id: str
    latitude: float
    longitude: float


@dataclass
class LayoutAssumptions:
    rotor_diameter_m: float = 120.0
    turbine_rating_mw: float = 3.0
    crosswind_spacing_rotor_diameters: float = 5.0
    downwind_spacing_rotor_diameters: float = 7.0
    prevailing_wind_direction_deg: float = 270.0  # meteorological: direction wind comes FROM
    wake_decay_constant: float = 0.06             # Jensen k, typical onshore
    thrust_coefficient: float = 0.80              # Ct at rated operation


@dataclass
class LayoutResult:
    layout_id: str
    turbines: list[TurbinePosition]
    spacing_violations: int
    estimated_wake_loss_percent: float
    layout_efficiency_score: float
    assumptions: LayoutAssumptions
    warnings: list[str]
    methodology: dict[str, str]
    audit_trail: list[str]
    generated_at: str


# ── Internal helpers ───────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2.0 * R * math.asin(math.sqrt(a))


def _bearing_deg(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lng2 - lng1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def _relative_position(
    a: TurbinePosition,
    b: TurbinePosition,
    dw_east: float,
    dw_north: float,
    cw_east: float,
    cw_north: float,
) -> tuple[float, float]:
    """Return (downwind_m, crosswind_m) of B relative to A."""
    dist_m = _haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)
    if dist_m < 1.0:
        return 0.0, 0.0
    bearing_rad = math.radians(_bearing_deg(a.latitude, a.longitude, b.latitude, b.longitude))
    east_m = dist_m * math.sin(bearing_rad)
    north_m = dist_m * math.cos(bearing_rad)
    downwind_m = east_m * dw_east + north_m * dw_north
    crosswind_m = east_m * cw_east + north_m * cw_north
    return downwind_m, crosswind_m


# ── Layout generation ──────────────────────────────────────────────────────────

def _place_turbines(
    center_lat: float,
    center_lng: float,
    turbine_count: int,
    assumptions: LayoutAssumptions,
) -> list[TurbinePosition]:
    D = assumptions.rotor_diameter_m
    crosswind_spacing_m = assumptions.crosswind_spacing_rotor_diameters * D
    downwind_spacing_m = assumptions.downwind_spacing_rotor_diameters * D

    cols = math.ceil(math.sqrt(turbine_count))
    rows = math.ceil(turbine_count / cols)

    # Prevailing wind FROM direction → direction wind travels TO
    wind_to_rad = math.radians((assumptions.prevailing_wind_direction_deg + 180.0) % 360.0)

    # Downwind unit vector (E, N components)
    dw_east = math.sin(wind_to_rad)
    dw_north = math.cos(wind_to_rad)
    # Crosswind unit vector (90° clockwise from downwind)
    cw_east = math.cos(wind_to_rad)
    cw_north = -math.sin(wind_to_rad)

    lat_rad = math.radians(center_lat)
    m_per_deg_lat = 111_111.0
    m_per_deg_lng = 111_111.0 * math.cos(lat_rad)

    turbines: list[TurbinePosition] = []
    count = 0
    for row in range(rows):
        for col in range(cols):
            if count >= turbine_count:
                break
            col_off = col - (cols - 1) / 2.0
            row_off = row - (rows - 1) / 2.0
            east_m = col_off * crosswind_spacing_m * cw_east + row_off * downwind_spacing_m * dw_east
            north_m = col_off * crosswind_spacing_m * cw_north + row_off * downwind_spacing_m * dw_north
            turbines.append(TurbinePosition(
                id=f"T{count + 1:02d}",
                latitude=center_lat + north_m / m_per_deg_lat,
                longitude=center_lng + east_m / m_per_deg_lng,
            ))
            count += 1
        if count >= turbine_count:
            break

    return turbines


# ── Spacing violation detection ────────────────────────────────────────────────

def estimate_spacing_violations(
    turbines: list[TurbinePosition],
    rotor_diameter_m: float,
) -> int:
    min_m = MIN_SAFE_SPACING_ROTOR_DIAMETERS * rotor_diameter_m
    violations = 0
    for i in range(len(turbines)):
        for j in range(i + 1, len(turbines)):
            if _haversine_m(
                turbines[i].latitude, turbines[i].longitude,
                turbines[j].latitude, turbines[j].longitude,
            ) < min_m:
                violations += 1
    return violations


# ── Wake loss estimation (Jensen/Park) ────────────────────────────────────────

def estimate_wake_loss_percent(
    turbines: list[TurbinePosition],
    assumptions: LayoutAssumptions,
) -> float:
    if len(turbines) <= 1:
        return 0.0

    D = assumptions.rotor_diameter_m
    k = assumptions.wake_decay_constant
    Ct = assumptions.thrust_coefficient

    wind_to_rad = math.radians((assumptions.prevailing_wind_direction_deg + 180.0) % 360.0)
    dw_east = math.sin(wind_to_rad)
    dw_north = math.cos(wind_to_rad)
    cw_east = math.cos(wind_to_rad)
    cw_north = -math.sin(wind_to_rad)

    # For each turbine, accumulate squared deficits from upstream wakers (RSS)
    per_turbine_power_deficit: list[float] = []

    for b_idx, B in enumerate(turbines):
        sum_sq_deficit = 0.0
        for a_idx, A in enumerate(turbines):
            if a_idx == b_idx:
                continue
            downwind_m, crosswind_m = _relative_position(A, B, dw_east, dw_north, cw_east, cw_north)
            if downwind_m <= 0:
                continue  # B is not downwind of A
            # Wake cone radius at B's downwind distance
            r_wake = D / 2.0 + k * downwind_m
            if abs(crosswind_m) >= r_wake:
                continue  # B outside wake cone
            # Velocity deficit from A (Jensen formula)
            deficit = (1.0 - math.sqrt(max(0.0, 1.0 - Ct))) * (D / (D + 2.0 * k * downwind_m)) ** 2
            sum_sq_deficit += deficit ** 2

        # RSS total velocity deficit
        total_vel_deficit = math.sqrt(sum_sq_deficit)
        # Power deficit: P ∝ U³  →  P_loss/P_free = 1 - (1 - ΔU/U)³
        power_deficit = 1.0 - (max(0.0, 1.0 - total_vel_deficit)) ** 3
        per_turbine_power_deficit.append(power_deficit)

    if not per_turbine_power_deficit:
        return 0.0

    mean_loss = sum(per_turbine_power_deficit) / len(per_turbine_power_deficit)
    return round(mean_loss * 100.0, 2)


# ── Efficiency score ───────────────────────────────────────────────────────────

def compute_layout_efficiency_score(
    wake_loss_percent: float,
    spacing_violations: int,
) -> float:
    # Coefficient 2.0 gives a meaningful score range for typical farms (5-30% wake loss)
    score = 100.0 - wake_loss_percent * 2.0 - spacing_violations * 3.0
    return round(max(0.0, min(100.0, score)), 1)


# ── Entry point ────────────────────────────────────────────────────────────────

def generate_candidate_layout(
    center_lat: float,
    center_lng: float,
    turbine_count: int,
    assumptions: LayoutAssumptions,
    wind_direction_was_defaulted: bool = False,
) -> LayoutResult:
    layout_id = generate_analysis_id()
    generated_at = utc_now_iso()

    turbines = _place_turbines(center_lat, center_lng, turbine_count, assumptions)
    violations = estimate_spacing_violations(turbines, assumptions.rotor_diameter_m)
    wake_loss = estimate_wake_loss_percent(turbines, assumptions)
    efficiency = compute_layout_efficiency_score(wake_loss, violations)

    warnings: list[str] = []
    if wind_direction_was_defaulted:
        warnings.append(
            "Prevailing wind direction not provided — defaulted to 270° (westerly). "
            "Provide a site-specific direction for a more accurate layout."
        )
    if turbine_count > 30:
        warnings.append(
            f"Large layout ({turbine_count} turbines) — screening accuracy degrades for "
            "arrays beyond ~30 turbines. Results are indicative only."
        )
    if violations > 0:
        warnings.append(
            f"{violations} spacing violation(s) detected — turbine pairs closer than "
            f"{MIN_SAFE_SPACING_ROTOR_DIAMETERS:.0f}D minimum. "
            "Consider reducing turbine count or increasing rotor diameter spacing."
        )
    warnings.append(
        "Wake loss is estimated for the single prevailing wind direction only — "
        "multi-directional analysis would typically yield lower average farm losses."
    )
    warnings.append(
        "Layout is preliminary screening only. Not suitable for engineering design, "
        "permitting, noise/shadow analysis, or investment decisions."
    )

    D = assumptions.rotor_diameter_m
    assumptions_dict = {
        "rotorDiameterM": f"{D:.0f} m",
        "turbineRatingMw": f"{assumptions.turbine_rating_mw:.1f} MW",
        "crosswindSpacing": f"{assumptions.crosswind_spacing_rotor_diameters:.1f}D ({assumptions.crosswind_spacing_rotor_diameters * D:.0f} m)",
        "downwindSpacing": f"{assumptions.downwind_spacing_rotor_diameters:.1f}D ({assumptions.downwind_spacing_rotor_diameters * D:.0f} m)",
        "prevailingWindFrom": f"{assumptions.prevailing_wind_direction_deg:.0f}° {'(defaulted)' if wind_direction_was_defaulted else '(provided)'}",
        "wakeDecayConstant": str(assumptions.wake_decay_constant),
        "thrustCoefficient": str(assumptions.thrust_coefficient),
        "minSafeSpacing": f"{MIN_SAFE_SPACING_ROTOR_DIAMETERS:.0f}D ({MIN_SAFE_SPACING_ROTOR_DIAMETERS * D:.0f} m)",
    }

    methodology = {
        "layoutModel": f"Wind-aligned rectangular grid (CHITTA layout v{LAYOUT_MODEL_VERSION})",
        "wakeModel": WAKE_MODEL_LABEL,
        "wakeFormula": "ΔU/U₀ = (1 − √(1−Cₜ)) × (D / (D + 2k·x))² ; RSS superposition for multiple wakes",
        "efficiencyFormula": "100 − wake_loss% × 4 − violations × 3 (clamped 0–100)",
        "gridAlignment": "Columns = crosswind axis; rows = downwind axis; centred on site",
        "coordinateConversion": "Approximate flat-Earth (Δlat = Δnorth/111111, Δlng = Δeast/(111111·cos(lat)))",
        "formulaVersion": LAYOUT_MODEL_VERSION,
    }

    cols = math.ceil(math.sqrt(turbine_count))
    rows = math.ceil(turbine_count / cols)
    audit_trail = [
        f"Layout ID: {layout_id}",
        f"Generated: {generated_at}",
        f"Site: {center_lat:.5f}, {center_lng:.5f}",
        f"Turbines requested: {turbine_count} → grid {rows}×{cols} = {len(turbines)} placed",
        f"Prevailing wind FROM {assumptions.prevailing_wind_direction_deg:.0f}°",
        f"Crosswind spacing: {assumptions.crosswind_spacing_rotor_diameters:.1f}D = {assumptions.crosswind_spacing_rotor_diameters * D:.0f} m",
        f"Downwind spacing: {assumptions.downwind_spacing_rotor_diameters:.1f}D = {assumptions.downwind_spacing_rotor_diameters * D:.0f} m",
        f"Spacing violations: {violations}",
        f"Estimated wake loss: {wake_loss:.1f}%",
        f"Layout efficiency score: {efficiency:.1f}/100",
        f"Wake model: {WAKE_MODEL_LABEL} (k={assumptions.wake_decay_constant}, Cₜ={assumptions.thrust_coefficient})",
    ]

    return LayoutResult(
        layout_id=layout_id,
        turbines=turbines,
        spacing_violations=violations,
        estimated_wake_loss_percent=wake_loss,
        layout_efficiency_score=efficiency,
        assumptions=assumptions,
        warnings=warnings,
        methodology=methodology,
        audit_trail=audit_trail,
        generated_at=generated_at,
    )
