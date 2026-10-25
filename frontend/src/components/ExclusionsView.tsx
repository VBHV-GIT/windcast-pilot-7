import React, { useState } from "react";
import { CheckCircle2, Download, ShieldAlert } from "lucide-react";
import { ExclusionsResponse, MatchedObservation } from "../types/evaluation";

interface ExclusionsViewProps {
  exclusions: ExclusionsResponse | null;
  observations: MatchedObservation[];
  isLoading: boolean;
}

export const ExclusionsView: React.FC<ExclusionsViewProps> = ({
  exclusions,
  observations,
  isLoading,
}) => {
  const [filterReason, setFilterReason] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Handle CSV Download strictly from verified API observations
  const handleExportCsv = () => {
    if (!observations || observations.length === 0) return;

    const headers = [
      "interval_start_utc",
      "interval_end_utc",
      "forecast_generation_mw",
      "actual_generation_mw",
      "signed_error_mw",
      "absolute_error_mw",
      "percentage_error",
      "forecast_publish_time_utc",
    ];

    const rows = observations.map((obs) => [
      obs.interval_start,
      obs.interval_end,
      obs.forecast_mw.toFixed(2),
      obs.actual_mw.toFixed(2),
      obs.error_mw.toFixed(2),
      obs.absolute_error_mw.toFixed(2),
      obs.percentage_error !== null ? obs.percentage_error.toFixed(2) : "N/A",
      obs.forecast_publish_time,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `windcast_evaluation_observations_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const unmatchedList = exclusions?.unmatched_intervals || [];

  const filteredUnmatched = unmatchedList.filter((item) => {
    const matchesReason = filterReason === "ALL" || item.reason === filterReason;
    const matchesSearch =
      searchTerm === "" || item.interval_start.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesReason && matchesSearch;
  });

  return (
    <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-5 mb-6">
      {/* Header and CSV Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Data Transparency, Exclusions & Coverage Audit
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Full accountability log of matched observations, missing actuals, and discarded hindcast forecasts.
          </p>
        </div>

        <button
          type="button"
          onClick={handleExportCsv}
          disabled={observations.length === 0}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white text-xs font-medium px-3.5 py-2 rounded-lg transition-colors shadow-xs"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export Matched CSV ({observations.length})</span>
        </button>
      </div>

      {/* Audit Stats Breakdown */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6 text-xs">
        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
          <p className="text-slate-500 mb-0.5">Target Intervals</p>
          <p className="text-lg font-bold text-slate-900">
            {exclusions?.total_target_intervals ?? "—"}
          </p>
          <p className="text-[10px] text-slate-400">Total delivery periods</p>
        </div>

        <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
          <p className="text-emerald-700 mb-0.5">Matched Observations</p>
          <p className="text-lg font-bold text-emerald-900">
            {exclusions?.matched_intervals ?? "—"}
          </p>
          <p className="text-[10px] text-emerald-600">
            Coverage: {exclusions?.coverage_rate_percent?.toFixed(1) ?? "—"}%
          </p>
        </div>

        <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
          <p className="text-amber-700 mb-0.5">Missing Actuals</p>
          <p className="text-lg font-bold text-amber-900">
            {exclusions?.missing_actual_count ?? "0"}
          </p>
          <p className="text-[10px] text-amber-600">Incomplete FUELHH</p>
        </div>

        <div className="p-3 bg-rose-50 rounded-lg border border-rose-200">
          <p className="text-rose-700 mb-0.5">Missing Forecasts</p>
          <p className="text-lg font-bold text-rose-900">
            {exclusions?.missing_forecast_count ?? "0"}
          </p>
          <p className="text-[10px] text-rose-600">No pre-cutoff forecast</p>
        </div>

        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
          <p className="text-slate-500 mb-0.5">Hindcasts Excluded</p>
          <p className="text-lg font-bold text-slate-700">
            {exclusions?.excluded_retrospective_forecasts ?? "0"}
          </p>
          <p className="text-[10px] text-slate-400">startTime ≤ publishTime</p>
        </div>

        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
          <p className="text-slate-500 mb-0.5">Post-Cutoff Discards</p>
          <p className="text-lg font-bold text-slate-700">
            {exclusions?.excluded_post_cutoff_forecasts ?? "0"}
          </p>
          <p className="text-[10px] text-slate-400">publishTime &gt; Cutoff</p>
        </div>
      </div>

      {/* Unmatched Intervals Table */}
      <div className="border border-slate-200 rounded-lg overflow-hidden">
        <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 font-semibold text-slate-700">
            <span>Unmatched Target Intervals</span>
            <span className="bg-slate-200 text-slate-700 text-[10px] px-2 py-0.5 rounded-full font-mono">
              {filteredUnmatched.length}
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <input
              type="text"
              placeholder="Filter by timestamp..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="px-2 py-1 bg-white border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
            <select
              value={filterReason}
              onChange={(e) => setFilterReason(e.target.value)}
              className="px-2 py-1 bg-white border border-slate-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="ALL">All Reasons</option>
              <option value="MISSING_ACTUAL">Missing Actual</option>
              <option value="MISSING_FORECAST">Missing Forecast</option>
              <option value="MISSING_BOTH">Missing Both</option>
            </select>
          </div>
        </div>

        <div className="max-h-60 overflow-y-auto divide-y divide-slate-100 text-xs">
          {isLoading ? (
            <div className="p-4 text-center text-slate-400">Loading audit log...</div>
          ) : filteredUnmatched.length === 0 ? (
            <div className="p-6 text-center text-slate-500">
              <CheckCircle2 className="w-5 h-5 text-emerald-500 mx-auto mb-1" />
              <p className="font-medium text-slate-700">Zero Unmatched Intervals in Filtered View</p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Every delivery interval has valid corresponding forecast and actual records.
              </p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50 text-slate-500 font-semibold border-b border-slate-100">
                  <th className="py-2 px-4">Interval Start (UTC)</th>
                  <th className="py-2 px-4">Exclusion Classification</th>
                  <th className="py-2 px-4">Audit Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredUnmatched.map((ex, idx) => {
                  const badgeColor =
                    ex.reason === "MISSING_ACTUAL"
                      ? "bg-amber-100 text-amber-800 border-amber-200"
                      : ex.reason === "MISSING_FORECAST"
                      ? "bg-rose-100 text-rose-800 border-rose-200"
                      : "bg-slate-100 text-slate-700 border-slate-200";

                  const description =
                    ex.reason === "MISSING_ACTUAL"
                      ? "Actual outturn record for one or both 30-min settlement periods was missing from FUELHH."
                      : ex.reason === "MISSING_FORECAST"
                      ? "No forecast was published by NGESO on or before the day-ahead decision cutoff."
                      : "Neither forecast nor actual generation was recorded for this interval.";

                  return (
                    <tr key={idx} className="hover:bg-slate-50/50">
                      <td className="py-2 px-4 font-mono font-medium text-slate-800">
                        {ex.interval_start}
                      </td>
                      <td className="py-2 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${badgeColor}`}>
                          {ex.reason}
                        </span>
                      </td>
                      <td className="py-2 px-4 text-slate-600 text-[11px]">{description}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="mt-3 text-[11px] text-slate-400 italic">
        * Note: CSV export and exclusion audit tables reflect only verified Elexon API data returned by the backend service. No values are fabricated or extrapolated.
      </div>
    </div>
  );
};
