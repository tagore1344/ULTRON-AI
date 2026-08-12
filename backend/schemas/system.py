# backend/schemas/system.py
from pydantic import BaseModel, Field


class CpuMetric(BaseModel):
    usage_percent: float = Field(..., description="CPU utilization percentage.")


class MemoryMetric(BaseModel):
    usage_percent: float = Field(..., description="Memory utilization percentage.")
    used_mb: int = Field(..., description="Currently used RAM in MB.")
    total_mb: int = Field(..., description="Total available RAM in MB.")


class DiskMetric(BaseModel):
    usage_percent: float = Field(..., description="Disk storage space utilization percentage.")


class BatteryMetric(BaseModel):
    available: bool = Field(..., description="Is battery hardware present on the system host?")
    percent: int = Field(..., description="Current battery charge percentage.")
    power_plugged: bool = Field(..., description="Is charger plugged into the system host?")


class GpuMetric(BaseModel):
    available: bool = Field(..., description="Is an Nvidia GPU detected on the host?")
    name: str = Field(..., description="Model name of the GPU device.")
    usage_percent: int = Field(..., description="GPU core utilization percentage.")


class OsMetric(BaseModel):
    name: str = Field(..., description="Name of the operating system (e.g. Windows, Linux).")
    version: str = Field(..., description="Release version of the operating system.")
    hostname: str = Field(..., description="Hostname of the host laptop.")


class SystemStatusResponse(BaseModel):
    """Pydantic schema validating unified system metrics responses."""

    cpu: CpuMetric
    memory: MemoryMetric
    disk: DiskMetric
    battery: BatteryMetric
    gpu: GpuMetric
    os: OsMetric
