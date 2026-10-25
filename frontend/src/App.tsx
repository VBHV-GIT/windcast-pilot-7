import React, { useCallback, useEffect, useState } from "react";
import {
  checkBackendHealth,
  fetchEvaluationExclusions,
  fetchEvaluationSummary,
  fetchEvaluationTimeseries,
} from "./services/api";
import {
  EvaluationQueryParams,
  EvaluationSummaryResponse,
  ExclusionsResponse,
  HealthResponse,
  TimeSeriesResponse,
} from "./types/evaluation";
import { Header } from "./components/Header";
import { ControlBar } from "./components/ControlBar";
import { ErrorBanner } from "./components/ErrorBanner";
import { KpiGrid } from "./components/KpiGrid";
import { GenerationChart } from "./components/GenerationChart";
import { ExclusionsView } from "./components/ExclusionsView";
import { MethodologyModal } from "./components/MethodologyModal";
import { BarChart2, ShieldAlert } from "lucide-react";

export const App: React.FC = () => {
  // Query parameters state (default: January 1–31, 2026, 17:00 UTC pilot cutoff, Hourly alignment, Cache enabled)
  const [params, setParams] = useState<EvaluationQueryParams>({
    startDate: "2026-01-01",
    endDate: "2026-01-31",
    cutoffTime: "17:00",
    alignment: "HOURLY",
    useCache: true,
  });

  // Data states
  const [summary, setSummary] = useState<EvaluationSummaryResponse | null>(null);
  const [timeseries, setTimeseries] = useState<TimeSeriesResponse | null>(null);
  const [exclusions, setExclusions] = useState<ExclusionsResponse | null>(null);

  // Health and UI states
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<string | undefined>(undefined);
  const [isMethodologyOpen, setIsMethodologyOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"overview" | "exclusions">("overview");

  // Check backend health on mount
  useEffect(() => {
    let isMounted = true;
    checkBackendHealth()
      .then((res) => {
        if (isMounted) {
          setHealth(res);
          setHealthLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setHealth(null);
          setHealthLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch all evaluation data concurrently
  const loadEvaluationData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    setErrorDetails(undefined);

    try {
      const [sumRes, timeRes, exclRes] = await Promise.all([
        fetchEvaluationSummary(params),
        fetchEvaluationTimeseries(params),
        fetchEvaluationExclusions(params),
      ]);

      setSummary(sumRes);
      setTimeseries(timeRes);
      setExclusions(exclRes);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to retrieve forecast evaluation data");
      setErrorDetails(err.details || undefined);
    } finally {
      setIsLoading(false);
    }
  }, [params]);

  // Trigger evaluation fetch on parameter changes
  useEffect(() => {
    loadEvaluationData();
  }, [loadEvaluationData]);

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-900 flex flex-col font-sans">
      {/* Application Navigation Header */}
      <Header
        health={health}
        healthLoading={healthLoading}
        onOpenMethodology={() => setIsMethodologyOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Interactive Query & Evaluation Controls */}
        <ControlBar
          params={params}
          onChange={setParams}
          onRefresh={loadEvaluationData}
          isLoading={isLoading}
        />

        {/* Global Error Banner */}
        {errorMessage && (
          <ErrorBanner
            message={errorMessage}
            details={errorDetails}
            onRetry={loadEvaluationData}
            isRetrying={isLoading}
          />
        )}

        {/* Navigation Tabs */}
        <div className="flex items-center justify-between mb-4 border-b border-slate-200">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("overview")}
              className={`flex items-center gap-1.5 py-2.5 px-4 text-xs font-semibold border-b-2 transition-all ${
                activeTab === "overview"
                  ? "border-emerald-600 text-emerald-800 bg-white/50 rounded-t-lg"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <BarChart2 className="w-4 h-4" />
              <span>Forecast Evaluation & Charts</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("exclusions")}
              className={`flex items-center gap-1.5 py-2.5 px-4 text-xs font-semibold border-b-2 transition-all ${
                activeTab === "exclusions"
                  ? "border-emerald-600 text-emerald-800 bg-white/50 rounded-t-lg"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              <span>
                Data Transparency & Exclusions ({exclusions?.unmatched_intervals.length ?? 0})
              </span>
            </button>
          </div>

          <div className="text-xs text-slate-500 hidden sm:block">
            <span>
              Evaluation Cutoff: <strong>{params.cutoffTime} UTC</strong> | Alignment:{" "}
              <strong>{params.alignment === "HOURLY" ? "Hourly (Mean)" : "Half-Hourly"}</strong>
            </span>
          </div>
        </div>

        {/* Tab 1: Primary Dashboard View */}
        {activeTab === "overview" && (
          <>
            {/* KPI Cards Grid */}
            <KpiGrid summary={summary} isLoading={isLoading} />

            {/* Time-Series Generation & Forecast Chart */}
            <GenerationChart
              series={timeseries?.series || []}
              alignment={params.alignment}
              isLoading={isLoading}
            />
          </>
        )}

        {/* Tab 2: Transparency & Exclusions Audit View */}
        {activeTab === "exclusions" && (
          <ExclusionsView
            exclusions={exclusions}
            observations={timeseries?.series || []}
            isLoading={isLoading}
          />
        )}
      </main>

      {/* Methodology Educational Modal */}
      <MethodologyModal
        isOpen={isMethodologyOpen}
        onClose={() => setIsMethodologyOpen(false)}
      />

      {/* Global Utility Footer */}
      <footer className="py-4 px-6 border-t border-slate-200 bg-white text-xs text-slate-500 text-center">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>WindCast Analytics &copy; 2026 | UK Electricity Utility Engineering Assignment</span>
          <span>Data Sources: Elexon BMRS <code>FUELHH</code> (WIND) & <code>WINDFOR</code></span>
        </div>
      </footer>
    </div>
  );
};

export default App;
