import React from "react";
import { Activity, Wind, Server, ShieldCheck } from "lucide-react";

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col">
      <header className="bg-slate-900 text-white px-6 py-4 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500/20 p-2 rounded-lg border border-emerald-500/40">
              <Wind className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">WindCast Analytics</h1>
              <p className="text-xs text-slate-400">UK Wind Forecast Accuracy Evaluation | January 2026</p>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-emerald-950/60 border border-emerald-700/50 text-emerald-300 text-xs px-3 py-1.5 rounded-full">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Milestone 1: Scaffold Initialized</span>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col items-center justify-center">
        <div className="max-w-xl w-full bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center">
          <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-600">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Core Environment Ready</h2>
          <p className="text-sm text-slate-600 mb-6">
            React 18 + Vite + TypeScript frontend and Python FastAPI backend are verified.
            The pipeline is prepared for Elexon BMRS <code className="bg-slate-100 px-1 py-0.5 rounded text-emerald-700 font-mono">FUELHH</code> and <code className="bg-slate-100 px-1 py-0.5 rounded text-emerald-700 font-mono">WINDFOR</code> ingestion in Milestone 2.
          </p>

          <div className="grid grid-cols-2 gap-3 text-left">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 mb-1">
                <Server className="w-4 h-4 text-emerald-600" /> Backend
              </div>
              <p className="text-xs text-slate-500">FastAPI & Pytest</p>
              <p className="text-xs text-emerald-600 font-medium mt-1">/health verified</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 mb-1">
                <Activity className="w-4 h-4 text-emerald-600" /> Frontend
              </div>
              <p className="text-xs text-slate-500">Vite, React & TS</p>
              <p className="text-xs text-emerald-600 font-medium mt-1">Tailwind CSS Ready</p>
            </div>
          </div>
        </div>
      </main>

      <footer className="py-4 text-center text-xs text-slate-500 border-t border-slate-200">
        WindCast Analytics &copy; 2026 | UK Electricity Utility Engineering Assignment
      </footer>
    </div>
  );
};

export default App;
