from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FuelHHRecord(BaseModel):
    """
    Normalized representation of an Elexon BMRS FUELHH outturn record.

    Units:
    - generation: Megawatts (MW), representing the average power over the 30-minute settlement period.
    - settlement_period: 1 to 50 (standard days have 48; clock change days have 46 or 50).
    """

    model_config = ConfigDict(populate_by_name=True)

    dataset: str = "FUELHH"
    publish_time: datetime = Field(..., alias="publishTime", description="Publication timestamp in UTC")
    start_time: datetime = Field(..., alias="startTime", description="Settlement interval start in UTC")
    settlement_date: str = Field(..., alias="settlementDate", description="Settlement date in YYYY-MM-DD")
    settlement_period: int = Field(..., alias="settlementPeriod", ge=1, le=50, description="Settlement period (1-50)")
    fuel_type: str = Field(..., alias="fuelType", description="Fuel type category (e.g. WIND)")
    generation: float = Field(..., alias="generation", ge=0.0, description="Generation outturn in MW")

    @property
    def deduplication_key(self) -> tuple[str, int]:
        """Unique identifier for a half-hour settlement interval."""
        return (self.settlement_date, self.settlement_period)


class WindforRecord(BaseModel):
    """
    Normalized representation of an Elexon BMRS WINDFOR forecast record.

    Units:
    - generation: Megawatts (MW), forecasted wind generation for the specified delivery start time.
    """

    model_config = ConfigDict(populate_by_name=True)

    dataset: str = "WINDFOR"
    publish_time: datetime = Field(..., alias="publishTime", description="Forecast publication timestamp in UTC")
    start_time: datetime = Field(..., alias="startTime", description="Delivery interval start in UTC")
    generation: float = Field(..., alias="generation", ge=0.0, description="Forecasted generation in MW")

    @property
    def deduplication_key(self) -> tuple[datetime, datetime]:
        """Unique composite key: (publish_time, start_time)."""
        return (self.publish_time, self.start_time)


class IngestionAudit(BaseModel):
    """Audit log capturing counts of received, retained, and excluded records."""

    dataset: str
    chunks_requested: int = 0
    raw_records_received: int = 0
    records_retained: int = 0
    duplicate_records_excluded: int = 0
    non_wind_records_excluded: int = 0
    malformed_records_excluded: int = 0
    exclusion_notes: List[str] = Field(default_factory=list)


class FuelHHIngestionResult(BaseModel):
    """Result container for FUELHH ingestion."""

    records: List[FuelHHRecord]
    audit: IngestionAudit


class WindforIngestionResult(BaseModel):
    """Result container for WINDFOR ingestion."""

    records: List[WindforRecord]
    audit: IngestionAudit
