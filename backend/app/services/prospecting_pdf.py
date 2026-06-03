"""
Consultant-style regional prospecting report PDF generator for CHITTA.

Reuses layout helpers and constants from pdf_export.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.api.schemas import ProspectingResponse, SimulationResponse, SynthesisResponse
from app.services.pdf_export import (
    ACCENT,
    DISCLAIMER,
    LIGHT_BG,
    MUTED,
    _bullet_list,
    _esc,
    _fmt_score,
    _section_heading,
)
from app.services.methodology import SCORING_FORMULA_VERSION

PROSPECTING_DISCLAIMER = (
    "Candidate scores are preliminary screening results produced by deterministic "
    "heuristics. Top-ranked sites require on-site wind measurement, geotechnical "
    "survey, and permitting review before any investment or development decision."
)

_BORDER = colors.HexColor("#cbd5e1")
_DARK = colors.HexColor("#0f172a")


# ── Shared style factory ────────────────────────────────────────────────────────

def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "PTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=ACCENT,
            spaceAfter=6,
        ),
        "Subtitle": ParagraphStyle(
            "PSubtitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=MUTED,
            spaceAfter=4,
        ),
        "SectionHeading": ParagraphStyle(
            "PSectionHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=_DARK,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "PBody",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
        ),
        "Small": ParagraphStyle(
            "PSmall",
            parent=base["Normal"],
            fontSize=8,
            leading=11,
            textColor=MUTED,
        ),
        "Disclaimer": ParagraphStyle(
            "PDisclaimer",
            parent=base["Normal"],
            fontSize=8,
            leading=11,
            textColor=MUTED,
            backColor=colors.HexColor("#f8fafc"),
            borderPadding=8,
        ),
        "Badge": ParagraphStyle(
            "PBadge",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=ACCENT,
            spaceAfter=4,
        ),
    }


# ── Table helpers ──────────────────────────────────────────────────────────────

def _meta_table(rows: list[list[str]], col_widths: list[float] | None = None) -> Table:
    widths = col_widths or [1.6 * inch, 4.9 * inch]
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _candidate_table(rows: list[list[str]]) -> Table:
    # 10 columns, total ~7"
    col_widths = [
        0.40 * inch,  # Rank
        0.50 * inch,  # Score
        0.65 * inch,  # Decision
        0.50 * inch,  # Wind
        0.50 * inch,  # Terrain
        0.50 * inch,  # Infra
        0.55 * inch,  # CF
        0.60 * inch,  # LCOE
        0.65 * inch,  # Payback
        1.15 * inch,  # Coords
    ]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 0), (7, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _cluster_table(rows: list[list[str]]) -> Table:
    col_widths = [2.0 * inch, 0.65 * inch, 0.75 * inch, 0.75 * inch, 2.35 * inch]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _ranking_changes_table(rows: list[list[str]]) -> Table:
    col_widths = [0.55 * inch, 0.85 * inch, 5.10 * inch]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ── Cover page ─────────────────────────────────────────────────────────────────

def _cover_page(
    prospecting: ProspectingResponse,
    simulation: SimulationResponse | None,
    synthesis: SynthesisResponse | None,
    styles: dict[str, ParagraphStyle],
    ts: str,
) -> list[Any]:
    region = prospecting.region
    region_name = str(region.get("name", "Custom Region"))
    lat = region.get("centerLatitude", 0)
    lng = region.get("centerLongitude", 0)
    radius = region.get("radiusKm", 0)
    grid = region.get("gridSize", 0)

    story: list[Any] = [
        Spacer(1, 40),
        Paragraph("CHITTA Regional Prospecting Report", styles["Title"]),
        Paragraph(
            "Climate Heuristics &amp; Intelligent Turbine Terrain Analysis",
            styles["Subtitle"],
        ),
        Spacer(1, 20),
        HRFlowable(width="100%", thickness=2, color=ACCENT),
        Spacer(1, 20),
        Paragraph(f"<b>Region:</b> {_esc(region_name)}", styles["Body"]),
        Paragraph(
            f"<b>Centre:</b> {lat:.4f}°, {lng:.4f}° &nbsp;|&nbsp; "
            f"<b>Radius:</b> {radius:.0f} km &nbsp;|&nbsp; "
            f"<b>Grid:</b> {grid}×{grid}",
            styles["Body"],
        ),
        Spacer(1, 12),
        Paragraph(f"<b>Candidates screened:</b> {prospecting.candidateCount}", styles["Body"]),
        Paragraph(f"<b>Fully enriched:</b> {prospecting.enrichedCount}", styles["Body"]),
        Paragraph(f"<b>Zones identified:</b> {len(prospecting.clusters)}", styles["Body"]),
        Spacer(1, 12),
    ]

    if synthesis:
        story.append(Paragraph(
            "AI synthesis: included",
            ParagraphStyle("CoverBadge", parent=styles["Small"], textColor=ACCENT),
        ))
    if simulation:
        story.append(Paragraph(
            "Scenario simulation: included",
            ParagraphStyle("CoverBadge2", parent=styles["Small"], textColor=MUTED),
        ))

    story += [
        Spacer(1, 40),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")),
        Spacer(1, 8),
        Paragraph(f"<b>Generated:</b> {_esc(ts)}", styles["Small"]),
        Paragraph(f"<b>Prospecting ID:</b> {_esc(prospecting.prospectingId)}", styles["Small"]),
        Paragraph(f"<b>Formula version:</b> CHITTA v{SCORING_FORMULA_VERSION}", styles["Small"]),
        PageBreak(),
    ]
    return story


# ── Section builders ───────────────────────────────────────────────────────────

def _executive_summary_section(
    prospecting: ProspectingResponse,
    synthesis: SynthesisResponse | None,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = _section_heading("Executive Summary", styles)

    if synthesis:
        n = synthesis.narrative
        story.append(Paragraph(_esc(n.executiveSummary), styles["Body"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph(_esc(n.strategicAssessment), styles["Body"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"<i>AI-generated from deterministic CHITTA evidence · "
            f"{_esc(synthesis.provider)} / {_esc(synthesis.model)}</i>",
            styles["Small"],
        ))
    else:
        region_name = str(prospecting.region.get("name", "the region"))
        story.append(Paragraph(
            f"This prospecting run screened {prospecting.candidateCount} candidate sites "
            f"across {_esc(region_name)}, of which {prospecting.enrichedCount} received "
            f"full enriched analysis. {len(prospecting.clusters)} corridor zones were identified.",
            styles["Body"],
        ))
        if prospecting.clusters:
            top_cl = prospecting.clusters[0]
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                f"Leading zone: <b>{_esc(top_cl.label)}</b> — "
                f"{top_cl.candidateCount} sites, avg score {top_cl.averageSuitability:.1f}/100, "
                f"top decision: {_esc(top_cl.topDecision)}.",
                styles["Body"],
            ))

    story.append(Spacer(1, 8))
    return story


def _regional_overview_section(
    prospecting: ProspectingResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = _section_heading("Regional Overview", styles)
    region = prospecting.region
    rows = [
        ["Field", "Value"],
        ["Region name", str(region.get("name", "Custom"))],
        ["Centre coordinates", f"{region.get('centerLatitude', 0):.4f}°, {region.get('centerLongitude', 0):.4f}°"],
        ["Search radius", f"{region.get('radiusKm', 0):.0f} km"],
        ["Grid size", f"{region.get('gridSize', 0)}×{region.get('gridSize', 0)}"],
        ["Candidates screened", str(prospecting.candidateCount)],
        ["Fully enriched", str(prospecting.enrichedCount)],
        ["Zones identified", str(len(prospecting.clusters))],
        ["Generated at", _esc(prospecting.generatedAt)],
        ["Prospecting ID", _esc(prospecting.prospectingId)],
    ]
    story.append(_meta_table(rows))
    story.append(Spacer(1, 8))
    return story


def _methodology_section(
    prospecting: ProspectingResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = _section_heading("Prospecting Methodology", styles)
    story += _bullet_list(prospecting.auditTrail, styles["Body"])
    story.append(Spacer(1, 6))
    if prospecting.methodology:
        meth_rows = [["Parameter", "Value"]] + [
            [_esc(k), _esc(v)] for k, v in prospecting.methodology.items()
        ]
        story.append(_meta_table(meth_rows))
        story.append(Spacer(1, 8))
    return story


def _cluster_section(
    prospecting: ProspectingResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    if not prospecting.clusters:
        return []
    story: list[Any] = _section_heading("Corridor Cluster Summary", styles)
    cluster_rows: list[list[str]] = [["Zone", "Sites", "Avg Score", "Top Decision", "Summary"]]
    for cl in prospecting.clusters:
        cluster_rows.append([
            _esc(cl.label),
            str(cl.candidateCount),
            f"{cl.averageSuitability:.1f}",
            _esc(cl.topDecision),
            _esc(cl.summary[:80] + "…" if len(cl.summary) > 80 else cl.summary),
        ])
    story.append(_cluster_table(cluster_rows))
    story.append(Spacer(1, 8))
    return story


def _candidate_rankings_section(
    prospecting: ProspectingResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    candidates = prospecting.topCandidates[:10]
    if not candidates:
        return []
    story: list[Any] = _section_heading("Top Candidate Rankings", styles)
    story.append(Paragraph(
        "Showing fully enriched candidates ranked by total suitability score.",
        styles["Small"],
    ))
    story.append(Spacer(1, 4))

    rows: list[list[str]] = [[
        "Rank", "Score", "Decision", "Wind", "Terrain", "Infra", "CF", "LCOE", "Payback", "Coords",
    ]]
    for i, c in enumerate(candidates, 1):
        cf_str = f"{c.capacityFactor * 100:.0f}%" if c.capacityFactor is not None else "—"
        lcoe_str = f"${c.lcoeUsdPerMwh:.0f}" if c.lcoeUsdPerMwh is not None else "—"
        payback_str = f"{c.paybackYears:.0f}yr" if c.paybackYears is not None else "—"
        rows.append([
            f"#{i}",
            _fmt_score(c.totalSuitability),
            _esc(c.finalDecision or "—"),
            _fmt_score(c.windScore),
            _fmt_score(c.terrainScore),
            _fmt_score(c.infrastructureScore),
            cf_str,
            lcoe_str,
            payback_str,
            f"{c.latitude:.3f}, {c.longitude:.3f}",
        ])
    story.append(_candidate_table(rows))
    story.append(Spacer(1, 8))
    return story


def _candidate_comparison_section(
    prospecting: ProspectingResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    candidates = prospecting.topCandidates[:5]
    if not candidates:
        return []
    story: list[Any] = _section_heading("Candidate Comparison: Strengths & Risks", styles)
    for i, c in enumerate(candidates, 1):
        story.append(Paragraph(
            f"<b>#{i} — {c.latitude:.3f}, {c.longitude:.3f} "
            f"(score: {_fmt_score(c.totalSuitability)}/100, {_esc(c.finalDecision or '—')})</b>",
            styles["Body"],
        ))
        if c.topStrengths:
            story += _bullet_list([f"[+] {s}" for s in c.topStrengths], styles["Small"])
        if c.topRisks:
            story += _bullet_list([f"[!] {r}" for r in c.topRisks], styles["Small"])
        story.append(Spacer(1, 6))
    return story


def _economic_section(
    prospecting: ProspectingResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    enriched = [c for c in prospecting.topCandidates if c.lcoeUsdPerMwh is not None]
    if not enriched:
        return []
    story: list[Any] = _section_heading("Economic Feasibility Summary", styles)
    story.append(Paragraph(
        "Preliminary estimates only — accuracy ±30–50% CAPEX, ±20–35% LCOE.",
        styles["Small"],
    ))
    story.append(Spacer(1, 4))

    eco_rows: list[list[str]] = [["Rank", "LCOE ($/MWh)", "Payback (yr)", "CF", "AEP (MWh/yr)", "Coords"]]
    lcoes: list[float] = []
    for i, c in enumerate(enriched[:8], 1):
        lcoe = c.lcoeUsdPerMwh
        if lcoe is not None:
            lcoes.append(lcoe)
        eco_rows.append([
            f"#{i}",
            f"${lcoe:.0f}" if lcoe is not None else "—",
            f"{c.paybackYears:.0f}" if c.paybackYears is not None else "—",
            f"{c.capacityFactor * 100:.0f}%" if c.capacityFactor is not None else "—",
            f"{c.annualEnergyMwh:,.0f}" if c.annualEnergyMwh is not None else "—",
            f"{c.latitude:.3f}, {c.longitude:.3f}",
        ])
    eco_table = Table(
        eco_rows,
        colWidths=[0.4 * inch, 0.9 * inch, 0.9 * inch, 0.6 * inch, 0.9 * inch, 3.3 * inch],
    )
    eco_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (4, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(eco_table)

    if lcoes:
        best = min(lcoes)
        worst = max(lcoes)
        avg = sum(lcoes) / len(lcoes)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"Best LCOE: ${best:.0f}/MWh &nbsp;|&nbsp; Avg: ${avg:.0f}/MWh &nbsp;|&nbsp; Highest: ${worst:.0f}/MWh",
            styles["Small"],
        ))

    story.append(Spacer(1, 8))
    return story


def _risks_section(
    prospecting: ProspectingResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = _section_heading("Environmental & Infrastructure Risks", styles)
    all_risks: list[str] = []
    seen: set[str] = set()
    for c in prospecting.topCandidates[:8]:
        for r in c.topRisks:
            if r not in seen:
                seen.add(r)
                all_risks.append(r)
    if all_risks:
        story += _bullet_list(all_risks[:12], styles["Body"])
    else:
        story.append(Paragraph("No specific risk flags surfaced from top candidates.", styles["Body"]))
    story.append(Spacer(1, 8))
    return story


def _ai_synthesis_section(
    synthesis: SynthesisResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    n = synthesis.narrative
    story: list[Any] = _section_heading("AI Strategic Assessment", styles)

    story.append(Paragraph(
        f"<i>AI-generated from deterministic CHITTA evidence · "
        f"{_esc(synthesis.provider)} / {_esc(synthesis.model)} · "
        f"{_esc(synthesis.synthesisId)}</i>",
        styles["Badge"],
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph(f"<b>Executive Summary</b>", styles["Body"]))
    story.append(Paragraph(_esc(n.executiveSummary), styles["Body"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph(f"<b>Strategic Assessment</b>", styles["Body"]))
    story.append(Paragraph(_esc(n.strategicAssessment), styles["Body"]))
    story.append(Spacer(1, 6))

    if n.strongestSignals:
        story.append(Paragraph("<b>Strongest signals:</b>", styles["Body"]))
        story += _bullet_list(n.strongestSignals, styles["Body"])

    if n.majorRisks:
        story.append(Paragraph("<b>Major risks:</b>", styles["Body"]))
        story += _bullet_list(n.majorRisks, styles["Body"])

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Economic assessment:</b>", styles["Body"]))
    story.append(Paragraph(_esc(n.economicNarrative), styles["Body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Recommendations:</b>", styles["Body"]))
    story += _bullet_list(n.recommendations, styles["Body"])

    if n.warnings:
        story.append(Spacer(1, 4))
        story += _bullet_list(n.warnings, styles["Disclaimer"])

    story.append(Spacer(1, 8))
    return story


def _simulation_section(
    simulation: SimulationResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = _section_heading("Simulation Sensitivity Findings", styles)
    cfg = simulation.config

    story.append(Paragraph("<b>Scenario configuration:</b>", styles["Body"]))
    cfg_rows = [
        ["Parameter", "Value"],
        ["Turbines", f"{cfg.turbineCount} × {cfg.turbineRatingMw} MW"],
        ["Electricity price", f"${cfg.electricityPriceUsdPerMwh}/MWh"],
        ["CAPEX", f"${cfg.capexUsdPerMw / 1e6:.2f}M/MW"],
        ["OPEX", f"{cfg.opexPercentOfCapex * 100:.0f}% of CAPEX/yr"],
        ["Project life", f"{cfg.projectLifeYears} years"],
        ["Environmental strictness", cfg.environmentalStrictness],
        ["Infrastructure preference", cfg.infrastructurePreference],
        ["Formula", simulation.methodology.get("formulaVersion", "sim-1.0")],
    ]
    story.append(_meta_table(cfg_rows))
    story.append(Spacer(1, 6))

    # Ranking changes
    changes = simulation.rankingChanges
    if changes:
        story.append(Paragraph(
            f"<b>Ranking changes ({len(changes)} candidates re-ranked):</b>",
            styles["Body"],
        ))
        rc_rows: list[list[str]] = [["Dir.", "Change", "Candidate (original rank → new rank)"]]
        for rc in changes[:15]:
            dir_sym = "↑" if rc.direction == "up" else ("↓" if rc.direction == "down" else "=")
            change_str = f"+{rc.rankChange}" if rc.rankChange > 0 else str(rc.rankChange)
            detail = (
                f"{rc.latitude:.3f}, {rc.longitude:.3f} — "
                f"#{rc.originalRank} → #{rc.newRank}"
            )
            rc_rows.append([dir_sym, change_str, detail])
        story.append(_ranking_changes_table(rc_rows))
        story.append(Spacer(1, 6))

    # Callouts
    callouts: list[str] = []
    if simulation.strongestCandidate:
        s = simulation.strongestCandidate
        callouts.append(
            f"Strongest post-simulation: {s.latitude:.3f}, {s.longitude:.3f} "
            f"— score {_fmt_score(s.newTotalSuitability)}/100, decision: {s.newDecision or '—'}"
        )
    if simulation.weakestCandidate:
        w = simulation.weakestCandidate
        callouts.append(
            f"Weakest post-simulation: {w.latitude:.3f}, {w.longitude:.3f} "
            f"— score {_fmt_score(w.newTotalSuitability)}/100"
        )
    if simulation.mostImprovedCandidate:
        mi = simulation.mostImprovedCandidate
        delta = mi.suitabilityDelta
        callouts.append(
            f"Most improved: {mi.latitude:.3f}, {mi.longitude:.3f} "
            f"— delta {'+' if (delta or 0) > 0 else ''}{delta:.1f} pts"
        )
    if simulation.mostSensitiveCandidate:
        ms = simulation.mostSensitiveCandidate
        delta = ms.suitabilityDelta
        callouts.append(
            f"Most sensitive: {ms.latitude:.3f}, {ms.longitude:.3f} "
            f"— |delta| {abs(delta or 0):.1f} pts"
        )
    if callouts:
        story += _bullet_list(callouts, styles["Body"])

    if simulation.auditTrail:
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Simulation audit trail:</b>", styles["Body"]))
        story += _bullet_list(simulation.auditTrail, styles["Small"])

    story.append(Spacer(1, 8))
    return story


def _methodology_audit_section(
    prospecting: ProspectingResponse,
    simulation: SimulationResponse | None,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = _section_heading("Methodology & Audit Trail", styles)
    story.append(Paragraph(f"<b>Prospecting ID:</b> {_esc(prospecting.prospectingId)}", styles["Body"]))
    story.append(Paragraph(f"<b>Generated:</b> {_esc(prospecting.generatedAt)}", styles["Body"]))
    story.append(Paragraph(f"<b>Formula version:</b> CHITTA v{SCORING_FORMULA_VERSION}", styles["Body"]))
    story.append(Spacer(1, 6))

    if prospecting.methodology:
        meth_rows = [["Parameter", "Value"]] + [
            [_esc(str(k)), _esc(str(v))] for k, v in prospecting.methodology.items()
        ]
        story.append(_meta_table(meth_rows))
        story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Audit trail:</b>", styles["Body"]))
    story += _bullet_list(prospecting.auditTrail, styles["Small"])

    if simulation:
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Simulation ID:</b> {_esc(simulation.simulationId)}", styles["Body"]))
        if simulation.methodology:
            sim_meth_rows = [["Parameter", "Value"]] + [
                [_esc(str(k)), _esc(str(v))] for k, v in simulation.methodology.items()
            ]
            story.append(_meta_table(sim_meth_rows))

    story.append(Spacer(1, 8))
    return story


def _data_sources_section(styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = _section_heading("Data Sources", styles)
    story += _bullet_list([
        "Wind: NASA POWER (WS10M / WS50M / WS100M) — 2014–2023 climatological means",
        "Elevation: OpenTopoData (SRTM 90m resolution)",
        "Infrastructure: OpenStreetMap via Overpass API",
        f"Scoring formula: CHITTA v{SCORING_FORMULA_VERSION} — 6-dimension weighted composite",
        "Economic estimates: CHITTA economics v1.0 — order-of-magnitude preliminary screening",
        "Land cover: ESA WorldCover proxy (heuristic classification)",
    ], styles["Body"])
    story.append(Spacer(1, 8))
    return story


def _disclaimer_section(styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = _section_heading("Limitations & Disclaimer", styles)
    story.append(Paragraph(_esc(PROSPECTING_DISCLAIMER), styles["Disclaimer"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(_esc(DISCLAIMER), styles["Disclaimer"]))
    story.append(Spacer(1, 8))
    return story


# ── Entry point ────────────────────────────────────────────────────────────────

def generate_prospecting_report_pdf(
    prospecting: ProspectingResponse,
    simulation: SimulationResponse | None = None,
    synthesis: SynthesisResponse | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="CHITTA Regional Prospecting Report",
    )

    styles = _build_styles()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story: list[Any] = []
    story += _cover_page(prospecting, simulation, synthesis, styles, ts)
    story += _executive_summary_section(prospecting, synthesis, styles)
    story += _regional_overview_section(prospecting, styles)
    story += _methodology_section(prospecting, styles)
    story += _cluster_section(prospecting, styles)
    story += _candidate_rankings_section(prospecting, styles)
    story += _candidate_comparison_section(prospecting, styles)
    story += _economic_section(prospecting, styles)
    story += _risks_section(prospecting, styles)

    if synthesis:
        story += _ai_synthesis_section(synthesis, styles)

    if simulation:
        story += _simulation_section(simulation, styles)

    story += _methodology_audit_section(prospecting, simulation, styles)
    story += _data_sources_section(styles)
    story += _disclaimer_section(styles)

    doc.build(story)
    return buffer.getvalue()
