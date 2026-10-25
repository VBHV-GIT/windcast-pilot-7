import React, { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertCircle, Eye, EyeOff, Zap } from "lucide-react";
import { MatchedObservation, ResolutionAlignment } from "../types/evaluation";

interface GenerationChartProps {
  series: MatchedObservation[];
  alignment: ResolutionAlignment;
  isLoading: boolean;
}

export const GenerationChart: React.FC<GenerationChartProps> = ({
  series,
  alignment,
  isLoading,
}) => {
  const [showErrorOverlay, setShowErrorOverlay] = useState<boolean>(false);
  const [viewWindow, setViewWindow] = useState<"ALL" | "W1" | "W2" | "W3" | "W4" | "W5">("ALL");

  // Format data points for Recharts
  const chartData = useMemo(() => {
    if (!series || series.length === 0) return [];

    let filtered = series;
    if (viewWindow !== "ALL") {
      const ranges = {
        W1: ["2026-01-01", "2026-01-07"],
        W2: ["2026-01-08", "2026-01-14"],
        W3: ["2026-01-15", "2026-01-21"],
        W4: ["2026-01-22", "2026-01-28"],
        W5: ["2026-01-29", "2026-01-31"],
      };
      const [startPrefix, endPrefix] = ranges[viewWindow];
      filtered = series.filter(
        (s) => s.interval_start >= `${startPrefix}T00:00:00Z` && s.interval_start <= `${endPrefix}T23:59:59Z`
      );
    }

    return filtered.map((obs) => {
      // Create readable labels
      const d = new Date(obs.interval_start);
      const label = d.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "UTC",
      });

      return {
        timestamp: obs.interval_start,
        label,
        actual: obs.actual_mw,
        forecast: obs.forecast_mw,
        error: obs.error_mw, // Forecast - Actual
        absError: obs.absolute_error_mw,
        percentageError: obs.percentage_error,
        publishTime: obs.forecast_publish_time,
      };
    });
  }, [series, viewWindow]);

  // Custom high-detail tooltip for energy traders
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const dStart = new Date(data.timestamp);
      const dPub = new Date(data.publishTime);

      const fmtUtc = (date: Date) =>
        date.toISOString().replace("T", " ").replace(":00.000Z", " UTC").replace(".000Z", " UTC");

      const errorVal = data.error;
      const isOver = errorVal > 0;

      return (
        <div className="bg-slate-900 text-white p-3 rounded-lg shadow-xl border border-slate-700 text-xs min-w-[240px]">
          <p className="font-semibold text-slate-200 border-b border-slate-800 pb-1.5 mb-2">
            Delivery: {fmtUtc(dStart)}
          </p>

          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Actual Outturn:
              </span>
              <span className="font-mono font-bold text-white">
                {data.actual.toLocaleString("en-GB", { maximumFractionDigits: 1 })} MW
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="flex items-center gap-1.5 text-blue-400 font-medium">
                <span className="w-2 h-2 rounded-full bg-blue-400" />
                Day-Ahead Forecast:
              </span>
              <span className="font-mono font-bold text-white">
                {data.forecast.toLocaleString("en-GB", { maximumFractionDigits: 1 })} MW
              </span>
            </div>

            <div className="flex justify-between items-center pt-1 border-t border-slate-800">
              <span className="text-slate-400">Signed Error (F - A):</span>
              <span className={`font-mono font-semibold ${isOver ? "text-amber-400" : "text-rose-400"}`}>
                {isOver ? "+" : ""}
                {data.error.toLocaleString("en-GB", { maximumFractionDigits: 1 })} MW
              </span>
            </div>

            {data.percentageError !== null && (
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-slate-400">Absolute % Error:</span>
                <span className="font-mono text-slate-300">
                  {data.percentageError.toFixed(1)}%
                </span>
              </div>
            )}

            <div className="pt-1.5 text-[10px] text-slate-400 border-t border-slate-800">
              <span>Forecast Published: {fmtUtc(dPub)}</span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-5 mb-6">
      {/* Chart toolbar & header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-emerald-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Wind Generation: Day-Ahead Forecast vs. Actual Outturn
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Generation rate in Megawatts (MW) across {alignment === "HOURLY" ? "hourly averaged" : "half-hourly"} delivery intervals.
          </p>
        </div>

        {/* Toolbar controls */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Zoom window selector */}
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setViewWindow("ALL")}
              className={`px-2 py-1 rounded font-medium transition-colors ${
                viewWindow === "ALL" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Full Jan
            </button>
            <button
              type="button"
              onClick={() => setViewWindow("W1")}
              className={`px-2 py-1 rounded font-medium transition-colors ${
                viewWindow === "W1" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Jan 1–7
            </button>
            <button
              type="button"
              onClick={() => setViewWindow("W2")}
              className={`px-2 py-1 rounded font-medium transition-colors ${
                viewWindow === "W2" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Jan 8–14
            </button>
            <button
              type="button"
              onClick={() => setViewWindow("W3")}
              className={`px-2 py-1 rounded font-medium transition-colors ${
                viewWindow === "W3" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Jan 15–21
            </button>
            <button
              type="button"
              onClick={() => setViewWindow("W4")}
              className={`px-2 py-1 rounded font-medium transition-colors ${
                viewWindow === "W4" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Jan 22–28
            </button>
            <button
              type="button"
              onClick={() => setViewWindow("W5")}
              className={`px-2 py-1 rounded font-medium transition-colors ${
                viewWindow === "W5" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Jan 29–31
            </button>
          </div>

          {/* Toggle optional error overlay */}
          <button
            type="button"
            onClick={() => setShowErrorOverlay(!showErrorOverlay)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
              showErrorOverlay
                ? "bg-amber-50 text-amber-800 border-amber-300"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
          >
            {showErrorOverlay ? <Eye className="w-3.5 h-3.5 text-amber-600" /> : <EyeOff className="w-3.5 h-3.5 text-slate-400" />}
            <span>Error Delta (|F - A|)</span>
          </button>
        </div>
      </div>

      {/* Chart rendering area */}
      {isLoading ? (
        <div className="h-[380px] flex items-center justify-center bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
          <div className="flex flex-col items-center gap-2 text-slate-500 text-xs">
            <div className="w-6 h-6 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
            <span>Loading time-series data...</span>
          </div>
        </div>
      ) : chartData.length === 0 ? (
        <div className="h-[380px] flex flex-col items-center justify-center bg-slate-50/60 rounded-lg border border-dashed border-slate-300 p-6 text-center">
          <AlertCircle className="w-8 h-8 text-slate-400 mb-2" />
          <h3 className="text-sm font-semibold text-slate-800">No Matched Observations Available</h3>
          <p className="text-xs text-slate-500 max-w-md mt-1">
            No matched forecast-versus-actual delivery intervals were found for the selected date range and cutoff. Try adjusting your parameters or enabling "Use Server Cache".
          </p>
        </div>
      ) : (
        <div className="h-[380px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 10, right: 20, left: 10, bottom: 25 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="label"
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                interval="preserveStartEnd"
                dy={10}
              />
              <YAxis
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                domain={[0, "auto"]}
                label={{
                  value: "Power (MW)",
                  angle: -90,
                  position: "insideLeft",
                  style: { fill: "#64748b", fontSize: 11 },
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                height={36}
                wrapperStyle={{ fontSize: "12px", paddingTop: "0px" }}
              />

              {/* Optional Error Area */}
              {showErrorOverlay && (
                <Line
                  type="monotone"
                  dataKey="absError"
                  name="Absolute Error |F - A| (MW)"
                  stroke="#f59e0b"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                />
              )}

              {/* Day-Ahead Forecast Line */}
              <Line
                type="monotone"
                dataKey="forecast"
                name="Day-Ahead Forecast (MW)"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 5, stroke: "#1d4ed8", strokeWidth: 1 }}
              />

              {/* Actual Outturn Line */}
              <Line
                type="monotone"
                dataKey="actual"
                name="Actual Outturn (MW)"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 5, stroke: "#047857", strokeWidth: 1 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};
