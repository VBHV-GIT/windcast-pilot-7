import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  details?: string;
  onRetry: () => void;
  isRetrying?: boolean;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  message,
  details,
  onRetry,
  isRetrying = false,
}) => {
  return (
    <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 mb-6 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="text-rose-600 mt-0.5 flex-shrink-0">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="flex-1 text-sm">
          <h3 className="font-semibold text-rose-900 mb-0.5">Evaluation Error</h3>
          <p className="text-rose-700">{message}</p>
          {details && (
            <p className="mt-1 text-xs font-mono bg-rose-100/70 p-2 rounded text-rose-800 break-words">
              {details}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onRetry}
          disabled={isRetrying}
          className="flex items-center gap-1.5 bg-rose-600 hover:bg-rose-700 disabled:bg-rose-400 text-white text-xs font-medium px-3 py-1.5 rounded-md transition-colors shadow-sm flex-shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? "animate-spin" : ""}`} />
          <span>{isRetrying ? "Retrying..." : "Try Again"}</span>
        </button>
      </div>
    </div>
  );
};
