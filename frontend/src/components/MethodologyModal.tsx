import React from "react";
import { BookOpen, Info, ShieldAlert, X } from "lucide-react";

interface MethodologyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MethodologyModal: React.FC<MethodologyModalProps> = ({
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden">
        {/* Modal Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-emerald-400" />
            <h2 className="text-base font-bold">Evaluation Methodology & Assumptions</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-5 text-xs text-slate-700 max-h-[75vh] overflow-y-auto leading-relaxed">
          {/* 1. Day-Ahead Cutoff Assumption */}
          <section className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
            <h3 className="font-bold text-slate-900 text-sm mb-1 flex items-center gap-1.5">
              <Info className="w-4 h-4 text-emerald-600" />
              1. Configurable Day-Ahead Decision Cutoff
            </h3>
            <p>
              In UK electricity procurement, trading and operational decisions are finalized before specific market gate closures on day <em>D-1</em>.
            </p>
            <div className="mt-2 p-2 bg-amber-50 rounded border border-amber-200 text-amber-900">
              <strong>Pilot Assumption Disclosure:</strong> The default cutoff of <strong>17:00 UTC</strong> on day <em>D-1</em> is implemented as an operational pilot assumption aligned with the NGESO Day-Ahead Indicative Operational Plan submission window. It is configurable via the dashboard and should not be construed as a statutory market deadline.
            </div>
          </section>

          {/* 2. Temporal Alignment */}
          <section className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
            <h3 className="font-bold text-slate-900 text-sm mb-1">
              2. Temporal Resolution & Physical Power Averaging
            </h3>
            <p>
              <strong>FUELHH</strong> provides generation outturn at 30-minute settlement periods (SPs 1–48 in January), while <strong>WINDFOR</strong> publishes forecasts for 1-hour start intervals.
            </p>
            <p className="mt-1.5">
              Since power in Megawatts (MW) represents an instantaneous rate of energy flow (1 MW = 1 MWh/h), the hourly actual is computed by taking the exact arithmetic mean of the two half-hours:
            </p>
            <code className="block bg-slate-100 p-2 rounded font-mono text-[11px] text-slate-800 my-1.5">
              Actual_Hourly (MW) = (Actual_SP1 + Actual_SP2) / 2.0
            </code>
            <p>
              If either half-hour actual is missing from FUELHH, the entire hourly actual is marked as missing. Half-hourly broadcasting is also available as an alternative view.
            </p>
          </section>

          {/* 3. Look-Ahead Bias & Hindcast Policy */}
          <section className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
            <h3 className="font-bold text-slate-900 text-sm mb-1 flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              3. Causality & Retrospective Hindcast Exclusion
            </h3>
            <p>
              In WINDFOR publication runs, model simulations initialized hours earlier include records where <code>startTime &le; publishTime</code>. These represent model initialization states or in-sample hindcasts.
            </p>
            <p className="mt-1 text-slate-600">
              To strictly prevent <strong>look-ahead bias</strong>, our algorithm enforces:
            </p>
            <code className="block bg-slate-100 p-2 rounded font-mono text-[11px] text-slate-800 my-1.5">
              publishTime &le; Cutoff(D) &lt; startTime
            </code>
            <p>Any record where delivery started before or during publication is strictly discarded.</p>
          </section>

          {/* 4. Zero-Actual Policy in MAPE */}
          <section className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
            <h3 className="font-bold text-slate-900 text-sm mb-1">
              4. Zero-Actual Policy & Metric Formulas
            </h3>
            <ul className="list-disc list-inside space-y-1 text-slate-600">
              <li>
                <strong>MAE:</strong> (1/N) &Sigma; |Forecast - Actual| in MW.
              </li>
              <li>
                <strong>RMSE:</strong> &radic;((1/N) &Sigma; (Forecast - Actual)&sup2;) in MW.
              </li>
              <li>
                <strong>Signed Bias:</strong> (1/N) &Sigma; (Forecast - Actual) in MW.
              </li>
              <li>
                <strong>MAPE Policy:</strong> When actual outturn is near zero (&lt; 1.0 MW), dividing by actual produces explosive percentage errors. These intervals are excluded from MAPE and their count is explicitly reported.
              </li>
              <li>
                <strong>WMAPE:</strong> (&Sigma; |Forecast - Actual| / &Sigma; Actual) &times; 100%. Volume-weighted normalized MAE, standard across UK utilities.
              </li>
            </ul>
          </section>
        </div>

        {/* Modal Footer */}
        <div className="bg-slate-100 px-6 py-3 border-t border-slate-200 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
