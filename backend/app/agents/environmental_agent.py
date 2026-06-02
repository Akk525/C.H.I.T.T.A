from __future__ import annotations

from app.agents.base import AgentContext, AgentEvidence, AgentOutput


_COVER_LABELS: dict[str, str] = {
    "barren": "Barren / bare land",
    "grassland": "Grassland",
    "shrubland": "Shrubland / heath",
    "cropland": "Agricultural / cropland",
    "forest": "Forest / woodland",
    "wetland": "Wetland",
    "urban": "Urban / residential",
}


class EnvironmentalAgent:
    def run(self, ctx: AgentContext) -> AgentOutput:
        lc_data = ctx.enriched.get("land_cover")
        pa_data = ctx.enriched.get("protected_area")
        env_score = ctx.env_score
        lc_score = ctx.lc_score
        pa_score = ctx.pa_score

        has_lc = lc_data is not None
        has_pa = pa_data is not None

        if has_lc and has_pa:
            status = "complete"
            confidence = 72.0
        elif has_lc or has_pa:
            status = "partial"
            confidence = 50.0
        else:
            status = "fallback"
            confidence = 10.0

        findings: list[str] = []
        risks: list[str] = []
        recs: list[str] = []
        evidence: list[AgentEvidence] = []

        if status == "fallback":
            summary = "Environmental data unavailable — land cover and protected area proximity cannot be assessed."
            risks.append(
                "No land cover or protected area data — permitting risk is unquantified."
            )
            recs.append(
                "Obtain WDPA protected area boundaries and ESA WorldCover land classification for this site."
            )
            return AgentOutput(
                agentName="Environmental",
                status=status,
                confidence=confidence,
                summary=summary,
                findings=findings,
                risks=risks,
                recommendations=recs,
                evidence=evidence,
            )

        # Land cover
        cover_class = lc_data.get("cover_class") if lc_data else None
        permitting_risk = lc_data.get("permitting_risk", "medium") if lc_data else "medium"

        if cover_class in {"barren", "grassland", "shrubland"}:
            findings.append(
                f"{_COVER_LABELS.get(cover_class, cover_class)} detected — favourable land cover with minimal clearing or ecological impact expected."
            )
        elif cover_class == "cropland":
            risks.append(
                "Agricultural land — land acquisition negotiations and crop compensation agreements will be required."
            )
        elif cover_class == "forest":
            risks.append(
                "Forest cover detected — high ecological sensitivity; environmental impact assessment and likely forest clearance permit required."
            )
        elif cover_class == "wetland":
            risks.append(
                "Wetland detected — development strongly constrained; mitigation measures or site redesign likely required."
            )
        elif cover_class == "urban":
            risks.append(
                "Urban land cover — wind energy development is highly constrained; noise, shadow flicker, and zoning conflicts are likely."
            )
        elif cover_class is None:
            risks.append(
                "Land cover class could not be determined from OSM data — verify using satellite imagery or national land use maps."
            )

        # Protected areas
        in_pa = pa_data.get("in_protected_area", False) if pa_data else False
        nearest_pa_m = pa_data.get("nearest_pa_m") if pa_data else None
        nearest_pa_name = pa_data.get("nearest_pa_name") if pa_data else None
        bio_risk = pa_data.get("biodiversity_risk", "unknown") if pa_data else "unknown"

        if in_pa:
            risks.append(
                f"Site overlaps a mapped protected area ({nearest_pa_name or 'unnamed'}) — development is almost certainly prohibited without special dispensation."
            )
        elif nearest_pa_m is not None and nearest_pa_m < 5_000:
            pa_km = nearest_pa_m / 1000
            risks.append(
                f"Protected area '{nearest_pa_name or 'unnamed'}' is {pa_km:.1f} km away — heightened regulatory scrutiny and buffer zone analysis needed."
            )
        elif nearest_pa_m is not None and nearest_pa_m < 15_000:
            pa_km = nearest_pa_m / 1000
            risks.append(
                f"Protected area '{nearest_pa_name or 'unnamed'}' is {pa_km:.1f} km away — include in environmental impact assessment."
            )
        elif has_pa:
            findings.append(
                "No protected areas within 25km of the site — ecological constraint from designated zones is low."
            )

        # Summary
        if env_score is not None:
            if env_score >= 70:
                summary = "Favourable environmental profile — low permitting risk from land cover and protected area proximity."
            elif env_score >= 45:
                summary = "Moderate environmental constraints — permitting pathway is possible but requires careful assessment."
            else:
                summary = "Significant environmental constraints — land cover or protected area proximity will challenge permitting."
        else:
            summary = "Environmental profile assessed from OSM land cover and protected area data."

        # Evidence
        if cover_class:
            evidence.append(AgentEvidence("Land cover class", _COVER_LABELS.get(cover_class, cover_class), "OpenStreetMap"))
        if permitting_risk:
            evidence.append(AgentEvidence("Permitting risk (land cover)", permitting_risk, "CHITTA model"))
        if nearest_pa_m is not None:
            evidence.append(AgentEvidence("Nearest protected area", f"{nearest_pa_m / 1000:.1f} km", "OpenStreetMap"))
        if nearest_pa_name:
            evidence.append(AgentEvidence("Protected area name", nearest_pa_name, "OpenStreetMap"))
        if bio_risk and bio_risk != "unknown":
            evidence.append(AgentEvidence("Biodiversity risk", bio_risk, "CHITTA model"))
        if env_score is not None:
            evidence.append(AgentEvidence("Environmental score", f"{env_score:.0f}/100", "CHITTA model"))

        recs.append(
            "Cross-reference with WDPA (Protected Planet) for authoritative protected area boundaries."
        )
        if cover_class in {"forest", "wetland"}:
            recs.append(
                "Commission a full ecological survey and seek pre-application advice from the environmental regulator."
            )
        elif bio_risk in {"high", "medium"}:
            recs.append(
                "Engage an ecologist early to assess impacts on biodiversity and determine mitigation requirements."
            )

        return AgentOutput(
            agentName="Environmental",
            status=status,
            confidence=confidence,
            summary=summary,
            findings=findings,
            risks=risks,
            recommendations=recs,
            evidence=evidence,
        )
