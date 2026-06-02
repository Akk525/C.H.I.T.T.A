/**
 * Client-side economic feasibility calculations for CHITTA.
 * Mirrors the Python formulas in backend/app/services/economics.py.
 * All values are preliminary screening estimates — not investment-grade.
 */

export type LocalEconomicInputs = {
  turbineRatingMw: number;
  turbineCount: number;
  electricityPriceUsdPerMwh: number;
  capexUsdPerMw: number;
  opexPctOfCapex: number;
  projectLifeYears: number;
  discountRate: number;
};

export type LocalEconomicMetrics = {
  capacityFactor: number;
  annualEnergyMwh: number;
  capexUsd: number;
  opexUsdPerYear: number;
  annualRevenueUsd: number;
  paybackYears: number | null;
  lcoeUsdPerMwh: number;
  economicScore: number;
};

export const DEFAULT_ASSUMPTIONS: LocalEconomicInputs = {
  turbineRatingMw: 3,
  turbineCount: 10,
  electricityPriceUsdPerMwh: 55,
  capexUsdPerMw: 1_300_000,
  opexPctOfCapex: 0.03,
  projectLifeYears: 20,
  discountRate: 0.08,
};

// Empirical breakpoints: [wind_speed_m_s, capacity_factor]
const CF_BREAKPOINTS: [number, number][] = [
  [3, 0.05], [4, 0.12], [5, 0.21], [6, 0.31],
  [7, 0.38], [8, 0.43], [9, 0.47], [12, 0.50],
];

function estimateCapacityFactor(meanWindMps: number): number {
  if (meanWindMps <= CF_BREAKPOINTS[0][0]) return CF_BREAKPOINTS[0][1];
  for (let i = 0; i < CF_BREAKPOINTS.length - 1; i++) {
    const [v1, cf1] = CF_BREAKPOINTS[i];
    const [v2, cf2] = CF_BREAKPOINTS[i + 1];
    if (meanWindMps <= v2) {
      const t = (meanWindMps - v1) / (v2 - v1);
      return cf1 + t * (cf2 - cf1);
    }
  }
  return CF_BREAKPOINTS[CF_BREAKPOINTS.length - 1][1];
}

function adjustedCf(baseCf: number, terrainScore: number | null): number {
  if (terrainScore !== null && terrainScore < 70) {
    const penalty = ((70 - terrainScore) / 70) * 0.08;
    return Math.max(0.05, baseCf - penalty);
  }
  return baseCf;
}

function crf(rate: number, years: number): number {
  if (rate <= 0) return 1 / Math.max(1, years);
  return (rate * Math.pow(1 + rate, years)) / (Math.pow(1 + rate, years) - 1);
}

export function computeEconomics(
  meanWindMps: number | null,
  terrainScore: number | null,
  infraScore: number | null,
  inputs: LocalEconomicInputs,
): LocalEconomicMetrics {
  const windMps = meanWindMps ?? 0;
  const baseCf = windMps > 0 ? estimateCapacityFactor(windMps) : 0.22;
  const cf = adjustedCf(baseCf, terrainScore);

  const capacityMw = inputs.turbineRatingMw * inputs.turbineCount;
  const aep = capacityMw * 8760 * cf;

  // CAPEX with terrain + infra premium
  const tScore = terrainScore ?? 60;
  const iScore = infraScore ?? 60;
  const terrainPremium = tScore >= 70 ? 0 : ((70 - tScore) / 70) * 0.20;
  const infraPremium = iScore >= 70 ? 0 : ((70 - iScore) / 70) * 0.15;
  const capex = capacityMw * inputs.capexUsdPerMw * (1 + terrainPremium + infraPremium);

  const opex = capex * inputs.opexPctOfCapex;
  const revenue = aep * inputs.electricityPriceUsdPerMwh;
  const netAnnual = revenue - opex;
  const payback = netAnnual > 0 ? capex / netAnnual : null;

  const annualCapexService = capex * crf(inputs.discountRate, inputs.projectLifeYears);
  const lcoe = aep > 0 ? (annualCapexService + opex) / aep : 9999;

  // Economic score
  const cfScore = Math.max(0, Math.min(100, ((cf - 0.15) / 0.30) * 100));
  const lcoeScore = Math.max(0, Math.min(100, ((75 - lcoe) / 35) * 100));
  const payScore = payback === null || payback > 30
    ? 5
    : Math.max(0, Math.min(100, ((20 - payback) / 12) * 100));
  const economicScore = Math.max(0, Math.min(100, 0.40 * cfScore + 0.35 * lcoeScore + 0.25 * payScore));

  return {
    capacityFactor: Math.round(cf * 1000) / 1000,
    annualEnergyMwh: Math.round(aep),
    capexUsd: Math.round(capex),
    opexUsdPerYear: Math.round(opex),
    annualRevenueUsd: Math.round(revenue),
    paybackYears: payback !== null ? Math.round(payback * 10) / 10 : null,
    lcoeUsdPerMwh: Math.round(lcoe * 10) / 10,
    economicScore: Math.round(economicScore * 10) / 10,
  };
}
