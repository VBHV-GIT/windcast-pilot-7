import React from "react";
import { Activity, BarChart3, CheckCircle2, Compass, TrendingDown, TrendingUp, Zap } from "lucide-react";
import { EvaluationSummaryResponse } from "../types/evaluation";

interface KpiGridProps {
  summary: EvaluationSummaryResponse | null;
  isLoading: boolean;
}

interface CardProps {
  title: string;
  value: string;
  unit?: string;
  description: string;
  subtext?: string;
  badge?: {
    text: string;
    variant: "neutral" | "emerald" | "amber" | "rose" | "blue";
  };
  icon: React.ReactNode;
  isLoading: boolean;
}

const KpiCard: React.FC<CardProps> = ({
  title,
  value,
  unit,
  description,
  subtext,
  badge,
  icon,
  isLoading,
}) => {
  const badgeClasses = {
    neutral: "bg-slate-100 text-slate-700 border-slate-200",
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
    rose: "bg-rose-50 text-rose-700 border-rose-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
  };

  return (
    <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-4 flex flex-col justify-between hover:border-slate-300 transition-all">
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{title}</span>
          <div className="text-slate-400 bg-slate-50 p-1.5 rounded-md border border-slate-100">{icon}</div>
        </div>

        {isLoading ? (
          <div className="my-2 h-7 bg-slate-100 animate-pulse rounded w-24" />
        ) : (
          <div className="flex items-baseline gap-1 my-1">
            <span className="text-2xl font-bold tracking-tight text-slate-900">{value}</span>
            {unit && <span className="text-xs font-medium text-slate-500">{unit}</span>}
          </div>
        )}

        <p className="text-xs text-slate-500 mt-1 leading-relaxed">{description}</p>
      </div>

      <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between flex-wrap gap-1 text-[11px]">
        {badge && (
          <span className={`px-1.5 py-0.5 rounded border font-medium ${badgeClasses[badge.variant]}`}>
            {badge.text}
          </span>
        )}
        {subtext && <span className="text-slate-400">{subtext}</span>}
      </div>
    </div>
  );
};

