import hashlib
import json
import logging
import os
import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
from pydantic import ValidationError

from backend.app.schemas.elexon import (
    FuelHHIngestionResult,
    FuelHHRecord,
    IngestionAudit,
    WindforIngestionResult,
    WindforRecord,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
MAX_CHUNK_DAYS = 7


class ElexonClientError(Exception):
    """Base exception for Elexon client errors."""
    pass


class ElexonAPIError(ElexonClientError):
    """Exception raised when Elexon API returns an error response."""
    def __init__(self, status_code: int, message: str, url: str):
        super().__init__(f"Elexon API error {status_code} at {url}: {message}")
        self.status_code = status_code
        self.url = url


def parse_date(d: Union[str, date]) -> date:
    """Safely parse date input into a datetime.date object."""
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    return datetime.strptime(d, "%Y-%m-%d").date()


def parse_datetime_utc(dt: Union[str, datetime]) -> datetime:
    """Safely parse datetime input into a UTC datetime object."""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    # Parse ISO string
    clean_str = dt.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(clean_str)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def generate_fuelhh_date_chunks(
    start_date: Union[str, date],
    end_date: Union[str, date],
    max_days: int = MAX_CHUNK_DAYS,
) -> List[Tuple[date, date]]:
    """
    Generate non-overlapping date chunks covering [start_date, end_date] inclusive.
    Each chunk contains at most max_days inclusive (default 7 days).
    Guarantees:
    - Zero gaps between chunks.
    - Zero overlapping dates between chunks.
    - Every date in the requested range is present in exactly one chunk.
    """
    s = parse_date(start_date)
    e = parse_date(end_date)
    if s > e:
        raise ValueError(f"start_date ({s}) cannot be after end_date ({e})")
    if max_days < 1:
        raise ValueError("max_days must be >= 1")

    chunks: List[Tuple[date, date]] = []
    current_start = s
    while current_start <= e:
        # Inclusive range: chunk_start to chunk_end has (chunk_end - chunk_start).days + 1 days
        chunk_end = min(current_start + timedelta(days=max_days - 1), e)
        chunks.append((current_start, chunk_end))
        current_start = chunk_end + timedelta(days=1)

    return chunks


def generate_windfor_date_chunks(
    start_dt: Union[str, datetime],
    end_dt: Union[str, datetime],
    max_days: int = MAX_CHUNK_DAYS,
) -> List[Tuple[datetime, datetime]]:
    """
    Generate non-overlapping UTC datetime chunks for WINDFOR publication filtering.
    Elexon requires that PublishDateTimeFrom and PublishDateTimeTo inclusive
    do not span more than 7 calendar days.
    """
    s = parse_datetime_utc(start_dt)
    e = parse_datetime_utc(end_dt)
    if s > e:
        raise ValueError(f"start_dt ({s}) cannot be after end_dt ({e})")
    if max_days < 1:
        raise ValueError("max_days must be >= 1")

    chunks: List[Tuple[datetime, datetime]] = []
    # Work on calendar date boundaries to strictly satisfy the 7 calendar days inclusive limit
    curr_date = s.date()
    end_date = e.date()

    while curr_date <= end_date:
        chunk_end_date = min(curr_date + timedelta(days=max_days - 1), end_date)
        
        # Start time of chunk: s time if on first day, else 00:00:00Z
        chunk_start = s if curr_date == s.date() else datetime.combine(curr_date, dt_time.min, tzinfo=timezone.utc)
        # End time of chunk: e time if on last day, else 23:59:59Z
        chunk_end = e if chunk_end_date == end_date else datetime.combine(chunk_end_date, dt_time(23, 59, 59), tzinfo=timezone.utc)
        
        chunks.append((chunk_start, chunk_end))
        curr_date = chunk_end_date + timedelta(days=1)

    return chunks


class ElexonClient:
    """
    Robust HTTP client for the Elexon BMRS Insights API.
    Handles:
    - 7-day query chunking.
    - Automatic retries with exponential backoff for transient failures.
    - Strict response validation using Pydantic schemas.
    - Deterministic, auditable deduplication and revision tracking.
    - Optional safe file caching (disabled by default).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 25.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        use_cache: bool = False,
        cache_dir: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.use_cache = use_cache
        self.cache_dir = Path(cache_dir or "backend/.cache")
        self._transport = transport

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self._transport,
        )

    def _make_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Create a deterministic hash key for cached queries."""
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        raw = f"{endpoint}::{sorted_params}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _read_cache(self, key: str) -> Optional[List[Dict[str, Any]]]:
        if not self.use_cache:
            return None
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception as ex:
            logger.warning(f"Failed to read cache file {cache_file}: {ex}")
        return None

    def _write_cache(self, key: str, data: List[Dict[str, Any]]) -> None:
        if not self.use_cache:
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / f"{key}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as ex:
            logger.warning(f"Failed to write cache file {key}: {ex}")

    def _request_with_retries(self, endpoint: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute GET request with exponential backoff on transient errors (429, 5xx, timeouts).
        """
        cache_key = self._make_cache_key(endpoint, params)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        last_exception: Optional[Exception] = None

        with self._get_client() as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = client.get(endpoint, params=params)
                    # Transient server or rate limit error
                    if response.status_code in (429, 500, 502, 503, 504):
                        if attempt < self.max_retries:
                            sleep_time = self.retry_delay * (2 ** attempt)
                            time.sleep(sleep_time)
                            continue
                        raise ElexonAPIError(response.status_code, response.text, url)

                    if response.status_code != 200:
                        raise ElexonAPIError(response.status_code, response.text, url)

                    payload = response.json()
                    data = payload.get("data", [])
                    if not isinstance(data, list):
                        raise ElexonClientError(f"Unexpected API response format: 'data' is not a list at {url}")

                    self._write_cache(cache_key, data)
                    return data

                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as net_err:
                    last_exception = net_err
                    if attempt < self.max_retries:
                        sleep_time = self.retry_delay * (2 ** attempt)
                        time.sleep(sleep_time)
                        continue
                    raise ElexonClientError(f"Network error accessing {url} after {self.max_retries} retries: {net_err}") from net_err

        if last_exception:
            raise last_exception
        raise ElexonClientError(f"Failed to fetch data from {url}")

    def fetch_fuelhh(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        fuel_type: str = "WIND",
    ) -> FuelHHIngestionResult:
        """
        Fetch FUELHH actual outturn data, chunking requests to <= 7 days inclusive.
        Applies:
        - Filtering to fuel_type == WIND (both API query and in-code filter).
        - Deterministic deduplication on (settlementDate, settlementPeriod).
        - Revision retention: when duplicates exist, the record with the latest publishTime is kept.
        - Comprehensive audit counting of received, duplicate, and excluded records.
        """
        chunks = generate_fuelhh_date_chunks(start_date, end_date)
        audit = IngestionAudit(dataset="FUELHH", chunks_requested=len(chunks))

        # Map key (settlement_date, settlement_period) -> FuelHHRecord
        retained_records: Dict[Tuple[str, int], FuelHHRecord] = {}

        for chunk_start, chunk_end in chunks:
            params = {
                "settlementDateFrom": chunk_start.isoformat(),
                "settlementDateTo": chunk_end.isoformat(),
                "fuelType": fuel_type,
                "format": "json",
            }
            raw_items = self._request_with_retries("/datasets/FUELHH", params)
            audit.raw_records_received += len(raw_items)

            for item in raw_items:
                # 1. Defensive fuel type filter
                raw_fuel = item.get("fuelType")
                if raw_fuel != fuel_type:
                    audit.non_wind_records_excluded += 1
                    continue

                # 2. Schema validation
                try:
                    record = FuelHHRecord.model_validate(item)
                except (ValidationError, TypeError, ValueError) as err:
                    audit.malformed_records_excluded += 1
                    if len(audit.exclusion_notes) < 10:
                        audit.exclusion_notes.append(f"Malformed FUELHH record: {err}")
                    continue

                # 3. Deduplication / revision resolution
                key = record.deduplication_key
                if key in retained_records:
                    existing = retained_records[key]
                    audit.duplicate_records_excluded += 1
                    # Keep revision with the latest publish_time
                    if record.publish_time > existing.publish_time:
                        retained_records[key] = record
                else:
                    retained_records[key] = record

        sorted_records = sorted(
            retained_records.values(),
            key=lambda r: (r.settlement_date, r.settlement_period),
        )
        audit.records_retained = len(sorted_records)

        return FuelHHIngestionResult(records=sorted_records, audit=audit)

    def fetch_windfor(
        self,
        publish_from: Union[str, datetime],
        publish_to: Union[str, datetime],
    ) -> WindforIngestionResult:
        """
        Fetch WINDFOR wind forecasts, chunking requests to <= 7 calendar days inclusive.
        Preserves publishTime, startTime, and generation.
        Applies:
        - Deterministic deduplication on (publishTime, startTime).
        - Audit tracking of received, retained, and duplicate records.
        """
        chunks = generate_windfor_date_chunks(publish_from, publish_to)
        audit = IngestionAudit(dataset="WINDFOR", chunks_requested=len(chunks))

        # Map key (publish_time, start_time) -> WindforRecord
        retained_records: Dict[Tuple[datetime, datetime], WindforRecord] = {}

        for chunk_start, chunk_end in chunks:
            # Elexon requires ISO format with Z or timezone
            params = {
                "publishDateTimeFrom": chunk_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "publishDateTimeTo": chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "format": "json",
            }
            raw_items = self._request_with_retries("/datasets/WINDFOR", params)
            audit.raw_records_received += len(raw_items)

            for item in raw_items:
                # Schema validation
                try:
                    record = WindforRecord.model_validate(item)
                except (ValidationError, TypeError, ValueError) as err:
                    audit.malformed_records_excluded += 1
                    if len(audit.exclusion_notes) < 10:
                        audit.exclusion_notes.append(f"Malformed WINDFOR record: {err}")
                    continue

                # Deduplication on (publishTime, startTime)
                key = record.deduplication_key
                if key in retained_records:
                    audit.duplicate_records_excluded += 1
                else:
                    retained_records[key] = record

        sorted_records = sorted(
            retained_records.values(),
            key=lambda r: (r.start_time, r.publish_time),
        )
        audit.records_retained = len(sorted_records)

        return WindforIngestionResult(records=sorted_records, audit=audit)

    def fetch_january_2026_actuals(self) -> FuelHHIngestionResult:
        """Fetch all FUELHH wind generation actuals for the complete month of January 2026."""
        return self.fetch_fuelhh(start_date="2026-01-01", end_date="2026-01-31", fuel_type="WIND")

    def fetch_january_2026_forecasts(self, lookback_days: int = 1) -> WindforIngestionResult:
        """
        Fetch all WINDFOR forecasts published to cover January 2026.
        By default, lookback_days=1 fetches starting from 2025-12-31T00:00:00Z to ensure
        day-ahead forecasts for January 1, 2026 are included.
        """
        start_date = date(2026, 1, 1) - timedelta(days=lookback_days)
        publish_from = datetime.combine(start_date, dt_time.min, tzinfo=timezone.utc)
        publish_to = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        return self.fetch_windfor(publish_from=publish_from, publish_to=publish_to)
