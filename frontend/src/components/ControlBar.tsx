import React, { useState } from "react";
import { Calendar, Database, Layers, RefreshCw, Sliders } from "lucide-react";
import { EvaluationQueryParams, ResolutionAlignment } from "../types/evaluation";

interface ControlBarProps {
  params: EvaluationQueryParams;
  onChange: (newParams: EvaluationQueryParams) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

const CUTOFF_PRESETS = [
  { label: "17:00 UTC (Pilot Default)", value: "17:00" },
  { label: "12:00 UTC", value: "12:00" },
  { label: "11:00 UTC", value: "11:00" },
  { label: "23:00 UTC", value: "23:00" },
];

export const ControlBar: React.FC<ControlBarProps> = ({
  params,
  onChange,
  onRefresh,
  isLoading,
}) => {
  const [customCutoff, setCustomCutoff] = useState("");
  const isCustomCutoffActive = !CUTOFF_PRESETS.some((p) => p.value === params.cutoffTime);

  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...params, startDate: e.target.value });
  };

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...params, endDate: e.target.value });
  };

  const handlePresetCutoff = (cutoffVal: string) => {
    setCustomCutoff("");
    onChange({ ...params, cutoffTime: cutoffVal });
  };

  const handleCustomCutoffSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (/^\d{2}:\d{2}$/.test(customCutoff)) {
      onChange({ ...params, cutoffTime: customCutoff });
    }
  };

  const handleAlignmentChange = (alignment: ResolutionAlignment) => {
    onChange({ ...params, alignment });
  };

  const handleCacheToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...params, useCache: e.target.checked });
  };

  const setJanuaryPreset = () => {
    onChange({
      ...params,
      startDate: "2026-01-01",
      endDate: "2026-01-31",
    });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Controls container */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:flex lg:flex-wrap items-center gap-4 text-xs">
          {/* Date range picker */}
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-2 rounded-lg">
            <Calendar className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <div className="flex items-center gap-1.5">
              <input
                type="date"
                value={params.startDate}
                min="2026-01-01"
                max="2026-01-31"
                onChange={handleStartDateChange}
                className="bg-transparent text-slate-800 font-medium focus:outline-none focus:ring-1 focus:ring-emerald-500 rounded px-1"
                aria-label="Delivery Start Date"
              />
              <span className="text-slate-400">to</span>
              <input
                type="date"
                value={params.endDate}
                min="2026-01-01"
                max="2026-01-31"
                onChange={handleEndDateChange}
                className="bg-transparent text-slate-800 font-medium focus:outline-none focus:ring-1 focus:ring-emerald-500 rounded px-1"
                aria-label="Delivery End Date"
              />
            </div>
            <button
              type="button"
              onClick={setJanuaryPreset}
              className="text-[11px] text-emerald-700 hover:text-emerald-800 font-semibold bg-emerald-50 hover:bg-emerald-100 px-1.5 py-0.5 rounded border border-emerald-200 transition-colors"
            >
              Full Jan
            </button>
          </div>

          {/* Evaluation cutoff selector */}
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-2 rounded-lg">
            <Sliders className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span className="font-semibold text-slate-700 whitespace-nowrap">Cutoff:</span>
            <div className="flex items-center gap-1 flex-wrap">
              {CUTOFF_PRESETS.map((preset) => {
                const isActive = params.cutoffTime === preset.value;
                return (
                  <button
                    key={preset.value}
                    type="button"
                    onClick={() => handlePresetCutoff(preset.value)}
                    className={`px-2 py-1 rounded text-xs font-medium transition-all ${
                      isActive
                        ? "bg-slate-900 text-white shadow-xs"
                        : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    {preset.value}
                  </button>
                );
              })}

              {/* Custom cutoff input */}
              <form onSubmit={handleCustomCutoffSubmit} className="flex items-center ml-1">
                <input
                  type="text"
                  placeholder="HH:MM"
                  value={customCutoff}
                  onChange={(e) => setCustomCutoff(e.target.value)}
                  className={`w-14 px-1.5 py-0.5 text-xs text-center rounded border focus:outline-none ${
                    isCustomCutoffActive
                      ? "border-emerald-600 ring-1 ring-emerald-500 bg-emerald-50 font-bold"
                      : "border-slate-300 bg-white"
                  }`}
                  aria-label="Custom Cutoff Time (HH:MM)"
                />
              </form>
            </div>
          </div>

          {/* Alignment toggle */}
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-2 rounded-lg">
            <Layers className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span className="font-semibold text-slate-700">Alignment:</span>
            <div className="inline-flex rounded-md shadow-xs bg-white border border-slate-200 p-0.5">
              <button
                type="button"
                onClick={() => handleAlignmentChange("HOURLY")}
                className={`px-2 py-0.5 text-xs rounded font-medium transition-colors ${
                  params.alignment === "HOURLY"
                    ? "bg-emerald-600 text-white"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                title="Averages the two 30-min actuals to match the 1-hour forecast resolution"
              >
                Hourly (Mean MW)
              </button>
              <button
                type="button"
                onClick={() => handleAlignmentChange("HALF_HOURLY")}
                className={`px-2 py-0.5 text-xs rounded font-medium transition-colors ${
                  params.alignment === "HALF_HOURLY"
                    ? "bg-emerald-600 text-white"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                title="Broadcasts the 1-hour forecast across both 30-minute settlement periods"
              >
                Half-Hourly
              </button>
            </div>
          </div>

          {/* Safe Server Cache Toggle */}
          <label className="flex items-center gap-2 text-slate-700 cursor-pointer select-none bg-slate-50 border border-slate-200 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors">
            <Database className="w-4 h-4 text-slate-500" />
            <input
              type="checkbox"
              checked={params.useCache}
              onChange={handleCacheToggle}
              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 w-3.5 h-3.5"
            />
            <span className="font-medium text-slate-700">Use Server Cache</span>
          </label>
        </div>

        {/* Refresh / Apply Action Button */}
        <div className="flex items-center justify-end">
          <button
            type="button"
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white font-medium text-xs px-4 py-2.5 rounded-lg shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1 w-full lg:w-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>{isLoading ? "Analyzing..." : "Refresh / Analyze"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