export const KpiGrid: React.FC<KpiGridProps> = ({ summary, isLoading }) => {
  // Format numbers safely, representing null as "—"
  const fmt = (val: number | null | undefined, decimals = 1): string => {
    if (val === null || val === undefined) return "—";
    return val.toLocaleString("en-GB", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  const biasValue = summary?.signed_bias_mw;
  const isOverForecasting = (biasValue ?? 0) > 0;
  const hasMatched = (summary?.matched_intervals ?? 0) > 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* 1. MAE Card */}
      <KpiCard
        title="Mean Absolute Error (MAE)"
        value={fmt(summary?.mae_mw)}
        unit="MW"
        description="Average magnitude of forecast errors over matched delivery intervals without regard to direction."
        subtext="Formula: (1/N) Σ |Forecast - Actual|"
        badge={
          hasMatched && summary?.mae_mw !== null
            ? { text: "Linear Penalty", variant: "neutral" }
            : { text: "No Data", variant: "neutral" }
        }
        icon={<Activity className="w-4 h-4 text-emerald-600" />}
        isLoading={isLoading}
      />

      {/* 2. RMSE Card */}
      <KpiCard
        title="Root Mean Square Error (RMSE)"
        value={fmt(summary?.rmse_mw)}
        unit="MW"
        description="Square root of average squared errors, heavily penalizing large forecast errors."
        subtext="Formula: √((1/N) Σ (Forecast - Actual)²)"
        badge={
          hasMatched && summary?.rmse_mw !== null
            ? { text: "Quadratic Penalty", variant: "blue" }
            : { text: "No Data", variant: "neutral" }
        }
        icon={<BarChart3 className="w-4 h-4 text-blue-600" />}
        isLoading={isLoading}
      />

      {/* 3. Signed Bias Card */}
      <KpiCard
        title="Signed Bias (Mean Error)"
        value={
          summary?.signed_bias_mw !== null && summary?.signed_bias_mw !== undefined
            ? `${summary.signed_bias_mw > 0 ? "+" : ""}${fmt(summary.signed_bias_mw)}`
            : "—"
        }
        unit="MW"
        description="Directional forecast skew. Positive = over-forecast; Negative = under-forecast."
        subtext="Formula: (1/N) Σ (Forecast - Actual)"
        badge={
          hasMatched && summary?.signed_bias_mw !== null
            ? isOverForecasting
              ? { text: "Surplus Risk (Over-forecast)", variant: "amber" }
              : { text: "Deficit Risk (Under-forecast)", variant: "rose" }
            : { text: "No Data", variant: "neutral" }
        }
        icon={
          isOverForecasting ? (
            <TrendingUp className="w-4 h-4 text-amber-600" />
          ) : (
            <TrendingDown className="w-4 h-4 text-rose-600" />
          )
        }
        isLoading={isLoading}
      />

      {/* 4. WMAPE Card */}
      <KpiCard
        title="Volume-Weighted MAPE (WMAPE)"
        value={fmt(summary?.wmape_percent)}
        unit="%"
        description="Total absolute error normalized by total generation. Standard for power utilities."
        subtext="Formula: (Σ |F - A| / Σ Actual) × 100%"
        badge={
          hasMatched && summary?.wmape_percent !== null
            ? { text: "Utility Standard", variant: "emerald" }
            : { text: "No Data", variant: "neutral" }
        }
        icon={<Zap className="w-4 h-4 text-emerald-600" />}
        isLoading={isLoading}
      />

      {/* 5. Standard MAPE Card */}
      <KpiCard
        title="Mean Absolute % Error (MAPE)"
        value={fmt(summary?.mape_percent)}
        unit="%"
        description={`Unweighted average percentage error. Excludes ${
          summary?.mape_excluded_zero_samples ?? 0
        } zero/near-zero actuals (< 1.0 MW).`}
        subtext="Formula: (1/k) Σ (|F - A| / Actual) × 100%"
        badge={
          summary?.mape_excluded_zero_samples
            ? { text: `${summary.mape_excluded_zero_samples} Excluded (<1 MW)`, variant: "amber" }
            : { text: "0 Zero Actuals", variant: "neutral" }
        }
        icon={<Compass className="w-4 h-4 text-slate-600" />}
        isLoading={isLoading}
      />

      {/* 6. Forecast Energy Volume Card */}
      <KpiCard
        title="Total Forecast Energy"
        value={fmt(summary?.total_forecast_energy_mwh, 0)}
        unit="MWh"
        description="Integrated day-ahead forecasted wind volume across all matched intervals."
        subtext="Calculated from matched intervals only"
        badge={{ text: "Forecast Energy", variant: "blue" }}
        icon={<Zap className="w-4 h-4 text-blue-500" />}
        isLoading={isLoading}
      />

      {/* 7. Actual Energy Volume Card */}
      <KpiCard
        title="Total Actual Energy"
        value={fmt(summary?.total_actual_energy_mwh, 0)}
        unit="MWh"
        description="Integrated actual wind outturn generation across all matched delivery intervals."
        subtext="Calculated from matched intervals only"
        badge={{ text: "Actual Energy", variant: "emerald" }}
        icon={<Zap className="w-4 h-4 text-emerald-500" />}
        isLoading={isLoading}
      />

      {/* 8. Interval Coverage Card */}
      <KpiCard
        title="Interval Coverage"
        value={`${summary?.matched_intervals ?? 0} / ${summary?.total_target_intervals ?? 0}`}
        unit={`(${fmt(summary?.coverage_rate_percent)}%)`}
        description="Share of target delivery intervals in the evaluation period with both forecast and actual data."
        subtext="Note: High coverage does not guarantee accuracy"
        badge={
          (summary?.coverage_rate_percent ?? 0) === 100
            ? { text: "100% Coverage", variant: "emerald" }
            : { text: "Partial Coverage", variant: "amber" }
        }
        icon={<CheckCircle2 className="w-4 h-4 text-emerald-600" />}
        isLoading={isLoading}
      />
    </div>
  );
};
