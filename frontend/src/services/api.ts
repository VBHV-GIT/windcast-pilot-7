import {
  EvaluationQueryParams,
  EvaluationSummaryResponse,
  ExclusionsResponse,
  HealthResponse,
  TimeSeriesResponse,
} from "../types/evaluation";

export class ApiError extends Error {
  statusCode: number;
  details?: string;

  constructor(statusCode: number, message: string, details?: string) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.details = details;
  }
}

function buildQuery(params: EvaluationQueryParams): string {
  const query = new URLSearchParams({
    start_date: params.startDate,
    end_date: params.endDate,
    cutoff_time: params.cutoffTime,
    alignment: params.alignment,
    use_cache: String(params.useCache),
  });
  return query.toString();
}

async function request<T>(endpoint: string): Promise<T> {
  const response = await fetch(endpoint, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Keep default response.statusText
    }

    throw new ApiError(
      response.status,
      `API request failed with status ${response.status}`,
      errorDetail
    );
  }

  return response.json() as Promise<T>;
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export async function fetchEvaluationSummary(
  params: EvaluationQueryParams
): Promise<EvaluationSummaryResponse> {
  return request<EvaluationSummaryResponse>(`/api/evaluation/summary?${buildQuery(params)}`);
}

export async function fetchEvaluationTimeseries(
  params: EvaluationQueryParams
): Promise<TimeSeriesResponse> {
  return request<TimeSeriesResponse>(`/api/evaluation/timeseries?${buildQuery(params)}`);
}

export async function fetchEvaluationExclusions(
  params: EvaluationQueryParams
): Promise<ExclusionsResponse> {
  return request<ExclusionsResponse>(`/api/evaluation/exclusions?${buildQuery(params)}`);
}
