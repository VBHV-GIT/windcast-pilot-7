import React from "react";
import { BookOpen, Clock, Wind } from "lucide-react";
import { HealthResponse } from "../types/evaluation";

interface HeaderProps {
  health: HealthResponse | null;
  healthLoading: boolean;
  onOpenMethodology: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  healthLoading,
  onOpenMethodology,
}) => {
  const isHealthy = health?.status === "ok";

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/30 text-emerald-400">
            <Wind className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">WindCast Analytics</h1>
              <span className="text-[10px] uppercase font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 px-2 py-0.5 rounded">
                UK Utility Pilot
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Elexon BMRS Wind Generation Forecast vs Outturn Accuracy Evaluation | Jan 2026
            </p>
          </div>
        </div>

        {/* Status badges & actions */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Timezone pill */}
          <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700 text-slate-300 text-xs px-2.5 py-1 rounded-md">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>All Times: <strong>UTC / GMT</strong></span>
          </div>

          {/* Connection status pill */}
          <div
            className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md border ${
              healthLoading
                ? "bg-slate-800 text-slate-400 border-slate-700"
                : isHealthy
                ? "bg-emerald-950/60 border-emerald-700/60 text-emerald-300"
                : "bg-rose-950/60 border-rose-700/60 text-rose-300"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                healthLoading
                  ? "bg-slate-400 animate-pulse"
                  : isHealthy
                  ? "bg-emerald-400"
                  : "bg-rose-400"
              }`}
            />
            <span>
              {healthLoading
                ? "Checking API..."
                : isHealthy
                ? `API Ready (${health?.service || "FastAPI"})`
                : "API Disconnected"}
            </span>
          </div>

          {/* Methodology button */}
          <button
            type="button"
            onClick={onOpenMethodology}
            className="flex items-center gap-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-2.5 py-1 rounded-md transition-colors"
          >
            <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
            <span>Methodology</span>
          </button>
        </div>
      </div>
    </header>
  );
};
